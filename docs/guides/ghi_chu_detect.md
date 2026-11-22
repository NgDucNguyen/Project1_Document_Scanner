# Ghi chú khi thử detect tài liệu

**Chốt luồng ảnh chụp 22/11/2026:** chọn hướng đọc → DocAligner → nắn hoặc crop nội dung → giữ bản màu. Với `pipeline.py --ocr-engine rapidocr`, khung dòng RapidOCR được dùng làm bằng chứng hướng/crop; OCR cuối đọc `scan_color.png` hoặc `ocr_input.png` tạo từ ảnh màu. `scan.png` tăng cường chỉ để xem. Đã so sánh bản màu và bản tăng cường trên cùng ba ảnh, chưa có TXT để đo CER/WER; không gọi tỷ lệ phân mảnh dòng là độ chính xác. DocAligner/Canny/Otsu vẫn được giữ, các điểm benchmark cũ chưa đo lại cho wrapper mới. Lệnh và vị trí kết quả ở [hướng dẫn OCR](thu_ocr_mot_anh.md).

**Cập nhật 18/11/2026.** Đây là sổ ghi chú khi thử ảnh mới và tài liệu giải thích ngắn để trình bày phương pháp. Báo cáo kết quả chính vẫn ở [báo cáo tiến độ](../bao_cao_tien_do_scanner.md).

## 1. Hiểu đúng các bước

- **Detect:** tìm vị trí bốn góc của trang trên ảnh gốc.
- **Nắn phối cảnh:** dùng bốn tọa độ để biến trang nghiêng thành ảnh hình chữ nhật.
- **Cắt vùng chữ dự phòng:** tìm vùng bao quanh chữ khi không có khung trang phù hợp. Khung nội dung có thể khác mép giấy, không thay thế được mọi trường hợp nắn phối cảnh.
- **OCR:** nhận dạng ảnh chữ thành văn bản. Có ảnh scan không có nghĩa OCR đúng hoặc ảnh đã giữ đủ nội dung.

## 2. DocAligner đang làm những gì

Mô hình hiện dùng là **DocAligner FastViT-T8 đã huấn luyện sẵn**, chạy ONNX bằng OpenCV. Dự án chưa tự huấn luyện hoặc tinh chỉnh mô hình này. Chưa xác minh dữ liệu huấn luyện sẵn có trùng SmartDoc.

Luồng thực tế trong `src/document_scanner/scanner/docaligner.py`:

1. Nhận ảnh màu BGR, resize về **256 × 256**, chia giá trị pixel cho **255**. Không dùng Canny hoặc Otsu để chuẩn bị ảnh đầu vào mạng.
2. Mạng tạo **bốn heatmap**. Mỗi heatmap là bản đồ giá trị thể hiện vị trí một góc; chưa phải tọa độ cuối cùng.
3. Resize từng heatmap về kích thước ảnh gốc; ghi nhận giá trị lớn nhất của mỗi heatmap.
4. Đặt các giá trị **nhỏ hơn 0,3** về 0, chuyển sang ảnh 8 bit rồi dùng **Otsu** tạo mặt nạ nhị phân.
5. Tìm contour trên mặt nạ, lấy vùng có diện tích lớn nhất. Tính trọng tâm bằng moments để lấy tọa độ góc.
6. Khi có đủ bốn tọa độ, sắp thứ tự và kiểm tra hình học: tọa độ hữu hạn, nằm trong ảnh, bốn điểm khác nhau, tứ giác lồi và thứ tự không gây lật gương.
7. Nếu thiếu góc hoặc kiểm tra không đạt, trả `corners = None`, trạng thái `no_candidate`. Nếu có khung hợp lệ, hiện trả `uncertain` cùng cảnh báo `document_presence_not_verified`.
8. Phần **nắn ảnh** nằm trong `geometry.py`, không nằm trong mạng: `build_scan()` dùng `getPerspectiveTransform()` và `warpPerspective()`.

`score` hiện là **giá trị đỉnh nhỏ nhất trong bốn heatmap**, không phải phần trăm xác suất khung đúng. Kiểm tra hình học cũng không bảo đảm đã chọn đúng tờ giấy.

### Có cần nhìn thấy đủ bốn góc không

Mô hình có thể suy đoán góc dù một phần mép bị che; không bắt buộc cả bốn góc vật lý đều rõ. Tuy nhiên, **code nắn phối cảnh hiện cần bốn tọa độ hợp lệ**. Nếu mô hình không tạo được đầu ra này thì nhánh nắn không chạy.

