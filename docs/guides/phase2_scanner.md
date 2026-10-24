# Phần 2 — Tìm góc và nắn tài liệu

## Luồng xử lý

Ảnh màu gốc → bản thu nhỏ cạnh dài tối đa 1.000 px → hai nhánh Canny và Otsu → tìm contour → lấy bao lồi → thử xấp xỉ bốn đỉnh → chấm điểm → đưa góc về ảnh gốc → kiểm tra hình học → nắn phối cảnh → lưu PNG và JSON.

Không dùng nhãn để tìm góc. Nhãn chỉ được đọc khi chấm IoU hoặc vẽ khung chuẩn để so sánh.

## Các lệnh thường dùng

Chạy tại gốc dự án với venv đã kích hoạt:

```powershell
# Toàn bộ ảnh, bốn ảnh xử lý đồng thời.
python -X utf8 -u src/document_scanner/scanner/scan.py --split all --workers 4

# Chấm train/validation và xuất 10 ca minh họa.
python -X utf8 src/document_scanner/scanner/evaluate.py --examples

# Chỉ quét train + validation khi phát triển các tuần sau.
python -X utf8 -u src/document_scanner/scanner/scan.py --split dev --workers 4

# Mở một ảnh để xem/sửa góc và xoay.
python -X utf8 src/document_scanner/scanner/manual_scan.py --image data/raw/smartdoc/background04/letter001/frame_0001.jpeg

# Kiểm tra các lỗi quan trọng.
python -X utf8 -B -m unittest discover -s tests -v
```

Để chấm một lần chạy cũ, thêm `--run artifacts/week2/batch/<run_id>`. Để tạo ảnh trung gian phải dùng đúng `detect.py`, `geometry.py` và cấu hình của lần chạy đó; các bản sao nằm trong `source/` và `config.json`. Nếu đã thay đổi thuật toán, khôi phục các file này về vị trí tương ứng trước khi tái tạo. Giữ `evaluate.py` hiện tại để đọc được đường dẫn ảnh trong processed; không chạy trực tiếp file snapshot từ thư mục artifacts.

Mỗi lần chạy sinh một thư mục mới. `batch/latest.json` chỉ cập nhật khi hoàn tất; nếu ngắt giữa chừng, kiểm tra đường dẫn được in khi khởi chạy và `run_info.json`, không nhầm với lần chạy hoàn tất trước đó. Batch hiện chưa có chức năng tiếp tục từ điểm dừng.

## Hiểu các trạng thái

| Trường | Giá trị | Ý nghĩa |
| --- | --- | --- |
| status | ok | Có ứng viên qua bộ lọc và chưa gặp cảnh báo hiện có; không bảo đảm đúng giấy |
| status | uncertain | Có ứng viên nhưng ảnh có dấu hiệu mờ hoặc hai vùng khác nhau có điểm gần nhau |
| status | no_candidate | Không có tứ giác qua bộ lọc |
| status | unreadable_image / processing_error | Không đọc được ảnh hoặc gặp lỗi xử lý; vẫn giữ bản ghi |
| scan_created | True | Đã ghi PNG; không phải nhãn chất lượng |
| passed | True | Khung đạt IoU ≥ 0,9 và đã tạo ảnh scan, chỉ có trong kết quả chấm train/val |

Ngưỡng cảnh báo mờ là phương sai Laplacian dưới 30 trên ảnh thu nhỏ. Cảnh báo mơ hồ khi hai ứng viên khác vùng có chênh điểm không quá 0,15. Đây là quy tắc khởi đầu, chưa được hiệu chỉnh thành xác suất đúng. Ảnh uncertain vẫn được lưu để xem; không được lặng lẽ tính thành ảnh đạt.

## Sửa góc mà không lật gương

Nếu có dự đoán, cửa sổ hiển thị sẵn bốn góc. Khi sai, bấm R rồi chọn đúng bốn đỉnh giấy. Chương trình sắp các điểm quanh tâm theo cùng một chiều và đánh số 0–3. Bấm P xem trước; nếu chữ nằm ngang hoặc ngược đầu, bấm E đến khi đúng hướng, sau đó S để lưu.

Sắp thứ tự hình học chỉ ngăn tráo điểm/lật gương, chưa biết đâu là đầu trang theo nội dung. Bộ quét tự động hiện chưa nhận dạng hướng chữ. Ảnh tương tác lưu trong `data/processed/manual/<run_id>/`; góc trước/sau và thông tin có sửa tay hay không nằm ở `artifacts/week2/manual/<run_id>/corners.json`.

## Đầu ra và ma trận

Ảnh tự động lưu ở `data/processed/scan/<run_id>/<split>/<background>/<model>/`. Trong `artifacts/week2/batch/<run_id>/`, `metadata/` giữ JSON từng ảnh, `results.csv` giữ danh sách kết quả, `evaluation/` giữ điểm đánh giá và `examples/` giữ hình minh họa các bước. Không cần tìm ảnh cuối giữa hàng nghìn JSON nữa.

`scan_path` tính từ gốc dự án khi `scan_path_base=project`; `metadata_path` tính từ thư mục batch. Bộ đánh giá vẫn đọc được đường dẫn ảnh kiểu cũ (tính từ batch) nếu dùng kết quả cũ chưa chuyển.

Mỗi ảnh có JSON chứa đường dẫn nguồn, trạng thái, điểm ứng viên, cảnh báo, thời gian. Ảnh nắn được có thêm bốn góc gốc, PNG, ma trận H từ ảnh gốc tới ảnh nắn và T từ ảnh gốc tới ảnh sau xoay. Khi chưa xoay, H và T giống nhau.

Kích thước ảnh nắn ước lượng bằng cạnh dài hơn của mỗi cặp cạnh đối diện. Chưa biết tỷ lệ vật lý thật của giấy nên không khẳng định kích thước chuẩn A4. Không tự cắt thêm lề, làm trắng nền hoặc tăng độ rõ ở tuần 2.

IoU = diện tích giao của hai tứ giác / diện tích hợp. Không tìm được giấy tính IoU bằng 0. Chỉ số đo vị trí khung, không đo chữ có bị ngược đầu, mờ, mất nét hay OCR đúng.

## Lưu trữ và thời gian

Bản gốc chỉ giữ một lần trong `data/raw/`; không sao chép ảnh gốc cho từng đầu ra. PNG được nén mức 1 để giảm thời gian ghi, vẫn không mất chất lượng do nén. Chỉ 10 ca minh họa có đầy đủ ảnh trung gian để tránh lưu dư hàng trăm nghìn file.

`detection_ms`: thời gian tìm góc. `warp_ms`: thời gian nắn ảnh. `total_ms`: đọc ảnh + tìm góc + nắn + ghi PNG, chưa tính ghi JSON. `wall_seconds`: thời gian cả vòng batch gồm ghi CSV/JSON. Chạy bốn workers là xử lý đồng thời bốn ảnh, không thay đổi thuật toán và không huấn luyện mô hình.

Xem [báo cáo tuần 2](../week2_report.md) để lấy số liệu và phân tích lỗi.
