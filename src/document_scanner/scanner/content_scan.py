"""Cắt vùng chữ khi ảnh không có đủ đường viền trang tài liệu."""
import math
from pathlib import Path
import tempfile

import cv2
import numpy as np

from ocr.recognize import recognize_word_boxes


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
    reliable = reliable_words(words)
    if len(reliable) < 3:
        return None

    # Chừa lề để hạn chế cắt sát các dấu hoặc nét chữ ở rìa.
    # Dùng các từ đáng tin cậy làm khung; lề giữ thêm dấu và ký tự ngắn ở gần.
    boxes = np.array([word["box"] for word in reliable])
    margin = max(15, round(0.035 * max(new_width, new_height)))
    x1 = max(0, int(boxes[:, 0].min()) - margin)
    y1 = max(0, int(boxes[:, 1].min()) - margin)
    x2 = min(new_width, int(boxes[:, 2].max()) + margin)
    y2 = min(new_height, int(boxes[:, 3].max()) + margin)
    scanned = rotated[y1:y2, x1:x2]
    transform = np.vstack([rotation, [0.0, 0.0, 1.0]])
    transform = np.array([[1, 0, -x1], [0, 1, -y1], [0, 0, 1]]) @ transform
    details = {"rotation_degrees": round(angle, 2), "proposed_rotation_degrees": round(proposed_angle, 2),
               "original_reliable_characters": original_score, "rotated_reliable_characters": rotated_score,
               "box_in_rotated_image": [x1, y1, x2, y2], "detected_words": len(words),
               "margin_pixels": margin,
               "content_box_area_ratio": round(((x2 - x1) * (y2 - y1)) / (new_width * new_height), 4)}
    return scanned, transform, details
