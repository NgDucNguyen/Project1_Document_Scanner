from pathlib import Path
from datetime import datetime
import argparse
import json
import hashlib

import cv2
import numpy as np

# Các hàm scanner và OCR đã làm trước đó.
from scanner.scan_image import scan_document
from ocr.metrics import edit_distance, normalize_text
from ocr.recognize import recognize_image
from ocr.prepare_image import prepare_ocr_image


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
ENGLISH_PSM = 11


def choose_ocr_model(language, tessdata_dir, choice, model_dir):
    """Dùng mô hình FUNSD cho tiếng Anh trong chế độ mặc định."""
    model_exists = (model_dir / "funsd_eng.traineddata").is_file()
    if choice == "funsd" and (language != "eng" or tessdata_dir is not None):
        raise ValueError("--ocr-model funsd yêu cầu --lang eng và không dùng cùng --tessdata-dir.")
    if choice == "standard" and tessdata_dir is not None:
        raise ValueError("--ocr-model standard không dùng cùng --tessdata-dir.")
    if language == "eng" and tessdata_dir is None and choice in ("auto", "funsd"):
        if not model_exists:
            raise ValueError("Không tìm thấy mô hình tiếng Anh FUNSD trong " + str(model_dir))
        return "funsd_eng", model_dir
    return language, tessdata_dir


