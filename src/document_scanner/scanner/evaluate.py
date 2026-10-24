"""Chấm dự đoán đã lưu trên train/validation; không mở nhãn test để chấm."""
import argparse
import json
from pathlib import Path
import shutil

import cv2
import numpy as np
import pandas as pd

from detect import detect_document, polygon_iou

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SMARTDOC_ROOT = PROJECT_ROOT / "data" / "raw" / "smartdoc"
MANIFEST_PATH = PROJECT_ROOT / "data" / "interim" / "manifest_with_split.csv"
BATCH_ROOT = PROJECT_ROOT / "artifacts" / "week2" / "batch"


def resolve_scan_path(row, run_folder):
    # Lần chạy mới lưu đường dẫn tính từ gốc dự án; vẫn đọc được kiểu cũ.
    base = PROJECT_ROOT if getattr(row, "scan_path_base", "run") == "project" else run_folder
    return base / row.scan_path


def summarize(report):
    summary = {
        "images": len(report), "iou_threshold": 0.9,
        "detected": int(report["detected"].sum()),
        "scans_created": int(report["scan_created"].sum()),
        "passed": int(report["passed"].sum()),
        "pass_rate": float(report["passed"].mean()),
        "mean_iou": float(report["iou"].mean()),
        "uncertain": int((report["status"] == "uncertain").sum()),
        "passed_without_warning": int((report["passed"] & (report["status"] == "ok")).sum()),
        "accuracy_status_counts": {str(k): int(v) for k, v in report["accuracy_status"].value_counts().items()},
    }
    for column in ("detection_ms", "warp_ms", "total_ms"):
        values = report[column].dropna()
        summary[column] = {
            "mean": float(values.mean()) if len(values) else None,
            "median": float(values.median()) if len(values) else None,
            "p95": float(values.quantile(0.95)) if len(values) else None,
        }
    return summary


def score_results(results, manifest):
    # Giữ nguyên mẫu số, kể cả ảnh không đọc được hoặc không tìm được giấy.
    dev = manifest[manifest["split"].isin(["train", "val"])]
    columns = ["image_path", "split"] + [corner + "_" + axis
                for corner in ("tl", "tr", "br", "bl") for axis in ("x", "y")]
    report = results[results["split"].isin(["train", "val"])].merge(
        dev[columns], on=["image_path", "split"], how="left", validate="one_to_one",
    )
    if report[["tl_x", "tl_y", "br_x", "br_y"]].isna().any().any():
        raise ValueError("Có ảnh không khớp manifest.")
    ious = []
    for row in report.itertuples(index=False):
        if not row.detected:
            ious.append(0.0)
            continue
        predicted = [[getattr(row, "pred_" + str(i) + "_x"),
                      getattr(row, "pred_" + str(i) + "_y")] for i in range(4)]
        expected = [[getattr(row, c + "_x"), getattr(row, c + "_y")]
                    for c in ("tl", "tr", "br", "bl")]
        ious.append(polygon_iou(predicted, expected))
    report["iou"] = ious
    report["passed"] = (report["iou"] >= 0.9) & report["scan_created"]
    report["accuracy_status"] = np.where(
        report["passed"], "matched",
        np.where(report["detected"], "low_iou_or_warp_failed", "no_document"),
    )
    return report


def select_examples(report):
    # Chọn 5 ca đạt và 5 ca lỗi, ưu tiên có nhiều nền và kiểu lỗi.
    validation = report[report["split"] == "val"]
    selected = []
    for passed in (True, False):
        pool = validation[validation["passed"] == passed].sample(frac=1, random_state=42)
        first = pool.drop_duplicates(["bg_name", "accuracy_status"]).head(5)
        extra = pool[~pool["image_path"].isin(first["image_path"])].head(5 - len(first))
        selected.append(pd.concat([first, extra]))
    return pd.concat(selected)


