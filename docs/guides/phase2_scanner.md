# Scanner: phương pháp và cách sử dụng

**Cập nhật 22/11/2026:** scan ảnh chụp đã thêm `orientation.py` để chọn hướng đọc trước detect/crop. Scan riêng dùng Tesseract; pipeline mặc định dùng khung dòng RapidOCR cho hướng/crop. Nhánh này OCR bản màu đã cắt/nắn (`scan_color.png` hoặc bản phóng `ocr_input.png`), không OCR `scan.png` tăng cường. Đây là lựa chọn đầu vào đã chốt sau đối chiếu ba ảnh; mặc định CLI nay là RapidOCR. Xem [hướng dẫn OCR](thu_ocr_mot_anh.md) để chạy.

## Hai phương pháp, cùng đầu ra

`detect.py` là điểm gọi chung, chọn theo `configs/scanner.json` hoặc tham số dòng lệnh.

| Phương pháp | File | Xác định góc bằng gì? |
| --- | --- | --- |
| `docaligner`, mặc định | `docaligner.py` | Mô hình FastViT-T8 đã huấn luyện sẵn sinh bốn heatmap; ngưỡng hóa/Otsu và lấy trọng tâm |
| `classic`, đối chứng | `classic.py` | Canny/Otsu, cạnh xám/Lab, contour, convex hull, xấp xỉ tứ giác và chấm điểm |

Hai cách đều trả tọa độ trên ảnh gốc cho `geometry.py` nắn phối cảnh. Không dùng nhãn thật để tìm hoặc chọn khung. Nhãn chỉ dùng để chấm điểm ngoại tuyến.

## Chạy scanner một ảnh không xuất văn bản

```powershell
python -X utf8 src/document_scanner/scanner/scan_image.py --image "data/raw/thu_detect/anh_2.jpg"
```

`scan_document()` trong `scan_image.py` là phần scan dùng chung với pipeline OCR: nếu đủ góc thì nắn; thiếu góc thì `crop_content()` tìm cụm nét chữ trên nền sáng, kiểm tra bằng hộp từ Tesseract và chọn một vùng lớn nhất. Không gom mọi hộp chữ vào một khung. Nếu không có vùng đủ bằng chứng thì dừng, không trả toàn ảnh làm kết quả scan giả.

Ảnh cuối `scan.png`, ảnh trước tăng cường `scan_color.png` và ảnh đánh dấu `region.png` ở `data/processed/scan/image_<tên>_<mã_đường_dẫn>/`; metadata ở thư mục cùng tên trong `artifacts/scans/`. Chạy lại cùng ảnh cập nhật đúng thư mục này; `--new-run` mới tạo lượt thời gian riêng. Các benchmark và batch không đổi cách lưu. Không xuất TXT hoặc chạy nhận dạng văn bản cuối. Tesseract vẫn cần nếu gọi nhánh tìm hộp chữ dự phòng.

Sau cập nhật 18/11, `appearance.py` kiểm tra chất lượng vùng cắt trước khi làm sáng ảnh. Vùng nắn không đạt thì thử vùng chữ; kết quả cuối không đạt thì báo `rejected_quality` và không xuất ảnh scan thành công. `configs/scan.json` giữ ngưỡng và cấu hình tăng cường riêng, không thay cấu hình/thuật toán detector SmartDoc. Cơ chế này chỉ loại một số ca rõ ràng, chưa phải mô hình phân loại tài liệu.

Nhánh vùng chữ thử thêm `refine_content_perspective()`: lấy contour/hull từ mặt nạ giấy, xấp xỉ tứ giác, kiểm tra giữ hộp chữ và nét ảnh rồi mới nắn. Nếu không đạt thì giữ xoay/cắt cũ. Không giả định mọi vùng chữ đều có đủ bằng chứng để nắn trang. Tọa độ tứ giác được đưa về ảnh gốc và ghi riêng trong `content_detection.perspective_refinement`, không thay nhãn góc DocAligner.

Ảnh qua kiểm tra được bù nền trong Lab, tăng độ đậm mực và làm trắng nền bằng hỗ trợ nét cục bộ. Tô trắng có thể sai với giấy tối, hình vẽ hoặc nét rất nhạt; phải đối chiếu `scan_color.png`. `--no-enhance` tắt tăng cường. Chưa sửa trang cong hoặc tự nhận hướng đọc 90°/180° một cách tổng quát.

`--detect-only` tắt dự phòng để đánh giá riêng detector; `--method both` so sánh hai nhánh độc lập. Xem [ghi chú detect](ghi_chu_detect.md) về cơ chế, giới hạn và mẫu ghi ca thử.

## Chạy một ảnh qua scanner và OCR

```powershell
python -X utf8 src/document_scanner/pipeline.py --image "data/raw/thu_ocr/anh.jpg"
python -X utf8 src/document_scanner/pipeline.py --image "data/raw/thu_ocr/anh.jpg" --scanner-method classic
```

Mỗi lệnh tạo một thư mục `data/processed/pipeline/<run_id>/` với ảnh, TXT và metadata. Pipeline gọi chung `scan_document()`; ngoài dự phòng khi thiếu góc còn yêu cầu kiểm tra mất chữ sau nắn như trước. Batch SmartDoc `scan.py` không chạy cắt dự phòng hoặc OCR, nên kết quả benchmark detector cũ không bị trộn với nhánh mới.

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
