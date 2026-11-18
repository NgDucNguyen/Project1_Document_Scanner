"""Chọn vùng nội dung và thử nắn tứ giác giấy khi detector thiếu góc."""
import math
from pathlib import Path
import tempfile

import cv2
import numpy as np

from ocr.recognize import recognize_word_boxes
from .appearance import paper_mask
from .classic import order_points
from .geometry import build_scan


def refine_content_perspective(image, words):
    """Thử nắn tứ giác giấy trong vùng nội dung đã chọn, có kiểm tra giữ chữ."""
    mask = paper_mask(image)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    contour = max(contours, key=cv2.contourArea)
    hull = cv2.convexHull(contour)
    perimeter = cv2.arcLength(hull, True)
    height, width = image.shape[:2]
    # Loại hộp OCR trên bàn/nền: chỉ kiểm tra giữ chữ có hỗ trợ giấy sáng.
    anchors = []
    for word in reliable_words(words):
        x1, y1, x2, y2 = word["box"]
        if np.mean(mask[y1:y2, x1:x2] > 0) >= .90:
            anchors.append(word)
    if len(anchors) < 3:
        return None
    for epsilon in (.015, .02, .03, .04):
        polygon = cv2.approxPolyDP(hull, epsilon * perimeter, True)
        if len(polygon) != 4:
            continue
        points = order_points(polygon.reshape(4, 2))
        area_fraction = cv2.contourArea(points) / (width * height)
        if not .50 <= area_fraction <= .985:
            continue
        # Khung đã gần chữ nhật thì không nắn thêm để tránh làm mờ ảnh.
        top_angle = math.degrees(math.atan2(*(points[1] - points[0])[::-1]))
        bottom_angle = math.degrees(math.atan2(*(points[2] - points[3])[::-1]))
        if abs(top_angle - bottom_angle) < 1.5:
            continue
        center = points.mean(axis=0)
        for expansion in (1.015, 1.03, 1.06):
            expanded = center + (points - center) * expansion
            expanded[:, 0] = np.clip(expanded[:, 0], 0, width - 1)
            expanded[:, 1] = np.clip(expanded[:, 1], 0, height - 1)
            expanded = expanded.astype(np.float32)
            # Kiểm tra đủ diện tích từng hộp từ, không chỉ tâm hộp.
            retained = []
            for word in anchors:
                x1, y1, x2, y2 = word["box"]
                box = np.float32([[x1, y1], [x2, y1], [x2, y2], [x1, y2]])
                intersection, _ = cv2.intersectConvexConvex(expanded, box)
                retained.append(intersection / max((x2 - x1) * (y2 - y1), 1))
            if min(retained) < .98:
                continue
            # Kiểm tra thêm nét ảnh để giữ phần chữ mà OCR chưa đọc được.
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            detail = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT,
                                      cv2.getStructuringElement(cv2.MORPH_RECT, (25, 9)))
            interior = cv2.erode(mask, np.ones((7, 7), np.uint8))
            ink = ((detail >= 12) & (interior > 0)).astype(np.uint8)
            count, labels, stats, _ = cv2.connectedComponentsWithStats(ink)
            keep = np.zeros(count, np.uint8)
            for index, (_, _, w, h, area) in enumerate(stats[1:], 1):
                if 2 <= h <= 45 and 1 <= w <= 150 and area >= 3 and area / (w * h) < .95:
                    keep[index] = 1
            ink = keep[labels]
            inside = np.zeros_like(mask)
            cv2.fillConvexPoly(inside, np.round(expanded).astype(np.int32), 1)
            ink_retained = float(np.count_nonzero(ink & inside) / max(np.count_nonzero(ink), 1))
            if ink_retained < .97:
                continue
            try:
                scanned, matrix, _ = build_scan(image, expanded)
            except ValueError:
                continue
            return scanned, matrix, {"applied": True, "method": "content_guided_paper_quad",
                                     "quad_in_crop": expanded.tolist(), "min_word_area_retained": round(min(retained), 4),
                                     "ink_retained": round(ink_retained, 4),
                                     "top_angle_before": round(top_angle, 2),
                                     "bottom_angle_before": round(bottom_angle, 2)}
    return None


