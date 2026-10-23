# Phần 1 — Dữ liệu và kiểm tra nhãn

**Hiện chưa có script Python để chạy.** Tài liệu này mô tả đầu vào và việc cần xây dựng trong phần 1.

## Đầu vào hiện có

- `data/raw/smartdoc/frames_metadata.csv`: một dòng cho mỗi frame.
- `data/raw/smartdoc/background01/` đến `background05/`: ảnh JPEG mà `image_path` trong CSV tham chiếu.
- Nhãn nguồn có thứ tự trường `tl`, `bl`, `br`, `tr` và tọa độ pixel. Nếu mã dùng thứ tự TL → TR → BR → BL, hãy đổi theo tên trường.

## Việc cần viết trong phần 1

1. Nạp metadata và ảnh bằng đường dẫn tương đối từ gốc SmartDoc.
2. Kiểm tra ảnh, nhãn, kích thước, tứ giác và đường dẫn; xuất thống kê số mẫu hợp lệ và không hợp lệ.
3. Tạo ảnh overlay có đánh số bốn góc để kiểm tra trực quan.
4. Tạo manifest và chia train/validation/test theo `model_name`, lưu seed và danh sách nhóm.
5. Viết notebook hoặc báo cáo EDA về loại tài liệu, nền, nhóm trang và các nhãn đáng ngờ.

Đặt mã phần này trong `src/document_scanner/data/` khi bắt đầu viết. Chỉ tạo dữ liệu dẫn xuất trong `data/interim/` hoặc `data/processed/`; giữ nguyên `data/raw/`. Ảnh tự chụp và bộ ảnh không có giấy sẽ bổ sung sau.

Xem [README gốc](../README.md) để chuẩn bị môi trường và bộ dữ liệu.
