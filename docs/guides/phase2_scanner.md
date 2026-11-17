# Scanner: phương pháp và cách sử dụng

## Hai phương pháp, cùng đầu ra

`detect.py` là điểm gọi chung, chọn theo `configs/scanner.json` hoặc tham số dòng lệnh.

| Phương pháp | File | Xác định góc bằng gì? |
| --- | --- | --- |
| `docaligner`, mặc định | `docaligner.py` | Mô hình FastViT-T8 đã huấn luyện sẵn sinh bốn heatmap; ngưỡng hóa/Otsu và lấy trọng tâm |
| `classic`, đối chứng | `classic.py` | Canny/Otsu, cạnh xám/Lab, contour, convex hull, xấp xỉ tứ giác và chấm điểm |

Hai cách đều trả tọa độ trên ảnh gốc cho `geometry.py` nắn phối cảnh. Không dùng nhãn thật để tìm hoặc chọn khung. Nhãn chỉ dùng để chấm điểm ngoại tuyến.

## Chạy một ảnh qua scanner và OCR

```powershell
python -X utf8 src/document_scanner/pipeline.py --image "data/raw/thu_ocr/anh.jpg"
python -X utf8 src/document_scanner/pipeline.py --image "data/raw/thu_ocr/anh.jpg" --scanner-method classic
```

Mỗi lệnh tạo một thư mục `data/processed/pipeline/<run_id>/` với ảnh, TXT và metadata. Khi thiếu góc hoặc khung có dấu hiệu mất chữ, pipeline dùng Tesseract tìm vùng chữ dự phòng. Batch `scan.py` không chạy cắt dự phòng hoặc OCR.

## Detect toàn bộ, không tạo ảnh

```powershell
python -X utf8 src/document_scanner/scanner/benchmark_detection.py --method docaligner --run-name doc_full_v2 --workers 4
python -X utf8 src/document_scanner/scanner/benchmark_detection.py --method classic --run-name classic_full_v2 --workers 4
```

Kết quả `artifacts/scanner_dev/<run_name>/`: mỗi ảnh một dòng trong `results.csv`, tổng hợp trong `summary.csv`. Chỉ chấm train/val, không chấm test. Không ghi đè tên đã có, không tự cập nhật bảng kết luận cũ trong docs.

## Tạo ảnh scan theo lô

```powershell
python -X utf8 src/document_scanner/scanner/scan.py --method docaligner --split val --limit 20 --workers 4
python -X utf8 src/document_scanner/scanner/evaluate.py
```

Ảnh ở `data/processed/scan/<run_id>/`; bảng và metadata ở `artifacts/scans/<run_id>/`. Bỏ `--limit` nếu cần xử lý cả tập đã chọn. `--split all` gồm đủ 24.889 ảnh. `evaluate.py` chấm IoU train/val cho lượt scan hoàn thành gần nhất; `--run` chọn lượt khác. Tùy chọn `--examples` chỉ dùng nếu snapshot khớp mã hiện tại.

## Trạng thái và giới hạn

- `ok`: có khung, chưa có cảnh báo của phương pháp; không bảo đảm đúng tài liệu.
- `uncertain`: có khung nhưng cần kiểm tra. DocAligner hiện báo `document_presence_not_verified` vì chưa đánh giá đủ ảnh không có tài liệu. Classic có cảnh báo mờ, khung cạnh tranh hoặc điểm yếu.
- `no_candidate`: chưa tìm được bốn góc phù hợp.
- `low_confidence`: classic có ứng viên nhưng điểm dưới 5,0, từ chối trả góc.
- `content_fallback`: pipeline dùng vùng chữ, không phải mép trang giấy.
- `unreadable_image`/`processing_error`: lỗi đọc hoặc xử lý.

IoU = diện tích giao / diện tích hợp của khung dự đoán và nhãn. Detect-only đạt khi IoU ≥ 0,9; đánh giá ảnh scan yêu cầu thêm nắn/lưu thành công. IoU không đo độ nét hoặc lỗi OCR. Bốn góc hình học không tự biết đầu trang theo chữ; nắn phối cảnh không tự phục hồi chữ bị che hoặc đã ra ngoài ảnh.

## Sửa góc bằng tay khi cần

```powershell
python -X utf8 src/document_scanner/scanner/manual_scan.py --image "data/raw/thu_ocr/anh.jpg"
```

`R` chọn lại góc, `P` xem trước, `E` xoay 90 độ, `S` lưu, `Q`/Esc thoát. Ảnh ở `data/processed/manual/`, metadata ở `artifacts/manual/`. Không cần sửa tay toàn bộ dữ liệu; kết quả sửa tay không được gộp vào chỉ số tự động.