Góc bị che và góc nằm ngoài ảnh là hai tình huống khác nhau. Bộ kiểm tra hiện từ chối tọa độ ngoài ảnh. Không có bước tự dựng thêm góc bị thiếu, và không phục hồi được phần chữ bị che hoặc nằm ngoài ảnh.

## 3. Canny và Otsu dùng ở đâu

| Nhánh                                     | Canny dùng để làm gì                                                                                                  | Otsu dùng để làm gì                                                         |
| ----------------------------------------- | --------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| DocAligner — `docaligner.py`              | Không dùng trong adapter suy luận góc hiện tại                                                                        | Nhị phân hóa **heatmap đầu ra mạng**, trước khi lấy vùng góc và trọng tâm   |
| Classic — `classic.py`                    | Tìm cạnh trên ảnh xám; thêm nhánh ngưỡng thấp trên ảnh xám/kênh Lab b; cung cấp bằng chứng bám cạnh khi chấm ứng viên | Nhị phân hóa **ảnh xám đã làm mượt**, tạo thêm nguồn contour để tìm tứ giác |
| Cắt nội dung dự phòng — `content_scan.py` | `estimate_text_angle()` dùng Canny rồi HoughLinesP để ước lượng góc nghiêng nhỏ                                       | Otsu tách nét black-hat và vùng nền sáng khi tạo ứng viên vùng chữ          |
| Nắn phối cảnh — `geometry.py`             | Không dùng                                                                                                            | Không dùng                                                                  |

**Điểm dễ nhầm:** `findContours()` trong DocAligner tìm vùng góc trên heatmap đã nhị phân hóa. Trong classic, contour đến từ các mặt nạ cạnh/vùng trên ảnh chụp. Cùng dùng hàm tìm contour nhưng khác dữ liệu và mục đích.

Khi chạy DocAligner mặc định, chương trình **không tự chạy tiếp classic** nếu DocAligner thất bại. Lệnh `scan_image.py --method both` chạy hai phương pháp riêng để so sánh; không trộn góc giữa hai phương pháp. File thử trước đây `detect_image.py` đã được thay bằng `scan_image.py`.

## 4. Phân biệt file thử và pipeline

| Công cụ                  | Thực hiện                                                                                                                     | Đầu ra                                                                                |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| `scanner/scan_image.py`  | Detect → nắn nếu có đủ góc; nếu thiếu thì tự cắt vùng chữ chính. Không xuất văn bản OCR. Thêm `--detect-only` để tắt dự phòng | `data/processed/scan/image_<tên>_<mã>/`; metadata ở thư mục cùng tên trong `artifacts/scans/`; chạy lại sẽ cập nhật |
| `pipeline.py`            | Detect, nắn, kiểm tra lượng chữ; thử cắt nội dung nếu thiếu khung hoặc nghi mất chữ; sau đó OCR                               | `data/processed/pipeline/<run_id>/`                                                   |
| `scanner/manual_scan.py` | Cho sửa bốn góc bằng tay và xem trước                                                                                         | `data/processed/manual/`; metadata ở `artifacts/manual/`                              |

Phần scan chung nằm ở `scan_image.py::scan_document()`, được `pipeline.py` gọi lại. Sau cập nhật chất lượng, cả hai thử dự phòng khi thiếu góc hoặc vùng nắn không đạt kiểm tra ảnh; pipeline OCR còn bật kiểm tra mất chữ bằng hộp từ sau nắn.

### Cách chọn vùng chữ chính sau cập nhật

1. Ước lượng xoay nhỏ bằng Canny/Hough; thử hộp chữ trên ảnh gốc và ảnh xoay để tránh xoay làm mất quá nhiều tín hiệu chữ.
2. Lấy nét tối nhỏ bằng black-hat trên ảnh xám. Ước lượng nền sáng qua kênh L của Lab; dùng Otsu tạo mặt nạ, hạn chế vân nền tối.
3. Lọc thành phần quá nhỏ, khối đặc và đường viền dài; dilation nối các nét gần nhau thành các vùng.
4. Dùng hộp từ Tesseract làm bằng chứng: một vùng ứng viên cần ít nhất ba từ đáng tin cậy. Phần nét ảnh giúp giữ cả chữ chưa nhận dạng được trong cùng vùng, thay vì chỉ cắt sát những từ đọc được.
5. Nếu không có vùng nét phù hợp, thử gom các hộp từ gần nhau thành từng cụm riêng. Không gom toàn bộ từ của ảnh thành một hộp.
6. Chọn **ứng viên có diện tích hộp bao lớn nhất**; chừa lề nhỏ rồi cắt hình chữ nhật trong ảnh đã xoay. Nếu vùng thứ hai có diện tích ít nhất 80% vùng chọn, gắn cảnh báo cạnh tranh.
7. Lưu vùng được chọn, các ứng viên và phép biến đổi vào metadata. Nếu không có vùng đủ bằng chứng thì báo thất bại, không ép trả ảnh.

