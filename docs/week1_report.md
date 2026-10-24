# Kết quả chuẩn bị dữ liệu tuần 1

Ngày kiểm tra: 24/10/2026. Bộ dữ liệu: SmartDoc 2015 Challenge 1, bản frames v2.0.0.

## Phạm vi đã thực hiện

Đã viết bốn script: đọc metadata, kiểm tra ảnh/nhãn, tạo manifest và chia tập, vẽ nhãn để kiểm tra trực quan. Chưa triển khai thuật toán tự tìm góc, nắn phối cảnh hoặc OCR. Đường viền trên overlay lấy từ nhãn nguồn.

## Kết quả dữ liệu

- 24.889 frame, 30 trang gốc, 6 loại tài liệu và 5 nền.
- 24.889 dòng được đánh dấu `valid`; `invalid_rows.csv` không có dòng dữ liệu.
- Kích thước ảnh trong manifest: 1920 × 1080.
- Không thiếu đường dẫn, không trùng đường dẫn; metadata nguồn được giữ nguyên trong manifest.
- Kiểm tra độc lập không phát hiện góc trùng, tọa độ không hữu hạn hoặc tứ giác không lồi.

| Nền | Số ảnh |
| --- | ---: |
| background01 | 6.180 |
| background02 | 6.011 |
| background03 | 5.952 |
| background04 | 4.169 |
| background05 | 2.577 |

| Loại tài liệu | Số ảnh |
| --- | ---: |
| datasheet | 4.391 |
| letter | 4.230 |
| magazine | 4.195 |
| paper | 4.097 |
| patent | 4.036 |
| tax | 3.940 |

## Chia tập

Seed: 42. Đơn vị chia là `model_name`, không phải frame. Tổng số dòng trước/sau chia không đổi; không thiếu nhãn tập và không trùng nhóm giữa các tập.

| Tập | Trang gốc | Frame |
| --- | ---: | ---: |
| Train | 21 | 17.495 |
| Validation | 4 | 3.192 |
| Test | 5 | 4.202 |

## Kiểm tra trực quan và giới hạn

Đã tạo 50 overlay, mỗi nền 10 ảnh; cả 50 file đọc được. Bộ mẫu bao phủ 10/30 trang gốc. Trong lần rà soát này đã mở xem 5 ảnh đại diện cho 5 nền: đường viền nhìn chung bám khung trang, có cả ảnh xoay và ảnh bị vật thể che. Đây là kiểm tra mẫu, chưa chứng minh tất cả 24.889 nhãn đều chính xác.

Cần bổ sung kiểm tra trực quan các trang chưa xem. Số frame lớn không đồng nghĩa có nhiều trang độc lập: 24.889 frame chỉ thuộc 30 trang gốc. SmartDoc cung cấp nhãn khung giấy; chưa có kết quả OCR tiếng Việt hoặc đánh giá báo nhầm trên ảnh không có giấy.

## Đầu vào cho tuần 2

Dùng ảnh gốc và `data/interim/manifest_with_split.csv` để phát triển tìm góc và nắn ảnh. Dùng validation để chọn tham số; giữ test cho đánh giá cuối. So góc dự đoán với nhãn nguồn để đo chất lượng. Hướng dẫn tái tạo đầu ra nằm trong [phase1_data.md](phase1_data.md).

Ảnh, dữ liệu gốc và CSV sinh ra chỉ lưu trên máy. Repository chứa code, hướng dẫn và báo cáo số liệu.
