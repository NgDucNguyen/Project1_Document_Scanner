> H? s? l?ch s? tr??c khi g?p c?u tr?c. D?ng README g?c v? b?o c?o hi?n t?i ?? ch?y ch??ng tr?nh; c?c l?nh v? ???ng d?n k?t qu? c? c? th? ?? chuy?n v?o `artifacts/history/`.

# Kế hoạch 7 ngày cải thiện scanner

Mục tiêu: cải thiện khả năng chọn đúng vùng tài liệu, giữ đủ nội dung và chuẩn bị kết quả so sánh cho lần báo cáo tiếp theo.

| Ngày | Công việc chính |
| ----- | --------------------------------------------------------------------------- |
| **1** | Chốt tập phát triển, lưu cấu hình và kết quả hiện tại làm mốc so sánh. |
| **2** | Phân tích ứng viên và nguyên nhân thất bại của Canny/Otsu/contour. |
| **3** | Cải thiện chọn khung, giữ mép ngoài và cơ chế từ chối khung không đáng tin. |
| **4** | Thử DBNet cho vùng chữ dự phòng; xử lý gom vùng và góc nghiêng. |
| **5** | Kiểm thử trên tài liệu mới, tiếng Việt và ảnh không có giấy. |
| **6** | Tổng hợp số liệu, xem các trường hợp còn lỗi, chốt phương án dùng tiếp. |
| **7** | Viết báo cáo, chuẩn bị ảnh trước/sau và demo một ảnh đi qua pipeline. |

**Tiến độ hiện tại:** đã hoàn thành ngày 1–4. Scanner đã được cải tiến ở ngày 3; ngày 4 thử DBNet và quyết định giữ cách cắt dự phòng hiện tại làm mặc định vì giữ chữ tốt hơn trong phép thử. Bước tiếp theo là ngày 5, kiểm thử thực tế/tiếng Việt/ảnh không có giấy.

## Ngày 1 — Đã hoàn thành ngày 17/11/2026

### 1. Chốt tập phát triển

- Danh sách cố định: [scanner_dev_manifest.csv](../results/scanner_dev_manifest.csv).
- Gồm **200 ảnh validation SmartDoc**, 40 ảnh cho mỗi nền trong 5 nền.
- Có 4 tài liệu: `letter001`, `patent002`, `patent003`, `tax002`.
- Mỗi cặp tài liệu/nền lấy 10 khung hình trải đều theo thứ tự thời gian, gồm đầu và cuối chuỗi. Không dùng kết quả IoU để chọn ảnh.
- Mỗi ảnh có SHA-256 để phát hiện ảnh nguồn bị thay đổi. Các lần so sánh dùng lại danh sách này, không chọn lại ảnh theo kết quả.
- Không lấy ảnh train hoặc test. Đây là tập phát triển trích từ validation đã từng sử dụng, **không phải tập kiểm tra độc lập mới**. Các khung hình cùng tài liệu vẫn có tương quan.
- Cân bằng số ảnh giữa các nền để nhìn rõ nền khó; không dùng tỷ lệ trên tập này thay cho kết quả toàn validation.

### 2. Đã lưu mốc scanner hiện tại

Thư mục: `artifacts/scanner_dev/baseline/`.

| Thành phần | Vai trò |
| --- | --- |
| `manifest.csv` | Bản sao danh sách ảnh đã dùng cho lần chạy này. |
| `source/` | Bản sao mã nguồn, cấu hình và requirements trước khi cải tiến. |
| `run_info.json` | Trạng thái hoàn thành, phiên bản thư viện, hash mã nguồn/cấu hình, danh sách ảnh và các mô hình OCR hiện có. |
| `results.csv` | Kết quả từng ảnh: góc dự đoán, IoU, trạng thái, điểm ứng viên, số ứng viên, cảnh báo và thời gian. |
| `summary.json` | Chỉ số tổng hợp và theo từng nền. |
| `examples.jpg` | Một ảnh tổng hợp 11 trường hợp minh họa. Xanh lá là nhãn thật; đỏ là dự đoán. |
| `examples.csv` | Đường dẫn ảnh gốc và ảnh scan tương ứng với số thứ tự trên ảnh tổng hợp. |

Ảnh scan minh họa được lưu trong `data/processed/scanner_dev/baseline/`. Chỉ lưu 7 ảnh scan trong các ví dụ có dự đoán; không tạo thêm 200 ảnh scan thường trực. Tất cả 200 ảnh đều đã được chạy phát hiện và thử nắn nếu có góc.

**Phạm vi đo:** tìm bốn góc bằng Canny/Otsu/contour và nắn phối cảnh bằng `build_scan`. Chưa đo cơ chế cắt vùng chữ dự phòng hoặc OCR trong pipeline. Mã nguồn các phần đó được lưu cùng mốc; hash mô hình được ghi lại, không sao chép thêm mô hình nặng. Khi thử DBNet ở ngày 4 cần có phép so sánh riêng cho vùng nội dung.

### 3. Kết quả làm mốc

| Chỉ số | Kết quả |
| --- | ---: |
| Tổng số ảnh | 200 |
| Tìm được khung và nắn được ảnh | 117/200 (58,5%) |
| Không tìm được khung | 83/200 (41,5%) |
| Có khung nhưng IoU < 0,9 | 19/200 (9,5%) |
| Đạt IoU ≥ 0,9 và nắn thành công | **98/200 (49%)** |
| IoU trung bình, tính ảnh không tìm thấy là 0 | **0,5446** |
| Lỗi nắn phối cảnh khi đã có khung | 0 |
| Thời gian phát hiện trung bình | 31,90 ms/ảnh |
| Thời gian phát hiện + nắn trung bình | 33,78 ms/ảnh |

Thời gian đo với OpenCV dùng 1 luồng; không gồm đọc/ghi ảnh, OCR hoặc cắt dự phòng. Thời gian có thể dao động theo tải máy.