Đây là heuristic, không phải mô hình hiểu trang nào quan trọng. Vùng dự phòng vẫn có thể chứa một phần bàn hoặc giấy bên dưới vì hộp cắt là hình chữ nhật; có thể gộp các trang sát nhau hoặc tách nhầm các cột xa nhau. Hiện ưu tiên nét tối trên nền sáng; giấy tối/chữ sáng chưa được kiểm chứng. Không bảo đảm giữ đủ chữ viết tay, công thức hoặc dấu tiếng Việt. Không xuất TXT ở lệnh scan riêng, nhưng nhánh dự phòng vẫn dùng Tesseract để lấy vị trí chữ.

### Lệnh thử

Chạy từ thư mục gốc, venv đã kích hoạt. Thay đường dẫn khi thử ảnh khác.

```powershell
# Scan tự động: DocAligner rồi vùng chữ chính nếu thiếu góc
python -X utf8 src/document_scanner/scanner/scan_image.py --image "data/raw/thu_detect/anh_2.jpg"

# Chỉ so sánh hai detector, tắt cắt dự phòng
python -X utf8 src/document_scanner/scanner/scan_image.py --image "data/raw/thu_detect/anh_2.jpg" --method both --detect-only

# Chạy toàn pipeline hiện tại, có cắt dự phòng và OCR
python -X utf8 src/document_scanner/pipeline.py --image "data/raw/thu_detect/anh_2.jpg"

# Chọn lại góc bằng tay khi cần; không tính vào thành tích tự động
python -X utf8 src/document_scanner/scanner/manual_scan.py --image "data/raw/thu_detect/anh_2.jpg"
```

## 5. Những kết quả đã quan sát

| Ảnh            | Detect                                                                               | Pipeline và lưu ý                                                                                                                                                                                         |
| -------------- | ------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `anh_viet.jpg` | DocAligner trả bốn góc; classic `no_candidate` ở lượt `20261118_164531_605441`       | Cần xem ảnh sau nắn để kiểm tra lề và chữ; chưa có nhãn nên chưa tính IoU                                                                                                                                 |
| `anh_2.jpg`    | Cả hai `no_candidate` ở lượt `20261118_164845_418424`; score DocAligner khoảng 0,037 | Pipeline lượt `20261118_165149_785451` tạo đầu ra bằng **`content_fallback`**, xoay −3,39°. `corners_original` và `H_source_to_warp` đều null; đây là xoay/cắt vùng chữ, chưa phải nắn bốn góc thành công |

Ảnh thứ hai có nhiều trang chồng nhau và trang chính sát mép ảnh. Đây là yếu tố cần khảo sát, chưa đủ bằng chứng để khẳng định nguyên nhân chính. Không hạ ngưỡng chỉ để ép có khung rồi coi là cải thiện.

Metadata xác nhận luồng đã chạy, không tự chứng minh ảnh cắt đúng. Cần mở `scan.png` và so sánh với ảnh gốc.

**Lượt thử nhánh mới:** `anh_2.jpg` tại `single_20261118_170413_305785` dùng `content_fallback`, xem `data/processed/scan/single_20261118_170413_305785/scan.png` và `region.png`. Phần lớn tờ bên trái và cây bút đã nằm ngoài vùng cắt; còn nền và một phần trang bên dưới, chưa phải tách mép trang hoàn hảo. `anh_viet.jpg` tại `single_20261118_170321_986081` dùng bốn góc DocAligner, không cần nhánh vùng chữ. Đã chạy 40 kiểm thử, gồm loại cụm chữ bên cạnh, cảnh báo vùng cạnh tranh, giữ nét đầu trang dù chỉ nhận dạng được từ phía dưới, và hai đường đi của scanner. Hai ảnh chưa có nhãn nên chưa chấm IoU và chưa kết luận cải thiện trên toàn bộ tập.

## 6. Các lưu ý khi kiểm tra ảnh mới

