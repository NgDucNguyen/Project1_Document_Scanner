# Hướng dẫn làm việc với Project 1 Document Scanner

## Đọc trước khi thay đổi

- `README.md`: cài đặt, cấu trúc và các lệnh hiện hành.
- `docs/bao_cao_tien_do_scanner.md`: báo cáo và kết quả hiện tại; bản Word cùng tên phục vụ trình bày.
- `docs/ke_hoach_7_ngay_cai_thien_scanner.md`: tiến độ và việc cần làm tiếp.
- Chỉ đọc `docs/history/` khi cần đối chiếu lịch sử. Không lấy lệnh hoặc tên file cũ ở đó làm hướng dẫn hiện tại.
- Kiểm tra `git status` trước khi sửa, giữ nguyên thay đổi của người dùng nếu chưa rõ mục đích.

## Các quyết định đang áp dụng

- Scanner mặc định là **DocAligner FastViT-T8 đã huấn luyện sẵn**, chạy ONNX bằng OpenCV.
- **Giữ Canny/Otsu trong `scanner/classic.py`** để đối chứng và báo cáo. Không bỏ nhánh này khi cải thiện mô hình chính.
- OCR tiếng Anh vẫn dùng Tesseract với `funsd_eng`; cắt vùng chữ dự phòng vẫn dùng Tesseract.
- DBNet đã thử và không được chọn. Không khôi phục vào luồng mặc định nếu chưa có phép đo mới chứng minh giữ nội dung tốt hơn.
- DocAligner chưa được tự huấn luyện/tinh chỉnh trong dự án. Chưa xác minh dữ liệu huấn luyện sẵn có trùng SmartDoc.
- Việc tiếp theo là kiểm thử ảnh mới, tiếng Việt và ảnh không có tài liệu. Không coi phần này đã hoàn thành.

## Phân chia trách nhiệm mã nguồn

| File | Vai trò |
| --- | --- |
| `src/document_scanner/pipeline.py` | Luồng một ảnh từ scanner đến OCR |
| `scanner/detect.py` | Chọn phương pháp và giao diện gọi chung |
| `scanner/docaligner.py` | Suy luận heatmap và giải mã bốn góc |
| `scanner/classic.py` | Canny/Otsu, nhánh cạnh xám/Lab, ứng viên và chấm điểm |
| `scanner/geometry.py` | Kiểm tra góc, nắn phối cảnh, ma trận H/T |
| `scanner/content_scan.py` | Tìm/cắt vùng chữ dự phòng bằng Tesseract |
| `scanner/benchmark_detection.py` | Detect toàn SmartDoc, không tạo ảnh hoặc OCR |
| `scanner/benchmark.py` | Kiểm chứng tập phát triển cố định hoặc validation còn lại |
| `scanner/scan.py`, `evaluate.py` | Tạo ảnh scan theo lô và chấm train/validation |
| `ocr/`, `data/` | OCR và chuẩn bị dữ liệu |

Các đường dẫn `scanner/` trong bảng tính từ `src/document_scanner/`.

## Quy tắc thực nghiệm

- Nhãn chỉ dùng đánh giá ngoại tuyến, không truyền vào detector để chọn khung.
- Giữ chia tập theo tài liệu gốc. Không trộn các frame cùng tài liệu vào nhiều tập để làm đẹp điểm.
- Test chỉ lưu dự đoán; không chấm hoặc dùng kết quả test để chọn ngưỡng khi chưa có yêu cầu rõ ràng cho giai đoạn đánh giá cuối.
- So sánh trên cùng danh sách ảnh. Lưu tên phương pháp, cấu hình, hash mô hình/nguồn và trạng thái hoàn thành.
- Không bỏ ảnh thất bại khỏi mẫu số. IoU của ảnh không có khung tính 0 trong đánh giá train/val.
- Phân biệt tỷ lệ trả khung, tỷ lệ IoU ≥ 0,9, nắn thành công và chất lượng OCR. Không gọi detect 100% là chính xác 100%.
- Khi báo cáo DocAligner, luôn ghi là mô hình đã huấn luyện sẵn và nêu giới hạn trùng dữ liệu huấn luyện chưa xác minh.
- Mỗi worker OpenCV DNN dùng mạng riêng; không gọi đồng thời một đối tượng mạng từ nhiều luồng.

