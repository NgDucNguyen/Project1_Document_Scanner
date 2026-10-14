import os
import csv
from datasets import load_dataset

# Thư mục lưu dữ liệu
output_dir = "data/raw/subset_2k"
os.makedirs(output_dir, exist_ok=True)
csv_path = os.path.join(output_dir, "labels.csv")

print("Đang kết nối tới dataset trên Hugging Face...")
dataset = load_dataset("mapo80/DocCornerDataset", split="train", streaming=True)
subset_2k = dataset.take(2000)

print("Đang tải ảnh và ghi file nhãn tọa độ...")
with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    # Ghi tiêu đề các cột (bao gồm tên file, trạng thái và tọa độ 4 góc)
    writer.writerow([
        "filename", "is_negative", 
        "tl_x", "tl_y", "tr_x", "tr_y", 
        "br_x", "br_y", "bl_x", "bl_y"
    ])
    
    count = 0
    for item in subset_2k:
        image = item["image"]
        # Lấy tên file gốc hoặc tạo tên theo thứ tự
        filename = item.get("filename", f"doc_{count:06d}.jpg")
        
        # 1. Lưu ảnh vào thư mục subset_2k
        image_path = os.path.join(output_dir, filename)
        if not os.path.exists(image_path):
            image.save(image_path)
        
        # 2. Ghi dòng nhãn tương ứng vào file CSV
        writer.writerow([
            filename,
            item.get("is_negative"),
            item.get("corner_tl_x"), item.get("corner_tl_y"),
            item.get("corner_tr_x"), item.get("corner_tr_y"),
            item.get("corner_br_x"), item.get("corner_br_y"),
            item.get("corner_bl_x"), item.get("corner_bl_y")
        ])
        
        count += 1
        if count % 100 == 0:
            print(f"Đã xử lý xong {count}/2000 mẫu...")

print(f"Hoàn tất! File nhãn đã được lưu tại: {csv_path}")