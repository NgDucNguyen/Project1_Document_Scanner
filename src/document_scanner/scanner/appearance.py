"""Kiểm tra ảnh scan và làm sáng nền, giữ màu mực bằng OpenCV."""
import json
from pathlib import Path

import cv2
import numpy as np

CONFIG_PATH = Path(__file__).resolve().parents[3] / "configs/scan.json"
SETTINGS = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def resize_for_analysis(image, max_size):
    scale = min(1.0, max_size / max(image.shape[:2]))
    return cv2.resize(image, None, fx=scale, fy=scale) if scale < 1 else image


def paper_mask(image):
    """Ước lượng vùng giấy sáng; không phải phân đoạn tài liệu bằng học sâu."""
    lightness = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)[:, :, 0]
    # Closing lấp nét chữ tối để không coi chữ là nền cần xóa.
    background = cv2.morphologyEx(lightness, cv2.MORPH_CLOSE,
                                 cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31)))
    threshold, _ = cv2.threshold(background, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # Otsu có thể chia đôi một tờ giấy hơi loang sáng. Chừa khoảng sáng
    # so với vùng giấy sáng nhất để giữ cả phần giấy trong bóng nhẹ.
    cutoff = max(120, min(threshold, float(np.percentile(background, 85)) - 45))
    mask = np.where(background >= cutoff, 255, 0).astype(np.uint8)
    _, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
    if len(stats) <= 1:
        return np.zeros_like(mask)
    largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    mask = np.where(labels == largest, 255, 0).astype(np.uint8)
    # Chừa thêm ít pixel quanh mép, hạn chế làm mất nét sát biên giấy.
    return cv2.dilate(mask, np.ones((3, 3), np.uint8))


def assess_document(image):
    """Từ chối một số ca rõ ràng; các ngưỡng là heuristic, chưa được hiệu chuẩn."""
    config = SETTINGS["quality"]
    reasons, warnings = [], []
    height, width = image.shape[:2]
    small = resize_for_analysis(image, config["analysis_size"])
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    mask = paper_mask(small)
    paper_pixels = int(np.count_nonzero(mask))
    fraction = paper_pixels / mask.size
    blackhat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT,
                               cv2.getStructuringElement(cv2.MORPH_RECT, (25, 9)))
    threshold, strokes = cv2.threshold(blackhat, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    strokes[blackhat < max(6, threshold)] = 0
    strokes = cv2.bitwise_and(strokes, mask)
    _, _, stats, _ = cv2.connectedComponentsWithStats(strokes)
    count, ink_pixels = 0, 0
    for _, _, w, h, area in stats[1:]:
        if 2 <= h <= 80 and 1 <= w <= 200 and 3 <= area <= 3000 and area / (w * h) < .95:
            count += 1
            ink_pixels += int(area)
    ink_fraction = ink_pixels / max(paper_pixels, 1)
    focus = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    if min(height, width) < config["min_output_side"]:
        reasons.append("document_too_small")
    if fraction < config["min_paper_fraction"]:
        reasons.append("insufficient_light_paper")
    if count < config["min_text_components"] or ink_fraction < config["min_ink_fraction"]:
        reasons.append("insufficient_text_evidence")
    if ink_fraction > config["max_ink_fraction"]:
        reasons.append("excessive_texture")
    if focus < config["min_focus"]:
        reasons.append("severely_blurred_or_low_detail")
    elif focus < config["review_focus"]:
        warnings.append("low_sharpness_review")
    return {"accepted": not reasons, "reasons": reasons, "warnings": warnings,
            "metrics": {"width": width, "height": height, "paper_fraction": round(fraction, 4),
                        "text_components": count, "ink_fraction": round(ink_fraction, 5),
                        "focus_score": round(focus, 3)},
            "policy": "light_paper_with_text_heuristic_v1"}


def enhance_document(image):
    """Bù độ sáng trong Lab, giảm ám màu nền; không nhị phân nét chữ."""
    config = SETTINGS["appearance"]
    small = resize_for_analysis(image, config["analysis_size"])
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,
                                       (config["background_kernel"], config["background_kernel"]))
    small_light = cv2.cvtColor(small, cv2.COLOR_BGR2LAB)[:, :, 0]
    background = cv2.dilate(small_light, kernel)
    background = cv2.GaussianBlur(background, (0, 0), config["background_sigma"])
    background = cv2.resize(background, (image.shape[1], image.shape[0])).astype(np.float32)
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    light = lab[:, :, 0].astype(np.float32)
    ratio = np.clip(light / np.maximum(background, 1), 0, 1)
    ink_signal = np.clip((1 - ratio) * config["ink_gain"], 0, 1)
    corrected_light = 255 * np.power(1 - ink_signal, config["ink_gamma"])
    # Bán kính nhỏ làm rõ mép nét, hạn chế quầng quanh chữ và dính dấu.
    blurred = cv2.GaussianBlur(corrected_light, (0, 0), config["sharpen_sigma"])
    lab[:, :, 0] = np.clip(corrected_light + config["sharpen_amount"] * (corrected_light - blurred), 0, 255).astype(np.uint8)
    # Giảm ám màu trên nền gần trắng, giữ chroma tại nét mực tối hơn nền.
    ink_weight = np.clip((1 - ratio) * 15, 0, 1)
    for channel in (1, 2):
        color = cv2.medianBlur(lab[:, :, channel], 3).astype(np.float32)
        lab[:, :, channel] = np.clip(128 + (color - 128) * ink_weight, 0, 255).astype(np.uint8)
    corrected = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    if config["clean_paper_background"]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # Mặt nạ này chỉ quyết định vùng nền cần làm trắng; ảnh chữ vẫn
        # liên tục mức màu, không thay toàn bộ đầu ra bằng ảnh nhị phân.
        ink = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY_INV, config["text_window"], config["text_offset"])
        support = cv2.dilate(ink, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
        corrected[support == 0] = 255
    removed_fraction = 0.0
    if config["whiten_outside_paper"]:
        mask = paper_mask(small)
        mask = cv2.resize(mask, (image.shape[1], image.shape[0]), interpolation=cv2.INTER_NEAREST)
        # Chỉ tô trắng vùng ngoài giấy ước lượng, không sinh hoặc vẽ lại ký tự.
        corrected[mask == 0] = 255
        removed_fraction = float(np.mean(mask == 0))
    return corrected, {"applied": True, "method": "lab_background_normalization",
                       "settings": dict(config), "whitened_fraction": round(removed_fraction, 4),
                       "note": "Giữ ảnh màu trước tăng cường để đối chiếu; không phục hồi chữ mất hoặc mờ nặng."}
