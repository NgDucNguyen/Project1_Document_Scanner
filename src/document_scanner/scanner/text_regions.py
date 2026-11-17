"""DBNet tìm vùng chữ; gom vùng và cắt nội dung, không dự đoán mép giấy."""
from functools import lru_cache
import math
from pathlib import Path

import cv2
import numpy as np

MODEL_PATH = Path(__file__).resolve().parents[3] / "models/dbnet/DB_TD500_resnet18.onnx"


@lru_cache(maxsize=1)
def load_dbnet():
    if not MODEL_PATH.is_file():
        raise FileNotFoundError("Chưa có mô hình DBNet: " + str(MODEL_PATH))
    model = cv2.dnn_TextDetectionModel_DB(str(MODEL_PATH))
    model.setBinaryThreshold(0.3)
    model.setPolygonThreshold(0.5)
    model.setMaxCandidates(500)
    model.setUnclipRatio(2.0)
    # Tham số tiền xử lý từ tài liệu chính thức OpenCV cho DB_TD500.
    model.setInputParams(1.0 / 255.0, (736, 736), (122.67891434, 116.66876762, 104.00698793))
    return model


def detect_text_regions(image):
    polygons, confidences = load_dbnet().detect(image)
    regions = []
    for polygon, confidence in zip(polygons, np.asarray(confidences).reshape(-1)):
        points = np.asarray(polygon, np.float32).reshape(4, 2)
        if confidence >= 0.5 and cv2.contourArea(points) >= 12:
            regions.append({"points": points, "confidence": float(confidence)})
    return regions


def region_angle(regions):
    """Chỉ xoay khi ít nhất ba vùng chữ dài đồng thuận về góc nghiêng."""
    angles, weights = [], []
    for region in regions:
        points = region["points"]
        vectors = np.roll(points, -1, axis=0) - points
        lengths = np.linalg.norm(vectors, axis=1)
        index = int(np.argmax(lengths))
        if lengths[index] < 2 * max(float(lengths.min()), 1):
            continue
        angle = math.degrees(math.atan2(*vectors[index][::-1]))
        angle = (angle + 90) % 180 - 90
        if abs(angle) <= 25:
            angles.append(angle)
            weights.append(min(float(lengths[index]), 400) * region["confidence"])
    if len(angles) < 3:
        return 0.0
    angles, weights = np.array(angles), np.array(weights)
    # Cụm hướng có tổng trọng số lớn nhất; không dùng cạnh bàn để xoay trang.
    supports = [weights[np.abs(angles - angle) <= 4].sum() for angle in angles]
    nearby = np.abs(angles - angles[int(np.argmax(supports))]) <= 4
    if nearby.sum() < 3 or weights[nearby].sum() < 0.6 * weights.sum():
        return 0.0
    angle = float(np.average(angles[nearby], weights=weights[nearby]))
    return angle if abs(angle) >= 0.3 else 0.0


def group_regions(boxes, shape):
    """Gom các hộp gần nhau, giữ cụm chính cùng các cụm nội dung lân cận."""
    height, width = shape[:2]
    median_height = float(np.median(boxes[:, 3] - boxes[:, 1]))
    gap_x = max(3 * median_height, .03 * width)
    gap_y = max(3 * median_height, .025 * height)
    parents = list(range(len(boxes)))

    def find(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    for i, first in enumerate(boxes):
        for j in range(i):
            second = boxes[j]
            dx = max(first[0] - second[2], second[0] - first[2], 0)
            dy = max(first[1] - second[3], second[1] - first[3], 0)
            if dx <= gap_x and dy <= gap_y:
                parents[find(i)] = find(j)
    groups = {}
    for index in range(len(boxes)):
        groups.setdefault(find(index), []).append(index)
    groups = list(groups.values())
    areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    groups.sort(key=lambda indices: areas[indices].sum(), reverse=True)
    selected = list(groups[0])
    main = boxes[selected]
    main_box = [main[:, 0].min(), main[:, 1].min(), main[:, 2].max(), main[:, 3].max()]
    ambiguous = False
    for indices in groups[1:]:
        other = boxes[indices]
        bound = [other[:, 0].min(), other[:, 1].min(), other[:, 2].max(), other[:, 3].max()]
        dx = max(bound[0] - main_box[2], main_box[0] - bound[2], 0)
        dy = max(bound[1] - main_box[3], main_box[1] - bound[3], 0)
        # Giữ tiêu đề/cột lân cận; các cụm xa đáng kể được báo mơ hồ.
        near = dx <= .10 * width and dy <= max(6 * median_height, .08 * height)
        substantial = areas[indices].sum() >= .15 * areas[groups[0]].sum()
        if near:
            selected.extend(indices)
        elif substantial:
            ambiguous = True
    return selected, len(groups), ambiguous


def crop_dbnet_content(image):
    regions = detect_text_regions(image)
    if len(regions) < 3:
        return None
    height, width = image.shape[:2]
    angle = region_angle(regions)
    rotation = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1)
    cos, sin = abs(rotation[0, 0]), abs(rotation[0, 1])
    new_width = int(math.ceil(height * sin + width * cos))
    new_height = int(math.ceil(height * cos + width * sin))
    rotation[0, 2] += (new_width - width) / 2
    rotation[1, 2] += (new_height - height) / 2
    polygons = [cv2.transform(region["points"].reshape(1, 4, 2), rotation)[0] for region in regions]
    boxes = np.array([[p[:, 0].min(), p[:, 1].min(), p[:, 0].max(), p[:, 1].max()] for p in polygons])
    selected, group_count, ambiguous = group_regions(boxes, (new_height, new_width))
    if len(selected) < 3:
        return None
    kept = boxes[selected]
    margin = max(15, round(.035 * max(new_width, new_height)))
    x1 = max(0, int(np.floor(kept[:, 0].min())) - margin)
    y1 = max(0, int(np.floor(kept[:, 1].min())) - margin)
    x2 = min(new_width, int(np.ceil(kept[:, 2].max())) + margin)
    y2 = min(new_height, int(np.ceil(kept[:, 3].max())) + margin)
    if x2 <= x1 or y2 <= y1:
        return None
    rotated = cv2.warpAffine(image, rotation, (new_width, new_height), borderValue=(255, 255, 255)) if angle else image
    transform = np.array([[1, 0, -x1], [0, 1, -y1], [0, 0, 1]]) @ np.vstack([rotation, [0, 0, 1]])
    details = {
        "detector": "dbnet_td500_resnet18", "rotation_degrees": round(angle, 2),
        "proposed_rotation_degrees": round(angle, 2), "box_in_rotated_image": [x1, y1, x2, y2],
        "detected_regions": len(regions), "selected_regions": len(selected),
        "excluded_regions": len(regions) - len(selected),
        "group_count": group_count, "ambiguous_groups": ambiguous,
        "margin_pixels": margin,
        "content_box_area_ratio": round((x2 - x1) * (y2 - y1) / (new_width * new_height), 4),
        "regions_original": [r["points"].tolist() for r in regions],
        "selected_region_indices": selected,
    }
    return rotated[y1:y2, x1:x2], transform, details
