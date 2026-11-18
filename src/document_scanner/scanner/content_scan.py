"""Cắt vùng chữ khi ảnh không có đủ đường viền trang tài liệu."""
import math
from pathlib import Path
import tempfile

import cv2
import numpy as np

from ocr.recognize import recognize_word_boxes


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
    """Xoay gần thẳng và cắt bao quanh chữ; không giả lập bốn góc trang."""
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
    return scanned, transform, details
