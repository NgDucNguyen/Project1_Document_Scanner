# Project 1 — Quét tài liệu và nhận dạng chữ tiếng Việt

Dự án hướng tới ứng dụng nhận ảnh chụp một trang giấy, tìm bốn góc, nắn phối cảnh thành ảnh scan và nhận dạng chữ in tiếng Việt. Phạm vi ưu tiên là giấy phẳng, đủ bốn góc và bố cục một cột.

**Sinh viên:** Nguyễn Đức Nguyên · MSSV 202416305 · Đại học Bách khoa Hà Nội (HUST).

> **Trạng thái hiện tại:** Dữ liệu SmartDoc đã có trên máy phát triển. Mã xử lý dữ liệu, thuật toán scan, OCR và giao diện chưa được viết; repository **chưa có lệnh chạy ứng dụng**. README này giúp chuẩn bị môi trường và dữ liệu cho phần 1, đồng thời phân biệt việc đã làm với kế hoạch.

## 1. Chuẩn bị môi trường

Cần Python **3.12 (64-bit)**, `pip` và Git. VS Code là tùy chọn. Trên Windows, hãy kiểm tra `python --version` trong terminal; WindowsApps alias không thay thế một bản Python hoạt động.

Mở terminal tại thư mục gốc repository (nơi có `requirements.txt`). Trong PowerShell:

```powershell
python --version
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -c "import cv2, numpy, pandas, matplotlib; print('Môi trường cơ bản OK')"
```

Có thể kích hoạt bằng `.\venv\Scripts\Activate.ps1` rồi dùng `python`. Gọi trực tiếp `venv\Scripts\python.exe` như trên không cần đổi execution policy.

Trên macOS/Linux:

```bash
python3.12 -m venv venv
./venv/bin/python -m pip install -r requirements.txt
./venv/bin/python -c "import cv2, numpy, pandas, matplotlib; print('Môi trường cơ bản OK')"
```

Nếu `venv` cũ báo không tìm thấy Python, hãy tạo lại nó bằng một bản Python đang hoạt động. Không chép `venv` giữa các máy: môi trường ảo lưu đường dẫn trình thông dịch của máy tạo ra nó. `requirements.txt` hiện chứa thư viện nền và một số thư viện dành cho các giai đoạn sau; bộ OCR sẽ được chọn và khóa phiên bản khi triển khai giai đoạn OCR.

## 2. Dữ liệu SmartDoc

