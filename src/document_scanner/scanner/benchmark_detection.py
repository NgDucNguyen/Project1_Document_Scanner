"""Kiểm tra detect toàn bộ SmartDoc, không tạo ảnh scan và không chấm nhãn test."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import platform
import shutil
import time

import cv2
import numpy as np
import pandas as pd

from detect import CONFIG, CONFIG_PATH, detect_document, polygon_iou

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "data/interim/manifest_with_split.csv"
RAW = ROOT / "data/raw/smartdoc"


def process_one(row):
    start = time.perf_counter()
    result = {"image_path": row.image_path, "split": row.split, "bg_name": row.bg_name,
              "model_name": row.model_name, "status": "processing_error", "detected": False,
              "score": None, "method": None, "candidate_count": 0, "warnings": "",
              "image_sha256": "", "iou": None, "iou_ge_0_9": None,
              "detection_ms": None, "total_ms": None, "error": ""}
    for i in range(4):
        for axis in ("x", "y"):
            result[f"pred_{i}_{axis}"] = None
    try:
        image_bytes = (RAW / row.image_path).read_bytes()
        result["image_sha256"] = hashlib.sha256(image_bytes).hexdigest()
        image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            result["status"] = "unreadable_image"
        else:
            started = time.perf_counter()
            detection = detect_document(image)
            result["detection_ms"] = (time.perf_counter() - started) * 1000
            for key in ("status", "score", "method", "candidate_count"):
                result[key] = detection[key]
            result["warnings"] = ";".join(detection["warnings"])
            corners = detection["corners"]
            result["detected"] = corners is not None
            if corners is not None:
                for i, point in enumerate(corners):
                    result[f"pred_{i}_x"], result[f"pred_{i}_y"] = map(float, point)
            # Nhãn test không được đọc để tính điểm hay tác động vào detector.
            if row.split in ("train", "val"):
                expected = np.array([[getattr(row, c + "_x"), getattr(row, c + "_y")]
                                     for c in ("tl", "tr", "br", "bl")], np.float32)
                result["iou"] = polygon_iou(corners, expected) if corners is not None else 0.0
                result["iou_ge_0_9"] = result["iou"] >= .9
    except (OSError, ValueError, cv2.error) as error:
        result["error"] = str(error)
    result["total_ms"] = (time.perf_counter() - start) * 1000
    return result


def summarize(frame):
    records = []
    for split, group in [("all", frame), *frame.groupby("split")]:
        for background, part in [("all", group), *group.groupby("bg_name")]:
            # Tổng all gồm test chỉ thống kê detect, không gộp điểm train/val vào mẫu số có test.
            scored = split in ("train", "val")
            records.append({"split": split, "background": background, "images": len(part),
                            "detected": int(part.detected.sum()), "detection_rate": float(part.detected.mean()),
                            "no_candidate": int((part.status == "no_candidate").sum()),
                            "low_confidence": int((part.status == "low_confidence").sum()),
                            "uncertain": int((part.status == "uncertain").sum()),
                            "errors": int(part.status.isin(["processing_error", "unreadable_image"]).sum()),
                            "iou_ge_0_9": int(part.iou_ge_0_9.fillna(False).astype(bool).sum()) if scored else None,
                            "iou_pass_rate": float(part.iou_ge_0_9.fillna(False).astype(bool).mean()) if scored else None,
                            "mean_iou": float(part.iou.fillna(0).mean()) if scored else None})
    return pd.DataFrame(records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-name", default="full_detection_day3")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if args.workers < 1 or not args.run_name or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in args.run_name):
        parser.error("Tên lần chạy chỉ gồm chữ/số/_/- và workers phải lớn hơn 0.")
    output = ROOT / "artifacts/scanner_dev" / args.run_name
    if output.exists():
        raise FileExistsError("Kết quả đã tồn tại, không ghi đè: " + str(output))
    samples = pd.read_csv(MANIFEST)
    if samples.empty or samples.image_path.duplicated().any() or not samples.validation_status.eq("valid").all():
        raise ValueError("Manifest rỗng, trùng ảnh hoặc có dòng không hợp lệ.")
    source = output / "source"
    source.mkdir(parents=True)
    for name in ("detect.py", "benchmark_detection.py"):
        shutil.copy2(Path(__file__).with_name(name), source / name)
    shutil.copy2(CONFIG_PATH, source / "scanner.json")
    shutil.copy2(MANIFEST, output / "manifest.csv")
    info = {"complete": False, "started_at": datetime.now().astimezone().isoformat(),
            "images_requested": len(samples), "workers": args.workers, "config_version": CONFIG["version"],
            "scope": "detection only; no warp, no OCR, no saved images; train/val IoU only",
            "python": platform.python_version(), "opencv": cv2.__version__, "numpy": np.__version__,
            "test_scored": False, "manifest_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
            "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in source.iterdir()}}
    info_path = output / "run_info.json"
    info_path.write_text(json.dumps(info, indent=2), encoding="utf-8")
    cv2.setNumThreads(1)
    started = time.perf_counter()
    print("Kết quả:", output, flush=True)
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        results = executor.map(process_one, samples.itertuples(index=False))
        with open(output / "results.csv", "w", newline="", encoding="utf-8") as file:
            writer = None
            for index, result in enumerate(results, 1):
                if writer is None:
                    writer = csv.DictWriter(file, fieldnames=list(result))
                    writer.writeheader()
                writer.writerow(result)
                if index % 500 == 0 or index == len(samples):
                    file.flush()
                    print(f"Đã detect {index}/{len(samples)}; {time.perf_counter() - started:.1f} giây", flush=True)
    frame = pd.read_csv(output / "results.csv")
    if len(frame) != len(samples) or frame.image_path.duplicated().any():
        raise ValueError("Kết quả thiếu/trùng ảnh.")
    if frame.loc[frame.split == "test", ["iou", "iou_ge_0_9"]].notna().any().any():
        raise AssertionError("Không được chấm nhãn test.")
    summary = summarize(frame)
    summary.to_csv(output / "summary.csv", index=False)
    summary.to_csv(ROOT / "docs/results/scanner_full_detection_summary.csv", index=False)
    info.update(complete=True, finished_at=datetime.now().astimezone().isoformat(),
                images=len(frame), wall_seconds=time.perf_counter() - started,
                detected=int(frame.detected.sum()), status_counts=frame.status.value_counts().to_dict())
    info_path.write_text(json.dumps(info, indent=2), encoding="utf-8")
    print(summary[summary.background == "all"].to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
