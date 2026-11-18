"""Scan một ảnh: tìm góc trang, nếu thiếu thì chọn vùng chữ chính; không xuất OCR."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sys

import cv2
import numpy as np

# Cho phép chạy trực tiếp file hoặc import từ pipeline.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scanner.detect import detect_document
from scanner.geometry import build_scan
from scanner.content_scan import crop_content, page_crop_seems_wrong
from scanner.appearance import assess_document, enhance_document, CONFIG_PATH as SCAN_CONFIG_PATH

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class ScanRejected(ValueError):
    """Giữ lý do từ chối trong metadata, không xuất ảnh scan thành công giả."""
    def __init__(self, message, info):
        super().__init__(message)
        self.info = info


def scan_document(image, method=None, language="eng", tessdata_dir=None, check_content=False, enhance=True):
    """Hàm scan dùng chung cho lệnh scan riêng và pipeline có OCR."""
    detection = detect_document(image, method=method)
    corners = detection["corners"]
    info = {"scanner_status": detection["status"], "page_detector_status": detection["status"],
            "page_detector_method": detection.get("method"), "detector_score": detection.get("score"),
            "warnings": list(detection["warnings"]), "content_detection": None,
            "page_crop_check": None, "rejected_page_corners": None,
            "scanner_method_requested": method or "configured_default"}
    matrix_h = None
    if corners is not None:
        scanned, matrix_h, matrix_t = build_scan(image, corners)
        # Pipeline OCR có thể yêu cầu kiểm tra mất chữ như trước.
        # Cả hai chế độ thử dự phòng nếu vùng nắn không đạt chất lượng.
        info["page_quality"] = assess_document(scanned)
        suspect = not info["page_quality"]["accepted"]
        if suspect:
            info["warnings"].append("page_quality_rejected")
        if check_content:
            text_mismatch, info["page_crop_check"] = page_crop_seems_wrong(image, scanned, language, tessdata_dir)
            suspect = suspect or text_mismatch
            if text_mismatch:
                info["warnings"].append("page_crop_text_mismatch")
    else:
        suspect = True
    if suspect:
        content = crop_content(image, language, tessdata_dir)
        if content is None:
            if corners is None:
                info["scanner_status"] = "scan_failed"
                raise ScanRejected("Không tìm được khung tài liệu hoặc vùng chữ chính đủ tin cậy. Hãy sửa góc bằng tay.", info)
            info["scanner_status"] = "uncertain"
        else:
            if corners is not None:
                info["rejected_page_corners"] = corners.tolist()
            scanned, matrix_t, info["content_detection"] = content
            corners = matrix_h = None
            info["scanner_status"] = "content_fallback"
            info["warnings"].append("content_bounds_not_page")
            if info["content_detection"].get("perspective_refinement", {}).get("applied"):
                info["warnings"].append("content_guided_quad_estimated")
                if info["content_detection"]["perspective_refinement"].get("outside_source"):
                    info["warnings"].append("content_quad_outside_source_white_padding")
            region = info["content_detection"].get("region_selection", {})
            if region.get("ambiguous"):
                info["warnings"].append("competing_content_regions")
            if info["content_detection"].get("content_box_area_ratio", 0) >= .8:
                info["warnings"].append("content_frame_broad")
    # Kiểm tra ảnh màu trước tăng cường, không dùng độ sắc nét tăng giả để chấp nhận.
    info["quality"] = assess_document(scanned)
    info["warnings"].extend(info["quality"]["warnings"])
    info.update(corners_original=None if corners is None else corners.tolist(),
                H_source_to_warp=None if matrix_h is None else matrix_h.tolist(),
                T_source_to_output=matrix_t.tolist(),
                review_recommended=bool(info["warnings"]) or info["scanner_status"] == "uncertain")
    if not info["quality"]["accepted"]:
        info["scanner_status"] = "rejected_quality"
        raise ScanRejected("Ảnh bị từ chối: " + ", ".join(info["quality"]["reasons"]), info)
    if enhance:
        scanned, info["enhancement"] = enhance_document(scanned)
    else:
        info["enhancement"] = {"applied": False}
    return scanned, info


def save_image(path, image):
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        raise OSError("Không mã hóa được ảnh: " + str(path))
    encoded.tofile(str(path))


def output_key(source):
    """Cùng đường dẫn ảnh dùng lại một thư mục; khác ảnh cùng tên không đè nhau."""
    source = source.resolve()
    name = re.sub(r"[^\w-]+", "_", source.stem).strip("_")[:50] or "image"
    path_hash = hashlib.sha256(str(source).casefold().encode("utf-8")).hexdigest()[:8]
    return "image_" + name + "_" + path_hash


def clear_managed_images(folder):
    """Xóa đúng tên đầu ra do CLI quản lý, tránh còn ảnh thành công cũ khi lần mới lỗi."""
    folder = folder.resolve()
    root = (PROJECT_ROOT / "data/processed/scan").resolve()
    if not folder.is_relative_to(root) or folder == root:
        raise ValueError("Thư mục đầu ra không nằm trong vùng scan một ảnh.")
    for prefix in ("", "docaligner_", "classic_"):
        for name in ("scan.png", "scan_color.png", "region.png"):
            path = folder / (prefix + name)
            if path.is_file():
                path.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="data/raw/thu_detect/anh_viet.jpg")
    parser.add_argument("--method", choices=["docaligner", "classic", "both"], default="docaligner")
    parser.add_argument("--detect-only", action="store_true", help="Chỉ thử góc trang, không cắt dự phòng.")
    parser.add_argument("--no-enhance", action="store_true", help="Giữ màu ảnh cắt gốc, không làm sáng nền.")
    parser.add_argument("--new-run", action="store_true", help="Chủ động lưu lượt lịch sử riêng thay vì cập nhật kết quả của ảnh.")
    args = parser.parse_args()
    source = Path(args.image).resolve()
    if not source.is_file():
        parser.error("Không tìm thấy ảnh: " + str(source))
    raw = source.read_bytes()
    image = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR) if raw else None
    if image is None:
        parser.error("Không đọc được ảnh: " + str(source))
    methods = ["docaligner", "classic"] if args.method == "both" else [args.method]
    execution_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    run_id = "single_" + execution_id if args.new_run else output_key(source)
    image_dir = PROJECT_ROOT / "data/processed/scan" / run_id
    info_dir = PROJECT_ROOT / "artifacts/scans" / run_id
    image_dir.mkdir(parents=True, exist_ok=True)
    info_dir.mkdir(parents=True, exist_ok=True)
    clear_managed_images(image_dir)
    model_dir = PROJECT_ROOT / "models/funsd_english"
    # Chỉ dùng hộp chữ cho nhánh dự phòng; không xuất văn bản nhận dạng.
    language, model_dir = ("funsd_eng", model_dir) if (model_dir / "funsd_eng.traineddata").is_file() else ("eng", None)
    metadata = {"source_image": str(source), "source_sha256": hashlib.sha256(raw).hexdigest(),
                "execution_id": execution_id, "storage": "history" if args.new_run else "latest_per_image",
                "mode": "detect_only" if args.detect_only else "automatic_scan",
                "content_box_model": language, "complete": False, "results": {}}
    failed = False
    try:
        for method in methods:
            if args.detect_only:
                detection = detect_document(image, method=method)
                if detection["corners"] is None:
                    metadata["results"][method] = {"scanner_status": detection["status"], "scan_path": None}
                    print(method, ": không tìm được bốn góc; đã tắt dự phòng.")
                    failed = True
                    continue
                scanned, matrix_h, matrix_t = build_scan(image, detection["corners"])
                info = {"scanner_status": detection["status"], "corners_original": detection["corners"].tolist(),
                        "warnings": detection["warnings"], "T_source_to_output": matrix_t.tolist()}
            else:
                try:
                    scanned, info = scan_document(image, method, language, model_dir, enhance=not args.no_enhance)
                except ValueError as error:
                    rejected = dict(getattr(error, "info", {}))
                    rejected.update(scanner_status=rejected.get("scanner_status", "scan_failed"),
                                    scan_path=None, error=str(error))
                    metadata["results"][method] = rejected
                    print(method, ":", error)
                    failed = True
                    continue
            prefix = method + "_" if len(methods) > 1 else ""
            scan_path = image_dir / (prefix + "scan.png")
            overlay_path = image_dir / (prefix + "region.png")
            save_image(scan_path, scanned)
            if info.get("enhancement", {}).get("applied"):
                h, w = scanned.shape[:2]
                color = cv2.warpPerspective(image, np.array(info["T_source_to_output"]), (w, h),
                                            borderValue=(255, 255, 255))
                color_path = image_dir / (prefix + "scan_color.png")
                save_image(color_path, color)
                info["color_scan_path"] = color_path.relative_to(PROJECT_ROOT).as_posix()
            # Đưa hình chữ nhật đầu ra về ảnh gốc để thấy vùng thực sự đã cắt.
            h, w = scanned.shape[:2]
            rectangle = np.float32([[[0, 0], [w-1, 0], [w-1, h-1], [0, h-1]]])
            selected = cv2.perspectiveTransform(rectangle, np.linalg.inv(np.array(info["T_source_to_output"])))
            overlay = image.copy()
            cv2.polylines(overlay, [np.round(selected[0]).astype(np.int32)], True, (0, 0, 255), 3)
            save_image(overlay_path, overlay)
            info.update(scan_path=scan_path.relative_to(PROJECT_ROOT).as_posix(),
                        overlay_path=overlay_path.relative_to(PROJECT_ROOT).as_posix())
            metadata["results"][method] = info
            if method == "docaligner":
                model = PROJECT_ROOT / "models/docaligner/fastvit_t8.onnx"
                info["model_sha256"] = hashlib.sha256(model.read_bytes()).hexdigest()
            print(method, ":", info["scanner_status"])
        metadata["complete"] = True
    finally:
        metadata["source_hashes"] = {name: hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest()
                                     for name in ("scan_image.py", "content_scan.py", "geometry.py", "appearance.py",
                                                  "detect.py", "docaligner.py", "classic.py")}
        metadata["scan_config"] = json.loads(SCAN_CONFIG_PATH.read_text(encoding="utf-8"))
        metadata["scan_config_sha256"] = hashlib.sha256(SCAN_CONFIG_PATH.read_bytes()).hexdigest()
        metadata["opencv_version"] = cv2.__version__
        (info_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Xem ảnh:", image_dir)
    print("Thông tin:", info_dir / "metadata.json")
    if any(item.get("scanner_status") == "content_fallback" for item in metadata["results"].values()):
        print("Đã dùng vùng nội dung dự phòng; xem metadata để biết có nắn tứ giác ước lượng hay chỉ cắt chữ.")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
