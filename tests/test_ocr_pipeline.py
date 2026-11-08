"""Kiểm tra cách nối scanner với OCR cho ảnh chụp và ảnh đã nắn."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import cv2
import numpy as np


WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src" / "document_scanner"))
import pipeline


class OcrPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=WORKSPACE, prefix="test_ocr_")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.image_path = self.root / "input.png"
        self.image = np.full((40, 60, 3), 255, np.uint8)
        self.assertTrue(cv2.imwrite(str(self.image_path), self.image))

    def test_scanned_input_skips_detector_and_records_configuration(self):
        with patch.object(pipeline, "OUTPUT_ROOT", self.root / "output"), \
                patch.object(pipeline, "detect_document") as detect, \
                patch.object(pipeline, "recognize_image", return_value="Hello") as recognize:
            result = pipeline.process_image(self.image_path, "eng", input_type="scan", psm=6)
        self.assertEqual(result, "Hello")
        detect.assert_not_called()
        self.assertEqual(recognize.call_args.kwargs["psm"], 6)
        output = next((self.root / "output").iterdir())
        metadata = json.loads((output / "metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["input_type"], "scan")
        self.assertEqual(metadata["scanner_status"], "already_scanned")
        self.assertEqual(metadata["psm"], 6)
        self.assertEqual((output / "text.txt").read_text(encoding="utf-8"), "Hello")
        np.testing.assert_array_equal(cv2.imread(str(output / "scan.png")), self.image)

    def test_photo_runs_detector_and_warp_before_ocr(self):
        corners = np.array([[5, 5], [55, 5], [55, 35], [5, 35]], np.float32)
        detection = {"status": "ok", "corners": corners, "warnings": []}
        matrix = np.eye(3)
        with patch.object(pipeline, "OUTPUT_ROOT", self.root / "output"), \
                patch.object(pipeline, "detect_document", return_value=detection) as detect, \
                patch.object(pipeline, "build_scan", return_value=(self.image, matrix, matrix)) as warp, \
                patch.object(pipeline, "recognize_image", return_value="Hello"):
            result = pipeline.process_image(self.image_path, "eng")
        self.assertEqual(result, "Hello")
        detect.assert_called_once()
        warp.assert_called_once()
        output = next((self.root / "output").iterdir())
        metadata = json.loads((output / "metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["input_type"], "photo")
        self.assertEqual(metadata["corners_original"], corners.tolist())
        self.assertEqual(metadata["H_source_to_warp"], matrix.tolist())

    def test_custom_model_directory_reaches_ocr_and_metadata(self):
        model_dir = self.root / "models"
        model_dir.mkdir()
        with patch.object(pipeline, "OUTPUT_ROOT", self.root / "output"), \
                patch.object(pipeline, "recognize_image", return_value="Hello") as recognize:
            pipeline.process_image(self.image_path, "funsd_eng", input_type="scan", tessdata_dir=model_dir)
        self.assertEqual(recognize.call_args.kwargs["tessdata_dir"], model_dir)
        self.assertEqual(recognize.call_args.args[1], "funsd_eng")
        output = next((self.root / "output").iterdir())
        metadata = json.loads((output / "metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["tessdata_dir"], str(model_dir.resolve()))

    def test_auto_selects_local_model_and_standard_can_be_forced(self):
        model_dir = self.root / "models"
        model_dir.mkdir()
        (model_dir / "funsd_eng.traineddata").touch()
        self.assertEqual(pipeline.choose_ocr_model("eng", None, "auto", model_dir), ("funsd_eng", model_dir))
        self.assertEqual(pipeline.choose_ocr_model("eng", None, "standard", model_dir), ("eng", None))
        self.assertEqual(pipeline.choose_ocr_model("vie", None, "auto", model_dir), ("vie", None))
        (model_dir / "funsd_eng.traineddata").unlink()
        self.assertEqual(pipeline.choose_ocr_model("eng", None, "auto", model_dir), ("eng", None))
        with self.assertRaises(ValueError):
            pipeline.choose_ocr_model("eng", None, "funsd", model_dir)

    def test_missing_corners_stops_before_ocr(self):
        detection = {"status": "no_candidate", "corners": None, "warnings": []}
        with patch.object(pipeline, "OUTPUT_ROOT", self.root / "output"), \
                patch.object(pipeline, "detect_document", return_value=detection), \
                patch.object(pipeline, "recognize_image") as recognize:
            with self.assertRaisesRegex(ValueError, "Không tìm được khung"):
                pipeline.process_image(self.image_path, "eng")
        recognize.assert_not_called()
        self.assertFalse((self.root / "output").exists())


if __name__ == "__main__":
    unittest.main()
