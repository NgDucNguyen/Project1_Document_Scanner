from pathlib import Path
import csv
import os
import subprocess
import tempfile


# Đường dẫn đến chương trình Tesseract đã cài trên máy.
TESSERACT_PATH = Path(
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


def recognize_word_boxes(image_path, language, tessdata_dir=None):
    """Lấy vị trí các từ Tesseract nhìn thấy để xác định vùng nội dung."""
    if not TESSERACT_PATH.is_file():
        raise FileNotFoundError("Không tìm thấy Tesseract: " + str(TESSERACT_PATH))
    command = [str(TESSERACT_PATH), str(image_path), "stdout", "-l", language,
               "--psm", "11"]
    if tessdata_dir is not None:
        if not tessdata_dir.is_dir():
            raise FileNotFoundError("Không tìm thấy thư mục mô hình: " + str(tessdata_dir))
        command.extend(["--tessdata-dir", str(tessdata_dir)])
    # Dùng đường dẫn đầy đủ vì mô hình riêng không chứa file cấu hình TSV.
    command.append(str(TESSERACT_PATH.parent / "tessdata" / "configs" / "tsv"))
    env = os.environ.copy()
    env["OMP_THREAD_LIMIT"] = "1"
    result = subprocess.run(command, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", env=env)
    if result.returncode:
        raise RuntimeError("Tesseract tìm vùng chữ bị lỗi:\n" + result.stderr)
    reader = csv.DictReader(result.stdout.splitlines(), delimiter="\t", quoting=csv.QUOTE_NONE)
    required = {"level", "text", "left", "top", "width", "height", "conf"}
    if not reader.fieldnames or not required.issubset(reader.fieldnames):
        raise ValueError("Tesseract không trả về vị trí chữ hợp lệ.")
    words = []
    for row in reader:
        if row["level"] != "5" or not row["text"].strip():
            continue
        x, y, width, height = (int(row[key]) for key in ("left", "top", "width", "height"))
        confidence = float(row["conf"])
        if width > 0 and height > 0 and confidence >= 20:
            words.append({"text": row["text"].strip(), "box": [x, y, x + width, y + height],
                          "confidence": confidence})
    return words

def parse_recognition_words(tsv):
    """Giữ cả từ có điểm thấp và dấu câu; không tự bỏ hoặc sửa nội dung."""
    reader = csv.DictReader(tsv.splitlines(), delimiter="\t", quoting=csv.QUOTE_NONE)
    required = {"level", "text", "left", "top", "width", "height", "conf",
                "page_num", "block_num", "par_num", "line_num"}
    if not reader.fieldnames or not required.issubset(reader.fieldnames):
        raise ValueError("Tesseract không trả bảng vị trí chữ hợp lệ.")
    words = []
    for row in reader:
        if row["level"] != "5" or not row["text"].strip():
            continue
        x, y, width, height = (int(row[k]) for k in ("left", "top", "width", "height"))
        if width <= 0 or height <= 0:
            continue
        words.append({"text": row["text"].strip(), "box": [x, y, x + width, y + height],
                      "confidence": float(row["conf"]),
                      "line_id": [int(row[k]) for k in ("page_num", "block_num", "par_num", "line_num")]})
    return words


def recognition_details(text, words, psm):
    lines = {}
    for word in words:
        key = tuple(word["line_id"])
        if key not in lines:
            lines[key] = {"line_id": list(key), "text": [], "box": list(word["box"])}
        line = lines[key]
        line["text"].append(word["text"])
        a, b = line["box"], word["box"]
        line["box"] = [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]
    for line in lines.values():
        line["text"] = " ".join(line["text"])
    scores = [w["confidence"] for w in words if w["confidence"] >= 0]
    warnings = []
    if not text.strip():
        warnings.append("ocr_empty")
    if any(s < 50 for s in scores):
        warnings.append("ocr_low_confidence_words_review")
    return {"text": text, "words": words, "lines": list(lines.values()), "psm": psm,
            "word_count": len(words),
            "mean_word_confidence": sum(scores) / len(scores) if scores else None,
            "low_confidence_word_count": sum(s < 50 for s in scores), "warnings": warnings,
            "confidence_note": "Điểm nội bộ Tesseract, không phải xác suất đúng hoặc độ chính xác OCR.",
            "coordinate_space": "Ảnh đầu vào OCR, không phải ảnh chụp gốc.",
            "reading_order": "Giữ TXT và thứ tự dòng của Tesseract; không tự sửa chính tả hay nội dung."}


def recognize_image(image_path, language, psm=None, tessdata_dir=None, return_details=False):
    # Kiểm tra chương trình Tesseract có tồn tại không.
    if not TESSERACT_PATH.is_file():
        raise FileNotFoundError(
            "Không tìm thấy Tesseract: " + str(TESSERACT_PATH)
        )

    # Kiểm tra ảnh có tồn tại không.
    if not image_path.is_file():
        raise FileNotFoundError(
            "Không tìm thấy ảnh: " + str(image_path)
        )

    # Tạo lệnh giống lệnh bạn đã chạy trong terminal.
    command = [
        str(TESSERACT_PATH),
        str(image_path),
        "stdout",
        "-l",
        language,
    ]

    # Dùng thư mục riêng khi cần thử mô hình đã tinh chỉnh.
    if tessdata_dir is not None:
        if not tessdata_dir.is_dir():
            raise FileNotFoundError("Không tìm thấy thư mục mô hình: " + str(tessdata_dir))
        command.extend(["--tessdata-dir", str(tessdata_dir)])

    # PSM xác định cách Tesseract phân tích bố cục của ảnh.
    # Nếu không truyền, giữ nguyên thiết lập mặc định như trước.
    if psm is not None:
        command.extend(["--psm", str(psm)])

    # Một lượt OCR xuất cả TXT và TSV, tránh chạy hai lần có đầu ra lệch nhau.
    env = os.environ.copy()
    env["OMP_THREAD_LIMIT"] = "1"
    with tempfile.TemporaryDirectory(prefix="english_ocr_") as temporary:
        output_base = Path(temporary) / "recognition"
        command[2] = str(output_base)
        for name in ("txt", "tsv"):
            command.append(str(TESSERACT_PATH.parent / "tessdata" / "configs" / name))
        result = subprocess.run(command, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", env=env, timeout=120)
        if result.returncode != 0:
            raise RuntimeError("Tesseract chạy lỗi:\n" + result.stderr)
        text = output_base.with_suffix(".txt").read_text(encoding="utf-8")
        if return_details:
            words = parse_recognition_words(output_base.with_suffix(".tsv").read_text(encoding="utf-8"))
            return recognition_details(text, words, psm)
        return text
