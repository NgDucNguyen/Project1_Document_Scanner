"""Điểm gọi chung: DocAligner mặc định, classic để so sánh Canny/Otsu."""
try:
    from .classic import CONFIG, CONFIG_PATH, order_points, polygon_iou, score_candidate
    from .classic import detect_document as detect_classic
except ImportError:
    from classic import CONFIG, CONFIG_PATH, order_points, polygon_iou, score_candidate
    from classic import detect_document as detect_classic


def detect_document(image, diagnostics=False, method=None):
    method = method or CONFIG.get("default_method", "docaligner")
    if method == "classic":
        return detect_classic(image, diagnostics=diagnostics)
    if method == "docaligner":
        try:
            from .docaligner import detect_document as detect_model
        except ImportError:
            from docaligner import detect_document as detect_model
        return detect_model(image)
    raise ValueError("Phương pháp scanner phải là docaligner hoặc classic.")


def detector_info():
    import hashlib
    method = CONFIG.get("default_method", "docaligner")
    info = {"scanner_method": method}
    if method == "docaligner":
        path = CONFIG_PATH.parent.parent / "models/docaligner/fastvit_t8.onnx"
        if not path.is_file():
            raise FileNotFoundError("Thiếu mô hình: " + str(path) + ". Xem README hoặc chọn classic.")
        info.update(model_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    detector="DocsaidLab DocAligner FastViT-T8")
    return info