def make_examples(report, run_folder):
    examples_folder = run_folder / "examples"
    examples_folder.mkdir(exist_ok=True)
    selected = select_examples(report)
    records = []
    for number, row in enumerate(selected.itertuples(index=False), 1):
        label = "good" if row.passed else "failed"
        folder = examples_folder / (str(number).zfill(2) + "_" + label)
        folder.mkdir(exist_ok=True)
        image = cv2.imread(str(SMARTDOC_ROOT / row.image_path))
        detection = detect_document(image)
        debug = detection["debug"]
        # Nguồn được tham chiếu trong JSON; chỉ lưu bản thu nhỏ để minh họa.
        cv2.imwrite(str(folder / "01_input.jpg"), debug["resized"])
        cv2.imwrite(str(folder / "02_edges.png"), debug["edges"])
        cv2.imwrite(str(folder / "03_mask.png"), debug["mask"])
        candidates = debug["resized"].copy()
        for points in debug["candidates"]:
            cv2.polylines(candidates, [points.astype(np.int32).reshape(-1, 1, 2)],
                          True, (0, 180, 255), 1)
        cv2.imwrite(str(folder / "04_candidates.jpg"), candidates)
        overlay = debug["resized"].copy()
        scales = np.array([overlay.shape[1] / image.shape[1], overlay.shape[0] / image.shape[0]])
        expected = np.array([[getattr(row, c + "_x"), getattr(row, c + "_y")]
                             for c in ("tl", "tr", "br", "bl")])
        cv2.polylines(overlay, [np.round(expected * scales).astype(np.int32).reshape(4, 1, 2)],
                      True, (0, 200, 0), 3)
        if row.detected:
            points = np.array([[getattr(row, "pred_" + str(i) + "_x"),
                                getattr(row, "pred_" + str(i) + "_y")] for i in range(4)])
            draw = np.round(points * scales).astype(np.int32)
            cv2.polylines(overlay, [draw.reshape(4, 1, 2)], True, (0, 0, 255), 2)
            for i, point in enumerate(draw):
                cv2.putText(overlay, str(i), tuple(point + 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                cv2.arrowedLine(overlay, tuple(point), tuple(draw[(i + 1) % 4]), (0, 0, 255), 1)
        cv2.imwrite(str(folder / "05_corners.jpg"), overlay)
        if row.scan_created:
            shutil.copy2(resolve_scan_path(row, run_folder), folder / "06_warp.png")
        record = {
            "example": folder.name, "image_path": row.image_path,
            "split": row.split, "iou": row.iou, "passed": bool(row.passed),
            "status": row.status, "warnings": row.warnings if isinstance(row.warnings, str) else "",
            "accuracy_status": row.accuracy_status,
            "overlay_legend": "green=ground_truth; red=prediction",
        }
        (folder / "result.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
        records.append(record)
    pd.DataFrame(records).to_csv(examples_folder / "index.csv", index=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, help="Thư mục batch; mặc định lần chạy xong gần nhất.")
    parser.add_argument("--examples", action="store_true", help="Tạo 5 ca tốt và 5 ca lỗi trên validation.")
    args = parser.parse_args()
    run_folder = args.run
    if run_folder is None:
        latest = json.loads((BATCH_ROOT / "latest.json").read_text(encoding="utf-8"))
        run_folder = PROJECT_ROOT / latest["run_folder"]
    info = json.loads((run_folder / "run_info.json").read_text(encoding="utf-8"))
    if not info["complete"]:
        raise ValueError("Batch chưa chạy xong.")
    results = pd.read_csv(run_folder / "results.csv")
    if len(results) != info["images_requested"] or results["image_path"].duplicated().any():
        raise ValueError("Kết quả thiếu ảnh hoặc trùng ảnh.")
    report = score_results(results, pd.read_csv(MANIFEST_PATH))
    output = run_folder / "evaluation"
    output.mkdir(exist_ok=True)
    report.to_csv(output / "results_dev.csv", index=False)
    report[~report["passed"]].to_csv(output / "failed_cases.csv", index=False)
    # Hàng đợi tham khảo; không yêu cầu người dùng sửa tay toàn bộ các ca này.
    report[(~report["passed"]) | report["needs_review"]].to_csv(output / "review_queue.csv", index=False)
    summaries = {split: summarize(group) for split, group in report.groupby("split")}
    (output / "summary.json").write_text(
        json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    groups = report.groupby(["split", "bg_name"]).agg(
        images=("image_path", "size"), detected=("detected", "sum"),
        scans_created=("scan_created", "sum"), passed=("passed", "sum"),
        mean_iou=("iou", "mean"),
    )
    groups["pass_rate"] = groups["passed"] / groups["images"]
    groups.to_csv(output / "by_background.csv")
    if args.examples:
        # Không tạo debug bằng code khác phiên bản đã chạy batch.
        import hashlib
        for name in ("detect.py", "geometry.py"):
            current = hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
            if current != info["source_sha256"][name]:
                raise ValueError("Code đã đổi; dùng snapshot của batch để tạo minh họa.")
        make_examples(report, run_folder)
    print(json.dumps(summaries, ensure_ascii=False, indent=2))
    print("Đã lưu:", output)
    print("Không tính điểm test; không đưa kết quả sửa tay vào chỉ số tự động.")


if __name__ == "__main__":
    main()

