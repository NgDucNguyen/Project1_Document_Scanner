"""Các lỗi thực tế cần ngăn khi chạy nhiều ảnh: lật gương, góc sai, lẫn test."""
from pathlib import Path
import json
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import cv2
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src/document_scanner/scanner"))
from detect import detect_document, order_points, polygon_iou
from geometry import build_scan, validate_corners
from evaluate import score_results
import evaluate
import manual_scan
import scan


class ScannerTests(unittest.TestCase):
    def setUp(self):
        self.image = np.zeros((80, 120, 3), np.uint8)
        self.corners = np.array([[10, 10], [100, 10], [100, 60], [10, 60]], np.float32)
        # Bốn màu phân biệt để phát hiện xoay/lật không đúng.
        for point, color in zip(self.corners, [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255)]):
            cv2.circle(self.image, tuple(point.astype(int)), 4, color, -1)

    def test_corner_colors_and_matrices_after_rotation(self):
        base, _, _ = build_scan(self.image, self.corners)
        for rotation in range(4):
            scanned, h, t = build_scan(self.image, self.corners, rotation)
            expected = np.rot90(base, -rotation)
            np.testing.assert_array_equal(scanned, expected)
            projected = cv2.perspectiveTransform(self.corners.reshape(1, 4, 2), t)[0]
            height, width = scanned.shape[:2]
            target = np.array([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]])
            np.testing.assert_allclose(projected, np.roll(target, -rotation, axis=0), atol=0.001)
            if rotation == 0:
                np.testing.assert_allclose(h, t)

    def test_reverse_click_order_is_normalized_before_warp(self):
        normal = order_points(self.corners)
        reversed_clicks = order_points(self.corners[[0, 3, 2, 1]])
        np.testing.assert_array_equal(normal, reversed_clicks)
        validate_corners(self.image, reversed_clicks)

    def test_invalid_quadrilaterals_rejected(self):
        cases = [
            [[10, 10], [10, 10], [100, 60], [10, 60]],
            self.corners[[0, 2, 1, 3]], self.corners[[0, 3, 2, 1]],
            [[-1, 10], [100, 10], [100, 60], [10, 60]],
            [[10, 10], [120, 10], [100, 60], [10, 60]],
            [[10, 10], [20, 10], [30, 10], [40, 10]],
            [[float("nan"), 10], [100, 10], [100, 60], [10, 60]],
        ]
        for points in cases:
            with self.subTest(points=points), self.assertRaises(ValueError):
                build_scan(self.image, points)

    def test_blank_and_invalid_images(self):
        for value in (0, 255):
            result = detect_document(np.full((100, 150, 3), value, np.uint8))
            self.assertEqual(result["status"], "no_candidate")
            self.assertIsNone(result["corners"])
        self.assertEqual(detect_document(None)["status"], "invalid_input")

    def test_iou_known_overlap(self):
        first = [[0, 0], [10, 0], [10, 10], [0, 10]]
        second = [[5, 0], [15, 0], [15, 10], [5, 10]]
        self.assertAlmostEqual(polygon_iou(first, second), 1 / 3)

    def test_scoring_keeps_failures_and_excludes_test(self):
        rows, labels = [], []
        for split, detected in [("val", True), ("val", False), ("test", True)]:
            path = str(len(rows)) + ".jpg"
            row = dict(image_path=path, split=split, detected=detected, scan_created=detected)
            label = dict(image_path=path, split=split)
            for i, corner in enumerate(("tl", "tr", "br", "bl")):
                for j, axis in enumerate(("x", "y")):
                    row["pred_" + str(i) + "_" + axis] = self.corners[i, j]
                    label[corner + "_" + axis] = self.corners[i, j]
            rows.append(row)
            labels.append(label)
        report = score_results(pd.DataFrame(rows), pd.DataFrame(labels))
        self.assertEqual(len(report), 2)
        self.assertEqual(report["passed"].sum(), 1)
        self.assertEqual(report["iou"].tolist(), [1.0, 0.0])

    def test_automatic_storage_and_evaluation_paths(self):
        # Dùng ảnh nhỏ để kiểm tra việc lưu; không chạy lại bộ dữ liệu.
        workspace = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(dir=workspace, prefix="test_storage_") as temporary:
            root = Path(temporary)
            raw = root / "raw"
            raw.mkdir()
            cv2.imwrite(str(raw / "page.png"), self.image)
            run = root / "artifacts/batch/run1"
            processed = root / "data/processed/scan"
            row = SimpleNamespace(image_path="page.png", split="val", model_name="page", bg_name="bg")
            detection = dict(status="ok", method="fixture", score=1, blur_score=100,
                             score_gap=1, candidate_count=1, warnings=[], corners=self.corners)
            with patch.multiple(scan, PROJECT_ROOT=root, SMARTDOC_ROOT=raw, PROCESSED_ROOT=processed), \
                    patch.object(scan, "detect_document", return_value=detection):
                result = scan.scan_one(row, run)
            self.assertTrue(result["scan_created"])
            output = root / result["scan_path"]
            self.assertEqual(output, processed / "run1/val/page.png")
            self.assertIsNotNone(cv2.imread(str(output)))
            metadata = json.loads((run / result["metadata_path"]).read_text(encoding="utf-8"))
            self.assertEqual(metadata["scan_path"], result["scan_path"])
            self.assertEqual(list(run.rglob("*.png")), [])
            with patch.object(evaluate, "PROJECT_ROOT", root):
                self.assertEqual(evaluate.resolve_scan_path(SimpleNamespace(**result), run), output)
                old = SimpleNamespace(scan_path="outputs/val/page.png")
                self.assertEqual(evaluate.resolve_scan_path(old, run), run / old.scan_path)
            # Ảnh không có khung vẫn có JSON, nhưng không sinh PNG giả.
            detection.update(status="no_candidate", corners=None)
            row.image_path = "blank.png"
            cv2.imwrite(str(raw / row.image_path), self.image)
            with patch.multiple(scan, PROJECT_ROOT=root, SMARTDOC_ROOT=raw, PROCESSED_ROOT=processed), \
                    patch.object(scan, "detect_document", return_value=detection):
                failed = scan.scan_one(row, run)
            self.assertFalse(failed["scan_created"])
            self.assertEqual(failed["scan_path"], "")
            self.assertTrue((run / failed["metadata_path"]).is_file())

    def test_manual_storage(self):
        workspace = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(dir=workspace, prefix="test_storage_") as temporary:
            root = Path(temporary)
            artifacts = root / "artifacts/manual"
            processed = root / "data/processed/manual"
            with patch.multiple(manual_scan, PROJECT_ROOT=root, OUTPUT_ROOT=artifacts,
                                PROCESSED_ROOT=processed):
                output = manual_scan.save_manual_result("example", self.image, {"manual_corrected": True})
            np.testing.assert_array_equal(cv2.imread(str(output)), self.image)
            metadata = json.loads((artifacts / "example/corners.json").read_text(encoding="utf-8"))
            self.assertEqual(root / metadata["scan_path"], output)
            self.assertEqual(metadata["scan_path_base"], "project")
            self.assertEqual(list(artifacts.rglob("*.png")), [])


if __name__ == "__main__":
    unittest.main()
