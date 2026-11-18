"""Các rủi ro của tăng cường ảnh: nhận ảnh trắng, mờ nặng và mất nét màu."""
from pathlib import Path
from contextlib import redirect_stdout
import io
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src/document_scanner"))
from scanner.appearance import assess_document, enhance_document
from scanner import scan_image
from scanner.content_scan import refine_content_perspective


def text_page():
    image = np.full((600, 500, 3), 220, np.uint8)
    for y in range(60, 560, 40):
        cv2.putText(image, "Document text 123", (30, y), cv2.FONT_HERSHEY_SIMPLEX,
                    .7, (130, 70, 40), 2, cv2.LINE_AA)
    return image


class ScanAppearanceTests(unittest.TestCase):
    def test_blank_page_is_not_a_text_document(self):
        result = assess_document(np.full((400, 500, 3), 255, np.uint8))
        self.assertFalse(result["accepted"])
        self.assertIn("insufficient_text_evidence", result["reasons"])

    def test_readable_text_page_passes_and_heavy_blur_does_not(self):
        page = text_page()
        self.assertTrue(assess_document(page)["accepted"])
        result = assess_document(cv2.GaussianBlur(page, (0, 0), 12))
        self.assertFalse(result["accepted"])
        self.assertIn("severely_blurred_or_low_detail", result["reasons"])

    def test_dark_flat_background_is_rejected(self):
        result = assess_document(np.full((400, 500, 3), (30, 55, 80), np.uint8))
        self.assertFalse(result["accepted"])
        self.assertIn("insufficient_light_paper", result["reasons"])

    def test_enhancement_preserves_size_dark_strokes_and_blue_direction(self):
        page = text_page()
        improved, info = enhance_document(page)
        self.assertEqual(improved.shape, page.shape)
        self.assertEqual(improved.dtype, np.uint8)
        ink = page[:, :, 2] < 100
        self.assertGreater(np.count_nonzero(ink), 100)
        self.assertLess(float(cv2.cvtColor(improved, cv2.COLOR_BGR2GRAY)[ink].mean()), 200)
        self.assertGreater(float(improved[:, :, 0][ink].mean()), float(improved[:, :, 2][ink].mean()))
        self.assertGreater(float(improved[580:590].mean()), float(page[580:590].mean()))
        self.assertTrue(info["applied"])

    def test_rejected_quality_cannot_be_turned_into_success_by_enhancement(self):
        page = np.full((400, 500, 3), 255, np.uint8)
        corners = np.float32([[0, 0], [499, 0], [499, 399], [0, 399]])
        detection = {"corners": corners, "status": "uncertain", "warnings": []}
        with patch.object(scan_image, "detect_document", return_value=detection), \
                patch.object(scan_image, "crop_content", return_value=None), \
                patch.object(scan_image, "enhance_document") as enhance:
            with self.assertRaises(scan_image.ScanRejected) as context:
                scan_image.scan_document(page)
        enhance.assert_not_called()
        self.assertEqual(context.exception.info["scanner_status"], "rejected_quality")
        self.assertFalse(context.exception.info["quality"]["accepted"])

    def test_content_paper_quad_reduces_perspective_slope(self):
        page = text_page()
        source = np.float32([[0, 0], [499, 0], [499, 599], [0, 599]])
        target = np.float32([[80, 35], [500, 115], [560, 700], [40, 710]])
        matrix = cv2.getPerspectiveTransform(source, target)
        photo = cv2.warpPerspective(page, matrix, (650, 750), borderValue=(40, 45, 50))
        words = []
        for y in (180, 260, 340):
            box = np.float32([[[50, y], [200, y], [200, y + 25], [50, y + 25]]])
            projected = cv2.perspectiveTransform(box, matrix)[0]
            words.append({"text": "Document", "confidence": 90,
                          "box": [int(projected[:, 0].min()), int(projected[:, 1].min()),
                                  int(projected[:, 0].max()), int(projected[:, 1].max())]})
        refined = refine_content_perspective(photo, words)
        self.assertIsNotNone(refined)
        result, correction, info = refined
        baseline = np.float32([[[50, 250], [400, 250]]])
        before = cv2.perspectiveTransform(baseline, matrix)[0]
        after = cv2.perspectiveTransform(baseline, correction @ matrix)[0]
        before_slope = abs((before[1, 1] - before[0, 1]) / (before[1, 0] - before[0, 0]))
        after_slope = abs((after[1, 1] - after[0, 1]) / (after[1, 0] - after[0, 0]))
        self.assertLess(after_slope, before_slope / 2)
        self.assertGreaterEqual(info["min_word_area_retained"], .98)

    def test_content_refinement_skips_already_rectangular_page(self):
        page = text_page()
        words = [{"text": "word", "confidence": 90, "box": [50, y, 100, y + 20]}
                 for y in (100, 200, 300)]
        self.assertIsNone(refine_content_perspective(page, words))

    def test_cleanup_keeps_faint_line_and_small_punctuation(self):
        page = text_page()
        cv2.line(page, (50, 570), (180, 570), (210, 210, 210), 1)
        cv2.circle(page, (230, 570), 1, (150, 150, 150), -1)
        output, _ = enhance_document(page)
        gray = cv2.cvtColor(output, cv2.COLOR_BGR2GRAY)
        self.assertLess(float(gray[570, 70:160].mean()), 250)
        self.assertLess(int(gray[570, 230]), 220)