- Xác định trước muốn lấy trang nào nếu ảnh có nhiều tờ; không đổi mục tiêu sau khi xem dự đoán.
- Xem ảnh vẽ góc **và** ảnh sau nắn: đúng tờ giấy, đủ tiêu đề/chân trang/lề, không mất chữ, không lật gương hoặc xoay sai.
- Ghi riêng các lỗi: không có góc, sai trang, khung bên trong, thiếu góc ngoài ảnh, gộp nhiều trang, mất nội dung khi cắt dự phòng.
- `uncertain` không đồng nghĩa detect thất bại; `no_candidate` nghĩa chưa có bốn góc hợp lệ. `content_fallback` là nhánh nội dung, không tính là DocAligner tìm được trang.
- Không có nhãn bốn góc thì chỉ đánh giá trực quan, chưa đưa ra IoU hoặc tỷ lệ chính xác.
- Lưu ca lỗi cùng ca thành công, ghi cấu hình và tên lượt; không chỉ chọn ảnh đẹp để báo cáo.
- Nếu so sánh thuật toán, dùng cùng ảnh và cùng tiêu chí. Điểm cao trên SmartDoc chưa thay thế kiểm thử ảnh mới/ảnh không có giấy.

## 7. Mẫu ghi chép cho mỗi ảnh

Sao chép khối dưới đây ngay trong file này khi cần thêm một ca.

### Ca thử mới

- Ngày thử:
- Tên/đường dẫn ảnh:
- Trang muốn lấy:
- Điều kiện chụp: nền, ánh sáng, độ nghiêng, che khuất, nhiều trang...
- Phương pháp và tham số:
- Đường dẫn kết quả hoặc run_id:
- Trạng thái detector / score:
- Có dùng cắt dự phòng không:
- Đúng trang / đủ lề / đủ chữ / đúng hướng:
- Lỗi quan sát được:
- Có nhãn bốn góc không / IoU nếu có:
- Giả thuyết nguyên nhân, chưa phải kết luận:
- Việc cần thử tiếp:

## 8. Mở code khi cần giải thích

- [Chọn detector](../../src/document_scanner/scanner/detect.py): `detect_document()`.
- [DocAligner](../../src/document_scanner/scanner/docaligner.py): `CornerModel.__call__()` — ảnh → heatmap → Otsu → contour → góc.
- [Classic](../../src/document_scanner/scanner/classic.py): `detect_document()`, `score_candidate()` — cạnh/vùng → ứng viên tứ giác → chấm điểm.
- [Hình học](../../src/document_scanner/scanner/geometry.py): `validate_corners()`, `build_scan()`.
- [Dự phòng](../../src/document_scanner/scanner/content_scan.py): `estimate_text_angle()`, `crop_content()`, `page_crop_seems_wrong()`.
- [Pipeline](../../src/document_scanner/pipeline.py): `process_image()` — gọi scanner chung rồi mới OCR.
- [Scanner dùng chung](../../src/document_scanner/scanner/scan_image.py): `scan_document()` — thực hiện nắn hoặc cắt dự phòng; pipeline gọi lại hàm này.

**Cách nói ngắn khi báo cáo:** “Em dùng DocAligner đã huấn luyện sẵn để dự đoán bốn bản đồ góc. Sau đó dùng Otsu trên các heatmap và lấy trọng tâm để ra tọa độ; OpenCV nắn phối cảnh từ bốn điểm. Canny/Otsu trên ảnh gốc vẫn giữ trong phương pháp truyền thống để đối chứng. Nếu không có khung phù hợp, pipeline thử cắt vùng nội dung và ghi rõ đó là kết quả dự phòng.”

## 9. Checklist rà soát ngày 18/11/2026

**Kết luận: đã có luồng scan tự động chạy được, chưa hoàn thiện chất lượng detect trên ảnh thực tế.** “Đã có” ở bảng dưới chỉ xác nhận cơ chế và kiểm thử hiện tại, không có nghĩa luôn chọn đúng trang.

