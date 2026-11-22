"""Giữ dấu trên crop màu và không thay dòng lỗi bằng bản OCR thiếu dấu."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/document_scanner'))
from ocr import vietnamese
import pipeline


class VietnameseTests(unittest.TestCase):
    def test_line_crop_keeps_color_and_adds_white_border(self):
        image = np.full((80, 160, 3), (220, 230, 245), np.uint8)
        cv2.circle(image, (60, 25), 2, (80, 40, 20), -1)  # Dấu nhỏ phía trên chữ.
        crop = vietnamese.crop_text_line(image, [[10, 10], [140, 10], [140, 60], [10, 60]])
        self.assertEqual(crop.shape, (74, 154, 3))
        self.assertTrue(np.all(crop[:12] == 255))
        self.assertLess(crop[20:35, 50:70, 0].min(), 100)
        self.assertFalse(np.array_equal(crop[:, :, 0], crop[:, :, 2]))

    def test_vietnamese_nfc_and_empty_line_are_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'input.png'
            cv2.imencode('.png', np.full((100, 200, 3), 255, np.uint8))[1].tofile(path)
            lines = [{'text': 'Ho ten', 'confidence': .9, 'polygon': [[0,0],[190,0],[190,40],[0,40]]},
                     {'text': 'Viec', 'confidence': .9, 'polygon': [[0,50],[190,50],[190,90],[0,90]]}]
            with patch.object(vietnamese, 'check_model'), patch.object(vietnamese, 'recognize_image', side_effect=[
                    {'text': 'Thi\u0323\n', 'mean_word_confidence': 85},
                    {'text': '', 'mean_word_confidence': None},
                    {'text': '', 'mean_word_confidence': None}]) as reader:
                output = vietnamese.recognize_vietnamese_lines(path, lines)
            self.assertEqual(output[0]['text'], 'Thị')
            self.assertEqual(output[1]['text'], '')
            self.assertEqual(output[1]['rapidocr_text_before_vie'], 'Viec')
            self.assertEqual(reader.call_args_list[0].kwargs['psm'], 7)
            self.assertEqual(reader.call_args.kwargs['psm'], 13)
            self.assertEqual(output[1]['recognition_psm'], 13)

    def test_vie_pipeline_keeps_color_preparation_and_records_real_backend(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); image = folder / 'input.png'
            cv2.imencode('.png', np.full((100,150,3), 240, np.uint8))[1].tofile(image)
            details = {'text':'Họ tên: Đỗ Thị', 'engine':'rapidocr_detection_tesseract_vie',
                       'lines':[{'text':'Họ tên: Đỗ Thị','box':[10,10,140,40]}],
                       'words':[], 'word_count':4, 'mean_word_confidence':None,
                       'low_confidence_word_count':None,'warnings':[], 'confidence_note':'not accuracy',
                       'coordinate_space':'OCR input','reading_order':'line order'}
            with patch.object(pipeline, 'OUTPUT_ROOT', folder/'output'), \
                    patch.object(pipeline, 'recognize_rapidocr', return_value=details) as reader:
                text = pipeline.process_image(image, 'vie', input_type='scan')
            self.assertIn('Đỗ Thị', text)
            self.assertEqual(reader.call_args.kwargs['language'], 'vie')
            result = next((folder/'output').iterdir())
            metadata = json.loads((result/'metadata.json').read_text(encoding='utf-8'))
            self.assertEqual(metadata['ocr_backend'], 'rapidocr_detection_tesseract_vie')
            self.assertTrue(metadata['ocr_preparation']['applied'])


if __name__ == '__main__':
    unittest.main()