def process_image(image_path, language, input_type="photo", psm=None, tessdata_dir=None, reference_path=None,
                  scanner_method=None, ocr_prepare=True):
    # Mô hình tiếng Anh dùng PSM 11 nếu không yêu cầu cấu hình khác.
    if psm is None and language == "funsd_eng":
        psm = ENGLISH_PSM
    # 1. Kiểm tra ảnh đầu vào.
    if not image_path.is_file():
        raise FileNotFoundError(
            "Không tìm thấy ảnh: " + str(image_path)
        )

    # Đọc bytes trước để hỗ trợ đường dẫn có dấu tiếng Việt trên Windows.
    image_bytes = image_path.read_bytes()
    image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR) if image_bytes else None

    if image is None:
        raise ValueError(
            "Không đọc được ảnh: " + str(image_path)
        )

    reference_text = None
    if reference_path is not None:
        if not reference_path.is_file():
            raise FileNotFoundError("Không tìm thấy file văn bản chuẩn: " + str(reference_path))
        reference_text = normalize_text(reference_path.read_text(encoding="utf-8-sig"))
        if not reference_text:
            raise ValueError("File văn bản chuẩn đang rỗng: " + str(reference_path))

    print("Đã đọc ảnh:", image_path)

    if input_type == "photo":
        # Dùng chung scanner với lệnh scan riêng, tránh lặp hai cách cắt.
        scanned, scan_info = scan_document(
            image, scanner_method, language, tessdata_dir, check_content=True,
        )
        print("Trạng thái scan:", scan_info["scanner_status"])
    elif input_type == "scan":
        scanned = image
        scan_info = {"scanner_status": "already_scanned", "warnings": []}
    else:
        raise ValueError("input_type phải là photo hoặc scan.")
    status = scan_info["scanner_status"]
    warnings = scan_info["warnings"]
    content_details = scan_info.get("content_detection")
    detector_status = scan_info.get("page_detector_status")
    detector_method = scan_info.get("page_detector_method")
    page_crop_check = scan_info.get("page_crop_check")
    rejected_corners = scan_info.get("rejected_page_corners")
    corners = scan_info.get("corners_original")
    matrix_h = scan_info.get("H_source_to_warp")
    matrix_t = scan_info.get("T_source_to_output")
    if warnings:
        print("Cảnh báo:", ", ".join(warnings))

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

    # 5. Chuẩn bị riêng cho OCR; scan.png vẫn là ảnh scanner đã tạo.
    ocr_path = scan_path
    preparation = {"applied": False, "method": "disabled_or_non_english", "T_scan_to_ocr": np.eye(3).tolist()}
    if ocr_prepare and language in ("eng", "funsd_eng"):
        ocr_image, preparation = prepare_ocr_image(scanned)
        if preparation["applied"]:
            ocr_path = output_folder / "ocr_input.png"
            if not cv2.imwrite(str(ocr_path), ocr_image):
                raise OSError("Không lưu được ảnh đầu vào OCR: " + str(ocr_path))
    recognition = recognize_image(ocr_path, language, psm=psm, tessdata_dir=tessdata_dir,
                                  return_details=True)
    # Giữ tương thích với các lời gọi cũ chỉ trả chuỗi văn bản.
    ocr_details = recognition if isinstance(recognition, dict) else None
    predicted_text = recognition["text"] if ocr_details is not None else recognition
    if ocr_details is not None:
        ocr_details["input_image"] = ocr_path.name
        ocr_details["preparation"] = preparation
        (output_folder / "ocr.json").write_text(
            json.dumps(ocr_details, ensure_ascii=False, indent=2), encoding="utf-8")
        for warning in ocr_details["warnings"]:
            print("Cảnh báo OCR:", warning)

    # 6. Lưu văn bản OCR ra file TXT.
    text_path.write_text(
        predicted_text,
        encoding="utf-8",
    )

    # Lưu nguồn và cấu hình để có thể đối chiếu kết quả sau này.
    metadata = {
        "source_image": str(image_path.resolve()),
        "source_sha256": hashlib.sha256(image_bytes).hexdigest(),
        "input_type": input_type,
        "language": language,
        "psm": psm,
        "tessdata_dir": None if tessdata_dir is None else str(tessdata_dir.resolve()),
        "reference_file": None if reference_path is None else str(reference_path.resolve()),
        "scanner_status": status,
        "page_detector_status": detector_status,
        "content_detection": content_details,
        "scanner_method_requested": scanner_method or "configured_default",
        "page_detector_method": detector_method,
        "page_crop_check": page_crop_check,
        "quality": scan_info.get("quality"),
        "enhancement": scan_info.get("enhancement"),
        "rejected_page_corners": rejected_corners,
        "warnings": warnings,
        "review_recommended": bool(warnings) or status == "uncertain",
        "corners_original": corners,
        "H_source_to_warp": matrix_h,
        "T_source_to_output": matrix_t,
        "ocr": None if ocr_details is None else {
            key: ocr_details[key] for key in ("word_count", "mean_word_confidence",
                                             "low_confidence_word_count", "warnings",
                                             "confidence_note", "coordinate_space", "reading_order")},
        "ocr_model_sha256": {},
        "ocr_preparation": preparation,
        "ocr_input_image": ocr_path.name,
        "T_source_to_ocr": (np.array(preparation["T_scan_to_ocr"]) @
                             (np.eye(3) if matrix_t is None else np.array(matrix_t))).tolist(),
        "source_sha256_code": {
            str(path.relative_to(PROJECT_ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (Path(__file__), Path(__file__).parent / "ocr/recognize.py",
                         Path(__file__).parent / "ocr/prepare_image.py")
        },
    }
    tessdata = tessdata_dir or Path(r"C:\Program Files\Tesseract-OCR\tessdata")
    for name in language.split("+"):
        model_path = tessdata / (name + ".traineddata")
        if model_path.is_file():
            metadata["ocr_model_sha256"][name] = hashlib.sha256(model_path.read_bytes()).hexdigest()
    if ocr_details is not None and ocr_details["warnings"]:
        metadata["review_recommended"] = True
    (output_folder / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Đánh giá tùy chọn trên toàn bộ văn bản, không tự tạo nhãn chuẩn.
    if reference_text is not None:
        prediction = normalize_text(predicted_text)
        reference_words = reference_text.split()
        char_errors = edit_distance(reference_text, prediction)
        word_errors = edit_distance(reference_words, prediction.split())
        evaluation = {
            "reference_file": str(reference_path.resolve()),
            "normalization": "Unicode NFC, gộp khoảng trắng; phân biệt hoa thường và dấu câu",
            "char_errors": char_errors,
            "reference_characters": len(reference_text),
            "cer": char_errors / len(reference_text),
            "word_errors": word_errors,
            "reference_words": len(reference_words),
            "wer": word_errors / len(reference_words),
            "note": "So sánh văn bản toàn trang; lỗi thứ tự đọc và nội dung nhãn ảnh hưởng kết quả.",
        }
        evaluation_path = output_folder / "evaluation.json"
        evaluation_path.write_text(json.dumps(evaluation, ensure_ascii=False, indent=2), encoding="utf-8")
        print("CER:", round(evaluation["cer"] * 100, 2), "%")
        print("WER:", round(evaluation["wer"] * 100, 2), "%")
        print("Đã lưu đánh giá:", evaluation_path)

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
        choices=[1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
        help="Chế độ bố cục của Tesseract; mô hình FUNSD mặc định dùng PSM 11.",
    )

    parser.add_argument(
        "--tessdata-dir",
        help="Thư mục chứa file .traineddata khi dùng mô hình riêng.",
    )
    parser.add_argument(
        "--ocr-model",
        choices=["auto", "standard", "funsd"],
        default="auto",
        help="auto: dùng mô hình FUNSD cho tiếng Anh; standard: Tesseract gốc; funsd: mô hình FUNSD.",
    )
    parser.add_argument(
        "--reference",
        help="File TXT chứa văn bản chuẩn của ảnh, tùy chọn để tính CER/WER.",
    )
    parser.add_argument("--scanner-method", choices=["docaligner", "classic"],
                        help="Mặc định DocAligner theo cấu hình; classic dùng Canny/Otsu để đối chứng.")
    parser.add_argument("--no-ocr-prepare", action="store_true",
                        help="Bỏ phóng ảnh nhỏ/thêm viền OCR để đối chứng, không thay scanner.")

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
        reference_path=Path(args.reference) if args.reference else None,
        scanner_method=args.scanner_method,
        ocr_prepare=not args.no_ocr_prepare,
    )

    print()
    print("===== VĂN BẢN NHẬN DẠNG =====")
    print(text)


if __name__ == "__main__":
    main()