## Chạy và kiểm tra

Dùng `python`, không dùng `python3`. Chạy từ gốc dự án với venv đã kích hoạt; nếu cần dùng trực tiếp `.\venv\Scripts\python.exe`.

```powershell
python -X utf8 src/document_scanner/pipeline.py --image "data/raw/thu_ocr/anh.jpg"
python -X utf8 src/document_scanner/pipeline.py --image "data/raw/thu_ocr/anh.jpg" --scanner-method classic
python -X utf8 -m unittest discover -s tests
```

- Sau thay đổi detector/pipeline, chạy kiểm thử liên quan và một số ca khó phù hợp với thay đổi. Không thêm kiểm thử chỉ lặp lại cách triển khai.
- Chỉ chạy toàn bộ 24.889 ảnh khi được yêu cầu hoặc cần thiết cho một phép kiểm chứng đã thống nhất. Người dùng ưu tiên nhận lệnh để tự chạy các lượt dài.
- Mỗi lượt benchmark dùng `--run-name` mới; không ghi đè mốc cũ. Chỉ kết luận từ lượt có `complete: true`.
- Không cần chạy lại toàn bộ dữ liệu khi chỉ sửa tài liệu hoặc sắp xếp file.

## Giữ cấu trúc và dọn file

- Báo cáo chính: `docs/bao_cao_tien_do_scanner.md` và `.docx`. Kế hoạch chỉ giữ lịch công việc, không sao chép toàn bộ báo cáo vào nhiều file.
- `docs/results/` giữ hai bảng chính: `scanner_comparison.csv` và `scanner_dev_manifest.csv`. Chỉ thêm bảng mới khi thực sự cần và giải thích vai trò.
- `docs/history/` là hồ sơ lịch sử, không phải kết quả hiện hành.
- `artifacts/scanner_dev/full_detection_v1/` và `docaligner_t8_full/` giữ hai lượt detect toàn bộ. `comparison/` giữ ảnh so sánh cần báo cáo.
- Ảnh cuối ở `data/processed/`; không chép ảnh gốc hoặc mô hình vào nhiều thư mục thử.
- Trước khi xóa hoặc chuyển thư mục, xác minh đường dẫn tuyệt đối nằm trong dự án và giữ số liệu/ảnh minh họa cần dùng. Với yêu cầu dọn file, chỉ xóa phạm vi đã được cho phép; hỏi rõ nếu phạm vi dữ liệu gốc, nhãn, trọng số hoặc kết quả duy nhất còn mơ hồ.
- Không xóa dữ liệu gốc/nhãn hoặc kết quả duy nhất cần tái hiện báo cáo chỉ để giảm số lượng file.
- Không thêm hàng loạt bản `final`, `final_v2`, `new`, `test` vào docs. Cập nhật bản chính; chỉ lưu lịch sử khi có lý do.

## Git và giao tiếp

- Ảnh, dữ liệu gốc, trọng số, venv và artifacts không push lên GitHub. Kiểm tra `.gitignore` và danh sách staged trước khi push.
- Chỉ commit/push khi người dùng yêu cầu. Không force-push hoặc sửa lịch sử từ xa nếu chưa được phép.
- Cập nhật README, báo cáo và lệnh khi thay phương pháp hoặc đường dẫn. Tài liệu lịch sử ghi rõ là lịch sử.
- Giải thích bằng tiếng Việt dễ hiểu, code Python đơn giản, comment ngắn ở bước quan trọng; tránh thêm type hint không cần thiết.
- Khi người dùng yêu cầu chỉ gợi ý hoặc chỉ cho lệnh, không tự sửa code hay khởi chạy lượt dài.
- Không hứa điểm số trước khi đo; ghi rõ điều đã làm, bằng chứng và phần chưa kiểm chứng.