| Hạng mục                                      | Trạng thái kiểm chứng                                                           | Còn thiếu                                                                                                                            |
| --------------------------------------------- | ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Ảnh → DocAligner → nắn hoặc vùng chữ dự phòng | Đã có trong `scan_document()`; hai ảnh mới đi qua được hai nhánh khác nhau      | Chưa đo tỷ lệ thành công của toàn luồng trên tập ảnh độc lập                                                                         |
| Bốn góc hợp lệ, không nối chéo/lật gương      | Có kiểm tra hình học và kiểm thử phép biến đổi                                  | Không bảo đảm đúng trang hoặc tự xác định đầu trang theo chữ                                                                         |
| Chọn một vùng chữ thay vì bao tất cả từ       | Đã có chọn vùng lớn nhất có ít nhất ba từ hỗ trợ; có kiểm thử loại cụm bên cạnh | Vùng lớn nhất chưa chắc là trang người dùng muốn lấy; các trang sát nhau vẫn có thể dính vùng                                        |
| Loại giấy phụ và vật xung quanh               | `anh_2.jpg` đã loại phần lớn giấy phụ/bút bên trái                              | Ảnh mới nhất vẫn chứa một phần nền bàn và giấy bên dưới; chưa đạt tách trang sạch hoàn toàn                                          |
| Giữ đủ nội dung, tiêu đề, chân trang và dấu   | Có lề và nét ảnh hỗ trợ, không chỉ dùng từ đã đọc được                          | Chưa có phép đo mất chữ hoặc nhãn kiểm chứng cho hai ảnh mới; nội dung nhiều cột xa nhau có thể bị tách                              |
| Từ chối ảnh không có tài liệu                 | Có cảnh báo `document_presence_not_verified` của DocAligner                     | Chưa có bộ kiểm thử âm tính; cảnh báo không phải cơ chế từ chối đáng tin cậy                                                         |
| Chữ viết tay và công thức                     | Đã thử hai ảnh; dự phòng tạo được crop cho ảnh thứ hai                          | Vẫn cần ít nhất ba từ Tesseract đủ tin cậy; chữ khó đọc/ít chữ có thể không qua điều kiện                                            |
| Xử lý nghiêng và phối cảnh                    | Có nắn phối cảnh khi đủ góc; dự phòng ước lượng góc nhỏ rồi xoay/cắt            | Dự phòng không khử phối cảnh đầy đủ; chưa xử lý cong trang, góc ngoài ảnh hoặc xoay lớn một cách tổng quát                           |
| Scan riêng và pipeline OCR dùng chung mã      | Cùng gọi `scan_document()`                                                      | Khác chế độ: scan riêng mặc định `check_content=False`, pipeline bật `True`; có thể chọn nhánh khác nếu đã có góc nhưng nghi mất chữ |
| Giữ classic Canny/Otsu để đối chứng           | Đã giữ; không tự trộn góc classic vào DocAligner                                | Kết quả detector thuần cần tách khỏi kết quả cắt dự phòng khi thống kê                                                               |
| Lưu ảnh, trạng thái và truy vết               | Có ảnh cuối, overlay, metadata, hash ảnh/model và ba file scan                  | Chưa snapshot đầy đủ `detect.py`, `docaligner.py`, `classic.py`, cấu hình và phiên bản Tesseract/OpenCV trong lệnh scan một ảnh      |
| Kiểm thử tự động và dữ liệu thực tế           | 40 kiểm thử đã đạt ở lần kiểm tra mã gần nhất; hai ảnh chụp mới đã xem kết quả  | Kiểm thử chức năng không thay thế độ chính xác thực tế; chưa có nhãn góc cho ảnh mới                                                 |

### Bằng chứng của lần rà soát

- Đã đọc metadata và mở lại `data/processed/scan/single_20261118_171702_792040/scan.png`: vẫn là `anh_2.jpg`, nhánh `content_fallback`, detector `no_candidate`.
- Ba hash nguồn ghi trong lượt này khớp mã hiện tại; đây là chạy lại cùng ảnh, không tính thành ảnh kiểm thử mới.
- Nhánh dự phòng chọn một vùng với 47 từ hỗ trợ trong 50 từ đáng tin cậy; số từ hỗ trợ không chứng minh giữ đủ chữ hoặc nhận dạng đúng.
- `corners_original = null`, `H_source_to_warp = null`: kết quả này không được ghi là DocAligner tìm đúng góc hay nắn phối cảnh thành công.
- Thống kê 24.889 ảnh trước đây là benchmark detector trên SmartDoc, chưa phải benchmark của toàn luồng vùng chữ mới. Chưa xác minh trùng dữ liệu huấn luyện sẵn.

### Việc cần ưu tiên trước khi chốt phần detect

