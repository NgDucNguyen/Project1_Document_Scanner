# Kế hoạch 7 ngày cải thiện scanner

**Cập nhật 19/11/2026.** DocAligner là scanner chính để tiếp tục kiểm thử; giữ Canny/Otsu làm đối chứng và Tesseract/FUNSD cho OCR tiếng Anh.

Báo cáo đầy đủ, phương pháp, số liệu và ảnh minh họa nằm trong [bản Markdown](bao_cao_tien_do_scanner.md) hoặc [bản Word](bao_cao_tien_do_scanner.docx). File này chỉ theo dõi công việc.

## Tiến độ

| Ngày | Công việc | Trạng thái |
| --- | --- | --- |
| 1 | Chốt tập phát triển, lưu cấu hình và kết quả mốc | Đã làm: 200 ảnh validation, cân bằng 5 nền |
| 2 | Phân tích lỗi Canny/Otsu/contour | Đã làm: thiếu khung tốt ngay từ bước tạo ứng viên |
| 3 | Cải thiện khung, mép ngoài và từ chối khung yếu | Đã làm: thêm cạnh xám/Lab, ngưỡng từ chối và cảnh báo |
| 4 | Thử DBNet cho vùng chữ dự phòng | Đã làm: bản thử mất nội dung, giữ Tesseract; mã thử không dùng đã gỡ |
| Bổ sung | Chạy toàn SmartDoc, thử mô hình bốn góc DocAligner | Đã làm: đủ 24.889 ảnh cho cả hai phương pháp |
| 5 | Kiểm thử ảnh mới, tiếng Việt và ảnh không có giấy | Đang làm: thử hai ảnh viết tay, dùng chung scanner với pipeline, nắn vùng chữ dự phòng và làm rõ ảnh; chưa đủ tập đánh giá/ảnh âm tính |
| 6 | Tổng hợp lỗi và chốt cấu hình sau kiểm thử thực tế | Đang chốt DocAligner làm phương pháp chính để kiểm thử tiếp |
| 7 | Báo cáo và demo pipeline | Đã cập nhật báo cáo MD/Word về scan riêng, dự phòng và làm rõ ảnh; chưa hoàn tất đánh giá ngày 5 |

## Việc cần làm ở ngày 5

Đã có kiểm tra chất lượng theo quy tắc, thư mục scan ổn định cho từng ảnh và mốc minh họa trước/sau. Còn cần kiểm tra cắt mất chữ, giấy phụ, nét nhạt và ảnh âm tính trên tập riêng. OCR tiếp tục dùng chung scanner; chưa đo lại chất lượng nhận dạng sau tăng cường ảnh.

1. Chuẩn bị tập riêng gồm ảnh tiếng Việt, tiếng Anh, giấy gần màu nền, bóng đổ, góc nghiêng và ảnh không có giấy. Không lấy lại frame SmartDoc để gọi là ảnh mới.
2. Lập danh sách nguồn ảnh; thống nhất cách xử lý sách, nhiều trang và tài liệu bị che trước khi chấm.
3. Gán bốn góc cho ảnh có trang giấy; ảnh không có tài liệu ghi nhãn âm tính. Giữ nhãn ngoài luồng dự đoán.
4. Chạy DocAligner và classic trên cùng danh sách, lưu góc và ảnh sau nắn. Kiểm tra mất lề, tiêu đề, chân trang và dấu tiếng Việt.
5. Tổng hợp IoU, tỷ lệ bỏ sót, tỷ lệ nhận nhầm trên ảnh âm tính và thời gian chạy. Với mẫu có TXT chuẩn, đo thêm CER/WER sau pipeline.

Chưa xác minh dữ liệu huấn luyện sẵn của DocAligner có trùng SmartDoc. Vì vậy không dùng điểm SmartDoc cao để thay cho kiểm thử độc lập này.

## Kết quả và quy tắc theo dõi

- [Bảng so sánh chính](results/scanner_comparison.csv).
- [Danh sách 200 ảnh phát triển](results/scanner_dev_manifest.csv).
- Ảnh so sánh cục bộ: `artifacts/scanner_dev/comparison/`.
- Dùng tên lượt chạy mới, giữ kết quả mốc; không chạy lại toàn bộ chỉ vì sửa tài liệu.
- Xem [README](../README.md) để lấy lệnh hiện hành và [AGENTS.md](../AGENTS.md) để biết quy tắc làm việc trong dự án.
- [Nhật ký thử nghiệm trước khi dọn cấu trúc](history/scanner_experiments_2026-11-17.md) chỉ để đối chiếu lịch sử.
