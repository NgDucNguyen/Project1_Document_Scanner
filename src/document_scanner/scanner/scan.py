"""Chạy tự động theo lô, lưu PNG và thông tin của từng ảnh."""
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

from detect import CONFIG, CONFIG_PATH, detect_document
from geometry import build_scan

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SMARTDOC_ROOT = PROJECT_ROOT / "data" / "raw" / "smartdoc"
MANIFEST_PATH = PROJECT_ROOT / "data" / "interim" / "manifest_with_split.csv"
OUTPUT_ROOT = PROJECT_ROOT / "artifacts" / "week2" / "batch"
PROCESSED_ROOT = PROJECT_ROOT / "data" / "processed" / "scan"


def save_image(path, image):
    # PNG không mất chất lượng; mức nén 1 giúp chạy cả bộ nhanh hơn.
    if not cv2.imwrite(str(path), image, [cv2.IMWRITE_PNG_COMPRESSION, 1]):
        raise OSError("Không lưu được ảnh: " + str(path))


def scan_one(row, run_folder):
    start_total = time.perf_counter()
    result = {
        "image_path": row.image_path, "model_name": row.model_name,
        "bg_name": row.bg_name, "split": row.split, "status": "",
        "detected": False, "scan_created": False, "needs_review": True,
        "method": "", "score": None, "warnings": "", "blur_score": None,
        "score_gap": None, "candidate_count": 0, "detection_ms": None,
        "warp_ms": None, "total_ms": None, "scan_path": "", "metadata_path": "",
        "error": "", "scan_path_base": "project",
    }
    for i in range(4):
        result["pred_" + str(i) + "_x"] = None
        result["pred_" + str(i) + "_y"] = None

    # Giữ cấu trúc nguồn, thêm split để tìm ảnh dễ hơn.
    relative = Path("metadata") / row.split / Path(row.image_path).with_suffix("")
    target = run_folder / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    # Ảnh cuối ở processed; JSON và số liệu vẫn ở artifacts.
    scan_path = PROCESSED_ROOT / run_folder.name / row.split / Path(row.image_path).with_suffix(".png")
    metadata = {"source_image": row.image_path, "mode": "automatic",
                "manual_corrected": False, "config_version": CONFIG["version"],
                "corners_original": None, "rotation_clockwise_degrees": 0}
    try:
        image = cv2.imread(str(SMARTDOC_ROOT / row.image_path))
        if image is None:
            result["status"] = "unreadable_image"
        else:
            start_detect = time.perf_counter()
            detection = detect_document(image)
            result["detection_ms"] = (time.perf_counter() - start_detect) * 1000
            for key in ("status", "method", "score", "blur_score", "score_gap", "candidate_count"):
                result[key] = detection[key]
            result["warnings"] = ";".join(detection["warnings"])
            corners = detection["corners"]
            if corners is not None:
                result["detected"] = True
                for i, (x, y) in enumerate(corners):
                    result["pred_" + str(i) + "_x"] = float(x)
                    result["pred_" + str(i) + "_y"] = float(y)
                metadata["corners_original"] = corners.tolist()
                metadata["corner_order"] = "clockwise_from_min_sum_xy"
                start_warp = time.perf_counter()
                scanned, matrix_h, matrix_t = build_scan(image, corners)
                result["warp_ms"] = (time.perf_counter() - start_warp) * 1000
                scan_path.parent.mkdir(parents=True, exist_ok=True)
                save_image(scan_path, scanned)
                result["scan_created"] = True
                result["needs_review"] = detection["status"] != "ok"
                result["scan_path"] = scan_path.relative_to(PROJECT_ROOT).as_posix()
                metadata.update(
                    H_source_to_warp=matrix_h.tolist(), T_source_to_output=matrix_t.tolist(),
                    output_width=scanned.shape[1], output_height=scanned.shape[0],
                )
    except (ValueError, cv2.error) as error:
        # Một ảnh hoặc hình học lỗi không làm dừng các ảnh tiếp theo.
        result["status"] = "processing_error"
        result["error"] = str(error)
    result["total_ms"] = (time.perf_counter() - start_total) * 1000
    result["metadata_path"] = relative.with_suffix(".json").as_posix()
    metadata.update(result)
    with open(target.with_suffix(".json"), "w", encoding="utf-8") as file:
        json.dump(metadata, file, ensure_ascii=False, indent=2)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=["train", "val", "test", "dev", "all"], default="dev")
    parser.add_argument("--limit", type=int, help="Chỉ dùng khi kiểm tra nhanh.")
    parser.add_argument("--workers", type=int, default=1, help="Số ảnh xử lý đồng thời.")
    args = parser.parse_args()
    if args.workers < 1 or (args.limit is not None and args.limit < 1):
        parser.error("workers và limit phải lớn hơn 0.")
    manifest = pd.read_csv(MANIFEST_PATH)
    selected_splits = {"dev": ["train", "val"], "all": ["train", "val", "test"]}
    splits = selected_splits.get(args.split, [args.split])
    samples = manifest[
        manifest["split"].isin(splits) & (manifest["validation_status"] == "valid")
    ]
    if args.limit:
        samples = samples.head(args.limit)
    if samples.empty or samples["image_path"].duplicated().any():
        raise ValueError("Danh sách ảnh rỗng hoặc có đường dẫn trùng.")

    run_name = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    run_folder = OUTPUT_ROOT / run_name
    code_folder = run_folder / "source"
    code_folder.mkdir(parents=True)
    for source in Path(__file__).resolve().parent.glob("*.py"):
        shutil.copy2(source, code_folder / source.name)
    shutil.copy2(CONFIG_PATH, run_folder / "config.json")
    hashes = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(code_folder.glob("*.py"))
    }
    # OpenCV dùng 1 luồng/ảnh để không nhân quá nhiều luồng khi workers > 1.
    cv2.setNumThreads(1)
    run_info = {
        "run_id": run_name, "started_at": datetime.now().isoformat(),
        "selection": args.split, "images_requested": len(samples), "workers": args.workers,
        "python": platform.python_version(), "opencv": cv2.__version__,
        "numpy": np.__version__, "pandas": pd.__version__, "platform": platform.platform(),
        "processor": platform.processor(), "opencv_threads": cv2.getNumThreads(),
        "source_sha256": hashes,
        "manifest_sha256": hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest(),
        "config_sha256": hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest(),
        "test_scored": False, "complete": False,
        "processed_folder": (PROCESSED_ROOT / run_name).relative_to(PROJECT_ROOT).as_posix(),
        "scan_path_base": "project",
    }
    info_path = run_folder / "run_info.json"
    info_path.write_text(json.dumps(run_info, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Thư mục kết quả:", run_folder, flush=True)
    print("Ảnh sau scan:", PROCESSED_ROOT / run_name, flush=True)
    start = time.perf_counter()
    rows = list(samples.itertuples(index=False))
    # Ghi CSV ngay từng ảnh để giữ kết quả nếu người dùng ngắt giữa chừng.
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        results = executor.map(lambda row: scan_one(row, run_folder), rows)
        with open(run_folder / "results.csv", "w", encoding="utf-8", newline="") as file:
            writer = None
            for index, result in enumerate(results, 1):
                if writer is None:
                    writer = csv.DictWriter(file, fieldnames=list(result))
                    writer.writeheader()
                writer.writerow(result)
                if index % 250 == 0 or index == len(rows):
                    file.flush()
                    print("Đã xử lý", index, "/", len(rows), flush=True)

    report = pd.read_csv(run_folder / "results.csv")
    run_info.update(
        complete=True, finished_at=datetime.now().isoformat(),
        wall_seconds=time.perf_counter() - start, images=len(report),
        scans_created=int(report["scan_created"].sum()),
        status_counts={str(k): int(v) for k, v in report["status"].value_counts().items()},
    )
    info_path.write_text(json.dumps(run_info, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT_ROOT / "latest.json").write_text(
        json.dumps({"run_folder": run_folder.relative_to(PROJECT_ROOT).as_posix()}, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(run_info, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