1. **Chọn đúng trang chính:** bổ sung ca nhiều giấy, chữ trên vật nền, sách và hai vùng lớn cạnh tranh; kiểm tra cả trường hợp detector có bốn góc nhưng chọn sai trang. Không chỉ kích hoạt dự phòng khi thiếu góc rồi coi đã xử lý hết sai khung.
2. **Đo mất nội dung:** gán góc trang trên tập ảnh mới, kiểm tra tiêu đề/chân trang/dấu/công thức. Đánh giá riêng vùng nội dung và mép trang; không bắt crop chữ phải mang ý nghĩa của khung giấy.
3. **Kiểm thử ảnh âm tính:** bàn trống, đồ vật, nền có chữ nhưng không có trang tài liệu; đo nhận nhầm và xây dựng tiêu chí từ chối trước khi gọi là dùng ổn định.
4. **Kiểm tra khả năng tổng quát:** chuẩn bị một tập nhỏ riêng gồm tiếng Việt/Anh, viết tay/in, tối/bóng đổ, mờ và góc nghiêng. Có thể bắt đầu 20–30 ảnh có tài liệu và 10 ảnh âm tính để tìm lỗi; đây là bước khảo sát, chưa đủ để khẳng định chất lượng đại diện.
5. **Chốt cách đánh giá và cấu hình:** thống kê riêng tỷ lệ trả góc, IoU đạt ngưỡng, cắt dự phòng, giữ đủ nội dung và lỗi chọn trang. Quy định thống nhất chế độ kiểm tra mất chữ nếu muốn scan riêng và pipeline luôn cho cùng ảnh ra. Giữ tên lượt/cấu hình riêng và các ca thất bại.

Chưa cần chạy lại 24.889 ảnh chỉ để rà checklist. Ưu tiên tập ảnh mới và ca lỗi trước; chỉ chạy lại toàn bộ khi đã chốt một cải tiến cần so sánh.

## 10. List các công việc cần hoàn thiện ở phần scan

- Loại sạch giấy phụ và nền
  - **Đang làm:** có vùng nội dung chính và tô trắng vùng ngoài giấy ước lượng. Chưa đánh dấu hoàn tất vì giấy phụ tiếp giáp vẫn còn và nhánh dự phòng chưa sửa hết phối cảnh.
- Từ chối những ảnh không tài liệu hoặc tài liệu quá kém chất lượng
  - **Đang làm:** đã nối kiểm tra kích thước, tỷ lệ giấy sáng, nét giống chữ và độ sắc nét trước tăng cường. Đã thử từ chối ảnh trắng, vùng lớp học không có giấy cắt từ ảnh gốc và ảnh làm mờ mạnh. Đây là khảo sát ít mẫu, chưa có tỷ lệ nhận nhầm trên bộ ảnh âm tính độc lập.

### Kết quả nối tăng cường và so sánh ảnh CamScanner

Luồng hiện tại: ảnh → DocAligner → kiểm tra vùng nắn → vùng chữ dự phòng nếu cần → kiểm tra chất lượng đầu ra → bù nền/tăng tương phản → lưu ảnh. Detector và ngưỡng heatmap cũ được giữ nguyên.

- `appearance.py::assess_document()` kiểm tra trên ảnh màu **trước tăng cường**. `rejected_quality` nghĩa không xuất ảnh scan thành công; không dùng độ sắc nét sau sharpen để làm đẹp điểm chấp nhận.
- `appearance.py::enhance_document()` bù độ sáng trong Lab và giảm ám màu trên nền gần trắng, giữ chroma tại nét tối; không nhị phân hóa chữ và không sinh lại nét bị mất.
- Cấu hình: `configs/scan.json`. Kết quả lưu cả `quality`, `enhancement` và cấu hình/hash nguồn trong metadata. Lệnh một ảnh ghi thêm phiên bản OpenCV; chưa ghi đầy đủ phiên bản Tesseract.
- `scan.png` là ảnh đã tăng cường; `scan_color.png` giữ ảnh màu trước tăng cường; `region.png` đánh dấu vùng đã cắt. `--no-enhance` tắt bước làm sáng, `--detect-only` chỉ thử detector như trước.
- Pipeline OCR cũng gọi chung bước mới và ghi thông tin chất lượng/tăng cường; không đổi mô hình đọc chữ. Chưa đo CER/WER sau thay đổi này nên chưa kết luận OCR tốt hơn.

Hai kết quả cuối của lần nối thử:

| Ảnh | Lượt chạy | Kết quả |
| --- | --- | --- |
| `anh_2.jpg` | `single_20261118_231026_318983` | `content_fallback`: nền sáng hơn và phần lớn nền ngoài giấy được tô trắng; còn giấy phụ, ít nền và trang vẫn xiên |
| `anh_viet.jpg` | `single_20261118_231029_591128` | Dùng bốn góc DocAligner, tăng cường sau nắn; vẫn thấy nhiễu/nét mờ từ ảnh gốc |

