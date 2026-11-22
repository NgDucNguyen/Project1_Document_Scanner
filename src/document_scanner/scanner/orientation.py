"""Chọn hướng đọc 0/90/180/270 độ, không ép mọi trang thành khổ dọc."""
import cv2
import numpy as np

from .content_scan import find_text_words


def rotate_quarter_turn(image, turns):
    """Xoay ngược chiều kim đồng hồ; trả cả phép đổi tọa độ pixel."""
    height, width = image.shape[:2]
    matrices = [np.eye(3),
                np.array([[0, 1, 0], [-1, 0, width - 1], [0, 0, 1]]),
                np.array([[-1, 0, width - 1], [0, -1, height - 1], [0, 0, 1]]),
                np.array([[0, -1, height - 1], [1, 0, 0], [0, 0, 1]])]
    return np.rot90(image, turns).copy(), matrices[turns].astype(float)


def orient_for_reading(image, text_reader=None):
    details = {"applied": False, "rotation_ccw": 0, "method": "four_way_text_evidence",
               "note": "Điểm chữ chỉ hỗ trợ chọn hướng, không phải độ chính xác OCR."}
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    if min(gray.shape) < 96 or float(gray.std()) < 5:
        details["status"] = "insufficient_detail"
        return image, np.eye(3), details
    scale = min(1.0, 1800 / max(gray.shape))
    analysis = cv2.resize(image, None, fx=scale, fy=scale) if scale < 1 else image
    candidates = []
    try:
        for turns in range(4):
            rotated = np.rot90(analysis, turns).copy()
            # eng chuẩn dùng riêng cho hướng trang, không thay mô hình OCR cuối.
            words = (text_reader or find_text_words)(rotated, "eng")
            score = sum(sum(c.isalpha() for c in word["text"]) for word in words
                        if word["confidence"] >= 60 and sum(c.isalpha() for c in word["text"]) >= 2
                        and word.get("box", [0, 0, 1, 1])[2] - word.get("box", [0, 0, 1, 1])[0]
                        >= word.get("box", [0, 0, 1, 1])[3] - word.get("box", [0, 0, 1, 1])[1])
            candidates.append({"rotation_ccw": turns * 90, "score": score})
    except (FileNotFoundError, RuntimeError) as error:
        details.update(status="unavailable", error=str(error))
        return image, np.eye(3), details
    ranked = sorted(candidates, key=lambda item: item["score"], reverse=True)
    details["candidates"] = candidates
    if text_reader is not None:
        details["anchor_source"] = "configured_ocr_text_reader"
    best, runner_up = ranked[:2]
    # Không xoay theo vài chữ ngẫu nhiên hoặc khi hai hướng gần bằng nhau.
    if best["score"] < 40 or best["score"] < max(1.8 * runner_up["score"], runner_up["score"] + 25):
        details["status"] = "uncertain"
        return image, np.eye(3), details
    turns = best["rotation_ccw"] // 90
    details.update(applied=turns != 0, rotation_ccw=turns * 90, status="selected")
    rotated, matrix = rotate_quarter_turn(image, turns)
    return rotated, matrix, details