def select_content_region(image, words):
    """Chọn một vùng lớn nhất có chữ, không bao chung mọi hộp từ."""
    reliable = reliable_words(words)
    if len(reliable) < 3:
        return None
    height, width = image.shape[:2]
    scale = min(1.0, 1200 / max(width, height))
    small = cv2.resize(image, None, fx=scale, fy=scale) if scale < 1 else image
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    # Black-hat lấy nét tối nhỏ trên nền sáng, kể cả nét viết tay chưa đọc được.
    blackhat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT,
                               cv2.getStructuringElement(cv2.MORPH_RECT, (25, 9)))
    _, strokes = cv2.threshold(blackhat, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    lightness = cv2.cvtColor(small, cv2.COLOR_BGR2LAB)[:, :, 0]
    # Ước lượng nền quanh nét mực trước khi phân ngưỡng, tránh xóa chữ đen.
    background = cv2.morphologyEx(lightness, cv2.MORPH_CLOSE, np.ones((9, 25), np.uint8))
    _, light = cv2.threshold(background, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    light = cv2.erode(light, np.ones((7, 7), np.uint8))
    strokes = cv2.bitwise_and(strokes, light)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(strokes)
    keep = np.zeros(count, np.uint8)
    for index, (_, _, w, h, area) in enumerate(stats[1:], 1):
        # Bỏ đường viền dài, khối đặc và nhiễu quá nhỏ trước khi nối nét.
        if 2 <= h <= 45 and 1 <= w <= 150 and area >= 3 and area / (w * h) < .95:
            keep[index] = 255
    clean = keep[labels]
    joined = cv2.dilate(clean, cv2.getStructuringElement(cv2.MORPH_RECT, (31, 23)))
    _, region_labels, region_stats, _ = cv2.connectedComponentsWithStats(joined)
    candidates = []
    for index, (x, y, w, h, area) in enumerate(region_stats[1:], 1):
        if area < 1500:
            continue
        # Chỉ lấy biên của nét thật, không lấy phần nở thêm do dilation.
        ys, xs = np.nonzero((region_labels[y:y+h, x:x+w] == index) & (clean[y:y+h, x:x+w] > 0))
        if not len(xs):
            continue
        box = [max(0, int((x + xs.min()) / scale)), max(0, int((y + ys.min()) / scale)),
               min(width, int(np.ceil((x + xs.max() + 1) / scale))),
               min(height, int(np.ceil((y + ys.max() + 1) / scale)))]
        support = [word for word in reliable if box[0] <= (word['box'][0] + word['box'][2]) / 2 <= box[2]
                   and box[1] <= (word['box'][1] + word['box'][3]) / 2 <= box[3]]
        if len(support) >= 3:
            candidates.append({"box": box, "word_count": len(support), "source": "text_strokes"})

    if not candidates:
        # Khi ảnh không có nét rõ: gom hộp từ gần nhau, vẫn không lấy toàn ảnh.
        boxes = np.array([word["box"] for word in reliable])
        size = float(np.median(boxes[:, 3] - boxes[:, 1]))
        remaining = set(range(len(boxes)))
        while remaining:
            group = [remaining.pop()]
            for current in group:
                a = boxes[current]
                for index in list(remaining):
                    b = boxes[index]
                    gap_x = max(0, int(max(a[0], b[0]) - min(a[2], b[2])))
                    gap_y = max(0, int(max(a[1], b[1]) - min(a[3], b[3])))
                    if gap_x <= 3 * size and gap_y <= 2 * size:
                        group.append(index)
                        remaining.remove(index)
            if len(group) >= 3:
                selected = boxes[group]
                box = [int(selected[:, 0].min()), int(selected[:, 1].min()),
                       int(selected[:, 2].max()), int(selected[:, 3].max())]
                candidates.append({"box": box, "word_count": len(group), "source": "word_cluster"})
    if not candidates:
        return None
    for candidate in candidates:
        x1, y1, x2, y2 = candidate["box"]
        candidate["area"] = (x2 - x1) * (y2 - y1)
    candidates.sort(key=lambda item: (item["area"], item["word_count"]), reverse=True)
    return {"selection": "largest_supported_text_region", "selected": candidates[0],
            "candidates": candidates, "reliable_words_total": len(reliable),
            "ambiguous": len(candidates) > 1 and candidates[1]["area"] >= .8 * candidates[0]["area"]}


def find_text_words(image, language, tessdata_dir=None):
    """Lấy vị trí chữ trên ảnh; file ảnh trung gian được xóa sau khi đọc."""
    with tempfile.TemporaryDirectory(prefix="scanner_text_") as folder:
        image_path = Path(folder) / "image.png"
        encoded, data = cv2.imencode(".png", image)
        if not encoded:
            raise OSError("Không tạo được ảnh tạm để tìm vùng chữ.")
        image_path.write_bytes(data.tobytes())
        return recognize_word_boxes(image_path, language, tessdata_dir)


def reliable_words(words):
    return [word for word in words if word["confidence"] >= 40
            and sum(char.isalnum() for char in word["text"]) >= 2]


def reliable_character_count(words):
    return sum(sum(char.isalnum() for char in word["text"]) for word in reliable_words(words))


def page_crop_seems_wrong(image, scanned, language, tessdata_dir=None):
    """Cảnh báo khi khung chỉ có rất ít chữ, trong khi ảnh gốc có nhiều chữ."""
    scan_count = reliable_character_count(find_text_words(scanned, language, tessdata_dir))
    # Chỉ kiểm tra thêm ảnh gốc khi ảnh sau cắt có rất ít chữ đáng tin cậy.
    if scan_count >= 40:
        return False, {"scan_reliable_characters": scan_count, "source_reliable_characters": None}
    source_count = reliable_character_count(find_text_words(image, language, tessdata_dir))
    suspect = source_count >= 40 and source_count >= 3 * max(scan_count, 1)
    return suspect, {"scan_reliable_characters": scan_count, "source_reliable_characters": source_count}


def estimate_text_angle(image):
    """Ước lượng độ nghiêng nhỏ từ các nét gần nằm ngang trong ảnh."""
    height, width = image.shape[:2]
    scale = min(1.0, 1200 / max(width, height))
    small = cv2.resize(image, None, fx=scale, fy=scale) if scale < 1 else image
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 80, 180)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 1800, threshold=50,
                            minLineLength=50, maxLineGap=15)
    if lines is None:
        return 0.0
    angles, weights = [], []
    for x1, y1, x2, y2 in lines.reshape(-1, 4):
        angle = math.degrees(math.atan2(int(y2 - y1), int(x2 - x1)))
        if angle > 90:
            angle -= 180
        if angle < -90:
            angle += 180
        if -20 <= angle <= 20:
            angles.append(angle)
            weights.append(min(math.hypot(int(x2 - x1), int(y2 - y1)), 250))
    if len(angles) < 3:
        return 0.0
    angles, weights = np.array(angles), np.array(weights)
    histogram, bins = np.histogram(angles, bins=np.arange(-20, 21), weights=weights)
    index = int(np.argmax(histogram))
    center = (bins[index] + bins[index + 1]) / 2
    nearby = np.abs(angles - center) <= 1.5
    if np.count_nonzero(nearby) < 3:
        return 0.0
    angle = float(np.average(angles[nearby], weights=weights[nearby]))
    return 0.0 if abs(angle) < 0.3 else angle