Xem các ảnh tại `data/processed/scan/<lượt_chạy>/`. Đã mở và kiểm tra hai ảnh cuối; 45 kiểm thử đạt, gồm ca trắng, mờ mạnh, nền tối, giữ hướng màu mực và từ chối trước tăng cường.

**So với ảnh mẫu CamScanner:** đã cải thiện nền sáng và tương phản; chưa đạt cùng mức về độ thẳng trang, độ sạch mép và độ rõ chữ. Ảnh mẫu là ảnh chụp màn hình ứng dụng nên chỉ dùng tham khảo trực quan, không dùng để tính điểm chất lượng hoặc suy ra thuật toán của ứng dụng. Tô trắng nền không đồng nghĩa đã tìm đúng mép trang. Ưu tiên tiếp theo vẫn là tách đúng trang chính, kiểm chứng giữ đủ chữ và mở rộng ảnh âm tính.

## 11. Sửa theo ba yêu cầu từ ảnh mẫu

Yêu cầu là cắt phần ngoài khung, nắn phối cảnh để trang/dòng chữ thẳng hơn và làm mực đậm dễ nhìn; làm sáng nền đơn thuần chưa đủ.

### Nắn thêm ở nhánh dự phòng

- Sau khi chọn vùng chữ chính, `content_scan.py::refine_content_perspective()` tìm contour giấy sáng, lấy convex hull và thử xấp xỉ tứ giác. Không dùng tọa độ viết tay riêng cho hai ảnh thử.
- Chỉ xét khung có diện tích phù hợp và dấu hiệu phối cảnh. Nới khung nhỏ để giữ ít nhất 98% diện tích từng hộp từ có bằng chứng nằm trên giấy và ít nhất 97% mặt nạ nét đủ điều kiện. Đây là kiểm tra tín hiệu ảnh, không phải chứng minh giữ đủ 97%/98% văn bản thật.
- Từ chối nắn thêm nếu không qua các kiểm tra; giữ xoay/cắt cũ. Nếu qua, ghép ma trận và nắn trực tiếp từ ảnh gốc một lần để giảm mờ do nhiều lần nội suy.
- `scanner_status` vẫn là `content_fallback`. Chi tiết tứ giác và ma trận nằm trong `content_detection.perspective_refinement`; `corners_original` của detector vẫn null. `T_source_to_output` có thể là phép phối cảnh dù `H_source_to_warp` của nhánh detector null.
- Nếu khung ước lượng đi ra ngoài ảnh gốc do trang bị cắt sát mép, lưu `outside_source` và cảnh báo đệm trắng. Không tạo lại nội dung nằm ngoài ảnh. Các tọa độ này là ước lượng ở nhánh dự phòng, không được đưa vào điểm detector SmartDoc.

### Làm chữ đậm và giảm nền loang

`appearance.py` tăng tín hiệu mực trước đường cong độ sáng. Mặt nạ adaptive threshold chỉ chọn vùng hỗ trợ nét để làm trắng nền, không biến toàn bộ đầu ra thành ảnh nhị phân. Ảnh trước tăng cường vẫn giữ ở `scan_color.png`. Nét rất nhạt và hình vẽ có thể bị ảnh hưởng; ngưỡng nằm trong `configs/scan.json`, tắt tăng cường bằng `--no-enhance` khi cần.

### Đối chiếu thực tế

- Ảnh `anh_2.jpg`, lượt `single_20261118_233035_505030`: nắn tứ giác dự phòng đã áp dụng; mép trên khung ước lượng trước nắn nghiêng khoảng 10,65°. Khung chữ nhật đầu ra thẳng hơn, các mảng bàn lớn đã bị cắt, chữ đậm và nền trắng hơn.
- Xem [mốc so sánh đã lưu riêng](../../artifacts/history/scan_report_20261118/comparison.jpg): bên trái là bản cũ, bên phải là bản nắn/tăng cường mới. Không dùng ảnh màn hình CamScanner để tính điểm so sánh số.
- `anh_viet.jpg`, lượt `single_20261118_233038_157463`: vẫn dùng khung DocAligner, áp dụng tăng cường mới sau nắn.
- 48 kiểm thử đạt ở lần kiểm tra này, gồm trường hợp nắn giảm độ dốc dòng trên ảnh phối cảnh tổng hợp, bỏ qua trang đã gần chữ nhật, và giữ nét mảnh/dấu chấm thử nghiệm. Chưa có nhãn kiểm tra mất chữ trên hai ảnh chụp.
- Còn dải giấy phụ bên trái, ít viền tối, nét chữ chưa sắc như ảnh mẫu và phần chữ bị cắt ngoài ảnh gốc không phục hồi được. Chưa có cơ chế tổng quát tự xoay trang ngược 180° theo nghĩa đọc. Hai mục người dùng thêm ở mục 10 vẫn chưa đánh dấu hoàn tất.

