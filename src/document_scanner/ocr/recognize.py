from pathlib import Path
import subprocess


# Đường dẫn đến chương trình Tesseract đã cài trên máy.
TESSERACT_PATH = Path(
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

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