| Nền | Số ảnh | Không tìm thấy | Có khung nhưng chưa đạt | Đạt IoU ≥ 0,9 |
| --- | ---: | ---: | ---: | ---: |
| `background01` | 40 | 9 | 7 | 24 (60%) |
| `background02` | 40 | 5 | 1 | 34 (85%) |
| `background03` | 40 | 0 | 0 | 40 (100%) |
| `background04` | 40 | 30 | 10 | 0 (0%) |
| `background05` | 40 | 39 | 1 | 0 (0%) |

`corner_error_normalized` trong CSV là sai số trung bình của bốn góc chia đường chéo ảnh, ghép góc theo chu trình tốt nhất. Chỉ số trung bình này chỉ tính ảnh có dự đoán; phải đọc kèm tỷ lệ không tìm thấy. IoU đo vùng trang, không đánh giá chất lượng nét chữ hay thứ tự đọc OCR.

Không so trực tiếp **49% của 200 ảnh cân bằng theo nền** với **60,49% của 3.192 ảnh validation trước đây**, vì tỷ trọng ảnh từng nền khác nhau. Điểm IoU từng ảnh trong 200 ảnh đã được đối chiếu và khớp lần chạy lịch sử trong sai số 0,000001.

### 4. Cách xem và chạy các lần tiếp theo

1. Mở `artifacts/scanner_dev/baseline/examples.jpg` để quan sát khung trang.
2. Xem `examples.csv` để biết ảnh gốc và ảnh scan tương ứng.
3. Mở `data/processed/scanner_dev/baseline/` để xem ảnh sau nắn. Có ảnh sai được giữ lại làm bằng chứng lỗi; không phải mọi ảnh được lưu đều đạt.
4. Dùng `results.csv` để tra trạng thái và điểm của bất kỳ ảnh nào trong tập phát triển.

Sau khi sửa scanner, kích hoạt venv và chạy từ thư mục gốc dự án:

```powershell
python -X utf8 src/document_scanner/scanner/benchmark.py --run-name candidate_v1
```

Chương trình dùng lại manifest cố định và lưu một thư mục mới `artifacts/scanner_dev/candidate_v1/`. Đổi tên cho mỗi phương án; chương trình từ chối ghi đè lần chạy đã tồn tại. Giữ nguyên `baseline` để đối chiếu. Kiểm tra `complete: true` trong `run_info.json` trước khi sử dụng kết quả.

Danh sách 200 ảnh, mã benchmark và tài liệu có thể đưa lên GitHub. Ảnh nguồn, ảnh kết quả và snapshot trong `artifacts` chỉ giữ trên máy theo `.gitignore` hiện tại.

### 5. Kiểm tra đã thực hiện và việc ngày 2

- Xác nhận đủ 200 ảnh, không trùng, chỉ thuộc validation, mỗi cặp tài liệu/nền có 10 ảnh.
- Kiểm tra hash ảnh nguồn và đối chiếu IoU với kết quả lịch sử.
- Mở ảnh tổng hợp để kiểm tra hiển thị nhãn/dự đoán và ca chọn nhầm sách.
- Chạy lại 29 kiểm thử hiện có: tất cả đạt.
- **Ngày 2:** bắt đầu với 83 ca không tìm thấy và 19 ca có khung nhưng chưa đạt. Bổ sung thông tin ứng viên bị loại tại bước nào và vì sao; sau đó mới quyết định sửa bộ lọc hay cách chấm điểm. Chưa thay thuật toán phát hiện trong ngày 1.

## Ngày 2 — Đã hoàn thành phân tích lỗi ngày 17/11/2026

### 1. Đã bổ sung gì vào mã nguồn?

- `src/document_scanner/scanner/detect.py`: thêm tham số `diagnostics=True` cho `detect_document`. Chế độ này ghi lại đường bao lồi, tứ giác, thứ hạng contour, epsilon, điểm số và lý do bị loại. Khi chạy bình thường vẫn gọi `detect_document(image)` như trước.
- `score_candidate`: ghi thêm tỷ lệ diện tích, cạnh ngắn nhất, độ bám cạnh Canny, độ khớp contour và lý do loại đầu tiên. Công thức điểm và ngưỡng không thay đổi.
- `src/document_scanner/scanner/audit.py`: chạy phân tích ngoại tuyến trên 200 ảnh đã chốt, đối chiếu ứng viên với nhãn thật và tự kiểm tra dự đoán vẫn khớp ngày 1.
- **Nhãn chỉ dùng trong công cụ phân tích.** Scanner không nhận nhãn và không dùng IoU để chọn khung khi xử lý ảnh thực tế.

### 2. Kết quả phân loại

| Nhóm | Điều kiện dùng để phân tích | Số ảnh |
| --- | --- | ---: |
| `passed` | Khung được chọn đạt IoU ≥ 0,9 | 98 |
| `imprecise_proposals` | Chưa đạt; tứ giác gần nhãn nhất trong các tứ giác đã sinh có 0,5 ≤ IoU < 0,9 | 24 |
| `no_close_proposal` | Chưa đạt; không có tứ giác được xét nào đạt IoU ≥ 0,5 | 78 |
| `ranking_failure` | Có tứ giác được chấp nhận đạt IoU ≥ 0,9 nhưng không được chọn | 0 |
| `close_quad_rejected` | Có tứ giác đã sinh đạt IoU ≥ 0,9 nhưng bị lọc loại | 0 |

Các ngưỡng 0,5 và 0,9 dùng để chia nhóm chẩn đoán; không phải tiêu chí mới cho scanner. Nhóm 78 ảnh bao gồm cả trường hợp không sinh được tứ giác lẫn sinh ra khung nhưng ở sai vị trí.

| Nền | Đạt | Có ứng viên tương đối gần nhưng chưa đủ chính xác | Không có ứng viên gần (IoU ≥ 0,5) |
| --- | ---: | ---: | ---: |
| `background01` | 24 | 13 | 3 |
| `background02` | 34 | 1 | 5 |
| `background03` | 40 | 0 | 0 |
| `background04` | 0 | 10 | 30 |
| `background05` | 0 | 0 | 40 |

