"""So sánh vùng chữ dự phòng: giữ nhãn từ FUNSD và đo OCR mẫu có TXT."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time

import cv2
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src/document_scanner"))
sys.path.insert(0, str(ROOT / "src/document_scanner/ocr"))
from scanner.content_scan import crop_content
from ocr.prepare_funsd_training import select_validation_pages
from ocr.recognize import recognize_image
from ocr.metrics import calculate_cer, calculate_wer


def samples():
    result = []
    funsd = ROOT / "data/raw/funsd/dataset/training_data"
    images = sorted((funsd / "images").glob("*.png"))
    validation = select_validation_pages(images)
    for path in images:
        if path.stem in validation:
            result.append(("funsd_val", path, funsd / "annotations" / (path.stem + ".json"), None))
    for path in sorted((ROOT / "data/raw/rdtag_sample/images").glob("*.jpg")):
        # Chưa dùng TXT RDTAG để chọn phương pháp: nhãn/layout có vấn đề đã ghi ở báo cáo trước.
        result.append(("rdtag_dev", path, None, None))
    folder = ROOT / "data/raw/thu_ocr"
    for name, reference in [("anh.jpg", "nhan.txt"), ("anh_test_02.jpg", "nhan_test_02.txt"),
                            ("anh_thu.png", None), ("anh_tu_chup.jpg", None)]:
        path = folder / name
        if path.exists():
            result.append(("personal", path, None, folder / reference if reference else None))
    return result


def retention(annotation_path, transform, crop_shape):
    annotation = json.loads(annotation_path.read_text(encoding="utf-8"))
    height, width = crop_shape[:2]
    crop_polygon = np.array([[0, 0], [width, 0], [width, height], [0, height]], np.float32)
    areas, intersections, full = [], [], []
    for region in annotation["form"]:
        for word in region.get("words", []):
            x1, y1, x2, y2 = word["box"]
            if x2 <= x1 or y2 <= y1 or not word.get("text", "").strip():
                continue
            points = np.array([[[x1, y1], [x2, y1], [x2, y2], [x1, y2]]], np.float32)
            points = cv2.perspectiveTransform(points, transform.astype(np.float64))[0]
            area = cv2.contourArea(points)
            intersection, _ = cv2.intersectConvexConvex(points, crop_polygon)
            areas.append(area)
            intersections.append(min(float(intersection), area))
            full.append(intersection >= .98 * area)
    return {"annotated_words": len(areas), "fully_retained_words": int(sum(full)),
            "word_retention": float(np.mean(full)) if full else None,
            "annotated_area_retention": float(sum(intersections) / sum(areas)) if areas else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--method", choices=["tesseract", "dbnet"], required=True)
    args = parser.parse_args()
    output = ROOT / "artifacts/scanner_dev" / ("day4_" + args.method)
    if output.exists():
        raise FileExistsError("Lần chạy đã tồn tại: " + str(output))
    output.mkdir(parents=True)
    source = output / "source"
    source.mkdir()
    for name in ("content_scan.py", "text_regions.py", "benchmark_content.py"):
        shutil.copy2(Path(__file__).with_name(name), source / name)
    cv2.setNumThreads(1)
    records, metadata = [], {}
    selected = samples()
    for index, (dataset, path, annotation, reference) in enumerate(selected, 1):
        image_bytes = path.read_bytes()
        image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
        started = time.perf_counter()
        result = crop_content(image, "funsd_eng", ROOT / "models/funsd_english", method=args.method)
        record = {"image_path": path.relative_to(ROOT).as_posix(), "dataset": dataset,
                  "image_sha256": hashlib.sha256(image_bytes).hexdigest(), "method": args.method,
                  "created": result is not None, "crop_seconds": time.perf_counter() - started}
        if result is not None:
            crop, transform, details = result
            record.update(angle=details["rotation_degrees"], area_ratio=details["content_box_area_ratio"],
                          ambiguous_groups=details.get("ambiguous_groups", False))
            metadata[record["image_path"]] = {"T": transform.tolist(), "details": details}
            if annotation is not None:
                record.update(retention(annotation, transform, crop.shape))
            # Giữ ảnh cá nhân và hai ảnh đầu mỗi tập làm minh họa.
            save = dataset == "personal" or sum(r["dataset"] == dataset for r in records) < 2
            if save or reference:
                target = ROOT / "data/processed/scanner_content" / args.method / (path.stem + ".png")
                target.parent.mkdir(parents=True, exist_ok=True)
                ok, data = cv2.imencode(".png", crop)
                if not ok:
                    raise OSError("Không mã hóa được ảnh crop.")
                target.write_bytes(data.tobytes())
                record["crop_path"] = target.relative_to(ROOT).as_posix()
                if reference:
                    prediction = recognize_image(target, "funsd_eng", psm=11, tessdata_dir=ROOT / "models/funsd_english")
                    (target.with_suffix(".txt")).write_text(prediction, encoding="utf-8")
                    expected = reference.read_text(encoding="utf-8-sig")
                    record.update(cer=calculate_cer(expected, prediction), wer=calculate_wer(expected, prediction))
        elif annotation:
            # Không tạo được crop được tính là không giữ được nhãn, không bỏ khỏi mẫu số.
            counts = retention(annotation, np.eye(3), image.shape)
            record.update(annotated_words=counts["annotated_words"], fully_retained_words=0,
                          word_retention=0.0, annotated_area_retention=0.0)
        records.append(record)
        pd.DataFrame(records).to_csv(output / "results.csv", index=False)
        print(f'{args.method} {index}/{len(selected)} {path.name}: {"crop" if result is not None else "none"}', flush=True)
    (output / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "run_info.json").write_text(json.dumps({
        "complete": True, "method": args.method, "images": len(records), "opencv": cv2.__version__,
        "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in source.iterdir()},
        "model_sha256": hashlib.sha256((ROOT / "models/dbnet/DB_TD500_resnet18.onnx").read_bytes()).hexdigest()
        if args.method == "dbnet" else None,
        "scope": "content fallback only; no page detector; FUNSD development validation; RDTAG development; personal photos",
    }, indent=2), encoding="utf-8")
    print("Kết quả:", output)


if __name__ == "__main__":
    main()
