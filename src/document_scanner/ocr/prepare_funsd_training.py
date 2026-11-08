"""Tạo dữ liệu dòng chữ tiếng Anh từ nhãn FUNSD training_data.

Ảnh gốc và testing_data không bị sửa. Kết quả cần được kiểm tra bằng mắt:
lọc theo hình học/độ tương phản không đảm bảo ảnh nét hoặc nhãn đúng.
"""
from pathlib import Path
from datetime import datetime
from collections import Counter
import csv
import json
import random
import statistics
import unicodedata

import cv2
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SOURCE = PROJECT_ROOT / "data" / "raw" / "funsd" / "dataset" / "training_data"
OUTPUT = PROJECT_ROOT / "data" / "interim" / "funsd_ocr_lines"


def clean_text(text):
    return " ".join(unicodedata.normalize("NFC", text).split())


def select_validation_pages(images):
    # Giữ riêng 12 trang từng dùng so sánh ban đầu và thêm 18 trang cố định.
    if len(images) < 31:
        raise ValueError("Cần ít nhất 31 trang để chia tập train và validation.")
    remaining = list(images[12:])
    random.Random(20261108).shuffle(remaining)
    return {p.stem for p in list(images[:12]) + remaining[:18]}


def select_line(region, image):
    """Chỉ lấy vùng giống một dòng có nhãn vùng khớp các nhãn từ."""
    text = clean_text(region.get("text", ""))
    words = region.get("words", [])
    if len(words) < 2 or len(text) < 8:
        return None, "short"
    if any(not (32 <= ord(char) <= 126) for char in text):
        return None, "non_ascii"
    if clean_text(" ".join(word.get("text", "") for word in words)) != text:
        return None, "label_mismatch"
    if any(len(word.get("box", [])) != 4 for word in words):
        return None, "bad_word_box"
    boxes = [word["box"] for word in words]
    height, width = image.shape[:2]
    if any(not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height)
           for x1, y1, x2, y2 in boxes):
        return None, "bad_word_box"
    # Giữ các từ có cùng độ cao và thứ tự từ trái sang phải.
    median_height = statistics.median(y2 - y1 for x1, y1, x2, y2 in boxes)
    top = min(box[1] for box in boxes)
    bottom = max(box[3] for box in boxes)
    if median_height < 10 or bottom - top > 1.8 * median_height:
        return None, "not_one_line"
    if any(boxes[i][0] > boxes[i + 1][0] for i in range(len(boxes) - 1)):
        return None, "word_order"
    left = max(0, min(box[0] for box in boxes) - 3)
    right = min(width, max(box[2] for box in boxes) + 3)
    top = max(0, top - 3)
    bottom = min(height, bottom + 3)
    crop = image[top:bottom, left:right]
    if crop.size == 0 or np.percentile(crop, 95) - np.percentile(crop, 5) < 40:
        return None, "low_contrast"
    return (crop, text, [left, top, right, bottom]), None


def main():
    images = sorted((SOURCE / "images").glob("*.png"))
    if not images:
        raise FileNotFoundError("Không tìm thấy ảnh FUNSD training_data.")
    # Chia theo trang, không theo dòng để tránh các dòng cùng trang lọt hai tập.
    # Giữ 12 trang đã dùng chọn cấu hình trước đây ngoài tập huấn luyện.
    validation = select_validation_pages(images)
    folder = OUTPUT / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    folder.mkdir(parents=True)
    rows = []
    rejected = Counter()
    for path in images:
        image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise ValueError("Không đọc được ảnh: " + str(path))
        annotation = SOURCE / "annotations" / (path.stem + ".json")
        regions = json.loads(annotation.read_text(encoding="utf-8"))["form"]
        split = "val" if path.stem in validation else "train"
        out = folder / split
        out.mkdir(exist_ok=True)
        for index, region in enumerate(regions):
            line, reason = select_line(region, image)
            if reason:
                rejected[reason] += 1
                continue
            crop, text, box = line
            name = path.stem + "_" + str(index).zfill(3)
            img_path = out / (name + ".png")
            if not cv2.imwrite(str(img_path), crop):
                raise OSError("Không lưu được: " + str(img_path))
            (out / (name + ".gt.txt")).write_text(text + "\n", encoding="utf-8")
            rows.append({"split": split, "page": path.stem, "region": index,
                         "image": img_path.relative_to(folder).as_posix(),
                         "box": json.dumps(box), "text": text})
    if not rows:
        raise ValueError("Không có dòng phù hợp.")
    with (folder / "manifest.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = {"source": "FUNSD training_data; testing_data không được sử dụng",
               "train_pages_with_lines": len({r["page"] for r in rows if r["split"] == "train"}),
               "val_pages_with_lines": len({r["page"] for r in rows if r["split"] == "val"}),
               "train_lines": sum(r["split"] == "train" for r in rows),
               "val_lines": sum(r["split"] == "val" for r in rows),
               "rejected_regions": dict(rejected),
               "warning": "Lọc tự động chưa bảo đảm chữ nét, nhãn đúng hoặc không có chữ viết tay; cần kiểm tra."}
    (folder / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Dữ liệu:", folder)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