Đã kiểm tra thêm convex hull của các contour có diện tích ít nhất 5% ảnh, kể cả contour nằm ngoài top 20. Trong 102 ảnh chưa đạt, không hull nào đạt IoU ≥ 0,9; hull tốt nhất trong nhóm này chỉ đạt khoảng **0,7926**. Không có contour đủ diện tích nằm ngoài top 20 trong tập này. Tỷ lệ diện tích nhãn nhỏ nhất khoảng 5,76%, không ảnh nào có nhãn nhỏ hơn ngưỡng diện tích 5%.

**Kết luận trong phạm vi tập phát triển này:** chỉ đổi cách chấm điểm để chọn trong các tứ giác hiện có sẽ không tạo thêm ảnh đạt ngưỡng 0,9. Cần cải thiện cách tạo đường bao/khung ứng viên. Chưa có bằng chứng để nói chỉ cần nới bộ lọc hoặc tăng top 20 là sẽ giải quyết được lỗi.

### 3. Quan sát trên ảnh trung gian

Đã mở và kiểm tra `artifacts/scanner_dev/day2_audit/diagnostics.jpg`:

- Một số ảnh nền 1: cạnh giấy trong ảnh Canny bị đứt; Otsu nối giấy với vùng nền sáng bên dưới, khiến khung bị kéo rộng hoặc không xấp xỉ thành bốn góc phù hợp.
- Ví dụ nền 2: có khung bám vào phần chữ bên trong thay vì mép giấy; một số ảnh Otsu lấy vùng bàn sáng rộng hơn trang.
- Ví dụ nền 4: Otsu khó tách giấy khỏi bàn gần màu; Canny chủ yếu giữ các nét chữ, đường bao ngoài chưa đủ tốt.
- Ví dụ nền 5: xuất hiện nhiều cạnh từ sách, dây, cốc và vật che. Khung của vật thể khác có thể cạnh tranh với trang giấy. Ảnh chọn nhầm sách vẫn xem được trong ảnh tổng hợp ngày 1.

Đây là quan sát trên các ví dụ minh họa, không phải nhãn nguyên nhân thủ công cho toàn bộ 102 ca lỗi. Phân tích hull/tứ giác chưa chứng minh riêng Canny hay Otsu là nguyên nhân duy nhất; lỗi có thể đến từ ngưỡng hóa, closing, contour bị nối/đứt và cách lấy convex hull.

### 4. Lý do loại và cách đọc đúng

| Lý do đầu tiên | Số lần thử tứ giác bị loại |
| --- | ---: |
| `image_boundary`: có góc quá sát biên ảnh | 500 |
| `polygon_area`: tỷ lệ diện tích ngoài khoảng cho phép | 11 |
| `weak_edge_support`: độ bám cạnh Canny quá thấp | 7 |

Có 1.070 lần thử tứ giác được chấp nhận. Đây là **số lần thử**, không phải số ảnh hoặc số khung duy nhất: cùng một contour có thể sinh cùng khung ở nhiều epsilon và hai nhánh có thể trùng nhau. Không được kết luận “500 ảnh bị loại do sát biên”. Không tứ giác bị loại nào đạt IoU ≥ 0,9 trên tập này.

### 5. Mở kết quả ở đâu?

Tất cả kết quả chi tiết đặt trong **một thư mục** `artifacts/scanner_dev/day2_audit/`:

| File | Công dụng |
| --- | --- |
| `diagnostics.jpg` | 7 ca minh họa, mỗi hàng có ảnh với khung, Canny, Otsu và ứng viên gần nhãn nhất. Xanh lá: nhãn; đỏ: khung được chọn; vàng: ứng viên gần nhãn nhất, chỉ xác định khi phân tích ngoại tuyến. |
| `images.csv` | 200 dòng: phân loại lỗi, IoU khung chọn, IoU ứng viên tốt nhất theo nhãn và IoU hull tốt nhất. |
| `candidates.csv` | Toàn bộ lần thử tứ giác, tọa độ trên ảnh gốc, điểm, thành phần điểm và lý do loại. |
| `summary.json` | Tổng hợp số liệu cho báo cáo. |
| `examples.csv` | Danh sách ảnh gốc tương ứng với các hàng minh họa. |
| `source/`, `run_info.json` | Mã/cấu hình đã chạy, hash và xác nhận hoàn thành. |

Không tạo thêm ảnh scan/OCR trong ngày 2. Mốc ngày 1 vẫn giữ nguyên. Công cụ từ chối ghi đè kết quả chẩn đoán đã có. Lệnh đã sử dụng:

```powershell
python -X utf8 src/document_scanner/scanner/audit.py
```

### 6. Kiểm chứng và hướng ngày 3

- Cả 200 ảnh đã được so sánh giữa chạy bình thường và bật chẩn đoán: trạng thái, phương pháp, điểm, số ứng viên, cảnh báo và tọa độ không đổi.
- Tọa độ, trạng thái và IoU vẫn khớp baseline ngày 1. Kết quả vẫn là 98/200 ảnh đạt, không phải đã cải thiện độ chính xác.
- 29 kiểm thử hiện có đã chạy đạt sau khi thêm cơ chế ghi lý do loại; lần phân tích cuối cũng kiểm tra bất biến trên toàn bộ 200 ảnh.
- Ngày 3 cần ưu tiên **tạo thêm ứng viên bám mép trang** để xử lý cạnh đứt và giấy dính nền; sau đó mới so sánh cách chấm điểm và từ chối vật thể khác. Giữ các nhánh hiện tại làm đối chứng, chạy lại cùng 200 ảnh và kiểm tra cả ảnh trước đây đã đúng.
- DBNet ở ngày 4 phục vụ vùng chữ dự phòng; nó không trực tiếp giải quyết việc tìm mép giấy. Nếu cách cổ điển vẫn thiếu ứng viên tốt trên nền khó, tiếp tục thử phân vùng trang theo hướng đã đề xuất.

## Ngày 3 — Đã cải tiến scanner và kiểm chứng ngày 17/11/2026

### 1. Thay đổi đã áp dụng vào scanner

Các thay đổi nằm trực tiếp trong `src/document_scanner/scanner/detect.py` và bật bằng `configs/scanner.json`, phiên bản `scanner_day3_v2`.

