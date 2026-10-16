# Data Pipeline & Preprocessing (`src/01_data_pipeline/`)

Module này chịu trách nhiệm quản lý toàn bộ luồng dữ liệu thô (raw data), tự động hóa quá trình tiền xử lý ảnh và chuẩn hóa dữ liệu đầu vào phục vụ cho các mô hình học máy và thuật toán thị giác máy tính phía sau.

---

## 📂 Cấu trúc các file trong module

```text
src/01_data_pipeline/
├── download_data.py    # Kịch bản tải dữ liệu và nhãn tọa độ từ Hugging Face
├── preprocess.py       # Pipeline tiền xử lý ảnh (Khử nhiễu, chuyển xám, căn chỉnh góc)
└── README.md           # Tài liệu hướng dẫn sử dụng module
```
