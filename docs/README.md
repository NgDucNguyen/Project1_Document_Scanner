# Mục lục tài liệu

Cập nhật ngày 09/11/2026: ảnh kết quả cũ đã dọn; tài liệu và bảng số liệu lịch sử được giữ lại. Dữ liệu gốc vẫn ở `data/raw/` trên máy.

## Bạn cần mở gì

| Mục đích | File |
| --- | --- |
| Đọc báo cáo tuần 2 | [week2_report.md](week2_report.md) |
| Đọc kết quả OCR tiếng Anh và cách chạy | [week3_ocr_report.md](week3_ocr_report.md) |
| Thử OCR trên ảnh và file TXT của bạn | [thu_ocr_mot_anh.md](guides/thu_ocr_mot_anh.md) |
| Cài đặt và chạy chương trình | [README gốc](../README.md) |
| Xem so sánh 20 ảnh RDTAG | [rdtag_development_comparison.csv](results/rdtag_development_comparison.csv) |

## Cấu trúc hiện tại

```text
docs/
├── README.md                 # Mục lục bạn đang đọc
├── week1_report.md           # Kết quả chuẩn bị dữ liệu tuần 1
├── week2_report.md           # Báo cáo tuần 2 chi tiết
├── week3_ocr_report.md       # Huấn luyện, đánh giá và chạy OCR tiếng Anh
├── guides/                   # Chỉ mở khi cần hướng dẫn hoặc tra cứu
│   ├── phase1_data.md        # Cách nạp, kiểm tra, chia tập và vẽ nhãn
│   ├── phase2_scanner.md     # Cách chạy quét, sửa tay, chấm và hiểu trạng thái
│   ├── thu_ocr_mot_anh.md    # Thử một ảnh và đánh giá bằng file TXT
│   └── data_sources.md       # Nguồn cũ/mới, lý do đổi dataset và quy ước nhãn
└── results/                  # Số liệu làm căn cứ cho báo cáo, không phải code
    ├── week2_metrics.json        # Tổng hợp lần chạy và điểm train/validation
    ├── week3_ocr_page_metrics.csv # Tổng hợp các lần đánh giá OCR toàn trang
    ├── rdtag_development_comparison.csv # Kết quả thử scanner → OCR trên 20 ảnh
    ├── week2_by_background.csv   # Số liệu theo từng nền
    ├── week2_examples.csv        # Danh sách 10 ảnh minh họa
    ├── week2_splits.json         # Danh sách trang gốc thuộc từng tập
    ├── week2_verification.json   # Kết quả kiểm tra toàn bộ PNG/JSON/H/T
    ├── week2_storage.json        # Kiểm tra chuyển PNG sang processed ngày 25/10
    └── week2_report_check.json   # Hash và xác nhận kiểm tra bố cục Word
```

## Vì sao giữ các file này

- Báo cáo tuần 1 và tuần 2 ghi hai giai đoạn khác nhau.
- guides là hướng dẫn thao tác và thông tin nguồn; không phải kết quả chạy thử.
- results chứa các bảng/file tổng hợp nhỏ của tuần 2 và OCR. Chúng giúp đối chiếu số trong báo cáo mà không cần đưa ảnh gốc hay toàn bộ kết quả chi tiết lên GitHub.
- week2_examples.csv chỉ đánh dấu 10 ảnh để minh họa. Điểm báo cáo lấy từ toàn bộ train/validation, không lấy riêng 10 ảnh đó.

Ba file hướng dẫn trước đây nằm ngay trong docs, nay đã gom vào guides. Bản Word ngày 24/10/2026 là hồ sơ đã bàn giao nên giữ nguyên; nếu gặp đường dẫn docs/phase2_scanner.md hoặc docs/data_sources.md trong Word, thêm guides sau docs theo cây trên.

Ảnh PNG và JSON từng ảnh của lượt chạy cũ đã dọn. CSV tổng hợp và các snapshot quan trọng vẫn giữ trên máy; số liệu trong báo cáo là số liệu của lượt đã chạy, không ngụ ý ảnh kết quả cũ còn tồn tại. Để tạo ảnh và JSON mới, chạy lại scanner theo README.

Không cần chạy các file trong docs. Chạy chương trình ở src/document_scanner/scanner theo README.
