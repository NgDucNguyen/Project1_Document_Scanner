# Phần 1 — Dữ liệu và kiểm tra nhãn

Đã có bốn script để nạp metadata, kiểm tra dữ liệu, chia tập và vẽ nhãn. Xem [kết quả tuần 1](week1_report.md).

## Đầu vào hiện có

- `data/raw/smartdoc/frames_metadata.csv`: một dòng cho mỗi frame.
- `data/raw/smartdoc/background01/` đến `background05/`: ảnh JPEG mà `image_path` trong CSV tham chiếu.
- Nhãn nguồn có thứ tự trường `tl`, `bl`, `br`, `tr` và tọa độ pixel. Nếu mã dùng thứ tự TL → TR → BR → BL, hãy đổi theo tên trường.

## Cách chạy

Tại gốc repository, khi `venv` đã kích hoạt:

```powershell
python src/document_scanner/data/adapters.py
python src/document_scanner/data/validate.py
python src/document_scanner/data/split.py
python src/document_scanner/data/overlay.py
```

Nếu Windows báo `UnicodeEncodeError` khi in tiếng Việt ra terminal hoặc chuyển hướng output, thêm `-X utf8` ngay sau `python`, ví dụ `python -X utf8 src/document_scanner/data/adapters.py`.

| Script | Công việc | Đầu ra |
| --- | --- | --- |
| `adapters.py` | Đọc metadata, thống kê ảnh/trang gốc/nền | Terminal |
| `validate.py` | Đọc ảnh, kiểm tra tọa độ, góc trùng, giới hạn, diện tích và tứ giác lồi | `data/interim/manifest.csv`, `invalid_rows.csv` |
| `split.py` | Chia nhóm `model_name` với seed 42 | `data/interim/manifest_with_split.csv` |
| `overlay.py` | Chọn 10 trang mỗi nền và vẽ nhãn | `artifacts/week1/overlays/` |

Manifest giữ các cột nguồn và thêm `validation_status`, `image_width`, `image_height`. Kích thước ảnh lấy từ ảnh đọc bằng OpenCV, không lấy từ `model_width`/`model_height`. File chia tập thêm `split`: `train`, `val`, `test`; dòng không hợp lệ để trống. `invalid_rows.csv` chỉ có tiêu đề nếu không có lỗi.

## Đọc trạng thái validation

| Trạng thái | Ý nghĩa |
| --- | --- |
| `valid` | Qua các kiểm tra tự động |
| `missing_image` | Không thấy file ảnh |
| `unreadable_image` | OpenCV không đọc được ảnh |
| `non_finite_corner` | Tọa độ thiếu hoặc vô cực |
| `duplicate_corner` | Các góc có vị trí trùng nhau |
| `corner_outside_image` | Tọa độ nằm ngoài ảnh |
| `zero_area` | Diện tích tứ giác không quá 1 pixel vuông |
| `non_convex` | Các góc không tạo thành tứ giác lồi |

Mỗi dòng lỗi ghi nguyên nhân đầu tiên được phát hiện. `valid` không chứng minh nhãn khớp mép giấy; phải xem overlay để kiểm tra điều đó.

## Chia tập và kiểm tra trực quan

Mọi frame cùng `model_name` nằm trong cùng một tập. Không chia ngẫu nhiên từng frame vì những ảnh liên tiếp của cùng trang rất giống nhau. Seed 42 cố định cách chia với cùng dữ liệu và môi trường; danh sách nhóm được in ra terminal và có thể lấy từ manifest.

Overlay hiện chọn cùng 10 trang trên 5 nền do dùng cùng seed trong mỗi nền. Cần bổ sung các trang chưa xem nếu muốn bao phủ đủ 30 trang gốc. Tên góc theo hướng trang tài liệu; khi giấy xoay, TL không nhất thiết ở phía trên trái màn hình. Ảnh nền phức tạp có thể bị che khuất; không mặc định coi đó là nhãn lỗi.

Ảnh và CSV đầu ra giữ trên máy, không đưa lên GitHub. Các script ghi đè đầu ra cùng tên khi chạy lại. Giữ nguyên dữ liệu gốc trong `data/raw/`. Ảnh tiếng Việt tự chụp và ảnh không có giấy sẽ bổ sung sau.

Xem [README gốc](../README.md) để chuẩn bị môi trường và bộ dữ liệu.
