import unittest

import numpy as np

from src.document_scanner.ocr.prepare_funsd_training import select_line


class FunsdTrainingDataTests(unittest.TestCase):
    def setUp(self):
        self.image = np.full((80, 220), 255, dtype=np.uint8)
        self.image[20:32, 10:90] = 0
        self.image[20:32, 100:180] = 0
        self.region = {
            "text": "Hello world",
            "words": [
                {"text": "Hello", "box": [10, 20, 90, 32]},
                {"text": "world", "box": [100, 20, 180, 32]},
            ],
        }

    def test_matching_single_line_produces_crop_and_transcription(self):
        result, error = select_line(self.region, self.image)
        self.assertIsNone(error)
        crop, text, box = result
        self.assertEqual(text, "Hello world")
        self.assertEqual(box, [7, 17, 183, 35])
        self.assertEqual(crop.shape, (18, 176))

    def test_mismatched_transcription_is_rejected(self):
        self.region["text"] = "Hello different"
        result, error = select_line(self.region, self.image)
        self.assertIsNone(result)
        self.assertEqual(error, "label_mismatch")

    def test_words_on_different_lines_are_rejected(self):
        self.region["words"][1]["box"] = [100, 50, 180, 62]
        result, error = select_line(self.region, self.image)
        self.assertIsNone(result)
        self.assertEqual(error, "not_one_line")


if __name__ == "__main__":
    unittest.main()
