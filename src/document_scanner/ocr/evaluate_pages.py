"""Đánh giá OCR chạy trên cả trang FUNSD bằng nhãn vùng có sẵn.

Tesseract chỉ nhận ảnh toàn trang. Sau OCR, các từ được gán vào vùng nhãn
theo vị trí để tính CER/WER trong các vùng được chú thích. Từ nằm ngoài
vùng nhãn được đếm riêng vì FUNSD có thể không chú thích toàn bộ trang.
"""
from pathlib import Path
from datetime import datetime
import argparse
import csv
import json
import os
import subprocess

from metrics import edit_distance, normalize_text
from prepare_funsd_training import select_validation_pages
from recognize import TESSERACT_PATH


ROOT = Path(__file__).resolve().parents[3]
FUNSD = ROOT / "data" / "raw" / "funsd" / "dataset"
OUTPUT = ROOT / "artifacts" / "week3" / "page_evaluation"
MODELS = {
    "eng": {"language": "eng", "tessdata": None},
    "funsd": {"language": "funsd_eng", "tessdata": ROOT / "models" / "funsd_english"},
}


def overlap_fraction(word_box, region_box):
    x1 = max(word_box[0], region_box[0])
    y1 = max(word_box[1], region_box[1])
    x2 = min(word_box[2], region_box[2])
    y2 = min(word_box[3], region_box[3])
    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    area = (word_box[2] - word_box[0]) * (word_box[3] - word_box[1])
    return intersection / area if area > 0 else 0


def assign_words(regions, words):
    """Mỗi từ OCR gán tối đa một vùng; từ không khớp được đếm riêng."""
    assigned = [[] for _ in regions]
    unassigned = []
    for word in words:
        candidates = []
        for index, region in enumerate(regions):
            fraction = overlap_fraction(word["box"], region["box"])
            if fraction >= 0.5:
                x1, y1, x2, y2 = region["box"]
                # Khi khung chồng nhau, chọn vùng khớp nhiều nhất, rồi vùng nhỏ hơn.
                candidates.append((fraction, -((x2 - x1) * (y2 - y1)), -index))
        if candidates:
            index = -max(candidates)[2]
            assigned[index].append(word["text"])
        else:
            unassigned.append(word["text"])
    return assigned, unassigned


def read_page_words(image, model, psm):
    command = [str(TESSERACT_PATH), str(image), "stdout", "-l", model["language"], "--psm", str(psm)]
    if model["tessdata"] is not None:
        command += ["--tessdata-dir", str(model["tessdata"])]
    # Khi dùng tessdata riêng, đường dẫn đầy đủ vẫn tìm được cấu hình TSV.
    command.append(str(TESSERACT_PATH.parent / "tessdata" / "configs" / "tsv"))
    env = os.environ.copy()
    env["OMP_THREAD_LIMIT"] = "1"
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    if result.returncode:
        raise RuntimeError("Tesseract lỗi trên " + str(image) + ":\n" + result.stderr)
    return parse_tsv_words(result.stdout)


def parse_tsv_words(tsv):
    # Nội dung OCR có thể là dấu ngoặc kép. TSV của Tesseract không dùng
    # quy tắc quote của CSV; bật quote sẽ làm gộp các dòng kế tiếp vào một từ.
    words = []
    reader = csv.DictReader(tsv.splitlines(), delimiter="\t", quoting=csv.QUOTE_NONE)
    if not reader.fieldnames or not {"level", "text", "left", "top", "width", "height"}.issubset(reader.fieldnames):
        raise ValueError("Tesseract không trả bảng TSV hợp lệ")
    for row in reader:
        if row["level"] != "5" or not row["text"].strip():
            continue
        x, y, width, height = (int(row[key]) for key in ("left", "top", "width", "height"))
        if width > 0 and height > 0:
            words.append({"text": row["text"].strip(), "box": [x, y, x + width, y + height]})
    return words


def valid_regions(annotation):
    result = []
    for index, region in enumerate(annotation["form"]):
        text = normalize_text(region.get("text", ""))
        box = region.get("box", [])
        if text and len(box) == 4 and box[0] < box[2] and box[1] < box[3]:
            result.append({"index": index, "text": text, "box": box})
    return result