Nguồn dữ liệu cho bài toán tìm khung giấy là [SmartDoc 2015 Challenge 1](https://github.com/jchazalon/smartdoc15-ch1-dataset). Dữ liệu không nằm trong Git. Máy phát triển hiện có **24.889 ảnh JPEG** và `frames_metadata.csv` tương ứng. Người clone repository phải tự tải bộ này nếu muốn chạy các bước xử lý ảnh sau này.

```text
data/
├── raw/
│   └── smartdoc/
│       ├── frames_metadata.csv
│       ├── background01/
│       ├── background02/
│       ├── background03/
│       ├── background04/
│       └── background05/
├── interim/                 # Manifest, split và báo cáo audit sẽ tạo
└── processed/               # Dữ liệu dẫn xuất sẽ tạo
```

### Tải dữ liệu trên máy mới

1. Vào [SmartDoc Releases](https://github.com/jchazalon/smartdoc15-ch1-dataset/releases), tải `frames.tar.gz` của bản `v2.0.0`. Gói `models.tar.gz` chưa cần cho phần 1.
2. Giải nén `frames.tar.gz` vào `data/raw/smartdoc/`. Các thư mục `background01` đến `background05` và `metadata.csv.gz` phải nằm **trực tiếp** trong `smartdoc/`, không nằm trong một thư mục `frames` lồng bên trong.
3. Giải nén `metadata.csv.gz` rồi đổi tên CSV thành `frames_metadata.csv`. Giữ nguyên ảnh gốc để có thể audit lại.
4. Kiểm tra trong PowerShell:

```powershell
Test-Path .\data\raw\smartdoc\frames_metadata.csv
Test-Path .\data\raw\smartdoc\background01\datasheet001\frame_0001.jpeg
(Import-Csv .\data\raw\smartdoc\frames_metadata.csv | Measure-Object).Count
```

Hai lệnh đầu phải trả `True`. Với đúng bản đang dùng, lệnh cuối trả `24889`. Nếu khác, hãy kiểm tra bản tải và vị trí giải nén trước khi tiếp tục.

**Quy ước nhãn:** `image_path` là đường dẫn tương đối từ `data/raw/smartdoc/`. Các trường `tl`, `bl`, `br`, `tr` là bốn góc theo tọa độ **pixel** của ảnh, không phải tọa độ 0–1. Nếu code dùng thứ tự TL → TR → BR → BL, hãy đổi theo tên trường. `model_name` là ID của trang gốc; mọi frame có cùng `model_name` phải ở cùng train/validation/test để tránh rò rỉ. Bộ dữ liệu có 30 trang gốc trên 5 nền, nên 24.889 frame không tương đương 24.889 trang độc lập. Xem [schema nguồn](https://github.com/jchazalon/smartdoc15-ch1-dataset) để đối chiếu.

SmartDoc chỉ cung cấp đầu vào và nhãn phù hợp cho bài toán khung giấy. Ảnh không có giấy và ảnh tiếng Việt tự chụp sẽ được thêm sau; hiện chưa thể dùng bộ này để đo tỷ lệ báo nhầm trên ảnh âm hoặc CER tiếng Việt.

## 3. Cấu trúc repository hiện tại

```text
Project1_document_scanner/
├── data/                       # raw, interim, processed; dữ liệu lớn không đưa lên Git
├── models/                     # Trọng số mô hình sẽ dùng sau
├── docs/
│   └── phase1_data.md           # Hướng dẫn riêng cho phần dữ liệu
├── src/
│   └── document_scanner/       # Package Python; hiện chỉ có __init__.py rỗng
│       ├── data/               # Nạp và kiểm tra dữ liệu phần 1
│       ├── scanner/            # Tìm góc và nắn ảnh
│       ├── ocr/                # Nhận dạng chữ
│       └── layout/             # Thứ tự đọc
├── tests/                      # Chưa có test
├── requirements.txt
└── README.md
```

Các file `__init__.py` rỗng chỉ giúp Python nhận ra package; chưa có thuật toán. Bốn thư mục chức năng đã được tạo sẵn để thêm mã theo từng giai đoạn. Xem [hướng dẫn phần 1](docs/phase1_data.md). Theo bản đề xuất, những file sẽ tự viết theo từng giai đoạn là:

| Nơi đặt mã | File dự kiến | Vai trò |
| --- | --- | --- |
| `src/document_scanner/data/` | `adapters.py`, `validate.py` | Nạp metadata, chuẩn hóa nhãn, audit dữ liệu |
| `src/document_scanner/scanner/` | `detect.py`, `geometry.py`, `enhance.py`, `orientation.py` | Tìm góc, nắn ảnh, làm rõ, xoay hướng |
| `src/document_scanner/ocr/` | `detect.py`, `recognize.py` | Tìm dòng chữ và nhận dạng ký tự |
| `src/document_scanner/layout/` | `reading_order.py` | Ghép khối/cột và sắp thứ tự đọc |
| `src/document_scanner/` | `export.py`, `evaluate.py` | Xuất kết quả và tính metric |
| Gốc repository | `app.py` | Giao diện demo sau khi pipeline hoạt động |

Ảnh trung gian cho từng lần chạy nên lưu dưới `artifacts/{run_id}/{sample_id}/` (đã được Git bỏ qua). Chỉ tạo các file ở bảng khi bắt đầu viết chức năng tương ứng; hiện chúng chưa tồn tại.

Các thư mục đánh số của bản cũ và hai script `download_data.py`, `preprocess.py` đã được bỏ. Đường dẫn `data/raw/subset_2k/labels.csv` thuộc phương án dữ liệu trước đây và **không dùng** ở trạng thái hiện tại.

## 4. Bắt đầu phần 1

Phần 1 dùng SmartDoc đã tải; chưa cần ảnh tự chụp hay mô hình OCR.

1. Đọc header và vài dòng `frames_metadata.csv`, đối chiếu `image_path` với file ảnh thật.
2. Kiểm tra ảnh đọc được, nhãn đủ bốn góc, tọa độ hữu hạn, bốn điểm khác nhau, tứ giác lồi và nằm trong ảnh. Ghi số mẫu giữ/loại và lý do.
3. Vẽ nhãn trên ít nhất 50 ảnh trải đều các `model_name` và nền; kiểm tra bằng mắt độ khớp mép giấy cùng thứ tự góc.
4. Tạo manifest với đường dẫn tương đối, kích thước ảnh, `model_name`, góc pixel và trạng thái nhãn.
5. Chia train/validation/test theo `model_name` **trước** khi lấy mẫu frame hoặc augmentation. Lưu seed và danh sách nhóm cho từng tập.
6. Chạy baseline nhỏ trên development, lưu cả ca đúng và ca lỗi. Giữ test để đánh giá cuối cùng.

Đầu ra phần 1 là báo cáo audit, ảnh overlay, manifest và split tái lập được. Tên file và lệnh chạy cụ thể sẽ bổ sung khi sinh viên viết xong module; README hiện không đưa lệnh chạy cho script chưa tồn tại.

## 5. Lộ trình

| Giai đoạn | Đầu ra dự kiến | Trạng thái |
| --- | --- | --- |
| Tuần 1 | Audit SmartDoc, overlay, manifest, split theo trang gốc | Chuẩn bị bắt đầu |
| Tuần 2 | Tìm góc, nắn phối cảnh, sửa góc thủ công | Chưa triển khai |
| Tuần 3 | Làm rõ scan và tách dòng | Chưa triển khai |
| Tuần 4 | Tích hợp OCR tiếng Việt có sẵn | Chưa triển khai |
| Tuần 5 | Thứ tự đọc và giao diện tối thiểu | Chưa triển khai |
| Tuần 6 | Đánh giá trên test đã khóa, báo cáo và demo | Chưa triển khai |

Các mốc chất lượng trong bản kế hoạch là **mục tiêu**, chưa phải kết quả đã đo. Khi pipeline hoạt động, README sẽ bổ sung lệnh chạy thật, cấu hình, phiên bản model OCR và kết quả đánh giá.

## 6. Ghi nguồn

SmartDoc được phát hành theo CC BY 4.0. Khi dùng ảnh hoặc công bố kết quả, hãy ghi nguồn theo [hướng dẫn của bộ dữ liệu](https://github.com/jchazalon/smartdoc15-ch1-dataset). Không commit toàn bộ ảnh vào repository này.
