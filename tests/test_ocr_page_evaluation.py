"""Kiểm tra cách chấm chữ sau khi OCR toàn trang."""
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "document_scanner" / "ocr"))
from evaluate_pages import assign_words, parse_tsv_words, score_regions


class PageEvaluationTests(unittest.TestCase):
    def test_tesseract_quote_is_a_word_and_does_not_join_rows(self):
        tsv = ("level\tleft\ttop\twidth\theight\ttext\n"
               "5\t1\t2\t3\t4\t\"\n"
               "5\t5\t2\t3\t4\tHello\n")
        words = parse_tsv_words(tsv)
        self.assertEqual([word["text"] for word in words], ['"', "Hello"])

    def test_missing_word_counts_as_error_and_unassigned_is_separate(self):
        regions = [{"index": 0, "text": "Hello world", "box": [0, 0, 100, 20]}]
        words = [{"text": "Hello", "box": [0, 0, 35, 20]},
                 {"text": "other", "box": [120, 0, 150, 20]}]
        rows, unassigned = score_regions("page", "eng", regions, words)
        self.assertEqual(rows[0]["prediction"], "Hello")
        self.assertEqual(rows[0]["word_errors"], 1)
        self.assertEqual(unassigned, ["other"])

    def test_overlapping_regions_do_not_duplicate_a_word(self):
        regions = [{"box": [0, 0, 100, 30]}, {"box": [10, 0, 50, 30]}]
        assigned, unassigned = assign_words(regions, [{"text": "word", "box": [12, 5, 45, 20]}])
        self.assertEqual(assigned, [[], ["word"]])
        self.assertEqual(unassigned, [])


if __name__ == "__main__":
    unittest.main()