## 12. Dọn kết quả lặp và cách chạy hiện tại

### Cập nhật crop dự phòng 22/11/2026

- `anh_thu.png` từng bị mất mục **3. Evaluation Metrics** vì phần đầu và phần cuối được chia thành hai cụm, chỉ cụm lớn nhất được giữ.
- `content_scan.py` vẫn chọn cụm chính lớn nhất trước, sau đó thử nối các đoạn gần theo chiều dọc: chồng lấn ngang ít nhất nửa chiều rộng cụm nhỏ hơn, khoảng cách tối đa bốn chiều cao hộp từ trung vị, nền sáng hỗ trợ ít nhất 95% vùng đoạn và 98% khoảng nối. Đây là heuristic, không phải xác suất cùng trang.
- Ngưỡng sáng lấy từ cụm chính để viền trắng sinh ra khi xoay ảnh không lấn át phần giấy trong bóng. Không gom toàn bộ hộp từ; hai cụm cách nhau bằng nền tối hoặc ở hai bên vẫn được tách.
- Metadata `content_detection.region_selection.joined_blocks` ghi các khối đã giữ. `source = same_paper_text_blocks` nghĩa là đã nối thêm đoạn; đây vẫn là fallback, không phải góc DocAligner.
- Pipeline đã chạy lại và giữ được tiêu đề mục 3 cùng cả hai dòng nội dung cuối. OCR đọc được phần này nhưng còn nhiễu và lỗi nhận dạng; không có TXT chuẩn cho ảnh nên chưa công bố CER/WER. Không coi đây là đã sửa hết lỗi giữ nội dung trên FUNSD hoặc ảnh mới.

Nguyên nhân lặp là CLI cũ luôn tạo `single_<thời_gian>` cho mỗi lần chạy. Theo yêu cầu người dùng, CLI một ảnh đã đổi sang cập nhật một thư mục cố định theo đường dẫn ảnh.

```powershell
python -X utf8 src/document_scanner/scanner/scan_image.py --image "data/raw/thu_detect/anh_2.jpg"
```

- Ảnh hiện tại: `data/processed/scan/image_anh_2_b016f626/scan.png`.
- Ảnh trước tăng cường: cùng thư mục, `scan_color.png`; vùng cắt: `region.png`.
- Metadata: `artifacts/scans/image_anh_2_b016f626/metadata.json`.
- `anh_viet.jpg` dùng thư mục `image_anh_viet_22947531`.
- Chạy lại không tạo bản lặp. Khi đổi chế độ hoặc lần mới bị từ chối, các ảnh đầu ra cũ do CLI quản lý được bỏ để tránh hiểu nhầm là kết quả mới. File ghi chú riêng vẫn được giữ.
- Muốn giữ một lượt riêng có chủ đích, thêm `--new-run`. Quy tắc này chỉ dành cho scan một ảnh, không ghi đè các benchmark theo lô.

Đã dọn 39 thư mục cũ chứa 74 file sinh ra từ hai ảnh trên, khoảng 47,57 MiB; không xóa ảnh gốc, mô hình, hai benchmark SmartDoc hay kết quả batch mốc. Các mã `single_...` ở các mục trước là nhật ký lịch sử, thư mục ảnh trung gian tương ứng đã được dọn. Mốc trước/sau, ảnh so sánh và metadata gốc được giữ trong `artifacts/history/scan_report_20261118/`.

51 kiểm thử đạt. Đã chạy cùng ảnh thật hai lần liên tiếp và xác nhận chỉ một thư mục; kiểm thử còn kiểm tra không xóa ghi chú riêng, không nhầm hai ảnh trùng tên ở hai đường dẫn, và không để ảnh thành công cũ xuất hiện sau lần chạy thất bại.

**Chỉnh nhẹ độ rõ chữ:** tăng `sharpen_amount` từ 0,20 lên 0,45, dùng `sharpen_sigma = 0,7` trong `configs/scan.json` để làm rõ mép nét bằng bán kính nhỏ. Đã xem vùng chữ phóng to trước/sau và chạy lại hai ảnh vào thư mục hiện tại, không tạo lượt lặp. 11 kiểm thử liên quan chất lượng, tăng cường và lưu đầu ra đạt; không coi sharpen là phục hồi chi tiết đã mất của ảnh gốc.
