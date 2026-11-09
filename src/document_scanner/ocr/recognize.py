from pathlib import Path
import csv
import os
import subprocess


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

def recognize_image(image_path, language, psm=None, tessdata_dir=None):
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

    # Chạy Tesseract và lấy văn bản mà chương trình trả về.
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    # Nếu Tesseract báo lỗi, hiển thị nội dung lỗi.
    if result.returncode != 0:
        raise RuntimeError(
            "Tesseract chạy lỗi:\n" + result.stderr
        )

    # Trả về phần văn bản đã nhận dạng.
    return result.stdout
