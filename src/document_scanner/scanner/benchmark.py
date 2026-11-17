"""Chốt tập phát triển và đo scanner khung trang trước/sau cải tiến."""
import argparse
from concurrent.futures import ThreadPoolExecutor
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

from detect import detect_document, polygon_iou
from geometry import build_scan

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "docs/results/scanner_dev_manifest.csv"
RAW = ROOT / "data/raw/smartdoc"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def prepare_samples():
    # Chỉ chốt danh sách một lần. Các lần so sánh dùng lại đúng file này.
    if not MANIFEST.exists():
        full = pd.read_csv(ROOT / "data/interim/manifest_with_split.csv")
        validation = full[(full["split"] == "val") & (full["validation_status"] == "valid")]
        groups = []
        for _, group in validation.groupby(["bg_name", "model_name"], sort=True):
            group = group.sort_values(["frame_index", "image_path"])
            # Trải đều theo chuỗi khung hình; không xem IoU để chọn ảnh.
            indices = np.linspace(0, len(group) - 1, min(10, len(group))).round().astype(int)
            groups.append(group.iloc[indices])
        if not groups:
            raise ValueError("Không có ảnh validation hợp lệ.")
        samples = pd.concat(groups).sort_values("image_path").reset_index(drop=True)
        samples["image_sha256"] = [sha256(RAW / path) for path in samples["image_path"]]
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        samples.to_csv(MANIFEST, index=False)
    samples = pd.read_csv(MANIFEST)
    if samples.empty or samples["image_path"].duplicated().any() or not samples["split"].eq("val").all():
        raise ValueError("Tập phát triển phải chỉ chứa validation, không rỗng và không trùng ảnh.")
    for row in samples.itertuples(index=False):
        if sha256(RAW / row.image_path) != row.image_sha256:
            raise ValueError("Ảnh nguồn đã thay đổi: " + row.image_path)
    return samples


def corner_error(predicted, expected, diagonal):
    # Ghép theo chu trình để không phạt khác vị trí bắt đầu của bốn góc.
    distances = []
    for target in (expected, expected[::-1]):
        for offset in range(4):
            distances.append(np.linalg.norm(predicted - np.roll(target, offset, axis=0), axis=1).mean())
    return float(min(distances) / diagonal)


def measure(row):
    image_bytes = (RAW / row.image_path).read_bytes()
    image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Không đọc được ảnh: " + row.image_path)
    expected = np.array([[getattr(row, c + "_x"), getattr(row, c + "_y")]
                         for c in ("tl", "tr", "br", "bl")], np.float32)
    start = time.perf_counter()
    detection = detect_document(image)
    detected_at = time.perf_counter()
    predicted = detection["corners"]
    scanned = None
    error = ""
    if predicted is not None:
        try:
            scanned, _, _ = build_scan(image, predicted)
        except (ValueError, cv2.error) as exception:
            error = str(exception)
    finished = time.perf_counter()
    iou = polygon_iou(predicted, expected) if predicted is not None else 0.0
    result = {
        "image_path": row.image_path, "bg_name": row.bg_name, "model_name": row.model_name,
        "image_sha256": hashlib.sha256(image_bytes).hexdigest(),
        "split": row.split, "status": detection["status"], "method": detection["method"],
        "detected": predicted is not None, "scan_created": scanned is not None,
        "iou": iou, "passed": iou >= 0.9 and scanned is not None,
        "corner_error_normalized": corner_error(predicted, expected, np.hypot(*image.shape[:2]))
        if predicted is not None else None,
        "score": detection["score"], "candidate_count": detection["candidate_count"],
        "warnings": ";".join(detection["warnings"]), "warp_error": error,
        "detection_ms": (detected_at - start) * 1000,
        "detect_and_warp_ms": (finished - start) * 1000,
    }
    quality = detection.get("quality", {})
    result.update(edge_support=quality.get("edge_support"), contour_fit=quality.get("fit"),
                  min_side_support=min(quality["edge_support_per_side"])
                  if "edge_support_per_side" in quality else None)
    for i in range(4):
        for j, axis in enumerate(("x", "y")):
            result[f"pred_{i}_{axis}"] = float(predicted[i, j]) if predicted is not None else None
    return result


def summarize(report):
    corners = report["corner_error_normalized"].dropna()
    return {
        "images": len(report), "detected": int(report["detected"].sum()),
        "scans_created": int(report["scan_created"].sum()),
        "not_detected": int((~report["detected"]).sum()),
        "no_candidate": int((report["status"] == "no_candidate").sum()),
        "rejected_low_confidence": int((report["status"] == "low_confidence").sum()),
        "passed_iou_0_9": int(report["passed"].sum()), "pass_rate": float(report["passed"].mean()),
        "mean_iou_including_misses": float(report["iou"].mean()),
        "mean_corner_error_detected_only": float(corners.mean()) if len(corners) else None,
        "mean_detection_ms": float(report["detection_ms"].mean()),
        "p95_detection_ms": float(report["detection_ms"].quantile(0.95)),
        "mean_detect_and_warp_ms": float(report["detect_and_warp_ms"].mean()),
        "warp_failures": int(((report["detected"]) & (~report["scan_created"])).sum()),
    }