def score_regions(image_id, method, regions, words):
    assigned, unassigned = assign_words(regions, words)
    result = []
    for region, predicted_words in zip(regions, assigned):
        reference = region["text"]
        prediction = normalize_text(" ".join(predicted_words))
        result.append({"image_id": image_id, "method": method, "region_index": region["index"],
                       "reference": reference, "prediction": prediction,
                       "char_errors": edit_distance(reference, prediction), "char_count": len(reference),
                       "word_errors": edit_distance(reference.split(), prediction.split()),
                       "word_count": len(reference.split())})
    return result, unassigned


def save_csv(path, rows):
    if not rows:
        raise ValueError("Không có dữ liệu để ghi: " + str(path))
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=["val", "test"], required=True)
    parser.add_argument("--methods", nargs="+", choices=sorted(MODELS), default=["eng", "funsd"])
    parser.add_argument("--psm", type=int, default=3, choices=[3, 6, 11])
    args = parser.parse_args()
    if len(set(args.methods)) != len(args.methods):
        raise ValueError("Không truyền trùng mô hình.")
    if args.split == "val":
        dataset = FUNSD / "training_data"
        page_ids = select_validation_pages(sorted((dataset / "images").glob("*.png")))
    else:
        dataset = FUNSD / "testing_data"
        page_ids = {path.stem for path in (dataset / "images").glob("*.png")}
    if not page_ids:
        raise ValueError("Không có trang để đánh giá.")
    folder = OUTPUT / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    folder.mkdir(parents=True)
    info = {"complete": False, "split": args.split, "methods": args.methods, "psm": args.psm,
            "interpretation": "OCR ảnh cả trang; CER/WER tính riêng trên vùng nhãn sau khi gán từ theo vị trí. "
            "Từ OCR nằm ngoài nhãn không tính vào CER/WER mà đếm riêng; không đo thứ tự đọc toàn trang.",
            "page_selection": "Validation là trang val của tập dòng FUNSD" if args.split == "val" else "Toàn bộ FUNSD testing_data"}
    info_path = folder / "run_info.json"
    info_path.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    all_rows, pages = [], []
    print("Kết quả:", folder, flush=True)
    for number, page_id in enumerate(sorted(page_ids), 1):
        image = dataset / "images" / (page_id + ".png")
        annotation = dataset / "annotations" / (page_id + ".json")
        if not image.is_file() or not annotation.is_file():
            raise FileNotFoundError("Thiếu ảnh hoặc nhãn của trang " + page_id)
        regions = valid_regions(json.loads(annotation.read_text(encoding="utf-8")))
        if not regions:
            raise ValueError("Không có vùng nhãn hợp lệ: " + page_id)
        for method in args.methods:
            words = read_page_words(image, MODELS[method], args.psm)
            rows, unassigned = score_regions(page_id, method, regions, words)
            all_rows.extend(rows)
            pages.append({"image_id": page_id, "method": method, "regions": len(rows),
                          "reference_words": sum(r["word_count"] for r in rows),
                          "ocr_words": len(words), "unassigned_words": len(unassigned),
                          "char_errors": sum(r["char_errors"] for r in rows),
                          "char_count": sum(r["char_count"] for r in rows),
                          "word_errors": sum(r["word_errors"] for r in rows),
                          "word_count": sum(r["word_count"] for r in rows)})
        print("Trang", number, "/", len(page_ids), page_id, flush=True)
    summary = []
    for method in args.methods:
        items = [row for row in pages if row["method"] == method]
        chars = sum(row["char_count"] for row in items)
        words = sum(row["word_count"] for row in items)
        ocr_words = sum(row["ocr_words"] for row in items)
        unassigned = sum(row["unassigned_words"] for row in items)
        summary.append({"method": method, "pages": len(items), "regions": sum(row["regions"] for row in items),
                        "cer": sum(row["char_errors"] for row in items) / chars,
                        "wer": sum(row["word_errors"] for row in items) / words,
                        "reference_words": words, "ocr_words": ocr_words, "unassigned_words": unassigned,
                        "unassigned_share": unassigned / ocr_words if ocr_words else 0})
    save_csv(folder / "regions.csv", all_rows)
    save_csv(folder / "pages.csv", pages)
    save_csv(folder / "summary.csv", summary)
    info.update(complete=True, pages=len(page_ids), finished_at=datetime.now().isoformat())
    info_path.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
