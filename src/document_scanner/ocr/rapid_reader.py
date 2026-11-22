"""Bộ đọc PP-OCR qua RapidOCR, chạy riêng để không đổi venv chính."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]


def recognize_rapidocr(image_path, use_cls=True, language="eng"):
    if language not in ("eng", "vie"):
        raise ValueError("Nhánh RapidOCR hỗ trợ cấu hình eng hoặc vie.")
    if language == "vie":
        try:
            from .vietnamese import check_model
        except ImportError:
            from vietnamese import check_model
        check_model()
    interpreter = Path(sys.executable) if importlib.util.find_spec("rapidocr") else ROOT / "artifacts/ocr/runtime/Scripts/python.exe"
    if not interpreter.is_file():
        raise FileNotFoundError("Chưa cài môi trường RapidOCR; xem README, mục thử OCR học sâu.")
    with tempfile.TemporaryDirectory(prefix="rapid_reader_") as temporary:
        output = Path(temporary) / "result.json"
        command = [str(interpreter), "-X", "utf8", str(Path(__file__)),
                   "--worker", str(Path(image_path).resolve()), str(output)]
        if not use_cls:
            command.append("--no-cls")
        if language == "vie":
            command += ["--lang", "vie"]
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                                errors="replace", timeout=240 if language == "vie" else 120,
                                env=dict(os.environ, OMP_NUM_THREADS="1"))
        if result.returncode:
            raise RuntimeError("RapidOCR không chạy được:\n" + result.stderr[-3000:])
        return json.loads(output.read_text(encoding="utf-8"))


def rapid_text_anchors(image, language=None, tessdata_dir=None):
    """Khung dòng dùng làm bằng chứng crop, không giả thành hộp từ OCR."""
    import cv2
    with tempfile.TemporaryDirectory(prefix="rapid_anchors_") as temporary:
        path = Path(temporary) / "input.png"
        cv2.imencode(".png", image)[1].tofile(str(path))
        result = recognize_rapidocr(path, use_cls=False)
    import math
    return [{"text": line["text"], "box": [max(0, math.floor(line["box"][0])),
              max(0, math.floor(line["box"][1])), min(image.shape[1], math.ceil(line["box"][2])),
              min(image.shape[0], math.ceil(line["box"][3]))], "polygon": line["polygon"],
             "confidence": line["confidence"] * 100} for line in result["lines"]]


def run_worker(image_path, output, use_cls=True, language="eng"):
    import importlib.metadata
    import numpy as np
    import rapidocr
    from rapidocr import RapidOCR
    model_dir = Path(rapidocr.__file__).parent / "models"
    models = {"Det": "PP-OCRv6_det_small.onnx", "Rec": "PP-OCRv6_rec_small.onnx",
              "Cls": "ch_ppocr_mobile_v2.0_cls_mobile.onnx"}
    params = {"EngineConfig.onnxruntime.intra_op_num_threads": 1,
              "EngineConfig.onnxruntime.inter_op_num_threads": 1, "Global.log_level": "warning",
              "Global.text_score": 0.0, "Global.use_cls": use_cls}
    for module, name in models.items():
        path = model_dir / name
        if not path.is_file():
            raise FileNotFoundError("Thiếu mô hình thử đã chốt: " + str(path))
        params[module + ".model_path"] = str(path)
    engine = RapidOCR(params=params)
    result = engine(image_path)
    lines = []
    if result.boxes is not None:
        for index, (polygon, text, confidence) in enumerate(zip(result.boxes, result.txts, result.scores)):
            polygon = np.asarray(polygon)
            lines.append({"text": text, "confidence": float(confidence), "line_id": index,
                          "polygon": polygon.tolist(),
                          "box": [float(polygon[:, 0].min()), float(polygon[:, 1].min()),
                                  float(polygon[:, 0].max()), float(polygon[:, 1].max())]})
    if language == "vie":
        from vietnamese import recognize_vietnamese_lines
        lines = recognize_vietnamese_lines(image_path, lines)
    warnings = [] if lines else ["ocr_empty"]
    if any(line["confidence"] < .8 for line in lines):
        warnings.append("ocr_low_confidence_lines_review")
    if language == "vie" and any(not line["text"] for line in lines):
        warnings.append("vietnamese_empty_lines_review")
    details = {"text": "\n".join(line["text"] for line in lines), "lines": lines, "words": [],
               "engine": "rapidocr", "engine_version": importlib.metadata.version("rapidocr"),
               "models": {name: hashlib.sha256((model_dir / name).read_bytes()).hexdigest() for name in models.values()},
               "word_count": sum(len(line["text"].split()) for line in lines),
               "word_count_note": "Đếm theo khoảng trắng trong TXT; mô hình trả khung dòng, không trả khung từng từ.",
               "mean_word_confidence": None, "low_confidence_word_count": None,
               "warnings": warnings, "confidence_note": "Điểm ở cấp dòng, không phải độ chính xác hay điểm từng từ.",
               "coordinate_space": "Ảnh đầu vào OCR.",
               "reading_order": "Giữ thứ tự dòng của RapidOCR; chưa khôi phục bố cục bảng/nhiều cột."}
    details["language"] = language
    if language == "vie":
        from vietnamese import check_model
        from recognize import TESSERACT_PATH
        model = check_model()
        details["models"]["vie.traineddata"] = hashlib.sha256(model.read_bytes()).hexdigest()
        details["engine"] = "rapidocr_detection_tesseract_vie"
        details["recognizer"] = "tesseract_vie_best_psm7_empty_to13"
        details["line_recognition_policy"] = "PSM7; chỉ thử PSM13 nếu dòng trả rỗng, không chọn theo nhãn hoặc confidence."
        details["tesseract_version"] = subprocess.run([str(TESSERACT_PATH), "--version"], capture_output=True,
            text=True, encoding="utf-8", errors="replace", timeout=15).stdout.splitlines()[0]
        details["confidence_note"] = "Điểm từ Tesseract gộp theo dòng, không phải độ chính xác; không so trực tiếp với điểm RapidOCR tiếng Anh."
        details["input_policy"] = "Cắt/nắn từng polygon dòng trên ảnh màu, viền trắng 12 px, không tự thêm dấu hoặc sửa chính tả."
    Path(output).write_text(json.dumps(details, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Worker nội bộ; dùng pipeline.py để chạy tài liệu.")
    parser.add_argument("--worker", nargs=2, required=True, metavar=("IMAGE", "OUTPUT"))
    parser.add_argument("--no-cls", action="store_true")
    parser.add_argument("--lang", choices=["eng", "vie"], default="eng")
    args = parser.parse_args()
    run_worker(*args.worker, use_cls=not args.no_cls, language=args.lang)
