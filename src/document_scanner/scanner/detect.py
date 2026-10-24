"""Tìm khung giấy bằng cạnh Canny và vùng sáng Otsu."""
import json
from pathlib import Path

import cv2
import numpy as np

CONFIG_PATH = Path(__file__).resolve().parents[3] / "configs" / "scanner.json"
with open(CONFIG_PATH, encoding="utf-8-sig") as file:
    CONFIG = json.load(file)


def order_points(points):
    # Sắp theo góc quanh tâm: tránh lấy trùng góc bằng tổng/hiệu tọa độ.
    points = np.array(points, dtype=np.float32)
    if points.shape != (4, 2) or not np.isfinite(points).all():
        raise ValueError("Cần bốn điểm có tọa độ hữu hạn.")
    center = points.mean(axis=0)
    angles = np.arctan2(points[:, 1] - center[1], points[:, 0] - center[0])
    points = points[np.argsort(angles)]
    # Có quy tắc phụ y, x nếu tổng x+y bằng nhau.
    start = min(range(4), key=lambda i: (sum(points[i]), points[i, 1], points[i, 0]))
    return np.roll(points, -start, axis=0)


def polygon_iou(first, second):
    first = np.asarray(first, dtype=np.float32)
    second = np.asarray(second, dtype=np.float32)
    intersection, _ = cv2.intersectConvexConvex(first, second)
    union = cv2.contourArea(first) + cv2.contourArea(second) - intersection
    return float(np.clip(intersection / union, 0, 1)) if union > 0 else 0.0


def score_candidate(points, contour, distances, width, height):
    area = cv2.contourArea(points)
    area_ratio = area / (width * height)
    if not CONFIG["min_area_ratio"] <= area_ratio <= CONFIG["max_area_ratio"]:
        return None
    if ((points[:, 0] <= 3).any() or (points[:, 0] >= width - 4).any()
            or (points[:, 1] <= 3).any() or (points[:, 1] >= height - 4).any()):
        return None
    lengths = np.linalg.norm(points - np.roll(points, -1, axis=0), axis=1)
    if lengths.min() < CONFIG["min_edge_length"]:
        return None
    supports = []
    for index in range(4):
        # Lấy 60 vị trí trên mỗi cạnh; xem có gần cạnh Canny hay không.
        samples = np.linspace(points[index], points[(index + 1) % 4], 60)
        xs = np.round(samples[:, 0]).astype(int)
        ys = np.round(samples[:, 1]).astype(int)
        supports.append(np.mean(distances[ys, xs] <= CONFIG["edge_distance"]))
    edge_support = float(np.mean(supports))
    if edge_support < CONFIG["min_edge_support"]:
        return None
    contour_area = cv2.contourArea(contour)
    fit = min(area, contour_area) / max(area, contour_area)
    area_score = min(area_ratio / 0.35, 1.0)
    # Điểm so sánh ứng viên, không phải xác suất dự đoán đúng.
    return 4 * edge_support + 2 * fit + area_score


def detect_document(image):
    result = {
        "corners": None, "score": None, "method": None,
        "status": "invalid_input", "warnings": [], "debug": {},
        "blur_score": None, "score_gap": None, "candidate_count": 0,
    }
    if image is None or image.size == 0 or image.ndim != 3 or image.shape[2] != 3:
        return result
    original_height, original_width = image.shape[:2]
    scale = min(1.0, CONFIG["max_detection_size"] / max(image.shape[:2]))
    width = max(1, int(round(original_width * scale)))
    height = max(1, int(round(original_height * scale)))
    resized = cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    kernel = np.ones((CONFIG["kernel_size"], CONFIG["kernel_size"]), np.uint8)

    edges = cv2.Canny(blurred, CONFIG["canny_low"], CONFIG["canny_high"])
    closed_edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
    _, mask = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    distances = cv2.distanceTransform(255 - edges, cv2.DIST_L2, 3)
    candidates = []
    for method, binary in (("canny", closed_edges), ("otsu", mask)):
        contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:CONFIG["max_contours"]]
        for contour in contours:
            if cv2.contourArea(contour) < CONFIG["min_area_ratio"] * width * height:
                continue
            hull = cv2.convexHull(contour)
            perimeter = cv2.arcLength(hull, True)
            for epsilon in CONFIG["epsilon_ratios"]:
                polygon = cv2.approxPolyDP(hull, epsilon * perimeter, True)
                if len(polygon) != 4 or not cv2.isContourConvex(polygon):
                    continue
                points = order_points(polygon.reshape(4, 2))
                score = score_candidate(points, contour, distances, width, height)
                if score is not None:
                    candidates.append({"points": points, "score": score, "method": method})

    # Giữ cách chọn khung của bản v2; thêm cảnh báo để người dùng kiểm tra.
    candidates.sort(key=lambda item: item["score"], reverse=True)
    result["debug"] = {
        "resized": resized, "edges": closed_edges, "mask": mask,
        "candidates": [item["points"] for item in candidates],
    }
    result["candidate_count"] = len(candidates)
    result["blur_score"] = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    result["status"] = "no_candidate"
    if not candidates:
        return result
    best = candidates[0]
    if result["blur_score"] < CONFIG["blur_warning_threshold"]:
        result["warnings"].append("blur")
    # Cùng một khung có thể xuất hiện nhiều lần; chỉ so với khung khác rõ rệt.
    for other in candidates[1:]:
        if polygon_iou(best["points"], other["points"]) < CONFIG["distinct_candidate_iou"]:
            result["score_gap"] = float(best["score"] - other["score"])
            if result["score_gap"] <= CONFIG["ambiguity_score_gap"]:
                result["warnings"].append("ambiguous_candidates")
            break

    points = best["points"].copy()
    # Dùng hai tỷ lệ riêng vì kích thước ảnh nhỏ đã được làm tròn.
    points[:, 0] *= original_width / width
    points[:, 1] *= original_height / height
    result.update(
        corners=points, score=float(best["score"]), method=best["method"],
        status="uncertain" if result["warnings"] else "ok",
    )
    return result

