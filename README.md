# Project 1 — Quét tài liệu và nhận dạng chữ tiếng Việt

**Sinh viên:** Nguyễn Đức Nguyên · MSSV 202416305 · Đại học Bách khoa Hà Nội.

Đầu vào là ảnh chụp một trang giấy. Tuần 1 chuẩn bị dữ liệu; tuần 2 đã có tìm bốn góc, nắn phối cảnh, sửa góc và xoay trang. OCR và làm rõ chữ thuộc các tuần tiếp theo.

**Đọc kết quả:** [Báo cáo tuần 2](docs/week2_report.md) · [Hướng dẫn tuần 2](docs/guides/phase2_scanner.md) · [Nguồn dữ liệu và các thay đổi](docs/guides/data_sources.md) · [Tuần 1](docs/week1_report.md).

## Mở nhanh kết quả hiện có

**Đã chạy đủ 24.889 ảnh ngày 24/10/2026.** Không cần chạy lại để xem kết quả.

- [Ảnh scan đã tạo](data/processed/scan/20261024_161837_753214/): 18.571 PNG; 6.318 ảnh còn lại không tìm được khung, đã ghi nhận trong CSV/JSON.
- [Ảnh đã sửa góc bằng tay](data/processed/manual/corrected_example/): một ảnh minh họa, lưu riêng với ảnh tự động.
- [10 ca minh họa](artifacts/week2/batch/20261024_161837_753214/examples/): trích từ lần chạy đầy đủ để xem các bước và lỗi.
- [Báo cáo Word](artifacts/week2/report/Bao_cao_tuan_2.docx) và [báo cáo Markdown](docs/week2_report.md).
- [Giải thích từng thư mục kết quả](artifacts/week2/README.md) và [mục lục tài liệu](docs/README.md).

## 1. Cài đặt

Chạy từ thư mục gốc dự án. Dùng **Python 3.12 64-bit** và terminal PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\Activate.ps1
python -m pip check
```

Nếu PowerShell không cho kích hoạt, thay `python` trong các lệnh bên dưới bằng `.\venv\Scripts\python.exe`. Với Git Bash dùng `source venv/Scripts/activate`. Không sao chép venv từ máy khác. Không cần gõ `python3`.

`requirements.txt` khóa ba thư viện đang dùng trong tuần 1–2. Đây là bộ quét OpenCV, chưa cần tải model, GPU hoặc thư viện OCR. Các thư viện cũ đã cài trong venv có thể còn, nhưng không cần để chạy bộ quét.

## 2. Chuẩn bị dữ liệu

Nguồn hiện tại: [SmartDoc 2015 Challenge 1](https://github.com/jchazalon/smartdoc15-ch1-dataset). Ảnh và dữ liệu lớn không đưa lên GitHub.

1. Tải `frames.tar.gz` tại [Releases](https://github.com/jchazalon/smartdoc15-ch1-dataset/releases), bản v2.0.0.
2. Giải nén vào `data/raw/smartdoc/`, để `background01` đến `background05` nằm trực tiếp bên trong.
3. Giải nén `metadata.csv.gz`, đổi tên CSV thành `frames_metadata.csv`.
4. Chạy tuần 1 theo thứ tự:

```powershell
python -X utf8 src/document_scanner/data/adapters.py
python -X utf8 src/document_scanner/data/validate.py
python -X utf8 src/document_scanner/data/split.py
python -X utf8 src/document_scanner/data/overlay.py
```

Máy hiện tại đã có manifest cho **24.889 ảnh hợp lệ**, 30 trang gốc, 5 nền. Không cần chạy lại tuần 1 mỗi khi quét ảnh. Mọi frame cùng một `model_name` ở cùng một tập: train 17.495 ảnh, validation 3.192 ảnh, test 4.202 ảnh. Nhãn nguồn dùng tọa độ pixel; không nhân lại với kích thước ảnh. Xem [phần dữ liệu](docs/guides/phase1_data.md).

## 3. Chạy tuần 2

Quét **toàn bộ 24.889 ảnh**, lưu PNG và JSON cho các ảnh tìm được khung; ảnh thất bại vẫn có bản ghi:

```powershell
python -X utf8 -u src/document_scanner/scanner/scan.py --split all --workers 4
python -X utf8 src/document_scanner/scanner/evaluate.py --examples
```

Lệnh thứ hai dùng lần chạy hoàn tất gần nhất, chỉ chấm **train và validation**. Không đưa kết quả sửa tay vào chỉ số tự động. Test được quét nhưng chưa chấm để giữ cho đánh giá cuối kỳ.

Tùy chọn: `--split dev` chỉ quét train + validation; `--split val` chỉ quét validation; `--workers 1` xử lý lần lượt và nhẹ máy hơn. `--limit 20` dành cho kiểm tra nhanh, không dùng để báo cáo toàn bộ dữ liệu.

Sửa một ảnh cụ thể khi cần:

```powershell
python -X utf8 src/document_scanner/scanner/manual_scan.py --image data/raw/smartdoc/background04/letter001/frame_0001.jpeg
```

Cửa sổ điền góc tự động nếu có. `R` xóa để chọn lại bốn góc; chương trình tự sắp thứ tự. `P` xem trước, `E` xoay 90 độ, `S` lưu, `Q` hoặc Esc thoát. **Không phải bấm tay cho toàn bộ dataset.** Chế độ này cần máy có màn hình; lệnh chạy theo lô không mở cửa sổ.

## 4. Kết quả nằm ở đâu

```text
data/processed/                       # Mở đây để xem ảnh sau xử lý
├── scan/<run_id>/<split>/<background>/<model>/frame_XXXX.png
└── manual/<run_id>/warped_color.png   # Ảnh lưu từ cửa sổ sửa góc