def crop_content(image, language, tessdata_dir=None):
    """Chọn cụm chữ chính, rồi thử ước lượng khung giấy để nắn phối cảnh."""
    height, width = image.shape[:2]
    proposed_angle = estimate_text_angle(image)
    # Không giả định mọi đường ngang đều là dòng chữ: thử đọc cả ảnh gốc.
    original_words = find_text_words(image, language, tessdata_dir)
    original_score = reliable_character_count(original_words)
    angle = proposed_angle
    rotation = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1.0)
    cos, sin = abs(rotation[0, 0]), abs(rotation[0, 1])
    new_width = int(math.ceil(height * sin + width * cos))
    new_height = int(math.ceil(height * cos + width * sin))
    rotation[0, 2] += (new_width - width) / 2
    rotation[1, 2] += (new_height - height) / 2
    if angle:
        rotated = cv2.warpAffine(image, rotation, (new_width, new_height),
                                 borderValue=(255, 255, 255))
        rotated_words = find_text_words(rotated, language, tessdata_dir)
        rotated_score = reliable_character_count(rotated_words)
    else:
        rotated, rotated_words, rotated_score = image, original_words, original_score
    # Điểm chỉ là tín hiệu so sánh, không bảo đảm vị trí hoặc nội dung đều đúng.
    # Ảnh gốc có thể chứa chữ nền, nên chỉ bỏ xoay khi điểm giảm rất mạnh.
    if angle and (rotated_score < 0.15 * original_score or rotated_score == 0):
        angle = 0.0
        rotated, rotated_words = image, original_words
        new_width, new_height = width, height
        rotation = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    words = rotated_words
    region = select_content_region(rotated, words)
    if region is None:
        return None

    # Chỉ chừa lề quanh vùng đã chọn, không gom thêm các cụm chữ bên ngoài.
    left, top, right, bottom = region["selected"]["box"]
    margin = max(15, round(0.01 * max(new_width, new_height)))
    x1, y1 = max(0, left - margin), max(0, top - margin)
    x2, y2 = min(new_width, right + margin), min(new_height, bottom + margin)
    scanned = rotated[y1:y2, x1:x2]
    transform = np.vstack([rotation, [0.0, 0.0, 1.0]])
    transform = np.array([[1, 0, -x1], [0, 1, -y1], [0, 0, 1]]) @ transform
    details = {"rotation_degrees": round(angle, 2), "proposed_rotation_degrees": round(proposed_angle, 2),
               "original_reliable_characters": original_score, "rotated_reliable_characters": rotated_score,
               "box_in_rotated_image": [x1, y1, x2, y2], "detected_words": len(words),
               "margin_pixels": margin, "region_selection": region,
               "content_box_area_ratio": round(((x2 - x1) * (y2 - y1)) / (new_width * new_height), 4)}
    local_words = []
    for word in reliable_words(words):
        left, top, right, bottom = word["box"]
        if x1 <= left and right <= x2 and y1 <= top and bottom <= y2:
            local_words.append(dict(word, box=[left - x1, top - y1, right - x1, bottom - y1]))
    refined = refine_content_perspective(scanned, local_words)
    details["perspective_refinement"] = {"applied": False}
    if refined is not None:
        result, matrix, refinement = refined
        quad = np.float32([refinement["quad_in_crop"]])
        refinement["quad_original"] = cv2.perspectiveTransform(quad, np.linalg.inv(transform))[0].tolist()
        source_points = np.array(refinement["quad_original"])
        refinement["outside_source"] = bool((source_points[:, 0] < 0).any() or (source_points[:, 0] >= width).any()
                                             or (source_points[:, 1] < 0).any() or (source_points[:, 1] >= height).any())
        refinement["H_crop_to_output"] = matrix.tolist()
        transform = matrix @ transform
        # Nắn trực tiếp ảnh gốc một lần, tránh mờ do xoay rồi nắn liên tiếp.
        scanned = cv2.warpPerspective(image, transform, (result.shape[1], result.shape[0]),
                                     borderValue=(255, 255, 255))
        details["perspective_refinement"] = refinement
    return scanned, transform, details
