# Nguồn dữ liệu và các thay đổi của dự án

Cập nhật ngày 24/10/2026. Tài liệu này phân biệt kế hoạch, lịch sử mã nguồn và dữ liệu thực tế đang có trên máy.

## 1. Phương án ban đầu

Code cũ ở commit `836946f`, file `src/01_data_pipeline/download_data.py`, dùng `load_dataset("mapo80/DocCornerDataset", split="train", streaming=True)` rồi lấy 2.000 phần tử đầu bằng `take(2000)`. Đầu ra dự kiến là `data/raw/subset_2k/` và `labels.csv`.

Theo [dataset card của DocCornerDataset](https://huggingface.co/datasets/mapo80/DocCornerDataset/blob/main/README.md), `is_negative=True` chỉ ảnh không có tài liệu; tọa độ của mẫu dương được chuẩn hóa. Vì vậy, trường góc trống của mẫu âm không tự nó chứng minh dữ liệu hỏng. Code cũ chưa tách mẫu âm, chưa chuyển tọa độ sang pixel, chưa có kiểm tra nhãn đầy đủ và chia tập theo trang gốc.

Bản đề xuất điều chỉnh ngày 23/10/2026 chọn SmartDoc làm nguồn chính để tập trung vào tìm khung trang giấy. DocCornerDataset được chuyển thành nguồn phụ có thể xem lại sau khi audit. Không có thống kê kiểm chứng đầy đủ cho bộ cũ còn lưu trên máy; không báo rằng “toàn bộ dữ liệu cũ bị lỗi”.

## 2. Dữ liệu đang sử dụng

- Nguồn: [SmartDoc 2015 Challenge 1](https://github.com/jchazalon/smartdoc15-ch1-dataset).
- Bản đóng gói đang sử dụng: frames v2.0.0, từ [Releases](https://github.com/jchazalon/smartdoc15-ch1-dataset/releases).
- Vị trí: `data/raw/smartdoc/`; CSV nguồn đổi tên thành `frames_metadata.csv` sau giải nén.
- Có dữ liệu trên máy trước khi kiểm tra tuần 1 ngày 24/10/2026. Chưa lưu nhật ký xác nhận chính xác thời điểm tải.
- Kiểm tra cục bộ: 24.889 ảnh JPEG, 1920 × 1080, 30 `model_name`, 6 loại tài liệu, 5 nền.
- Nhãn khung giấy là tọa độ pixel. Đọc trường theo tên TL, TR, BR, BL, không dựa vào thứ tự cột nguồn TL, BL, BR, TR.
- Điều kiện ghi nguồn: xem hướng dẫn CC BY 4.0 tại kho SmartDoc. Ảnh gốc và ảnh dẫn xuất giữ trên máy.

24.889 frame không tương đương 24.889 trang độc lập. Các frame cùng trang có thể rất giống nhau; số trang gốc độc lập chỉ là 30.

## 3. Các điểm khác với bản đề xuất

| Nội dung | Đề xuất 6 tuần | Thực hiện hiện tại |
| --- | --- | --- |
| Số ảnh SmartDoc | Subset khoảng 1.500 | Giữ cả 24.889 ảnh hợp lệ |
| Chia trang | Gợi ý 21 train, 3 val, 6 test | 21 train, 4 val, 5 test theo seed 42 |
| Số frame mỗi tập | Dự kiến 1.050/150/300 | 17.495/3.192/4.202 |
| Định dạng manifest | JSONL và splits JSON | CSV, dễ đọc bằng pandas; thêm JSON danh sách nhóm trong docs/results |
| Lấy frame thưa theo thời gian | Đề xuất để giảm trùng gần | Chưa áp dụng; chạy toàn bộ frame |
| Hash ảnh / tìm trùng gần | Đề xuất audit bổ sung | Đã kiểm tra đường dẫn, chưa kiểm tra trùng nội dung toàn bộ ảnh |
| EXIF | Chuẩn hóa hướng ảnh đầu vào | Bộ SmartDoc cố định dùng ảnh 1920 × 1080; chưa có luồng chuẩn hóa EXIF cho ảnh điện thoại tùy ý |
| Ảnh tiếng Việt tự chụp | 180 ảnh dương và 60 ảnh âm | Chưa bổ sung, chuyển sang giai đoạn sau theo thống nhất |
| Nhãn OCR | 36 ảnh chi tiết | Chưa có; chưa thể đo CER/WER |

Việc đổi nguồn đã được chốt khi chuẩn bị tuần 1; báo cáo tuần 2 nhắc lại vì nó ảnh hưởng trực tiếp tới thuật toán và cách chấm. Không phải tuần 2 mới âm thầm thay bộ đánh giá.

## 4. Quy tắc sử dụng các tập

`model_name` là đơn vị chia. Cùng một trang trên mọi nền luôn ở cùng một tập. Danh sách nhóm thực tế lưu tại `docs/results/week2_splits.json`; manifest chi tiết vẫn ở `data/interim/manifest_with_split.csv` trên máy.

Train dùng phát triển; validation dùng đối chiếu và chọn tham số. Lượt quét đầy đủ tuần 2 xử lý cả test theo cấu hình đã chốt để tạo ảnh, nhưng không tính IoU test, không chọn ảnh test để minh họa và không dùng kết quả test để sửa thuật toán. Việc này phải được ghi lại khi đánh giá cuối kỳ; kết quả OCR cuối cùng vẫn chưa tồn tại.

## 5. Tài liệu đối chiếu

- Đề xuất Project 1 bản 6 tuần: file `De_xuat_Project1_6_tuan.docx`, bản điều chỉnh 23/10/2026.
- Lịch sử Git: `836946f` chứa code tải/tiền xử lý cũ; `4c506df` tổ chức lại dự án; `5302ac7` thêm mã dữ liệu tuần 1; `50fab80` bổ sung tài liệu tuần 1.
- Metadata, manifest và kết quả chạy trên máy là căn cứ cho số lượng thực nghiệm trong báo cáo.