1. Giữ hai nhánh Canny/Otsu cũ.
2. Thêm Canny trên ảnh xám với ngưỡng thấp 5/20, làm mượt Gaussian 3×3 và closing như cấu hình hiện tại để tìm thêm cạnh giấy nhạt.
3. Thêm Canny trên kênh **b của Lab**. Kênh này thể hiện khác biệt màu xanh dương–vàng, có thể giúp phân biệt giấy và nền dù độ sáng gần nhau. Đây là cách xử lý màu bằng OpenCV, không phải mô hình học máy.
4. Các contour mới tiếp tục qua convex hull, xấp xỉ tứ giác và công thức chấm điểm chung. Mỗi cạnh của ứng viên từ hai nhánh mới phải có ít nhất 35% vị trí lấy mẫu nằm gần cạnh Canny của chính nhánh đó. Điều này giảm việc một cạnh mạnh bù cho các cạnh yếu.
5. Nếu điểm cao nhất nhỏ hơn **5,0**, trả `low_confidence`, không trả góc để nắn. Nếu điểm từ **5,0 đến dưới 5,75**, vẫn trả góc nhưng thêm cảnh báo `weak_candidate`, trạng thái `uncertain`.

Ngưỡng điểm là quy tắc được lựa chọn trong quá trình phát triển trên 200 ảnh; **không phải xác suất tin cậy**. Các điểm số của nhánh mới sử dụng độ bám cạnh trên kênh tương ứng, nên cần đánh giá thực nghiệm khi so chung với nhánh cũ.

Không có quy tắc “luôn chọn khung lớn nhất”, vì nó có thể chọn mặt bàn hoặc vật thể khác. Việc giữ mép ngoài được cải thiện bằng cách tạo thêm ứng viên có bằng chứng cạnh trang, rồi chấm điểm chung. Vẫn còn trường hợp chọn khung bên trong.

### 2. Thử nghiệm đã thực hiện

- Bản thử nhiều kênh xét thêm ảnh tăng tương phản CLAHE và kênh a của Lab, đạt 128/200 ảnh nhưng xuất ra 22 khung chưa đạt.
- Trên tập phát triển, nhánh CLAHE chọn 7 khung và cả 7 chưa đạt; kênh a không được chọn. Bản chốt bỏ hai nhánh này và thêm ngưỡng từ chối/cảnh báo.
- Bản chốt vẫn đạt 128/200 ảnh nhưng chỉ xuất ra 5 khung chưa đạt. Đây là quyết định dựa trên tập phát triển, không khẳng định CLAHE hoặc kênh a luôn vô ích với các ảnh khác.
- Sau khi chốt, chạy thêm **2.992 ảnh validation không nằm trong 200 ảnh phát triển**. Không chỉnh thêm ngưỡng dựa trên lượt kiểm chứng này.

### 3. Kết quả so sánh

| Tập ảnh | Bản cũ đạt IoU ≥ 0,9 | Bản mới đạt IoU ≥ 0,9 | Thêm ảnh đạt | Ảnh cũ đạt nhưng bản mới không đạt |
| --- | ---: | ---: | ---: | ---: |
| 200 ảnh phát triển | 98/200 (49%) | **128/200 (64%)** | 30 | 0 |
| 2.992 ảnh validation còn lại | 1.833/2.992 (61,26%) | **2.296/2.992 (76,74%)** | 463 | 0 |
| Toàn bộ 3.192 ảnh validation | 1.931/3.192 (60,49%) | **2.424/3.192 (75,94%)** | **493** | **0** |

“Không mất ảnh đạt” nghĩa là không ảnh nào trước đây đạt ngưỡng 0,9 bị tụt dưới ngưỡng này; không có nghĩa tọa độ hay IoU từng ảnh đều giữ nguyên hoặc tăng.

| Nền, trên toàn validation | Số ảnh | Bản cũ đạt | Bản mới đạt |
| --- | ---: | ---: | ---: |
| `background01` | 797 | 503 (63,11%) | **782 (98,12%)** |
| `background02` | 780 | 698 (89,49%) | **747 (95,77%)** |
| `background03` | 751 | 730 (97,20%) | **746 (99,33%)** |
| `background04` | 515 | 0 | **149 (28,93%)** |
| `background05` | 349 | 0 | **0** |

- IoU trung bình toàn validation, tính ảnh không có góc đầu ra là 0: **0,6521 → 0,7503**.
- Bản mới có 2.489 ảnh nắn thành công, gồm 2.424 ảnh đạt và 65 ảnh có khung nhưng chưa đạt IoU 0,9.
- Có 703 ảnh không xuất khung trang: 584 ảnh `no_candidate`, 119 ảnh `low_confidence`. Không được gộp tất cả thành “không sinh được ứng viên”.
- Không có lỗi nắn phối cảnh khi đã trả được góc trong lượt kiểm chứng.
- Trên 200 ảnh, cùng cấu hình một luồng OpenCV và một worker: thời gian phát hiện trung bình khoảng **31,90 → 58,36 ms/ảnh**; phát hiện + nắn khoảng **33,78 → 60,80 ms/ảnh**. Không gồm OCR và đọc/ghi ảnh. Lượt 2.992 ảnh dùng 4 worker nên không dùng thời gian từng ảnh của lượt đó để so trực tiếp với lượt một worker.

**Phạm vi:** đã chạy 3.192 ảnh validation, chưa chạy lại toàn bộ 24.889 ảnh. 2.992 ảnh bổ sung không trùng ảnh phát triển nhưng vẫn cùng 4 tài liệu validation và đã từng được đánh giá trong giai đoạn trước; đây không phải tập kiểm tra độc lập hoặc đánh giá trên tài liệu mới. Chưa chấm tập test. Chỉ số trên là khung trang + nắn, không gồm vùng chữ dự phòng và OCR.

### 4. Xem kết quả mới ở đâu?

