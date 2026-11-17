"""Ngày 2: truy vết lỗi khung trang bằng nhãn, chỉ dùng để phân tích ngoại tuyến."""
import json
from pathlib import Path
import shutil

import cv2
import numpy as np
import pandas as pd

from benchmark import ROOT, RAW, MANIFEST, prepare_samples, sha256, write_json
from detect import CONFIG_PATH, detect_document, polygon_iou

OUTPUT = ROOT / "artifacts/scanner_dev/day2_audit"


def classify(selected_iou, best_accepted_iou, best_generated_iou):
    if selected_iou >= 0.9:
        return "passed"
    if best_accepted_iou >= 0.9:
        return "ranking_failure"
    if best_generated_iou >= 0.9:
        return "close_quad_rejected"
    if best_generated_iou >= 0.5:
        return "imprecise_proposals"
    return "no_close_proposal"


def examine(row, baseline):
    image = cv2.imdecode(np.frombuffer((RAW / row.image_path).read_bytes(), np.uint8), cv2.IMREAD_COLOR)
    normal = detect_document(image)
    detection = detect_document(image, diagnostics=True)
    # Chẩn đoán không được thay đổi hành vi chạy bình thường hay mốc ngày 1.
    for key in ("status", "method", "score", "candidate_count", "warnings"):
        if normal[key] != detection[key]:
            raise AssertionError("Chẩn đoán đã thay đổi kết quả: " + row.image_path)
    if normal["corners"] is not None:
        np.testing.assert_array_equal(normal["corners"], detection["corners"])
    expected = np.array([[getattr(row, c + "_x"), getattr(row, c + "_y")]
                         for c in ("tl", "tr", "br", "bl")], np.float32)
    predicted = detection["corners"]
    selected_iou = polygon_iou(predicted, expected) if predicted is not None else 0.0
    if abs(selected_iou - baseline.iou) > 1e-6 or detection["status"] != baseline.status:
        raise AssertionError("Scanner không còn khớp baseline: " + row.image_path)
    if predicted is not None:
        old = np.array([[baseline[f"pred_{i}_x"], baseline[f"pred_{i}_y"]] for i in range(4)])
        np.testing.assert_allclose(predicted, old, atol=1e-4)
    debug = detection["debug"]
    scale = np.array([image.shape[1] / debug["resized"].shape[1], image.shape[0] / debug["resized"].shape[0]])
    records = []
    for item in debug["candidate_trace"]:
        points = np.array(item["points"], np.float32) * scale
        records.append({
            "image_path": row.image_path, "bg_name": row.bg_name,
            **{key: value for key, value in item.items() if key not in ("points", "edge_support_per_side")},
            "points_original": json.dumps(points.tolist()),
            "edge_support_per_side": json.dumps(item.get("edge_support_per_side")),
            "iou": polygon_iou(points, expected),
        })
    accepted = [item for item in records if item["reason"] == "accepted"]
    best_accepted = max((item["iou"] for item in accepted), default=0.0)
    best = max(records, key=lambda item: item["iou"], default=None)
    best_iou = best["iou"] if best else 0.0
    hull_ious = [polygon_iou(np.array(item["points"], np.float32) * scale, expected)
                 for item in debug["contour_hulls"]]
    best_hull_iou = max(hull_ious, default=0.0)
    result = {
        "image_path": row.image_path, "bg_name": row.bg_name, "model_name": row.model_name,
        "status": detection["status"], "selected_iou": selected_iou,
        "best_accepted_iou": best_accepted, "best_generated_iou": best_iou,
        "best_contour_hull_iou": best_hull_iou,
        "proposal_stage": "good_quad_exists" if best_iou >= 0.9 else (
            "good_hull_but_no_good_quad" if best_hull_iou >= 0.9 else "no_good_contour_hull"),
        "diagnosis": classify(selected_iou, best_accepted, best_iou),
        "best_generated_reason": best["reason"] if best else "no_quad",
        "best_generated_method": best["method"] if best else "",
        "best_generated_rank": best["contour_rank"] if best else None,
        "generated_quad_attempts": len(records), "accepted_quad_attempts": len(accepted),
    }
    for method, counts in debug["branch_counts"].items():
        result.update({method + "_" + key: value for key, value in counts.items()})
    return result, records


