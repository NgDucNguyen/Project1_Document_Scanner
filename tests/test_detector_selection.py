"""Kiểm tra chuyển phương pháp và không dùng nhãn test khi chạy toàn bộ."""
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src/document_scanner/scanner"))
import detect
import docaligner
import benchmark_detection


class DetectorSelectionTests(unittest.TestCase):
    def test_classic_is_explicitly_selectable_without_model(self):
        with patch.object(detect, "detect_classic", return_value={"method": "classic"}) as classic:
            result = detect.detect_document(None, method="classic")
        self.assertEqual(result["method"], "classic")
        classic.assert_called_once()

    def test_configured_default_dispatches_to_docaligner(self):
        with patch.dict(detect.CONFIG, {"default_method": "docaligner"}), \
                patch.object(docaligner, "detect_document", return_value={"method": "docaligner"}) as model:
            self.assertEqual(detect.detect_document(None)["method"], "docaligner")
        model.assert_called_once()

    def test_invalid_method_is_not_silently_replaced(self):
        with self.assertRaises(ValueError):
            detect.detect_document(None, method="unknown")

    def test_full_detection_does_not_require_any_test_corner_labels(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            cv2.imwrite(str(path / "page.png"), np.full((50, 70, 3), 255, np.uint8))
            row = SimpleNamespace(image_path="page.png", split="test", bg_name="bg", model_name="doc")
            result = dict(corners=None, status="no_candidate", method="fixture", score=None,
                          candidate_count=0, warnings=[])
            with patch.object(benchmark_detection, "RAW", path), \
                    patch.object(benchmark_detection, "detect_document", return_value=result):
                measured = benchmark_detection.process_one(row)
            self.assertEqual(measured["error"], "")
            self.assertIsNone(measured["iou"])
            self.assertIsNone(measured["iou_ge_0_9"])


if __name__ == "__main__":
    unittest.main()
