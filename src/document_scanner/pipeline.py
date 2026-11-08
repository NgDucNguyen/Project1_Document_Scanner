from pathlib import Path
from datetime import datetime
import argparse
import json

import cv2

# Các hàm scanner và OCR đã làm trước đó.
from scanner.detect import detect_document
from scanner.geometry import build_scan
from ocr.recognize import recognize_image


# Từ pipeline.py đi lên thư mục gốc của dự án.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Kết quả của chương trình nối scanner với OCR.
OUTPUT_ROOT = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "pipeline"
)
FUNSD_MODEL_DIR = PROJECT_ROOT / "models" / "funsd_english"


def choose_ocr_model(language, tessdata_dir, choice, model_dir):
    """Chọn mô hình cục bộ nếu có; các ngôn ngữ khác giữ nguyên."""
    model_exists = (model_dir / "funsd_eng.traineddata").is_file()
    if choice == "funsd" and (language != "eng" or tessdata_dir is not None):
        raise ValueError("--ocr-model funsd yêu cầu --lang eng và không dùng cùng --tessdata-dir.")
    if choice == "standard" and tessdata_dir is not None:
        raise ValueError("--ocr-model standard không dùng cùng --tessdata-dir.")
    if choice == "funsd" and not model_exists:
        raise ValueError("Không tìm thấy mô hình FUNSD trong " + str(model_dir))
    if language == "eng" and tessdata_dir is None and (choice == "funsd" or
                                                        (choice == "auto" and model_exists)):
        return "funsd_eng", model_dir
    return language, tessdata_dir


def process_image(image_path, language, input_type="photo", psm=None, tessdata_dir=None):
    # 1. Kiểm tra ảnh đầu vào.
    if not image_path.is_file():
        raise FileNotFoundError(
            "Không tìm thấy ảnh: " + str(image_path)
        )

    image = cv2.imread(str(image_path))

    if image is None:
        raise ValueError(
            "Không đọc được ảnh: " + str(image_path)
        )

    print("Đã đọc ảnh:", image_path)

    if input_type == "photo":
        # 2. Ảnh chụp phải tìm góc rồi nắn trước khi OCR.
        detection = detect_document(image)
        status = detection["status"]
        corners = detection["corners"]
        warnings = detection["warnings"]
        print("Trạng thái tìm khung:", status)
        if warnings:
            print("Cảnh báo:", ", ".join(warnings))
        if corners is None:
            raise ValueError(
                "Không tìm được khung tài liệu. "
                "Hãy kiểm tra lại ảnh hoặc sửa góc bằng tay."
            )
        scanned, matrix_h, matrix_t = build_scan(image, corners)
    elif input_type == "scan":
        # FUNSD và ảnh đã nắn có thể đưa trực tiếp vào OCR.
        scanned = image
        status = "already_scanned"
        corners = matrix_h = matrix_t = None
        warnings = []
    else:
        raise ValueError("input_type phải là photo hoặc scan.")

    # 4. Mỗi lần chạy tạo một thư mục riêng.
    run_id = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    output_folder = OUTPUT_ROOT / run_id
    output_folder.mkdir(parents=True, exist_ok=True)

    scan_path = output_folder / "scan.png"
    text_path = output_folder / "text.txt"

    # Lưu ảnh nắn để OCR đọc.
    saved = cv2.imwrite(str(scan_path), scanned)

    if not saved:
        raise OSError(
            "Không lưu được ảnh scan: " + str(scan_path)
        )

    print("Đã lưu ảnh scan:", scan_path)

    # 5. Nhận dạng chữ từ ảnh vừa scan.
    if tessdata_dir is None:
        predicted_text = recognize_image(scan_path, language, psm=psm)
    else:
        predicted_text = recognize_image(scan_path, language, psm=psm, tessdata_dir=tessdata_dir)

    # 6. Lưu văn bản OCR ra file TXT.
    text_path.write_text(
        predicted_text,
        encoding="utf-8",
    )

    # Lưu nguồn và cấu hình để có thể đối chiếu kết quả sau này.
    metadata = {
        "source_image": str(image_path.resolve()),
        "input_type": input_type,
        "language": language,
        "psm": psm,
        "tessdata_dir": None if tessdata_dir is None else str(tessdata_dir.resolve()),
        "scanner_status": status,
        "warnings": warnings,
        "corners_original": None if corners is None else corners.tolist(),
        "H_source_to_warp": None if matrix_h is None else matrix_h.tolist(),
        "T_source_to_output": None if matrix_t is None else matrix_t.tolist(),
    }
    (output_folder / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("Đã lưu văn bản OCR:", text_path)

    return predicted_text


def main():
    parser = argparse.ArgumentParser(
        description="Quét tài liệu và nhận dạng chữ."
    )

    parser.add_argument(
        "--image",
        required=True,
        help="Đường dẫn ảnh chụp tài liệu.",
    )

    parser.add_argument(
        "--lang",
        default="eng",
        help="Tên mô hình OCR, ví dụ eng, vie hoặc funsd_eng.",
    )

    parser.add_argument(
        "--input-type",
        choices=["photo", "scan"],
        default="photo",
        help="photo: tìm khung trước; scan: ảnh đã nắn sẵn.",
    )

    parser.add_argument(
        "--psm",
        type=int,
        choices=range(14),
        help="Chế độ bố cục của Tesseract; mặc định do Tesseract chọn.",
    )

    parser.add_argument(
        "--tessdata-dir",
        help="Thư mục chứa file .traineddata khi dùng mô hình riêng.",
    )
    parser.add_argument(
        "--ocr-model",
        choices=["auto", "standard", "funsd"],
        default="auto",
        help="auto: dùng mô hình FUNSD nếu có; standard: Tesseract gốc; funsd: bắt buộc mô hình FUNSD.",
    )

    args = parser.parse_args()

    image_path = Path(args.image)
    language = args.lang
    tessdata_dir = Path(args.tessdata_dir) if args.tessdata_dir else None
    try:
        language, tessdata_dir = choose_ocr_model(language, tessdata_dir, args.ocr_model, FUNSD_MODEL_DIR)
    except ValueError as error:
        parser.error(str(error))
    print("Mô hình OCR:", language, "- thư mục:", tessdata_dir or "Tesseract cài trên máy")

    # Chạy cả scanner và OCR.
    text = process_image(
        image_path,
        language,
        input_type=args.input_type,
        psm=args.psm,
        tessdata_dir=tessdata_dir,
    )

    print()
    print("===== VĂN BẢN NHẬN DẠNG =====")
    print(text)


if __name__ == "__main__":
    main()
