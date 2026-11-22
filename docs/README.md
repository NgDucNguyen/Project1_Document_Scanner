# Mục lục tài liệu

**Báo cáo cập nhật 23/11/2026:** mục 4 có 8 hình OCR ngay cạnh nội dung phân tích: ảnh và TXT tiếng Anh, form trước/sau gom hàng, giới hạn RDTAG, tiếng Việt trước/sau và lỗi mất tiêu đề. Bản Word hiện có 18 trang; OCR ở trang 11–18. Đã bổ sung CER/WER sơ bộ cho Trang1 từ bản chép thủ công chưa được kiểm chứng độc lập; chưa có nhãn chuẩn cho cả sáu trang. Mục 4.7 tổng hợp vấn đề còn tồn tại, mục 4.8 ghi lệnh và đường dẫn demo.
**Tiếng Việt bổ sung 22/11/2026:** --lang vie dùng RapidOCR tìm dòng và Tesseract vie_best đọc từng dòng màu đã nắn; đã chạy sáu trang cùng báo cáo. Xem mục 4.4–4.6 của báo cáo.
**Cập nhật 22/11/2026:** báo cáo MD/Word đã đồng bộ phần chọn hướng đọc, sửa crop mất mục 3 và thử RapidOCR trên ba ảnh chụp cùng trang. Đã chốt nhánh RapidOCR đọc ảnh màu sau cắt/nắn; `scan.png` tăng cường chỉ để xem. Mục 4.1–4.2 giải thích kết quả đối chiếu hai đầu vào, vai trò từng file và các giới hạn. Chưa có CER/WER cho ba ảnh mới; RapidOCR đã được chọn làm mặc định CLI; Tesseract/FUNSD giữ để đối chứng. Điểm test DocAligner 4.201/4.202 (99,98%), mean IoU 0,9889 và audit mục 3.6 là mốc ngày 19/11, chưa đo lại cho luồng mới.

Báo cáo giữ phần Hustack người dùng đã sửa trong Word (W8), 6 ca minh họa Canny/Otsu đối chiếu DocAligner, 2 ví dụ khung/heatmap và hình trước/sau ở đúng nội dung phân tích. Nội dung mới bổ sung đến 23/11/2026; không coi các kế hoạch tiếp theo là đã hoàn thành.

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