artifacts/week2/
├── batch/<run_id>/
│   ├── metadata/<split>/<background>/<model>/frame_XXXX.json
│   │                           # Trạng thái, góc, H/T, đường dẫn ảnh
│   ├── results.csv             # Một dòng cho mỗi ảnh đã xử lý
│   ├── run_info.json           # Số ảnh, thời gian, phiên bản, hash code
│   ├── config.json
│   ├── source/                 # Bản code đúng tại thời điểm chạy
│   ├── evaluation/             # Chỉ số train/val và danh sách lỗi
│   └── examples/               # 5 ca đạt + 5 ca lỗi có ảnh trung gian
├── manual/<run_id>/corners.json # Thông tin góc và xoay của ảnh sửa tay
├── report/                     # Báo cáo Word và hình minh họa
├── history.zip                 # Lịch sử cũ đã nén; chỉ mở khi đối chiếu
└── batch/latest.json           # Chỉ tới lần chạy đã hoàn tất gần nhất
```

`batch` nghĩa là chạy nhiều ảnh tự động trong một lượt; `manual` là mở từng ảnh để người dùng sửa góc hoặc xoay. Hai nơi dùng cùng mã lượt chạy với thư mục ảnh tương ứng trong `data/processed`. `scan_path` trong CSV/JSON mới tính từ gốc dự án (`scan_path_base=project`); `metadata_path` tính từ thư mục batch.

Ảnh PNG giữ màu và đã nắn phối cảnh; chưa tự làm trắng nền hoặc nhận dạng chữ. `ok` là trạng thái xử lý, không bảo đảm khung đúng. `uncertain` là có khung nhưng cần xem lại; `no_candidate` là chưa tìm được khung phù hợp. Kết quả đúng/sai được chấm bằng IoU riêng.

## 5. Cấu trúc mã nguồn

```text
configs/scanner.json                 # Các ngưỡng xử lý
src/document_scanner/
├── data/                            # Nạp, kiểm tra, chia tập và overlay tuần 1
├── scanner/
│   ├── detect.py                    # Canny + Otsu, chọn tứ giác
│   ├── geometry.py                  # Kiểm tra góc, warp, ma trận H/T, xoay
│   ├── scan.py                      # Chạy tự động theo lô
│   ├── manual_scan.py               # Xem/sửa góc một ảnh
│   └── evaluate.py                  # Chấm kết quả và xuất minh họa
├── ocr/                             # Dành cho phần OCR sau này
└── layout/                          # Dành cho thứ tự đọc sau này
```

`detect.py` và `geometry.py` là thư viện dùng chung, không còn đoạn chạy thử riêng ở cuối file. Dữ liệu gốc ở `data/raw/`; manifest ở `data/interim/`; ảnh sau scan ở `data/processed/`; thông tin chạy và đánh giá ở `artifacts/week2/`. `models/`, `ocr/`, `layout/` được giữ cho các phần sau.

## 6. Kiểm tra và giới hạn

```powershell
python -X utf8 -B -m unittest discover -s tests -v
```

Các kiểm tra bao phủ lỗi lật gương, xoay và H/T, góc sai/ngoài ảnh, ảnh trống, công thức IoU, giữ ca thất bại trong mẫu số và không chấm test. Có kiểm tra lưu PNG vào processed, JSON vào artifacts cho cả chạy tự động và sửa tay, cùng khả năng đọc đường dẫn kiểu cũ.

Thuật toán hiện còn yếu ở nền khó, đặc biệt background04–05. Số ảnh lớn không thay thế sự đa dạng: 24.889 frame chỉ thuộc 30 trang gốc. Chưa đo được CER/WER tiếng Việt hay tỷ lệ báo nhầm trên ảnh không có giấy thực tế. Chi tiết và số liệu cuối cùng nằm trong [báo cáo tuần 2](docs/week2_report.md).

## 7. Git và nguồn

Chỉ đưa code, cấu hình, tài liệu và bảng tổng hợp nhỏ lên Git. `.gitignore` giữ ảnh, dữ liệu gốc, manifest, venv và artifacts trên máy. Không commit ảnh nhúng trong tài liệu nếu muốn giữ ảnh hoàn toàn cục bộ.

Khi dùng ảnh SmartDoc, ghi nguồn theo [hướng dẫn của bộ dữ liệu](https://github.com/jchazalon/smartdoc15-ch1-dataset). Việc tạo báo cáo không tự động tạo commit hoặc đẩy code lên GitHub.