class ScanOutputTests(unittest.TestCase):
    def setUp(self):
        workspace = Path(__file__).resolve().parents[1]
        self.temporary = tempfile.TemporaryDirectory(dir=workspace, prefix="test_scan_output_")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "photo.png"
        self.image = text_page()
        cv2.imwrite(str(self.source), self.image)
        model = self.root / "models/docaligner/fastvit_t8.onnx"
        model.parent.mkdir(parents=True)
        model.write_bytes(b"fixture; detector is mocked")

    def run_cli(self, rejected=False):
        info = {"scanner_status": "ok", "T_source_to_output": np.eye(3).tolist(),
                "enhancement": {"applied": False}}
        args = ["scan_image.py", "--image", str(self.source)]
        with patch.object(scan_image, "PROJECT_ROOT", self.root), \
                patch.object(sys, "argv", args), \
                patch.object(scan_image, "scan_document") as scan, redirect_stdout(io.StringIO()):
            if rejected:
                scan.side_effect = scan_image.ScanRejected("rejected", {"scanner_status": "rejected_quality"})
                with self.assertRaises(SystemExit) as error:
                    scan_image.main()
                self.assertEqual(error.exception.code, 1)
            else:
                scan.return_value = (self.image, info)
                scan_image.main()

    def test_repeated_command_updates_same_folder_without_deleting_notes(self):
        self.run_cli()
        folder = next((self.root / "data/processed/scan").iterdir())
        (folder / "notes.txt").write_text("user notes", encoding="utf-8")
        self.run_cli()
        self.assertEqual(len(list((self.root / "data/processed/scan").iterdir())), 1)
        self.assertEqual(len(list((self.root / "artifacts/scans").iterdir())), 1)
        self.assertTrue((folder / "scan.png").is_file())
        self.assertEqual((folder / "notes.txt").read_text(encoding="utf-8"), "user notes")

    def test_failed_repeat_removes_stale_success_image(self):
        self.run_cli()
        self.run_cli(rejected=True)
        folder = next((self.root / "data/processed/scan").iterdir())
        self.assertFalse((folder / "scan.png").exists())
        metadata_file = next((self.root / "artifacts/scans").glob("*/metadata.json"))
        result = json.loads(metadata_file.read_text(encoding="utf-8"))["results"]["docaligner"]
        self.assertEqual(result["scanner_status"], "rejected_quality")
        self.assertIsNone(result["scan_path"])

    def test_same_filename_in_different_locations_has_separate_output(self):
        other = self.root / "other" / self.source.name
        self.assertNotEqual(scan_image.output_key(self.source), scan_image.output_key(other))


if __name__ == "__main__":
    unittest.main()
