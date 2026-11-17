"""Ngăn xoay theo nền và cắt mất nhóm chữ lân cận trong nhánh DBNet."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src/document_scanner"))
from scanner import text_regions


class TextRegionTests(unittest.TestCase):
    def test_keeps_nearby_title_and_columns_but_excludes_small_distant_noise(self):
        boxes = np.array([[100, 200, 400, 220], [100, 240, 400, 260],
                          [100, 280, 400, 300], [100, 80, 400, 100],
                          [550, 10, 580, 20]], np.float32)
        selected, groups, ambiguous = text_regions.group_regions(boxes, (800, 600))
        self.assertTrue({0, 1, 2, 3}.issubset(selected))
        self.assertNotIn(4, selected)
        self.assertGreater(groups, 1)
        self.assertFalse(ambiguous)

    def test_transform_maps_selected_regions_into_crop_and_ignores_background_lines(self):
        image = np.full((300, 400, 3), 255, np.uint8)
        regions = [{"points": np.array([[60, y], [180, y], [180, y + 20], [60, y + 20]], np.float32),
                    "confidence": .9} for y in (80, 110, 140)]
        with patch.object(text_regions, "detect_text_regions", return_value=regions):
            crop, matrix, details = text_regions.crop_dbnet_content(image)
        self.assertEqual(details["rotation_degrees"], 0)
        self.assertEqual(details["box_in_rotated_image"], [45, 65, 195, 175])
        np.testing.assert_allclose(matrix @ [45, 65, 1], [0, 0, 1])
        self.assertEqual(crop.shape, (110, 150, 3))

    def test_does_not_crop_without_enough_detected_regions(self):
        with patch.object(text_regions, "detect_text_regions", return_value=[]):
            self.assertIsNone(text_regions.crop_dbnet_content(np.zeros((100, 100, 3), np.uint8)))

    def test_region_angle_corrects_slanted_text_without_mirroring(self):
        import cv2
        regions = []
        rotation = cv2.getRotationMatrix2D((200, 150), -8, 1)
        for y in (80, 110, 140):
            points = np.array([[[60, y], [180, y], [180, y + 15], [60, y + 15]]], np.float32)
            regions.append({"points": cv2.transform(points, rotation)[0], "confidence": .9})
        with patch.object(text_regions, "detect_text_regions", return_value=regions):
            _, matrix, details = text_regions.crop_dbnet_content(np.full((300, 400, 3), 255, np.uint8))
        self.assertAlmostEqual(details["rotation_degrees"], 8, places=1)
        points = cv2.perspectiveTransform(regions[0]["points"].reshape(1, 4, 2), matrix)[0]
        self.assertAlmostEqual(points[0, 1], points[1, 1], places=3)
        self.assertGreater(points[1, 0], points[0, 0])


if __name__ == "__main__":
    unittest.main()
