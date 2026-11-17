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


def score_candidate(points, contour, distances, width, height, details=None):
    # details chỉ ghi chẩn đoán; không tham gia quyết định chọn khung.
    if details is None:
        details = {}
    area = cv2.contourArea(points)
    area_ratio = area / (width * height)
    details["area_ratio"] = float(area_ratio)
    if not CONFIG["min_area_ratio"] <= area_ratio <= CONFIG["max_area_ratio"]:
        details["reason"] = "polygon_area"
        return None
    if ((points[:, 0] <= 3).any() or (points[:, 0] >= width - 4).any()
            or (points[:, 1] <= 3).any() or (points[:, 1] >= height - 4).any()):
        details["reason"] = "image_boundary"
        return None
    lengths = np.linalg.norm(points - np.roll(points, -1, axis=0), axis=1)
    details["min_edge_length"] = float(lengths.min())
    if lengths.min() < CONFIG["min_edge_length"]:
        details["reason"] = "short_edge"
        return None
    supports = []
    for index in range(4):
        # Lấy 60 vị trí trên mỗi cạnh; xem có gần cạnh Canny hay không.
        samples = np.linspace(points[index], points[(index + 1) % 4], 60)
        xs = np.round(samples[:, 0]).astype(int)
        ys = np.round(samples[:, 1]).astype(int)
        supports.append(np.mean(distances[ys, xs] <= CONFIG["edge_distance"]))
    edge_support = float(np.mean(supports))
    details["edge_support"] = edge_support
    details["edge_support_per_side"] = [float(value) for value in supports]
    if edge_support < CONFIG["min_edge_support"]:
        details["reason"] = "weak_edge_support"
        return None
    contour_area = cv2.contourArea(contour)
    fit = min(area, contour_area) / max(area, contour_area)
    area_score = min(area_ratio / 0.35, 1.0)
    details.update(reason="accepted", fit=float(fit), area_score=float(area_score))
    # Điểm so sánh ứng viên, không phải xác suất dự đoán đúng.
    return 4 * edge_support + 2 * fit + area_score


def detect_document(image, diagnostics=False):
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
    branches = [("canny", closed_edges, distances), ("otsu", mask, distances)]
    if CONFIG.get("enhanced_proposals", False):
        # Cạnh giấy nhạt có thể biến mất với ngưỡng Canny cũ. Xét thêm
        # ảnh xám và các kênh màu; không cần nhãn hay OCR để sinh khung.
        lab = cv2.cvtColor(resized, cv2.COLOR_BGR2LAB)
        channels = [("gray_low", gray), ("lab_b", lab[:, :, 2])]
        for name, channel in channels:
            smooth = cv2.GaussianBlur(channel, (3, 3), 0)
            extra_edges = cv2.Canny(smooth, CONFIG["extra_canny_low"], CONFIG["extra_canny_high"])
            closed = cv2.morphologyEx(extra_edges, cv2.MORPH_CLOSE, kernel)
            extra_distances = cv2.distanceTransform(255 - extra_edges, cv2.DIST_L2, 3)
            branches.append((name, closed, extra_distances))
    candidates = []
    trace = []
    hull_trace = []
    branch_counts = {}
    for method, binary, branch_distances in branches:
        contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        counts = {"contours_total": len(contours), "below_min_area": 0,
                  "large_contours_outside_top_k": 0, "not_convex_quad_attempts": 0}
        branch_counts[method] = counts
        if not diagnostics:
            contours = contours[:CONFIG["max_contours"]]
        for rank, contour in enumerate(contours):
            if cv2.contourArea(contour) < CONFIG["min_area_ratio"] * width * height:
                counts["below_min_area"] += 1
                continue
            outside_top_k = rank >= CONFIG["max_contours"]
            if outside_top_k:
                counts["large_contours_outside_top_k"] += 1
            hull = cv2.convexHull(contour)
            if diagnostics:
                hull_trace.append({"method": method, "contour_rank": rank + 1,
                                   "points": hull.reshape(-1, 2).tolist()})
            perimeter = cv2.arcLength(hull, True)
            for epsilon in CONFIG["epsilon_ratios"]:
                polygon = cv2.approxPolyDP(hull, epsilon * perimeter, True)
                if len(polygon) != 4 or not cv2.isContourConvex(polygon):
                    counts["not_convex_quad_attempts"] += 1
                    continue
                points = order_points(polygon.reshape(4, 2))
                details = {}
                score = score_candidate(points, contour, branch_distances, width, height, details)
                if score is not None and method not in ("canny", "otsu"):
                    # Một cạnh mạnh không đủ bù cho ba cạnh không có bằng chứng.
                    if min(details["edge_support_per_side"]) < CONFIG["extra_min_side_support"]:
                        details["reason"] = "weak_side_support"
                        score = None
                if diagnostics:
                    trace.append({
                        "method": method, "contour_rank": rank + 1, "epsilon": epsilon,
                        "points": points.tolist(), "score": float(score) if score is not None else None,
                        **details, "reason": "contour_rank" if outside_top_k else details["reason"],
                        "score_filter_reason": details["reason"],
                    })
                if score is not None and not outside_top_k:
                    candidates.append({"points": points, "score": score, "method": method,
                                       "details": details})

    # Giữ cách chọn khung của bản v2; thêm cảnh báo để người dùng kiểm tra.
    candidates.sort(key=lambda item: item["score"], reverse=True)
    result["debug"] = {
        "resized": resized, "edges": closed_edges, "mask": mask,
        "candidates": [item["points"] for item in candidates],
    }
    if diagnostics:
        result["debug"].update(candidate_trace=trace, contour_hulls=hull_trace,
                               branch_counts=branch_counts, raw_edges=edges)
    result["candidate_count"] = len(candidates)
    result["blur_score"] = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    result["status"] = "no_candidate"
    if not candidates:
        return result
    best = candidates[0]
    result["quality"] = best["details"].copy()
    # Điểm là tổng các bằng chứng hình học, không phải xác suất. Cho phép
    # trả về không có khung khi mọi ứng viên đều yếu, để pipeline thử vùng chữ.
    if best["score"] < CONFIG.get("min_candidate_score", 0.0):
        result.update(status="low_confidence", score=float(best["score"]), method=best["method"])
        result["warnings"].append("weak_candidate_rejected")
        return result
    if best["score"] < CONFIG.get("review_candidate_score", 0.0):
        result["warnings"].append("weak_candidate")
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

