"""RapidOCR tìm dòng; Tesseract tiếng Việt đọc crop màu đã nắn từng dòng."""
from pathlib import Path
import hashlib
import tempfile
import unicodedata

import cv2
import numpy as np

try:
    from .recognize import recognize_image
except ImportError:
    from recognize import recognize_image

ROOT = Path(__file__).resolve().parents[3]
MODEL_DIR = ROOT / "models/tesseract_vi"
MODEL_SHA256 = "b6b49293d95d0b6dbd8780174627e82c75be957b6f4ed9862155540d6b00bb45"


def check_model():
    path = MODEL_DIR / "vie.traineddata"
    if not path.is_file():
        raise FileNotFoundError("Thiếu models/tesseract_vi/vie.traineddata; xem README, mục tiếng Việt.")
    if hashlib.sha256(path.read_bytes()).hexdigest() != MODEL_SHA256:
        raise ValueError("Hash mô hình tiếng Việt không khớp bản đã thử; xem README để khôi phục.")
    return path


def crop_text_line(image, polygon):
    """Nắn theo bốn điểm dòng, tránh cắt hộp ngang lấy lẫn dòng bên cạnh."""
    points = np.asarray(polygon, np.float32)
    if points.shape != (4, 2) or not np.isfinite(points).all():
        raise ValueError("Khung dòng tiếng Việt không hợp lệ.")
    width = round(max(np.linalg.norm(points[1] - points[0]), np.linalg.norm(points[2] - points[3])))
    height = round(max(np.linalg.norm(points[3] - points[0]), np.linalg.norm(points[2] - points[1])))
    if min(width, height) < 2 or abs(cv2.contourArea(points)) < 4:
        raise ValueError("Khung dòng quá nhỏ để đọc.")
    target = np.float32([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]])
    matrix = cv2.getPerspectiveTransform(points, target)
    crop = cv2.warpPerspective(image, matrix, (width, height),
                               flags=cv2.INTER_CUBIC, borderValue=(255, 255, 255))
    if height > width * 1.5:
        crop = np.rot90(crop).copy()
    # Viền trắng giúp đọc dòng đơn; không nhị phân hóa hoặc làm mòn dấu.
    return cv2.copyMakeBorder(crop, 12, 12, 12, 12, cv2.BORDER_CONSTANT, value=(255, 255, 255))


def recognize_vietnamese_lines(image_path, lines):
    check_model()
    image = cv2.imdecode(np.fromfile(image_path, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Không đọc được ảnh đầu vào tiếng Việt.")
    recognized = []
    with tempfile.TemporaryDirectory(prefix="ocr_vie_") as temporary:
        path = Path(temporary) / "line.png"
        for line in lines:
            crop = crop_text_line(image, line["polygon"])
            cv2.imencode(".png", crop)[1].tofile(path)
            details = recognize_image(path, "vie", psm=7, tessdata_dir=MODEL_DIR, return_details=True)
            psm = 7
            # Chỉ thử raw-line khi dòng đơn trả rỗng; không chọn theo nhãn/confidence.
            if not details["text"].strip():
                details = recognize_image(path, "vie", psm=13, tessdata_dir=MODEL_DIR, return_details=True)
                psm = 13
            result = dict(line)
            result["rapidocr_text_before_vie"] = line["text"]
            result["rapidocr_confidence_before_vie"] = line["confidence"]
            result["text"] = unicodedata.normalize("NFC", details["text"].strip())
            score = details["mean_word_confidence"]
            result["confidence"] = max(0, score / 100) if score is not None else 0.0
            result["recognizer"] = "tesseract_vie_best"
            result["recognition_psm"] = psm
            recognized.append(result)
    return recognized
