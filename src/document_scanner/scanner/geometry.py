"""Kiểm tra bốn góc, nắn phối cảnh và xoay ảnh bằng OpenCV."""
import cv2
import numpy as np


def validate_corners(image, corners):
    if image is None or image.size == 0 or image.ndim not in (2, 3):
        raise ValueError("Ảnh đầu vào không hợp lệ.")
    points = np.array(corners, dtype=np.float32)
    if points.shape != (4, 2) or not np.isfinite(points).all():
        raise ValueError("Cần đúng bốn góc có tọa độ hữu hạn.")
    if len(np.unique(points, axis=0)) != 4:
        raise ValueError("Bốn góc phải khác nhau.")
    height, width = image.shape[:2]
    if ((points[:, 0] < 0).any() or (points[:, 0] >= width).any()
            or (points[:, 1] < 0).any() or (points[:, 1] >= height).any()):
        raise ValueError("Có góc nằm ngoài ảnh.")
    contour = points.reshape(4, 1, 2)
    if not cv2.isContourConvex(contour):
        raise ValueError("Các góc phải đi quanh tứ giác lồi, không nối chéo.")
    if cv2.contourArea(contour) <= 1:
        raise ValueError("Diện tích tứ giác quá nhỏ.")
    # Trong hệ tọa độ ảnh, chiều kim đồng hồ có diện tích dương.
    if cv2.contourArea(contour, oriented=True) < 0:
        raise ValueError("Thứ tự góc ngược chiều, có thể làm chữ bị lật gương.")
    return points


def build_scan(image, corners, rotation=0):
    """Trả ảnh scan, H trước xoay và T sau xoay."""
    points = validate_corners(image, corners)
    if rotation not in (0, 1, 2, 3):
        raise ValueError("rotation phải là 0, 1, 2 hoặc 3 lần xoay 90 độ.")
    tl, tr, br, bl = points
    # Lấy cạnh dài hơn của từng cặp cạnh đối diện để ước lượng kích thước.
    width = int(round(max(np.linalg.norm(tr - tl), np.linalg.norm(br - bl))))
    height = int(round(max(np.linalg.norm(bl - tl), np.linalg.norm(br - tr))))
    if width < 2 or height < 2:
        raise ValueError("Kích thước ảnh sau nắn quá nhỏ.")
    if width * height > 40_000_000:
        raise ValueError("Ảnh đầu ra quá lớn, cần kiểm tra lại góc.")
    destination = np.array(
        [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
        dtype=np.float32,
    )
    matrix_h = cv2.getPerspectiveTransform(points, destination)
    scanned = cv2.warpPerspective(image, matrix_h, (width, height))
    matrix_t = matrix_h.copy()
    for _ in range(rotation):
        height, width = scanned.shape[:2]
        # Xoay 90 độ: x mới = height - 1 - y, y mới = x.
        rotate_matrix = np.array(
            [[0, -1, height - 1], [1, 0, 0], [0, 0, 1]], dtype=np.float64,
        )
        scanned = cv2.rotate(scanned, cv2.ROTATE_90_CLOCKWISE)
        matrix_t = rotate_matrix @ matrix_t
    return scanned, matrix_h, matrix_t


def warp_document(image, corners):
    scanned, _, _ = build_scan(image, corners)
    return scanned

