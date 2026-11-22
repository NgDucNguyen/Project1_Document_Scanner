"""Giữ dấu câu, từ điểm thấp và tọa độ khi xuất kết quả OCR để kiểm tra."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import numpy as np
import cv2

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src/document_scanner'))
from ocr.recognize import parse_recognition_words,recognition_details
from ocr.prepare_image import prepare_ocr_image
from scanner.orientation import orient_for_reading, rotate_quarter_turn


class EnglishRecognitionTests(unittest.TestCase):
    def test_quarter_turn_maps_source_pixels_exactly(self):
        image = np.arange(5 * 7 * 3, dtype=np.uint8).reshape(5, 7, 3)
        for turns in range(4):
            rotated, matrix = rotate_quarter_turn(image, turns)
            for x, y in ((0, 0), (6, 4), (2, 3)):
                px, py, _ = matrix @ [x, y, 1]
                np.testing.assert_array_equal(rotated[int(py), int(px)], image[y, x])

    def test_reading_orientation_requires_clear_text_evidence(self):
        image = np.full((200, 300, 3), 230, np.uint8)
        image[60:140, 80:220] = 60
        strong = [{"text": "Document", "confidence": 90}] * 15
        weak = [{"text": "noise", "confidence": 30}]
        with patch("scanner.orientation.find_text_words", side_effect=[weak, weak, weak, strong]):
            upright, matrix, info = orient_for_reading(image)
        self.assertEqual(info["rotation_ccw"], 270)
        self.assertEqual(upright.shape[:2], (300, 200))
        with patch("scanner.orientation.find_text_words", return_value=strong):
            unchanged, _, info = orient_for_reading(image)
        self.assertEqual(info["status"], "uncertain")
        np.testing.assert_array_equal(unchanged, image)

    def test_punctuation_and_low_score_words_are_not_discarded(self):
        tsv='level\tpage_num\tblock_num\tpar_num\tline_num\tleft\ttop\twidth\theight\tconf\ttext\n'
        tsv+='5\t1\t1\t1\t1\t10\t20\t4\t8\t0\t"\n'
        tsv+='5\t1\t1\t1\t1\t20\t20\t30\t8\t24\tHello\n'
        tsv+='5\t1\t2\t1\t1\t10\t90\t20\t9\t95\tworld\n'
        words=parse_recognition_words(tsv)
        self.assertEqual([w['text'] for w in words],['"','Hello','world'])
        details=recognition_details('" Hello\nworld',words,11)
        self.assertEqual(len(details['lines']),2)
        self.assertEqual(details['low_confidence_word_count'],2)
        self.assertEqual(details['lines'][0]['box'],[10,20,50,28])

    def test_empty_output_is_reported_without_inventing_text(self):
        details=recognition_details('',[],11)
        self.assertIn('ocr_empty',details['warnings'])
        self.assertIsNone(details['mean_word_confidence'])
        self.assertEqual(details['text'],'')

    def test_ocr_preparation_preserves_content_coordinate_mapping(self):
        page=np.full((1000,750,3),255,np.uint8)
        cv2.rectangle(page,(0,0),(20,20),(0,0,0),-1)
        prepared,info=prepare_ocr_image(page)
        matrix=np.array(info['T_scan_to_ocr'])
        point=matrix@np.array([5,5,1])
        self.assertLess(int(prepared[round(point[1]),round(point[0])].max()),30)
        np.testing.assert_allclose(np.linalg.inv(matrix)@point,[5,5,1])
        self.assertTrue(np.all(prepared[:12]==255))
        # Trang đã lớn không bị thu nhỏ làm mất chữ.
        large=np.full((2000,1000,3),255,np.uint8)
        _,large_info=prepare_ocr_image(large)
        self.assertEqual(large_info['scale_x'],1)
        self.assertEqual(large_info['scale_y'],1)


if __name__=='__main__':unittest.main()
