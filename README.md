# Project 1: Document Scanner & SmartDoc Processing

## 📌 Thông tin sinh viên (Student Information)

- **Họ và tên:** Nguyễn Đức Nguyên
- **Mã sinh viên:** 202416305
- **Trường:** Đại học Bách khoa Hà Nội (HUST)

---

## Cấu trúc thư mục dự án (Project Structure)

Dự án được tổ chức theo chuẩn cấu trúc MLOps chuyên nghiệp:

```text
PROJECT1_DOCUMENT_SCANNER/
├── data/
│   ├── raw/                  # Chứa dữ liệu thô (ảnh tải từ Hugging Face & file labels.csv)
│   └── processed/            # Chứa dữ liệu đã qua tiền xử lý (làm sạch, cân bằng sáng, khử nghiêng)
├── models/                   # Thư mục lưu trọng số mô hình train
├── src/
│   ├── 01_data_pipeline/     # Code tải dữ liệu tự động và pipeline tiền xử lý (preprocess.py)
│   ├── 02_eda/               # Khám phá dữ liệu và trực quan hóa bounding box
│   ├── 03_model_training/    # Huấn luyện mô hình tìm 4 góc tài liệu
│   ├── 04_evaluation/        # Đánh giá độ chính xác (IoU, v.v.)
│   └── 05_web_dashboard/     # Giao diện ứng dụng Demo (Streamlit)
├── tests/                    # Unit tests kiểm thử code
├── .gitignore                # Cấu hình bỏ qua file nặng (venv, data, models)
├── requirements.txt          # Danh sách thư viện phụ thuộc của dự án
└── README.md                 # Tài liệu mô tả dự án
```

## Hướng dẫn cài đặt và Chạy dự án (Getting Started)

### 1. Thiết lập môi trường ảo (Virtual Environment)

Mở Terminal tại thư mục gốc của dự án và thực hiện các lệnh sau:

```bash
# Tạo môi trường ảo python
python -m venv venv

# Kích hoạt môi trường ảo
# - Trên Windows (Git Bash / Command Prompt):
source venv/Scripts/activate
# - Trên Windows (PowerShell):
# venv\Scripts\Activate.ps1
```

### 2. Cài đặt các thư viện phụ thuộc

Sau khi đã kích hoạt môi trường ảo `(venv)`, tiến hành nâng cấp `pip` và cài đặt các thư viện cần thiết bằng lệnh:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```
