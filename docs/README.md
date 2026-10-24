# Mục lục tài liệu

Cập nhật cách sắp xếp ngày 25/10/2026. Đây là tài liệu và số liệu nhỏ; không chứa bộ ảnh gốc hay 18.571 ảnh scan.

## Bạn cần mở gì

| Mục đích | File |
| --- | --- |
| Đọc báo cáo tuần 2 | [week2_report.md](week2_report.md) |
| Mở báo cáo Word có hình | [Bao_cao_tuan_2.docx](../artifacts/week2/report/Bao_cao_tuan_2.docx) |
| Cài đặt và chạy chương trình | [README gốc](../README.md) |
| Biết từng thư mục kết quả chứa gì | [Chỉ dẫn artifacts](../artifacts/week2/README.md) |
| Xem toàn bộ ảnh sau scan | [data/processed/scan](../data/processed/scan/20261024_161837_753214/) |

## Cấu trúc hiện tại

```text
docs/
├── README.md                 # Mục lục bạn đang đọc
├── week1_report.md           # Kết quả chuẩn bị dữ liệu tuần 1
├── week2_report.md           # Báo cáo tuần 2 chi tiết
├── guides/                   # Chỉ mở khi cần hướng dẫn hoặc tra cứu
│   ├── phase1_data.md        # Cách nạp, kiểm tra, chia tập và vẽ nhãn
│   ├── phase2_scanner.md     # Cách chạy quét, sửa tay, chấm và hiểu trạng thái
│   └── data_sources.md       # Nguồn cũ/mới, lý do đổi dataset và quy ước nhãn
└── results/                  # Số liệu làm căn cứ cho báo cáo, không phải code
    ├── week2_metrics.json        # Tổng hợp lần chạy và điểm train/validation
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
- results chỉ có bảy bảng/file tổng hợp nhỏ. Chúng giúp đối chiếu số trong báo cáo mà không phải mở CSV của 24.889 ảnh.
- week2_examples.csv chỉ đánh dấu 10 ảnh để minh họa. Điểm báo cáo lấy từ toàn bộ train/validation, không lấy riêng 10 ảnh đó.

Ba file hướng dẫn trước đây nằm ngay trong docs, nay đã gom vào guides. Bản Word ngày 24/10/2026 là hồ sơ đã bàn giao nên giữ nguyên; nếu gặp đường dẫn docs/phase2_scanner.md hoặc docs/data_sources.md trong Word, thêm guides sau docs theo cây trên.

Ảnh cuối trước đây nằm cùng JSON trong `artifacts/week2/batch/<run_id>/outputs/`. Từ 25/10, PNG chuyển sang `data/processed/scan/<run_id>/`, JSON sang `artifacts/week2/batch/<run_id>/metadata/`. Ảnh sửa tay chuyển sang `data/processed/manual/`; thông tin góc vẫn ở artifacts. Số liệu trong báo cáo và snapshot gốc không đổi; các đường dẫn trong Word ngày 24/10 cần tra theo bố cục mới này.

Không cần chạy các file trong docs. Chạy chương trình ở src/document_scanner/scanner theo README.
