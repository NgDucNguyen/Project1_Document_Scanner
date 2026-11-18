# Mục lục tài liệu

**Cập nhật 19/11/2026:** báo cáo MD/Word đã bổ sung scan riêng, chọn vùng chữ chính khi thiếu góc, nắn phối cảnh dự phòng, kiểm tra chất lượng và làm rõ ảnh. Pipeline OCR đã gọi chung scanner. Số liệu SmartDoc giữ nguyên; hai ảnh mới chỉ là thử chức năng, chưa hoàn tất đánh giá độc lập hoặc đo lại OCR.

Chỉ cần mở:

1. Báo cáo scanner hiện tại: [Word có ảnh minh họa](bao_cao_tien_do_scanner.docx) · [Markdown](bao_cao_tien_do_scanner.md).
2. [Kế hoạch 7 ngày và trạng thái công việc](ke_hoach_7_ngay_cai_thien_scanner.md).
3. [Bảng so sánh Canny/Otsu với DocAligner](results/scanner_comparison.csv).
4. [README gốc: cài đặt, chạy và cấu trúc](../README.md) và [quy tắc dành cho AI](../AGENTS.md).

## Hướng dẫn khi cần

- [Ghi chú thử detect, DocAligner và vị trí dùng Canny/Otsu](guides/ghi_chu_detect.md): có mẫu để tự ghi các ca thử.
- [Scanner: phương pháp và trạng thái](guides/phase2_scanner.md).
- [Thử OCR trên một ảnh](guides/thu_ocr_mot_anh.md).
- [Chuẩn bị dữ liệu](guides/phase1_data.md).
- [Nguồn dữ liệu](guides/data_sources.md).

## Hồ sơ lịch sử

`history/` giữ báo cáo tuần 1–3, đề xuất OCR cũ, nhật ký các lượt thử và bảng số liệu trước khi chốt DocAligner. Đây là hồ sơ để đối chiếu, không phải hướng dẫn chạy hiện tại. Các tên script thử và đường dẫn cũ có thể đã được gộp hoặc chuyển chỗ.

- [Tuần 1](history/week1_report.md).
- [Tuần 2](history/week2_report.md).
- [OCR tiếng Anh](history/week3_ocr_report.md).
- [Nhật ký thử nghiệm scanner](history/scanner_experiments_2026-11-17.md).