| Đường dẫn | Nội dung |
| --- | --- |
| `artifacts/scanner_dev/day3_final/before_after.jpg` | So sánh trước/sau: 3 ví dụ cải thiện, 1 ca bị từ chối và 1 ca vẫn chọn nhầm sách. Xanh lá là nhãn, đỏ là dự đoán. |
| `artifacts/scanner_dev/day3_final/before_after_index.csv` | Đường dẫn ảnh gốc, IoU và trạng thái của các ví dụ trước/sau. |
| `artifacts/scanner_dev/day3_final/examples.jpg` | Tổng hợp ví dụ của bản scanner mới trên 200 ảnh. |
| `data/processed/scanner_dev/day3_final/` | Ảnh scan minh họa của bản mới; xem `examples.csv` để tra nguồn. |
| `artifacts/scanner_dev/day3_final/comparison.csv` | So sánh từng ảnh trên toàn bộ 3.192 ảnh validation. |
| `artifacts/scanner_dev/day3_validation_check/` | Kết quả, nguồn và cấu hình của lượt kiểm chứng 2.992 ảnh bổ sung. |
| `docs/results/scanner_day3_metrics.csv` | Bảng tổng hợp nhỏ để đưa lên GitHub và dùng làm báo cáo. |

Mốc ngày 1 và chẩn đoán ngày 2 được giữ nguyên. `day3_multichannel` là lượt thử nhiều kênh; `day3_final` là bản chốt. Chỉ lưu ảnh scan minh họa, không giữ hàng nghìn ảnh scan mới. Các số liệu từng ảnh vẫn được lưu đủ.

### 5. Cách sử dụng và kiểm chứng

Pipeline một ảnh và batch scanner đều gọi `detect_document`, nên tự dùng bản scanner mới. Không cần tạo một pipeline riêng. Với `input-type scan`, chương trình vẫn bỏ qua phát hiện khung như trước.

Ví dụ chạy ảnh chụp qua scanner rồi OCR, khi venv đã kích hoạt:

```powershell
python -X utf8 src/document_scanner/pipeline.py --input-type photo --image "data/raw/thu_ocr/anh.jpg"
```

Nếu scanner trả `low_confidence`, pipeline một ảnh sẽ thử vùng chữ dự phòng hiện có. Batch `scanner/scan.py` không gọi vùng chữ dự phòng; ảnh bị từ chối không được nắn trong batch. Ngày 3 chưa thay mô hình hoặc phương pháp OCR.

Lệnh benchmark đã sử dụng, không chạy lại cùng tên vì chương trình bảo vệ kết quả cũ:

```powershell
python -X utf8 src/document_scanner/scanner/benchmark.py --run-name day3_final
python -X utf8 src/document_scanner/scanner/benchmark.py --run-name day3_validation_check --remaining-validation --workers 4
```

Đã thêm 2 kiểm thử về từ chối ứng viên yếu và cảnh báo kiểm tra, đồng thời kiểm tra bật chẩn đoán không thay đổi lựa chọn trên ảnh thử. Tổng cộng **31 kiểm thử đạt**. Bảng so sánh kiểm tra không trùng ảnh, chỉ validation và khớp đủ 3.192 ảnh với kết quả lịch sử.

### 6. Những việc vẫn chưa giải quyết

- Nền 5 vẫn 0/349 ảnh đạt: vật che và vật thể cạnh tranh còn khó. Ví dụ chọn nhầm sách vẫn sai, hiện được gắn `uncertain`; cảnh báo không đồng nghĩa đã sửa được khung.
- Nền 4 cải thiện nhưng còn 366/515 ảnh chưa đạt.
- Ngưỡng điểm không nhận biết được ngữ nghĩa “tờ giấy cần scan” và không bảo đảm từ chối mọi ảnh không có giấy. Cần kiểm thử ảnh âm tính ở ngày 5.
- Chưa chứng minh giữ đủ dấu tiếng Việt, chất lượng chữ hay OCR tốt hơn sau thay đổi này.
- Bước kế tiếp, ngày 4: cải thiện tìm và gom vùng chữ dự phòng bằng DBNet đã huấn luyện sẵn, đánh giá riêng với khung trang. Không xem vùng chữ là nhãn mép giấy.

## Ngày 4 — Đã thử DBNet, so sánh và chốt mặc định ngày 17/11/2026

### 1. Đã thực hiện

