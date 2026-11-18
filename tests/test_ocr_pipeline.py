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
from scanner import content_scan, scan_image


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
                patch.object(scan_image, "detect_document") as detect, \
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
                patch.object(scan_image, "detect_document", return_value=detection) as detect, \
                patch.object(scan_image, "build_scan", return_value=(self.image, matrix, matrix)) as warp, \
                patch.object(scan_image, "page_crop_seems_wrong", return_value=(False, {})), \
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

    def test_auto_requires_local_model_and_standard_can_be_forced(self):
        model_dir = self.root / "models"
        model_dir.mkdir()
        (model_dir / "funsd_eng.traineddata").touch()
        self.assertEqual(pipeline.choose_ocr_model("eng", None, "auto", model_dir), ("funsd_eng", model_dir))
        self.assertEqual(pipeline.choose_ocr_model("eng", None, "standard", model_dir), ("eng", None))
        self.assertEqual(pipeline.choose_ocr_model("vie", None, "auto", model_dir), ("vie", None))
        (model_dir / "funsd_eng.traineddata").unlink()
        with self.assertRaises(ValueError):
            pipeline.choose_ocr_model("eng", None, "auto", model_dir)
        with self.assertRaises(ValueError):
            pipeline.choose_ocr_model("eng", None, "funsd", model_dir)

    def test_funsd_model_uses_one_default_psm_and_records_it(self):
        model_dir = self.root / "models"
        model_dir.mkdir()
        with patch.object(pipeline, "OUTPUT_ROOT", self.root / "output"), \
                patch.object(pipeline, "recognize_image", return_value="Hello") as recognize:
            pipeline.process_image(self.image_path, "funsd_eng", input_type="scan", tessdata_dir=model_dir)
        self.assertEqual(recognize.call_args.kwargs["psm"], 11)
        output = next((self.root / "output").iterdir())
        metadata = json.loads((output / "metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["psm"], 11)

    def test_missing_corners_stops_before_ocr(self):
        detection = {"status": "no_candidate", "corners": None, "warnings": []}
        with patch.object(pipeline, "OUTPUT_ROOT", self.root / "output"), \
                patch.object(scan_image, "detect_document", return_value=detection), \
                patch.object(scan_image, "crop_content", return_value=None), \
                patch.object(pipeline, "recognize_image") as recognize:
            with self.assertRaisesRegex(ValueError, "Không tìm được khung"):
                pipeline.process_image(self.image_path, "eng")
        recognize.assert_not_called()
        self.assertFalse((self.root / "output").exists())

    def test_missing_corners_uses_content_crop_before_ocr(self):
        detection = {"status": "no_candidate", "corners": None, "warnings": []}
        details = {"rotation_degrees": -7.0, "box_in_rotated_image": [2, 2, 40, 30]}
        transform = np.eye(3)
        with patch.object(pipeline, "OUTPUT_ROOT", self.root / "output"), \
                patch.object(scan_image, "detect_document", return_value=detection), \
                patch.object(scan_image, "crop_content", return_value=(self.image, transform, details)) as crop, \
                patch.object(scan_image, "build_scan") as warp, \
                patch.object(pipeline, "recognize_image", return_value="Hello"):
            self.assertEqual(pipeline.process_image(self.image_path, "eng"), "Hello")
        crop.assert_called_once()
        warp.assert_not_called()
        output = next((self.root / "output").iterdir())
        metadata = json.loads((output / "metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["scanner_status"], "content_fallback")
        self.assertEqual(metadata["page_detector_status"], "no_candidate")
        self.assertIn("content_bounds_not_page", metadata["warnings"])
        self.assertIsNone(metadata["corners_original"])
        self.assertIsNone(metadata["H_source_to_warp"])
        self.assertEqual(metadata["content_detection"], details)

    def test_suspect_page_crop_uses_content_fallback(self):
        corners = np.array([[5, 5], [55, 5], [55, 35], [5, 35]], np.float32)
        detection = {"status": "ok", "corners": corners, "warnings": []}
        transform = np.eye(3)
        details = {"rotation_degrees": 0, "box_in_rotated_image": [0, 0, 60, 40]}
        with patch.object(pipeline, "OUTPUT_ROOT", self.root / "output"), \
                patch.object(scan_image, "detect_document", return_value=detection), \
                patch.object(scan_image, "build_scan", return_value=(self.image, transform, transform)), \
                patch.object(scan_image, "page_crop_seems_wrong", return_value=(True, {"scan_reliable_characters": 1})), \
                patch.object(scan_image, "crop_content", return_value=(self.image, transform, details)), \
                patch.object(pipeline, "recognize_image", return_value="Text"):
            pipeline.process_image(self.image_path, "eng")
        output = next((self.root / "output").iterdir())
        metadata = json.loads((output / "metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["scanner_status"], "content_fallback")
        self.assertEqual(metadata["page_detector_status"], "ok")
        self.assertEqual(metadata["rejected_page_corners"], corners.tolist())
        self.assertIsNone(metadata["corners_original"])
        self.assertIn("page_crop_text_mismatch", metadata["warnings"])

    def test_unicode_image_path_and_optional_reference(self):
        image_path = self.root / "ảnh tài liệu.png"
        image_path.write_bytes(self.image_path.read_bytes())
        reference = self.root / "văn bản chuẩn.txt"
        reference.write_text("Hello there\n", encoding="utf-8-sig")
        with patch.object(pipeline, "OUTPUT_ROOT", self.root / "output"), \
                patch.object(pipeline, "recognize_image", return_value="Hello world"):
            pipeline.process_image(image_path, "eng", input_type="scan", reference_path=reference)
        output = next((self.root / "output").iterdir())
        result = json.loads((output / "evaluation.json").read_text(encoding="utf-8"))
        self.assertEqual(result["reference_words"], 2)
        self.assertEqual(result["word_errors"], 1)
        self.assertEqual(result["wer"], 0.5)
        self.assertEqual(result["reference_characters"], 11)
        metadata = json.loads((output / "metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["reference_file"], str(reference.resolve()))

    def test_empty_reference_stops_before_ocr(self):
        reference = self.root / "empty.txt"
        reference.write_text("  \n", encoding="utf-8")
        with patch.object(pipeline, "OUTPUT_ROOT", self.root / "output"), \
                patch.object(pipeline, "recognize_image") as recognize:
            with self.assertRaisesRegex(ValueError, "văn bản chuẩn đang rỗng"):
                pipeline.process_image(self.image_path, "eng", input_type="scan", reference_path=reference)
        recognize.assert_not_called()
        self.assertFalse((self.root / "output").exists())

    def test_content_crop_uses_word_positions_and_real_transform(self):
        image = np.full((300, 400, 3), 255, np.uint8)
        words = [
            {"text": "First", "box": [60, 80, 100, 100], "confidence": 90},
            {"text": "second", "box": [120, 80, 180, 100], "confidence": 90},
            {"text": "third", "box": [60, 120, 100, 140], "confidence": 90},
            {"text": "x", "box": [350, 270, 360, 280], "confidence": 20},
        ]
        with patch.object(content_scan, "estimate_text_angle", return_value=0), \
                patch.object(content_scan, "recognize_word_boxes", return_value=words):
            cropped, transform, details = content_scan.crop_content(image, "eng")
        self.assertEqual(details["box_in_rotated_image"], [45, 65, 195, 155])
        self.assertEqual(details["content_box_area_ratio"], 0.1125)
        self.assertEqual(cropped.shape, (90, 150, 3))
        np.testing.assert_array_equal(transform @ [45, 65, 1], [0, 0, 1])

    def test_broad_content_crop_warns_user_to_review(self):
        detection = {"status": "no_candidate", "corners": None, "warnings": []}
        details = {"rotation_degrees": 0, "content_box_area_ratio": 0.9}
        with patch.object(pipeline, "OUTPUT_ROOT", self.root / "output"), \
                patch.object(scan_image, "detect_document", return_value=detection), \
                patch.object(scan_image, "crop_content", return_value=(self.image, np.eye(3), details)), \
                patch.object(pipeline, "recognize_image", return_value="Text"):
            pipeline.process_image(self.image_path, "eng")
        output = next((self.root / "output").iterdir())
        metadata = json.loads((output / "metadata.json").read_text(encoding="utf-8"))
        self.assertIn("content_frame_broad", metadata["warnings"])
        self.assertTrue(metadata["review_recommended"])

    def test_content_crop_refuses_when_not_enough_words_found(self):
        with patch.object(content_scan, "recognize_word_boxes", return_value=[]):
            self.assertIsNone(content_scan.crop_content(self.image, "eng"))

    def test_content_crop_rejects_rotation_that_loses_words(self):
        image = np.full((300, 400, 3), 255, np.uint8)
        words = [{"text": text, "box": [x, 80, x + 35, 100], "confidence": 90}
                 for x, text in ((50, "one"), (100, "two"), (150, "three"))]
        with patch.object(content_scan, "estimate_text_angle", return_value=8), \
                patch.object(content_scan, "find_text_words", side_effect=[words, []]):
            _, _, details = content_scan.crop_content(image, "eng")
        self.assertEqual(details["rotation_degrees"], 0)
        self.assertEqual(details["proposed_rotation_degrees"], 8)

    def test_page_crop_check_detects_missing_text(self):
        few = [{"text": "Hi", "box": [0, 0, 10, 10], "confidence": 90}]
        many = [{"text": "Reliable", "box": [0, 0, 10, 10], "confidence": 90}] * 6
        with patch.object(content_scan, "find_text_words", side_effect=[few, many]):
            suspect, details = content_scan.page_crop_seems_wrong(self.image, self.image, "eng")
        self.assertTrue(suspect)
        self.assertEqual(details["scan_reliable_characters"], 2)
        self.assertEqual(details["source_reliable_characters"], 48)

    def test_largest_cluster_excludes_separate_surrounding_text(self):
        image = np.full((500, 700, 3), 255, np.uint8)
        main = [{"text": "main", "box": [x, y, x + 40, y + 20], "confidence": 90}
                for y in (100, 140, 180) for x in (300, 360, 420)]
        side = [{"text": "side", "box": [30, y, 70, y + 20], "confidence": 90}
                for y in (250, 290, 330)]
        with patch.object(content_scan, "estimate_text_angle", return_value=0), \
                patch.object(content_scan, "find_text_words", return_value=main + side):
            cropped, transform, details = content_scan.crop_content(image, "eng")
        self.assertEqual(details["box_in_rotated_image"], [285, 85, 475, 215])
        self.assertEqual(len(details["region_selection"]["candidates"]), 2)
        self.assertEqual(details["region_selection"]["selected"]["word_count"], 9)
        self.assertFalse(details["region_selection"]["ambiguous"])
        self.assertEqual(cropped.shape, (130, 190, 3))
        np.testing.assert_array_equal(transform @ [285, 85, 1], [0, 0, 1])

    def test_two_similar_regions_are_flagged_instead_of_merged(self):
        image = np.full((500, 700, 3), 255, np.uint8)
        words = [{"text": "word", "box": [x, y, x + 50, y + 20], "confidence": 90}
                 for x in (60, 500) for y in (100, 140, 180)]
        result = content_scan.select_content_region(image, words)
        self.assertTrue(result["ambiguous"])
        self.assertEqual(len(result["candidates"]), 2)
        self.assertLess(result["selected"]["area"], 10000)

    def test_visual_region_preserves_strokes_above_recognized_words(self):
        image = np.full((600, 800, 3), 230, np.uint8)
        # Tesseract chỉ thấy ba từ cuối; nét ảnh phải giữ cả phần đầu trang.
        for y in range(100, 501, 25):
            cv2.putText(image, "Document text line", (250, y), cv2.FONT_HERSHEY_SIMPLEX,
                        .55, (80, 60, 40), 1, cv2.LINE_AA)
        words = [{"text": "word", "box": [x, 480, x + 35, 500], "confidence": 90}
                 for x in (260, 310, 360)]
        result = content_scan.select_content_region(image, words)
        self.assertEqual(result["selected"]["source"], "text_strokes")
        self.assertLess(result["selected"]["box"][1], 110)
        self.assertGreater(result["selected"]["box"][3], 490)

    def test_scan_only_with_corners_skips_text_detection(self):
        corners = np.array([[5, 5], [55, 5], [55, 35], [5, 35]], np.float32)
        detection = {"corners": corners, "status": "uncertain", "warnings": []}
        with patch.object(scan_image, "detect_document", return_value=detection), \
                patch.object(scan_image, "crop_content") as crop, \
                patch.object(scan_image, "page_crop_seems_wrong") as check:
            scanned, info = scan_image.scan_document(self.image)
        crop.assert_not_called()
        check.assert_not_called()
        self.assertEqual(scanned.shape, (30, 50, 3))
        self.assertEqual(info["corners_original"], corners.tolist())
        self.assertIsNone(info["content_detection"])

    def test_scan_only_automatically_falls_back_without_page_warp(self):
        detection = {"corners": None, "status": "no_candidate", "warnings": []}
        details = {"region_selection": {"ambiguous": True}}
        with patch.object(scan_image, "detect_document", return_value=detection), \
                patch.object(scan_image, "build_scan") as warp, \
                patch.object(scan_image, "crop_content", return_value=(self.image, np.eye(3), details)):
            scanned, info = scan_image.scan_document(self.image)
        warp.assert_not_called()
        self.assertEqual(info["scanner_status"], "content_fallback")
        self.assertIn("competing_content_regions", info["warnings"])
        self.assertIsNone(info["H_source_to_warp"])


if __name__ == "__main__":
    unittest.main()
