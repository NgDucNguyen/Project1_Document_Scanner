"""DocsaidLab DocAligner FastViT-T8: d? ?o?n b?n g?c b?ng heatmap.

Ti?n/h?u x? l? tham kh?o m? upstream (Apache-2.0):
https://github.com/DocsaidLab/DocAligner/blob/main/docaligner/heatmap_reg/infer.py
Tr? uncertain v? ch?a ki?m ch?ng kh? n?ng t? ch?i ?nh kh?ng c? t?i li?u.
"""
from pathlib import Path
import threading

import cv2
import numpy as np

try:
    from .classic import order_points
    from .geometry import validate_corners
except ImportError:
    from classic import order_points
    from geometry import validate_corners

MODEL = Path(__file__).resolve().parents[3] / "models/docaligner/fastvit_t8.onnx"


class CornerModel:
    def __init__(self):
        if not MODEL.is_file():
            raise FileNotFoundError("Thi?u m? h?nh DocAligner: " + str(MODEL) + "; xem README ?? t?i ho?c ch?n --scanner-method classic.")
        self.net = cv2.dnn.readNetFromONNX(str(MODEL))
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)

    def __call__(self, image):
        # Giữ BGR, không cắt tâm; resize 256×256 và chia 255 theo upstream.
        blob = cv2.dnn.blobFromImage(image, 1 / 255.0, (256, 256), swapRB=False, crop=False)
        self.net.setInput(blob)
        heatmaps = self.net.forward("heatmap")
        if heatmaps.ndim != 4 or heatmaps.shape[1] != 4:
            raise ValueError("Đầu ra không phải bốn bản đồ góc: " + str(heatmaps.shape))
        height, width = image.shape[:2]
        points, peaks = [], []
        for heatmap in heatmaps[0]:
            heatmap = cv2.resize(heatmap, (width, height), interpolation=cv2.INTER_LINEAR)
            peaks.append(float(heatmap.max()))
            limited = np.where(heatmap >= .3, heatmap, 0)
            binary = np.clip(limited * 255, 0, 255).astype(np.uint8)
            _, binary = cv2.threshold(binary, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                continue
            contour = max(contours, key=cv2.contourArea)
            moments = cv2.moments(contour)
            if moments["m00"] > 0:
                points.append([moments["m10"] / moments["m00"], moments["m01"] / moments["m00"]])
        corners = order_points(points) if len(points) == 4 else None
        if corners is not None:
            try:
                corners = validate_corners(image, corners)
            except ValueError:
                corners = None
        return {"corners": corners, "score": min(peaks), "method": "docaligner_fastvit_t8",
                "status": "uncertain" if corners is not None else "no_candidate",
                "warnings": ["document_presence_not_verified"] if corners is not None else [],
                "candidate_count": int(corners is not None), "blur_score": None, "score_gap": None,
                "debug": {}}


class ThreadLocalModel:
    """Mỗi worker giữ mạng riêng, tránh gọi đồng thời cùng một mạng OpenCV."""
    def __init__(self):
        self.local = threading.local()

    def __call__(self, image):
        if not hasattr(self.local, "model"):
            self.local.model = CornerModel()
        return self.local.model(image)


_model = ThreadLocalModel()


def detect_document(image):
    if image is None or image.size == 0 or image.ndim != 3 or image.shape[2] != 3:
        return {"corners": None, "score": None, "method": "docaligner_fastvit_t8",
                "status": "invalid_input", "warnings": [], "candidate_count": 0,
                "blur_score": None, "score_gap": None, "debug": {}}
    return _model(image)