def save_examples(report, samples, output, run_name):
    # Tối đa ba ảnh/nền: đạt, không tìm thấy và có khung nhưng sai.
    selected = []
    for _, group in report.groupby("bg_name", sort=True):
        for condition in (group["passed"], ~group["detected"], group["detected"] & ~group["passed"]):
            pool = group[condition].sort_values("image_path")
            if not pool.empty:
                selected.append(pool.iloc[0])
    tiles = []
    records = []
    for number, result in enumerate(selected, 1):
        row = samples[samples["image_path"] == result.image_path].iloc[0]
        image = cv2.imdecode(np.frombuffer((RAW / result.image_path).read_bytes(), np.uint8), cv2.IMREAD_COLOR)
        expected = np.array([[row[c + "_x"], row[c + "_y"]] for c in ("tl", "tr", "br", "bl")])
        scale = 480 / image.shape[1]
        preview = cv2.resize(image, (480, int(image.shape[0] * scale)))
        cv2.polylines(preview, [(expected * scale).round().astype(np.int32)], True, (0, 200, 0), 2)
        scan_path = ""
        if result.detected:
            points = np.array([[result[f"pred_{i}_x"], result[f"pred_{i}_y"]] for i in range(4)], np.float32)
            cv2.polylines(preview, [(points * scale).round().astype(np.int32)], True, (0, 0, 255), 2)
            if result.scan_created:
                scanned, _, _ = build_scan(image, points)
                destination = ROOT / "data/processed/scanner_dev" / run_name / f"{number:02d}.png"
                destination.parent.mkdir(parents=True, exist_ok=True)
                ok, encoded = cv2.imencode(".png", scanned)
                if not ok:
                    raise OSError("Không mã hóa được ảnh scan.")
                destination.write_bytes(encoded.tobytes())
                scan_path = destination.relative_to(ROOT).as_posix()
        tile = np.full((350, 500, 3), 255, np.uint8)
        tile[40:40 + preview.shape[0], 10:490] = preview
        cv2.putText(tile, f"{number:02d} {result.bg_name} IoU={result.iou:.3f}", (10, 24), 0, .55, (0, 0, 0), 1)
        cv2.putText(tile, "green=label red=prediction", (10, 335), 0, .5, (0, 0, 0), 1)
        tiles.append(tile)
        records.append({"example": number, "image_path": result.image_path, "iou": result.iou,
                        "status": result.status, "scan_path": scan_path})
    sheet = np.full((((len(tiles) + 2) // 3) * 350, 1500, 3), 255, np.uint8)
    for index, tile in enumerate(tiles):
        y, x = (index // 3) * 350, (index % 3) * 500
        sheet[y:y + 350, x:x + 500] = tile
    cv2.imwrite(str(output / "examples.jpg"), sheet)
    pd.DataFrame(records).to_csv(output / "examples.csv", index=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-name", default="baseline", help="Tên mới cho mỗi phương án; không ghi đè kết quả cũ.")
    parser.add_argument("--remaining-validation", action="store_true", help="Kiểm chứng trên validation ngoài tập phát triển cố định.")
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("workers phải lớn hơn 0.")
    if not args.run_name or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in args.run_name):
        parser.error("Tên chỉ gồm chữ, số, dấu gạch ngang hoặc gạch dưới.")
    output = ROOT / "artifacts/scanner_dev" / args.run_name
    if output.exists() or (ROOT / "data/processed/scanner_dev" / args.run_name).exists():
        raise FileExistsError("Tên lần chạy đã tồn tại; chọn --run-name khác để giữ mốc cũ.")
    samples = prepare_samples()
    if args.remaining_validation:
        full = pd.read_csv(ROOT / "data/interim/manifest_with_split.csv")
        samples = full[(full["split"] == "val") & (full["validation_status"] == "valid")
                       & (~full["image_path"].isin(samples.image_path))].copy()
        if samples.empty or samples.image_path.duplicated().any():
            raise ValueError("Tập kiểm chứng rỗng hoặc trùng ảnh.")
    source = output / "source"
    shutil.copytree(ROOT / "src/document_scanner", source / "document_scanner", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(ROOT / "configs", source / "configs")
    shutil.copy2(ROOT / "requirements.txt", source / "requirements.txt")
    if args.remaining_validation:
        samples.to_csv(output / "manifest.csv", index=False)
    else:
        shutil.copy2(MANIFEST, output / "manifest.csv")
    info = {
        "complete": False, "created_at": datetime.now().astimezone().isoformat(),
        "scope": "page detector + perspective warp; excludes content fallback and OCR",
        "selection": "remaining validation excluding fixed development set" if args.remaining_validation
        else "10 evenly spaced frames per validation background/document group; no outcome-based selection",
        "manifest_sha256": sha256(output / "manifest.csv"),
        "fixed_dev_manifest_sha256": sha256(MANIFEST), "workers": args.workers,
        "python": platform.python_version(),
        "opencv": cv2.__version__, "numpy": np.__version__, "pandas": pd.__version__,
        "source_sha256": {p.relative_to(source).as_posix(): sha256(p) for p in sorted(source.rglob("*")) if p.is_file()},
        "model_sha256": {p.relative_to(ROOT).as_posix(): sha256(p) for p in sorted((ROOT / "models").rglob("*.traineddata"))},
        "test_scored": False,
    }
    write_json(output / "run_info.json", info)
    cv2.setNumThreads(1)
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        for index, result in enumerate(executor.map(measure, samples.itertuples(index=False)), 1):
            results.append(result)
            if index % 250 == 0 or index == len(samples):
                print(f"Đã xử lý {index}/{len(samples)}", flush=True)
    report = pd.DataFrame(results)
    report.to_csv(output / "results.csv", index=False)
    summary = {"overall": summarize(report), "by_background": {
        name: summarize(group) for name, group in report.groupby("bg_name")}}
    write_json(output / "summary.json", summary)
    save_examples(report, samples, output, args.run_name)
    info["complete"] = True
    write_json(output / "run_info.json", info)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("Kết quả:", output)


if __name__ == "__main__":
    main()
