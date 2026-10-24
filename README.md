# Project 1 — Quét tài liệu và nhận dạng chữ tiếng Việt

Dự án hướng tới ứng dụng nhận ảnh chụp một trang giấy, tìm bốn góc, nắn phối cảnh thành ảnh scan và nhận dạng chữ in tiếng Việt. Phạm vi ưu tiên là giấy phẳng, đủ bốn góc và bố cục một cột.

**Sinh viên:** Nguyễn Đức Nguyên · MSSV 202416305 · Đại học Bách khoa Hà Nội (HUST).

> **Trạng thái hiện tại:** Đã có bốn script tuần 1 để đọc SmartDoc, kiểm tra dữ liệu, chia tập và vẽ nhãn. Đã tạo manifest cho **24.889 ảnh hợp lệ** và 50 ảnh overlay trên máy phát triển. Thuật toán tự tìm góc, nắn ảnh, OCR và giao diện chưa triển khai. Xem [kết quả tuần 1](docs/week1_report.md).

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
├── interim/                 # Manifest, danh sách lỗi và kết quả chia tập
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
│   ├── phase1_data.md           # Hướng dẫn chạy tuần 1
│   └── week1_report.md          # Kết quả kiểm tra và giới hạn
├── src/
│   └── document_scanner/
│       ├── data/               # adapters.py, validate.py, split.py, overlay.py
│       ├── scanner/            # Tìm góc và nắn ảnh
│       ├── ocr/                # Nhận dạng chữ
│       └── layout/             # Thứ tự đọc
├── tests/                      # Chưa có test
├── requirements.txt
└── README.md
```

Các file `__init__.py` giúp Python nhận ra package. Thư mục `data` đã có mã xử lý dữ liệu; `scanner`, `ocr`, `layout` hiện là khung cho các giai đoạn sau. Xem [hướng dẫn phần 1](docs/phase1_data.md). Các module hiện có và dự kiến:

| Nơi đặt mã | File | Vai trò |
| --- | --- | --- |
| `src/document_scanner/data/` | `adapters.py`, `validate.py`, `split.py`, `overlay.py` | Đã có: nạp nhãn, kiểm tra, chia tập, vẽ overlay |
| `src/document_scanner/scanner/` | `detect.py`, `geometry.py`, `enhance.py`, `orientation.py` | Tìm góc, nắn ảnh, làm rõ, xoay hướng |
| `src/document_scanner/ocr/` | `detect.py`, `recognize.py` | Tìm dòng chữ và nhận dạng ký tự |
| `src/document_scanner/layout/` | `reading_order.py` | Ghép khối/cột và sắp thứ tự đọc |
| `src/document_scanner/` | `export.py`, `evaluate.py` | Xuất kết quả và tính metric |
| Gốc repository | `app.py` | Giao diện demo sau khi pipeline hoạt động |

Overlay tuần 1 được lưu dưới `artifacts/week1/overlays/`. Ảnh, môi trường ảo và dữ liệu dẫn xuất được Git bỏ qua, chỉ giữ trên máy. Các file ngoài module `data` trong bảng trên là kế hoạch, chưa tồn tại.

Các thư mục đánh số của bản cũ và hai script `download_data.py`, `preprocess.py` đã được bỏ. Đường dẫn `data/raw/subset_2k/labels.csv` thuộc phương án dữ liệu trước đây và **không dùng** ở trạng thái hiện tại.

## 4. Chạy phần 1

Phần 1 dùng SmartDoc đã tải; chưa cần ảnh tự chụp hay mô hình OCR.

Sau khi cài môi trường và tải dữ liệu, mở PowerShell ở gốc repository rồi chạy theo thứ tự:

```powershell
.\venv\Scripts\python.exe src\document_scanner\data\adapters.py
.\venv\Scripts\python.exe src\document_scanner\data\validate.py
.\venv\Scripts\python.exe src\document_scanner\data\split.py
.\venv\Scripts\python.exe src\document_scanner\data\overlay.py
```

Nếu đã kích hoạt `venv`, có thể thay `.\venv\Scripts\python.exe` bằng `python`. Trên macOS/Linux dùng `./venv/bin/python` và dấu `/` trong đường dẫn script. Các script được chạy trực tiếp theo lệnh trên.

`validate.py` đọc toàn bộ ảnh nên có thể mất vài phút. Nó tạo `data/interim/manifest.csv` và `invalid_rows.csv`. `split.py` tạo `manifest_with_split.csv`, chia theo `model_name` với seed 42. `overlay.py` tạo 50 ảnh để xem nhãn có khớp giấy không. Chạy lại sẽ ghi đè các CSV và ảnh cùng tên; dữ liệu gốc không bị chỉnh sửa.

| Tập | Trang gốc | Ảnh |
| --- | ---: | ---: |
| Train | 21 | 17.495 |
| Validation | 4 | 3.192 |
| Test | 5 | 4.202 |

Không có trang gốc nào xuất hiện ở nhiều tập. Giữ test để đánh giá cuối cùng. 50 overlay hiện bao phủ 10 trang gốc trên 5 nền; cần bổ sung kiểm tra trực quan các trang còn lại. Overlay vẽ nhãn có sẵn, chưa phải kết quả tự tìm góc. Chi tiết đầu ra: [hướng dẫn phần 1](docs/phase1_data.md).

## 5. Lộ trình

| Giai đoạn | Đầu ra dự kiến | Trạng thái |
| --- | --- | --- |
| Tuần 1 | Audit SmartDoc, overlay, manifest, split theo trang gốc | Đã chạy; cần mở rộng kiểm tra trực quan |
| Tuần 2 | Tìm góc, nắn phối cảnh, sửa góc thủ công | Chưa triển khai |
| Tuần 3 | Làm rõ scan và tách dòng | Chưa triển khai |
| Tuần 4 | Tích hợp OCR tiếng Việt có sẵn | Chưa triển khai |
| Tuần 5 | Thứ tự đọc và giao diện tối thiểu | Chưa triển khai |
| Tuần 6 | Đánh giá trên test đã khóa, báo cáo và demo | Chưa triển khai |

Các mốc chất lượng trong bản kế hoạch là **mục tiêu**, chưa phải kết quả đã đo. Khi pipeline hoạt động, README sẽ bổ sung lệnh chạy thật, cấu hình, phiên bản model OCR và kết quả đánh giá.

## 6. Ghi nguồn

SmartDoc được phát hành theo CC BY 4.0. Khi dùng ảnh hoặc công bố kết quả, hãy ghi nguồn theo [hướng dẫn của bộ dữ liệu](https://github.com/jchazalon/smartdoc15-ch1-dataset). Không commit toàn bộ ảnh vào repository này.
