from pathlib import Path
from datetime import datetime
import argparse
import json

import cv2
import numpy as np

# Các hàm scanner và OCR đã làm trước đó.
from scanner.detect import detect_document
from scanner.geometry import build_scan
from scanner.content_scan import crop_content, page_crop_seems_wrong
from ocr.metrics import edit_distance, normalize_text
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


def process_image(image_path, language, input_type="photo", psm=None, tessdata_dir=None, reference_path=None):
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

    content_details = None
    detector_status = None
    page_crop_check = None
    rejected_corners = None
    if input_type == "photo":
        # 2. Ưu tiên tìm đủ góc trang để nắn phối cảnh.
        detection = detect_document(image)
        status = detection["status"]
        detector_status = status
        corners = detection["corners"]
        warnings = list(detection["warnings"])
        print("Trạng thái tìm khung:", status)
        if warnings:
            print("Cảnh báo:", ", ".join(warnings))
        if corners is None:
            print("Không tìm được đủ góc trang; đang thử tìm vùng chữ...")
            content = crop_content(image, language, tessdata_dir)
            if content is None:
                raise ValueError(
                    "Không tìm được khung tài liệu hoặc đủ chữ để cắt vùng nội dung. "
                    "Hãy kiểm tra lại ảnh hoặc sửa góc bằng tay."
                )
            scanned, matrix_t, content_details = content
            matrix_h = None
            status = "content_fallback"
            warnings.append("content_bounds_not_page")
            print("Đã cắt theo vùng chữ, góc xoay:", content_details["rotation_degrees"], "độ.")
            print("Lưu ý: đây không phải mép trang; hãy kiểm tra scan.png để tránh mất chữ.")
        else:
            scanned, matrix_h, matrix_t = build_scan(image, corners)
            suspect, page_crop_check = page_crop_seems_wrong(image, scanned, language, tessdata_dir)
            if suspect:
                print("Khung trang có quá ít chữ so với ảnh gốc; đang thử vùng chữ...")
                warnings.append("page_crop_text_mismatch")
                content = crop_content(image, language, tessdata_dir)
                if content is not None:
                    rejected_corners = corners.tolist()
                    corners = None
                    scanned, matrix_t, content_details = content
                    matrix_h = None
                    status = "content_fallback"
                    warnings.append("content_bounds_not_page")
                    print("Đã chuyển sang cắt vùng chữ. Hãy kiểm tra scan.png.")
                else:
                    status = "uncertain"
                    print("Không tạo được vùng chữ thay thế; cần kiểm tra ảnh scan.")
    elif input_type == "scan":
        # FUNSD và ảnh đã nắn có thể đưa trực tiếp vào OCR.
        scanned = image
        status = "already_scanned"
        corners = matrix_h = matrix_t = None
        warnings = []
    else:
        raise ValueError("input_type phải là photo hoặc scan.")

    if content_details and content_details.get("content_box_area_ratio", 0) >= 0.8:
        warnings.append("content_frame_broad")
        print("Cảnh báo: vùng chữ chiếm gần toàn ảnh; có thể đã lấy cả nền hoặc bỏ sót chữ.")
        print("Hãy mở scan.png và đối chiếu với ảnh gốc.")

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
        "reference_file": None if reference_path is None else str(reference_path.resolve()),
        "scanner_status": status,
        "page_detector_status": detector_status,
        "content_detection": content_details,
        "page_crop_check": page_crop_check,
        "rejected_page_corners": rejected_corners,
        "warnings": warnings,
        "review_recommended": bool(warnings) or status == "uncertain",
        "corners_original": None if corners is None else corners.tolist(),
        "H_source_to_warp": None if matrix_h is None else matrix_h.tolist(),
        "T_source_to_output": None if matrix_t is None else matrix_t.tolist(),
    }
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
        choices=range(14),
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
    )

    print()
    print("===== VĂN BẢN NHẬN DẠNG =====")
    print(text)


if __name__ == "__main__":
    main()