- Tải mô hình `DB_TD500_resnet18.onnx` theo [tài liệu chính thức OpenCV](https://docs.opencv.org/4.6.0/d4/d43/tutorial_dnn_text_spotting.html), kiểm tra SHA-1 khớp `8a3700bdc13e00336a815fc7afff5dcc1ce08546`. Mô hình nặng khoảng 48,77 MB, nằm ở `models/dbnet/`, được bỏ qua khi đưa lên GitHub.
- Thêm `src/document_scanner/scanner/text_regions.py`: chạy DBNet bằng OpenCV DNN trên CPU, không thêm thư viện Python; nhận đa giác vùng chữ và điểm phát hiện.
- Thử gom các hộp chữ gần nhau thành cụm chính, giữ thêm các cụm lân cận để hạn chế bỏ tiêu đề/cột chữ; báo mơ hồ khi có cụm lớn ở xa.
- Ước lượng góc nghiêng từ cạnh dài của vùng chữ. Chỉ xoay khi ít nhất ba vùng chữ đồng thuận về hướng; không dùng đường nền để quyết định góc trong nhánh DBNet.
- Xoay trên nền trắng mở rộng, cắt với lề và lưu ma trận biến đổi. Đây là vùng nội dung, không phải bốn góc giấy và không thay phép nắn phối cảnh trang.
- Thêm phương án `dbnet` trong `crop_content` và cờ `--content-method` của pipeline. Mặc định vẫn là `tesseract`.
- Thêm `benchmark_content.py` để đo hai cách trên cùng danh sách ảnh, lưu hash ảnh, mã nguồn, ma trận và kết quả. Sau phép thử bổ sung cảnh báo khi nhánh DBNet loại vùng chữ khỏi khung, để người dùng kiểm tra tiêu đề/chân trang.

DBNet ở đây chỉ tìm vị trí chữ; Tesseract/FUNSD vẫn là mô hình đọc chữ tiếng Anh cuối cùng. Không huấn luyện hoặc tinh chỉnh DBNet trong ngày 4. Mô hình TD500 được tài liệu OpenCV giới thiệu cho chữ tiếng Anh/Trung; chưa có bằng chứng hoạt động tốt với tiếng Việt trong dự án này.

### 2. Tập thử và cách đánh giá

Tổng cộng **54 ảnh**, mỗi cách chạy đủ cùng danh sách và hash ảnh:

| Nhóm | Số ảnh | Dùng để kiểm tra |
| --- | ---: | --- |
| FUNSD validation đã có | 30 | Đo giữ lại 4.616 hộp từ có nhãn. |
| RDTAG development đã tải | 20 | Quan sát khả năng tạo crop, góc và trường hợp khó; không có nhãn vùng nội dung để chấm crop chính xác. |
| Ảnh cá nhân `anh.jpg`, `anh_test_02.jpg`, `anh_thu.png`, `anh_tu_chup.jpg` | 4 | Xem crop; hai ảnh đầu có TXT để đo CER/WER. |

Đây là phép thử **chạy trực tiếp nhánh cắt vùng chữ trên ảnh gốc**, không chạy bước chọn khung giấy trước. Vì vậy không so trực tiếp CER dưới đây với CER của ảnh đã qua nắn phối cảnh trong pipeline trước đó.

Với FUNSD, một hộp từ được tính là giữ đủ khi ít nhất **98% diện tích hộp nhãn** nằm trong crop sau biến đổi. Ảnh không tạo được crop được tính giữ 0 hộp từ; không bỏ ảnh đó khỏi mẫu số. Chỉ số này đo giữ hộp nhãn, không chứng minh mọi nét chữ/dấu đều sắc nét hoặc OCR đọc đúng. Không dùng IoU mép giấy để chấm vùng chữ.

Các ảnh đều là dữ liệu phát triển hoặc mẫu đã dùng trước đây, không phải kiểm thử độc lập. Chưa đánh giá giữ dấu tiếng Việt; chưa có nhãn vùng nền để tính tỷ lệ lấy thừa nền thực sự. Diện tích crop nhỏ hơn chỉ là quan sát, không phải bằng chứng chất lượng tốt hơn.

### 3. Kết quả thực tế

| Chỉ số | Cách hiện tại: Tesseract | Bản thử DBNet + gom cụm |
| --- | ---: | ---: |
| FUNSD tạo được crop | 30/30 | 29/30 |
| Hộp từ giữ đủ theo tiêu chí 98% diện tích | **4.595/4.616 (99,55%)** | 4.092/4.616 (88,65%) |
| RDTAG tạo được crop | 20/20 | 4/20 |
| Ảnh cá nhân tạo được crop | 4/4 | 4/4 |
| Tổng ảnh tạo được crop | 54/54 | 37/54 |
| Thời gian cắt trung bình trên 54 ảnh, không gồm OCR cuối | Khoảng 4,35 giây | Khoảng 1,64 giây |

Số crop tạo được không đồng nghĩa crop đúng. Đặc biệt, không được suy ra Tesseract cắt đúng 20/20 RDTAG; nhóm này chưa có nhãn khung nội dung và có thể lấy thừa nền. Thời gian trên là của lượt thử trên máy hiện tại, có cả lần nạp mô hình đầu tiên; hai lượt có giai đoạn chạy đồng thời nên chỉ tham khảo, chưa phải phép đo tốc độ có kiểm soát tải máy.

| Ảnh có TXT, chạy cắt nội dung rồi OCR PSM 11 | CER Tesseract | CER DBNet | WER Tesseract | WER DBNet |
| --- | ---: | ---: | ---: | ---: |
| `anh.jpg` | **0,38%** | 7,41% | **0,72%** | 7,97% |
| `anh_test_02.jpg` | 1,59% | **1,06%** | 8,97% | **7,69%** |

DBNet có kết quả tốt hơn trên một ảnh nhưng kém hơn trên ảnh còn lại; hai ảnh không đủ để kết luận tổng quát về OCR.

### 4. Quan sát và quyết định

Đã mở ảnh tổng hợp để kiểm tra:

- Trên `0001129658.png`, cách hiện tại giữ khoảng 99,6% hộp từ, DBNet + gom cụm chỉ giữ khoảng 48,8%; phần chữ nhỏ bên dưới bị bỏ.
- Trên `0001239897.png`, DBNet không tạo được crop theo điều kiện ít nhất ba vùng được giữ; cách hiện tại vẫn tạo được.
- Trên `anh.jpg`, crop DBNet bỏ chân trang nên CER tăng rõ.
- Trên `anh_thu.png`, hai cách cắt gần tương đương, góc xoay khoảng −7,4°. Ảnh không có văn bản chuẩn nên không báo CER/WER.

**Chốt sử dụng:** giữ **Tesseract làm mặc định cho vùng chữ dự phòng**. Bản DBNet thử hiện tại chỉ dùng khi chủ động chọn `--content-method dbnet`. Không tự thay mặc định bằng phương pháp làm mất nhiều nhãn từ hơn.

Kết quả này chỉ áp dụng cho **mô hình TD500 ResNet-18, đầu vào 736×736, ngưỡng phát hiện và cách gom cụm đã thử**. Chưa tách được toàn bộ ảnh hưởng của bộ phát hiện, việc giảm độ phân giải và bước chọn cụm. Không kết luận mọi biến thể DBNet đều kém hơn Tesseract. Nếu nghiên cứu tiếp, cần kiểm tra riêng vùng không được phát hiện và vùng đã phát hiện nhưng bị gom/loại sai, rồi mới thử độ phân giải/đa tỷ lệ hoặc mô hình khác.

### 5. File và cách chạy

| Đường dẫn | Nội dung |
| --- | --- |
| `artifacts/scanner_dev/day4_dbnet/comparison.jpg` | 4 ví dụ ảnh gốc, crop hiện tại và crop DBNet, gồm ca mất nội dung. |
| `docs/results/scanner_day4_comparison.csv` | So sánh từng ảnh, đủ 54 dòng; có thể đưa lên GitHub. |
| `artifacts/scanner_dev/day4_tesseract/` | Kết quả, ma trận và mã nguồn của cách hiện tại. |
| `artifacts/scanner_dev/day4_dbnet/` | Kết quả, ma trận, hash mô hình và mã nguồn của bản thử. |
| `data/processed/scanner_content/tesseract/` | Ảnh crop minh họa của cách hiện tại. |
| `data/processed/scanner_content/dbnet/` | Ảnh crop minh họa của DBNet. |
| `models/dbnet/source.json` | Nguồn tải và hash của mô hình cục bộ. |

Chạy bình thường, **không cần chọn lại phương pháp**:

```powershell
python -X utf8 src/document_scanner/pipeline.py --input-type photo --image "data/raw/thu_ocr/anh_thu.png"
```

Chỉ khi muốn thử DBNet:

```powershell
python -X utf8 src/document_scanner/pipeline.py --input-type photo --image "data/raw/thu_ocr/anh_thu.png" --content-method dbnet
```

Đã chạy thử lệnh DBNet ở trên thành công: scanner không tìm được tứ giác, chuyển sang DBNet để cắt vùng chữ rồi Tesseract đọc chữ. Kết quả thử ở `data/processed/pipeline/20261117_143911_885356/`. Có ảnh scan, TXT và metadata; chưa có nhãn để chấm điểm mẫu này.

Mô hình không nằm trên GitHub. Máy khác muốn dùng cờ DBNet phải tải [đúng mô hình ONNX](https://drive.google.com/uc?export=download&id=1sZszH3pEt8hliyBlTmB-iulxHP1dCQWV), kiểm tra SHA-1 ở trên và đặt tại `models/dbnet/DB_TD500_resnet18.onnx`. Không cần cài PyTorch để chạy bản thử này. Lệnh mặc định không yêu cầu DBNet.

Hai lệnh benchmark đã chạy, không ghi đè các thư mục kết quả cũ:

```powershell
python -X utf8 src/document_scanner/scanner/benchmark_content.py --method tesseract
python -X utf8 src/document_scanner/scanner/benchmark_content.py --method dbnet
```

Đã chạy **35 kiểm thử, tất cả đạt**, gồm kiểm tra giữ tiêu đề lân cận, loại cụm nhiễu nhỏ ở xa, ma trận crop và chiều xoay không lật gương. Các kiểm thử này bảo vệ xử lý hình học và luồng chương trình; chúng không thay thế đánh giá chất lượng trên 54 ảnh.

**Ngày 5 tiếp theo:** kiểm thử trên tài liệu mới/tiếng Việt và ảnh không có giấy; ưu tiên phát hiện mất nội dung và nhận nhầm vật thể. Chưa chạy lại toàn bộ SmartDoc hoặc thay đổi mô hình OCR tiếng Anh.

## Kiểm chứng detect toàn bộ SmartDoc — Hoàn thành ngày 17/11/2026

Sau ngày 4, đã chạy toàn bộ **24.889 ảnh** bằng cấu hình `scanner_day3_v2`, trước khi chuyển sang kiểm thử dữ liệu mới của ngày 5. Phần này cập nhật trạng thái “chưa chạy toàn bộ” tại các mục lịch sử phía trên.

Lệnh đã chạy từ thư mục gốc khi venv kích hoạt:

```powershell
python -X utf8 src/document_scanner/scanner/benchmark_detection.py --run-name full_detection_v1 --workers 4
```

Lượt chạy chỉ tìm khung và lưu tọa độ, không nắn ảnh, không tạo ảnh scan, không gọi OCR hoặc cắt vùng chữ dự phòng. Thời gian thực tế khoảng **850,36 giây (14 phút 10 giây)**. Không so trực tiếp thời gian này với batch cũ vì phạm vi xử lý khác nhau.

### Kết quả tổng thể

| Chỉ số | Bản cũ | Bản mới |
| --- | ---: | ---: |
| Tổng số ảnh | 24.889 | 24.889 |
| Tìm được khung | 18.571 (74,62%) | **20.503 (82,38%)** |
| Không trả khung | 6.318 | **4.386** |
| Train đạt IoU ≥ 0,9 | 11.186/17.495 (63,94%) | **13.366/17.495 (76,40%)** |
| Validation đạt IoU ≥ 0,9 | 1.931/3.192 (60,49%) | **2.424/3.192 (75,94%)** |

Trạng thái bản mới: 16.784 `ok`, 3.719 `uncertain`, 3.476 `no_candidate`, 910 `low_confidence`; không có ảnh lỗi đọc hoặc xử lý. Có khung hay trạng thái `ok` không bảo đảm khung đúng.

- Train: thêm **2.209 ảnh đạt**, nhưng có **29 ảnh cũ đạt bị tụt dưới ngưỡng 0,9**. Mức tăng ròng là 2.180 ảnh; cần xem lại các ca giảm trước khi khẳng định phương pháp không gây thoái lui.
- Validation: thêm **493 ảnh đạt**, không có ảnh cũ đạt bị tụt dưới ngưỡng.
- Test: đã chạy đủ **4.202 ảnh**, trả khung ở 3.417 ảnh; **không chấm IoU và không dùng nhãn test để điều chỉnh**.
- Nền 5 vẫn không có ảnh đạt IoU ≥ 0,9 trên train/validation. Trên toàn bộ dữ liệu, 375 ảnh nền 5 được trả khung không đồng nghĩa 375 khung đúng.

### Đọc kết quả

- `artifacts/scanner_dev/full_detection_v1/run_info.json`: `complete: true`, hash nguồn/cấu hình/manifest, số ảnh và thời gian.
- `artifacts/scanner_dev/full_detection_v1/results.csv`: đủ 24.889 dòng kết quả, tọa độ và hash ảnh nguồn. Cột IoU và đạt ngưỡng của test để trống.
- `artifacts/scanner_dev/full_detection_v1/summary.csv`: thống kê theo tập và nền.
- `docs/results/scanner_full_detection_summary.csv`: bản tổng hợp nhỏ đưa lên GitHub.

Đã đối chiếu đủ số dòng, không trùng ảnh, cùng danh sách ảnh với lượt cũ và xác nhận test không có điểm IoU. Lượt `full_detection_day3` chạy trước đó đã được dừng theo yêu cầu người dùng; không dùng lượt chưa hoàn thành này cho báo cáo.

**Kết luận hiện tại:** bản mới cải thiện rõ khả năng tìm đúng khung trên train/validation, nhưng vẫn còn lỗi nền 5 và 29 ca giảm trên train. Chưa có cơ sở kết luận chất lượng OCR tăng hay scanner đã hoạt động tốt trên mọi ảnh. Ngày 5 tiếp tục kiểm thử tài liệu mới/tiếng Việt/ảnh không có giấy.

## Thử mô hình tìm bốn góc DocAligner — 17/11/2026

Đã thử **DocsaidLab DocAligner, biến thể heatmap FastViT-T8** đã huấn luyện sẵn, trên đúng 200 ảnh phát triển cố định. Mô hình tìm bốn góc trang, không phải DBNet tìm chữ. Mã thử là `src/document_scanner/scanner/try_docaligner.py`; chưa thay scanner mặc định.

| Chỉ số trên cùng 200 ảnh | Scanner ngày 3 | DocAligner FastViT-T8 |
| --- | ---: | ---: |
| Đạt IoU ≥ 0,9 và nắn thành công | 128/200 (64%) | **200/200 (100%)** |
| IoU trung bình, tính cả ảnh không trả khung | 0,6404 | **0,9888** |
| IoU thấp nhất | Có ảnh không trả khung, tính 0 | **0,9660** |
| Thời gian phát hiện trung bình, một worker | 58,36 ms | 279,59 ms |

- Mỗi nền có 40 ảnh; DocAligner đạt đủ 40/40 ở cả năm nền, kể cả nền 4 và 5.
- Thêm **72 ảnh đạt** so với scanner ngày 3; không mất ảnh đạt cũ trong 200 ảnh này. Tất cả 200 ảnh có khung và nắn được.
- Đã kiểm tra ảnh minh họa: mô hình bám khung giấy ở ví dụ có dây/vật che cạnh sách. Không dùng nhãn để chọn bốn góc; nhãn chỉ được dùng sau suy luận để chấm IoU.
- Thử qua OpenCV DNN với adapter theo các bước tiền/hậu xử lý trong [mã chính thức](https://github.com/DocsaidLab/DocAligner/blob/main/docaligner/heatmap_reg/infer.py): BGR, resize 256×256, chia 255, giải mã bốn heatmap với ngưỡng 0,3 và trọng tâm vùng lớn nhất. Không cắt tâm. Chưa kiểm chứng tương đương số học từng bước với gói Python chính thức sử dụng ONNX Runtime/Capybara.
- Mô hình tải từ liên kết do upstream cung cấp, khoảng 13,17 MB, nằm tại `models/docaligner/fastvit_t8.onnx`. Nguồn và SHA-256 được lưu trong `models/docaligner/source.json` và thông tin lần chạy. Không cài thêm PyTorch/ONNX Runtime và không đổi môi trường OCR.

**Giới hạn:** 100% chỉ là kết quả trên 200 ảnh phát triển, không phải trên 24.889 ảnh hoặc trên tài liệu mới. Chưa xác minh mô hình đã huấn luyện sẵn có từng dùng SmartDoc hay không, nên không xem đây là đánh giá độc lập. Chưa đo nhận nhầm trên ảnh không có tài liệu, chất lượng OCR hay khả năng khái quát sang ảnh thực tế. Mô hình chậm hơn scanner ngày 3 khoảng 4,8 lần trong hai lượt đo trên máy này.

### Xem kết quả

- `artifacts/scanner_dev/docaligner_t8_200/examples.jpg`: ảnh minh họa khung dự đoán màu đỏ và nhãn màu xanh lá trên 5 nền.
- `artifacts/scanner_dev/docaligner_t8_200/results.csv`, `summary.json`, `run_info.json`: kết quả đủ 200 ảnh, mã nguồn và nguồn mô hình.
- `data/processed/scanner_dev/docaligner_t8_200/`: ảnh sau nắn minh họa, tra đường dẫn gốc trong `examples.csv`.
- `docs/results/docaligner_t8_comparison_200.csv`: so sánh từng ảnh với scanner ngày 3.

**Kết luận thử:** mô hình này tốt hơn rõ trên 200 ảnh và đáng kiểm chứng rộng hơn. Chưa tự thay mặc định hoặc chạy toàn bộ dữ liệu. Lệnh để người dùng chạy kiểm chứng trên **2.992 ảnh validation còn lại**, không dùng nhãn test:

```powershell
python -X utf8 src/document_scanner/scanner/try_docaligner.py --run-name docaligner_t8_validation_check --remaining-validation
```

Chạy từ gốc dự án với venv đã kích hoạt và mô hình ONNX có trên máy. Adapter hiện hỗ trợ nhiều worker bằng cách tạo một mạng riêng cho mỗi luồng; đã kiểm tra 4 worker tái tạo đúng tọa độ đã lưu trên 4 ảnh. Chương trình từ chối ghi đè thư mục lần chạy đã có. Các lần chạy DocAligner được gắn cảnh báo `experimental_model` để phân biệt với scanner mặc định; cảnh báo này không có nghĩa IoU thấp.

Để người dùng chạy detect đủ 24.889 ảnh, không tạo ảnh scan hoặc chạy OCR:

```powershell
python -X utf8 src/document_scanner/scanner/try_docaligner.py --full-detection --run-name docaligner_t8_full --workers 4
```

Kết quả nằm trong `artifacts/scanner_dev/docaligner_t8_full/`; chỉ chấm IoU train/validation, test lưu dự đoán. Bản tổng hợp sẽ lưu riêng tại `docs/results/docaligner_full_detection_summary.csv`, không ghi đè bảng scanner hiện tại. Đây là lệnh chuẩn bị cho người dùng tự chạy, chưa phải kết quả đã hoàn thành.