def make_figure(report, samples, candidates):
    # Minh họa mỗi kiểu lỗi theo nền; bảng đầy đủ vẫn có cả 200 ảnh.
    examples = report[report["diagnosis"] != "passed"].drop_duplicates(["bg_name", "diagnosis"]).head(8)
    sheet = np.full((len(examples) * 250, 1440, 3), 255, np.uint8)
    for index, row in enumerate(examples.itertuples(index=False)):
        source = samples[samples["image_path"] == row.image_path].iloc[0]
        image = cv2.imdecode(np.frombuffer((RAW / row.image_path).read_bytes(), np.uint8), cv2.IMREAD_COLOR)
        detection = detect_document(image, diagnostics=True)
        debug = detection["debug"]
        height, width = debug["resized"].shape[:2]
        scale = np.array([width / image.shape[1], height / image.shape[0]])
        expected = np.array([[source[c + "_x"], source[c + "_y"]] for c in ("tl", "tr", "br", "bl")]) * scale
        overlay = debug["resized"].copy()
        cv2.polylines(overlay, [expected.round().astype(np.int32)], True, (0, 200, 0), 3)
        if detection["corners"] is not None:
            cv2.polylines(overlay, [(detection["corners"] * scale).round().astype(np.int32)], True, (0, 0, 255), 2)
        best_view = debug["resized"].copy()
        cv2.polylines(best_view, [expected.round().astype(np.int32)], True, (0, 200, 0), 3)
        pool = candidates[candidates["image_path"] == row.image_path]
        if not pool.empty:
            best = pool.sort_values("iou", ascending=False).iloc[0]
            points = np.array(json.loads(best.points_original)) * scale
            cv2.polylines(best_view, [points.round().astype(np.int32)], True, (0, 200, 255), 2)
        panels = [overlay, debug["edges"], debug["mask"], best_view]
        captions = [f"{index + 1:02d} {row.bg_name} IoU={row.selected_iou:.3f}",
                    "Canny + closing", "Otsu + closing", f"Offline best IoU={row.best_generated_iou:.3f}"]
        for column, (panel, caption) in enumerate(zip(panels, captions)):
            if panel.ndim == 2:
                panel = cv2.cvtColor(panel, cv2.COLOR_GRAY2BGR)
            panel = cv2.resize(panel, (350, 197))
            x, y = column * 360, index * 250
            sheet[y + 25:y + 222, x + 5:x + 355] = panel
            cv2.putText(sheet, caption, (x + 5, y + 18), 0, .42, (0, 0, 0), 1)
        cv2.putText(sheet, row.diagnosis + " / best reason: " + row.best_generated_reason,
                    (5, index * 250 + 242), 0, .45, (0, 0, 0), 1)
    cv2.imwrite(str(OUTPUT / "diagnostics.jpg"), sheet)
    examples.to_csv(OUTPUT / "examples.csv", index=False)


def main():
    if OUTPUT.exists():
        raise FileExistsError("Đã có kết quả ngày 2; giữ lại để đối chiếu, không ghi đè.")
    samples = prepare_samples()
    baseline_root = ROOT / "artifacts/scanner_dev/baseline"
    info = json.loads((baseline_root / "run_info.json").read_text(encoding="utf-8"))
    if not info["complete"] or info["manifest_sha256"] != sha256(MANIFEST):
        raise ValueError("Baseline chưa hoàn thành hoặc danh sách ảnh đã thay đổi.")
    baseline = pd.read_csv(baseline_root / "results.csv").set_index("image_path")
    if set(baseline.index) != set(samples.image_path):
        raise ValueError("Ảnh baseline không khớp tập phát triển.")
    OUTPUT.mkdir(parents=True)
    source = OUTPUT / "source"
    source.mkdir()
    for name in ("detect.py", "audit.py", "benchmark.py"):
        shutil.copy2(Path(__file__).with_name(name), source / name)
    shutil.copy2(CONFIG_PATH, source / "scanner.json")
    write_json(OUTPUT / "run_info.json", {"complete": False, "manifest_sha256": sha256(MANIFEST)})
    cv2.setNumThreads(1)
    images, attempts = [], []
    for index, row in enumerate(samples.itertuples(index=False), 1):
        result, records = examine(row, baseline.loc[row.image_path])
        images.append(result)
        attempts.extend(records)
        if index % 25 == 0:
            print(f"Đã phân tích {index}/{len(samples)}", flush=True)
    report, candidates = pd.DataFrame(images), pd.DataFrame(attempts)
    report.to_csv(OUTPUT / "images.csv", index=False)
    candidates.to_csv(OUTPUT / "candidates.csv", index=False)
    summary = {
        "images": len(report), "baseline_predictions_unchanged": True,
        "diagnoses": {str(k): int(v) for k, v in report.diagnosis.value_counts().items()},
        "close_rejected_reasons": {str(k): int(v) for k, v in report[report.diagnosis == "close_quad_rejected"].best_generated_reason.value_counts().items()},
        "attempt_rejection_counts": {str(k): int(v) for k, v in candidates.reason.value_counts().items()},
        "failed_proposal_stages": {str(k): int(v) for k, v in report[report.diagnosis != "passed"].proposal_stage.value_counts().items()},
        "by_background": pd.crosstab(report.bg_name, report.diagnosis).to_dict(orient="index"),
    }
    write_json(OUTPUT / "summary.json", summary)
    make_figure(report, samples, candidates)
    write_json(OUTPUT / "run_info.json", {
        "complete": True, "manifest_sha256": sha256(MANIFEST), "images": len(report),
        "baseline_predictions_unchanged": True,
        "source_sha256": {p.name: sha256(p) for p in source.iterdir()},
        "scope": "offline GT analysis; all contours above min area including those beyond top-k; no OCR",
    })
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("Kết quả:", OUTPUT)


if __name__ == "__main__":
    main()
