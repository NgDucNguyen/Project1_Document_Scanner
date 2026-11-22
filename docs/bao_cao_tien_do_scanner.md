# Báo cáo tiến độ Project 1 Document Scanner

**Sinh viên:** Nguyễn Đức Nguyên — **MSSV:** 202416305
**Đơn vị:** Đại học Bách khoa Hà Nội — **Cập nhật nội dung:** 23/11/2026
**Mục đích:** Chuẩn bị trình bày trong buổi báo cáo tuần tới, dựa trên kết quả hiện có. Ngày báo cáo cụ thể chưa chốt.

## 1 Công việc đã thực hiện

### Hustack

Hoàn thành tiến độ hustack W8 (giữ nội dung người dùng đã cập nhật trong bản Word).

### Project 1 Document Scanner

Trong giai đoạn này, em tập trung cải thiện bước tìm khung và cắt/nắn tài liệu. Nhánh scanner truyền thống Canny/Otsu được phân tích lỗi, bổ sung cạnh trên ảnh xám và kênh Lab để tăng khả năng tìm mép giấy nhạt. Sau đó em tích hợp DocAligner FastViT-T8 đã huấn luyện sẵn để so sánh trên cùng dữ liệu và chọn làm detector mặc định.

Khi DocAligner không trả khung phù hợp, scanner chuyển sang tìm vùng chữ chính kết hợp xử lý ảnh: scan riêng dùng Tesseract; pipeline RapidOCR dùng khung dòng RapidOCR để hỗ trợ. Mục tiêu là chọn trang chính, tránh gom chữ của các tờ giấy xung quanh. Nhánh này thử nắn phối cảnh nếu ước lượng được tứ giác đủ bằng chứng. Ảnh sau cắt được kiểm tra chất lượng và tăng độ rõ chữ; ảnh màu trước tăng cường vẫn được giữ để đối chiếu.

Scanner đã chạy độc lập được và dùng chung với pipeline OCR. Báo cáo trình bày scanner và cập nhật OCR tiếng Anh, biểu mẫu, tiếng Việt có dấu; kèm ảnh đầu vào, TXT thực tế, số đo và các lỗi còn tồn tại.

## 2 Sản phẩm đạt được

| Sản phẩm | Trạng thái hiện tại |
| --- | --- |
| Scanner Canny/Otsu cải tiến | Giữ mã nguồn và kết quả làm đối chứng |
| Detector DocAligner đã huấn luyện sẵn | Là phương pháp mặc định, suy luận ONNX bằng OpenCV |
| Hai lượt detect toàn SmartDoc | Cả hai detect đủ 24.889 ảnh; DocAligner đã chấm test cuối |
| Scan một ảnh và cắt dự phòng | Đã nối chung trong scanner, thử trên hai ảnh viết tay |
| Ảnh minh họa cho báo cáo | 9 hình scanner và 8 hình OCR đặt ngay tại phần phân tích |
| Đầu ra để kiểm tra | Ảnh scan, ảnh màu, vùng chọn và metadata; OCR có văn bản riêng |

Các sản phẩm trên có phạm vi khác nhau: chạy đủ ảnh không có nghĩa mọi khung đều đúng, và có ảnh scan không đồng nghĩa OCR chính xác. Chưa hoàn thành kiểm thử độc lập trên ảnh mới và ảnh không có giấy.

<!-- PAGEBREAK -->

## 3 Đánh giá và thảo luận kết quả

### 3.1 Dữ liệu và cách đánh giá

SmartDoc gồm 24.889 ảnh của 30 tài liệu gốc trên 5 nền. Dữ liệu được chia theo tài liệu: train 17.495 ảnh, validation 3.192 ảnh, test 4.202 ảnh. Các frame của cùng tài liệu không bị trộn giữa các tập. Nhãn chỉ dùng đánh giá sau dự đoán, không truyền vào detector để chọn khung.

IoU bằng diện tích giao chia diện tích hợp của hai tứ giác dự đoán và nhãn thật. Ảnh không có khung tính IoU bằng 0. Tỷ lệ đạt được tính với ngưỡng IoU ≥ 0,9; không bỏ các ca thất bại khỏi mẫu số. Ngày 19/11/2026, sau khi chốt phương án, em chấm test DocAligner từ dự đoán đã lưu. Không dùng điểm test để chỉnh cấu hình; classic test vẫn chỉ lưu dự đoán.

| Chỉ số | Canny/Otsu cải tiến | DocAligner FastViT-T8 |
| --- | ---: | ---: |
| Trả được bốn góc toàn dữ liệu | 20.503/24.889 | 24.889/24.889 |
| Train đạt IoU ≥ 0,9 | 13.366/17.495 (76,40%) | 17.493/17.495 (99,99%) |
| Validation đạt IoU ≥ 0,9 | 2.424/3.192 (75,94%) | 3.192/3.192 (100%) |
| Test đạt IoU ≥ 0,9 | Chưa chấm | 4.201/4.202 (99,98%) |
| IoU trung bình validation | 0,7503 | 0,9893 |

Đánh giá cuối chấm lại 24.889 bộ góc DocAligner đã lưu: train/validation khớp mốc cũ; test đạt 4.201/4.202 (99,98%), IoU trung bình 0,9889. Manifest và trọng số khớp hash lượt gốc, mọi khung đều qua kiểm tra hình học hiện tại. Đã đóng băng nguồn/cấu hình trước chấm; không chạy lại detector. Đây chỉ là đánh giá định vị bốn góc, chưa chấm toàn luồng vùng chữ dự phòng, làm rõ ảnh hoặc OCR. Tập train của dự án chưa được dùng để huấn luyện DocAligner.

### 3.2 Scanner truyền thống và các cải tiến

`scanner/classic.py` thu nhỏ ảnh cạnh dài tối đa 1.000 pixel, làm xám và làm mượt. Canny tìm biên thay đổi sáng mạnh; Otsu tự chọn ngưỡng sáng/tối. Closing nối khe nhỏ. Từ contour, chương trình lấy bao lồi và xấp xỉ đa giác để tạo tứ giác ứng viên.

Contour là đường bao của một vùng trong ảnh nhị phân. Nó có thể thuộc mép giấy, bìa sách hoặc khung bên trong trang, nên không phải contour nào cũng là tài liệu. Các tứ giác được lọc và chấm theo diện tích, hình học, vị trí và bằng chứng cạnh; điểm dùng xếp hạng, không phải xác suất đúng.

Em bổ sung Canny ngưỡng thấp trên ảnh xám và cạnh trên kênh Lab b để tìm thêm mép giấy nhạt. Ứng viên mới cần bằng chứng trên từng cạnh; khung quá yếu bị từ chối. Tỷ lệ validation đạt IoU ≥ 0,9 tăng từ mốc cũ 60,49% lên 75,94%. Nhánh này vẫn dễ chọn nhầm vật thể hoặc khung bên trong khi nền phức tạp.

Trên validation, classic đạt lần lượt 782/797, 747/780, 746/751, 149/515 và 0/349 ảnh ở nền 1–5. DocAligner đạt toàn bộ từng nền. Hai nền cuối là nơi nhánh truyền thống còn hạn chế rõ; Các trường hợp dưới đây minh họa trực tiếp từng hạn chế của scanner truyền thống; không thay thế thống kê toàn tập.

Đối chiếu vấn đề thiếu khung: classic giảm từ 6.318 ảnh ở mốc cũ xuống 4.386 ảnh sau cải tiến. Phân tích 200 ảnh ở mốc classic ban đầu có 98 ảnh đạt, 24 ảnh có ứng viên gần nhưng chưa chính xác và 78 ảnh không có ứng viên đạt IoU ≥ 0,5. Không có ca đã sinh khung đạt IoU ≥ 0,9 rồi bị lọc loại hoặc xếp hạng sai. Trong tập này, điểm nghẽn chủ yếu là tạo đường bao/ứng viên; chưa quy riêng mọi lỗi cho Canny hay Otsu.

<!-- PAGEBREAK -->

Các hình đối chiếu cùng ảnh: **trái là Canny/Otsu cải tiến, phải là DocAligner**. Xanh lá là nhãn thật, đỏ là dự đoán. Đây là các ca khó được chọn để giải thích lỗi.

### 3.2.1 Chọn nhầm bìa sách

Classic trả khung bám bìa sách thay vì tờ giấy, trạng thái uncertain. IoU bằng 0 là khung sai, không phải chương trình không chạy.

Vật thể có cạnh rõ và dạng tứ giác có thể được chấm cao hơn giấy cần quét. Cần xem các ứng viên và bằng chứng cạnh; không chỉ chọn vùng lớn hoặc đường bao rõ nhất.

![Chọn nhầm bìa sách](../artifacts/scanner_dev/comparison/01_wrong_book_corners.jpg)

**Hình 1. Chọn nhầm bìa sách.** **Ảnh:** `background05/patent003/frame_0030.jpeg`. **IoU classic:** 0.0000; **DocAligner:** 0.9920.

### 3.2.2 Giấy có vật thể che và cạnh bị gián đoạn

Classic không trả ứng viên được chấp nhận, trạng thái no_candidate. DocAligner vẫn dự đoán được khung trang trong ví dụ này.

Các vật nằm trên giấy làm cạnh đứt đoạn và sinh thêm contour. Muốn xác định bị bỏ sót ở khâu tạo hay lọc ứng viên phải xem dữ liệu chẩn đoán; chỉ ảnh cuối chưa đủ kết luận chính xác khâu gây lỗi.

![Giấy có vật thể che và cạnh bị gián đoạn](../artifacts/scanner_dev/comparison/02_occluded_page_corners.jpg)

**Hình 2. Giấy có vật thể che và cạnh bị gián đoạn.** **Ảnh:** `background05/letter001/frame_0001.jpeg`. **IoU classic:** 0.0000; **DocAligner:** 0.9880.

<!-- PAGEBREAK -->

### 3.2.3 Giấy gần màu mặt bàn

Classic không tìm được khung, trạng thái no_candidate; đường xanh cho thấy mép giấy tương phản thấp với nền.

Cạnh giấy yếu làm Canny khó nối đủ biên; ngưỡng Otsu cũng có thể không tách rõ giấy với bàn. Bổ sung kênh màu cải thiện một phần nhưng không đảm bảo xử lý mọi nền tương tự.

![Giấy gần màu mặt bàn](../artifacts/scanner_dev/comparison/03_paper_similar_to_table_corners.jpg)

**Hình 3. Giấy gần màu mặt bàn.** **Ảnh:** `background04/letter001/frame_0001.jpeg`. **IoU classic:** 0.0000; **DocAligner:** 0.9915.

### 3.2.4 Chọn khung bên trong và mất lề

Classic có tứ giác nhưng khung đỏ nằm bên trong khung xanh; trạng thái uncertain. Nắn theo khung này sẽ làm thiếu một phần lề trang.

Đường kẻ hoặc vùng in trong trang có thể có cạnh rõ hơn mép ngoài. Cần xem cả overlay và ảnh sau nắn; trả được bốn góc chưa đủ để coi scan đạt.

![Chọn khung bên trong và mất lề](../artifacts/scanner_dev/comparison/04_inner_frame_lost_margin_corners.jpg)

**Hình 4. Chọn khung bên trong và mất lề.** **Ảnh:** `background04/tax002/frame_0001.jpeg`. **IoU classic:** 0.6416; **DocAligner:** 0.9922.

<!-- PAGEBREAK -->

### 3.2.5 Khung trong trên một nền khác

Classic tiếp tục chọn khung nhỏ hơn trang trên background02, trạng thái uncertain. Sai lệch vừa phải vẫn làm IoU dưới 0,9.

Lỗi chọn vùng bên trong không chỉ xuất hiện ở nền 4–5. Cần kiểm tra vùng in sát mép, tiêu đề và chân trang để tránh khung nhìn hợp lý nhưng mất nội dung.

![Khung trong trên một nền khác](../artifacts/scanner_dev/comparison/05_inner_frame_background02_corners.jpg)

**Hình 5. Khung trong trên một nền khác.** **Ảnh:** `background02/tax002/frame_0169.jpeg`. **IoU classic:** 0.7587; **DocAligner:** 0.9869.

### 3.2.6 Từ chối khung yếu dù ảnh có giấy

Classic trả trạng thái low_confidence nên không xuất khung được chấp nhận. IoU đánh giá tính 0; điều này khác với chọn nhầm một vật thể.

Cơ chế từ chối giúp hạn chế khung sai nhưng có thể bỏ sót trang thật. Phải đo đồng thời số khung đúng, số bỏ sót và số nhận nhầm, thay vì chỉ tăng tỷ lệ trả khung.

Cụ thể, classic từ chối khi điểm ứng viên tốt nhất dưới 5,0; từ 5,0 đến dưới 5,75 thì cảnh báo khung yếu. Luồng scan còn kiểm tra ảnh trước tăng cường và thử vùng chữ nếu khung không đạt. Không tìm được vùng đủ bằng chứng hoặc ảnh cuối không đạt chất lượng thì báo thất bại. Các quy tắc này chưa bảo đảm loại hết bìa sách có chữ; cần đo tỷ lệ nhận nhầm trên tập ảnh không có tài liệu.

![Từ chối khung yếu dù ảnh có giấy](../artifacts/scanner_dev/comparison/06_weak_frame_rejected_corners.jpg)

**Hình 6. Từ chối khung yếu dù ảnh có giấy.** **Ảnh:** `background01/tax002/frame_0001.jpeg`. **IoU classic:** 0.0000; **DocAligner:** 0.9885.

<!-- PAGEBREAK -->

### 3.3 DocAligner và luồng scan hiện tại

DocAligner FastViT-T8 là mô hình đã huấn luyện sẵn của DocsaidLab, được chạy ONNX bằng OpenCV. Em thực hiện tích hợp, xử lý đầu ra và đánh giá; chưa tự huấn luyện hoặc tinh chỉnh mô hình này. Chưa xác minh dữ liệu huấn luyện sẵn có trùng SmartDoc hay không, nên điểm cao chưa chứng minh khả năng tổng quát hóa độc lập.

Ảnh BGR được resize 256 × 256 và chia 255. Mạng tạo bốn heatmap tương ứng bốn góc. Adapter loại giá trị dưới 0,3, dùng Otsu trên heatmap, lấy vùng lớn nhất và tính trọng tâm. Góc được đổi về ảnh gốc, sắp thứ tự, kiểm tra rồi nắn phối cảnh. Chưa kiểm chứng tương đương số học với toàn bộ gói Python upstream.

**Vị trí dùng Canny và Otsu:** classic dùng chúng trực tiếp trên ảnh để tìm ứng viên. DocAligner không dùng Canny tìm góc; Otsu của adapter xử lý heatmap đầu ra mạng. Trong nhánh dự phòng, Canny/Hough hỗ trợ chỉnh nghiêng nhỏ, Otsu hỗ trợ mặt nạ nét chữ và giấy.

Hai ví dụ dưới minh họa riêng DocAligner: bên trái là ảnh gốc với khung đỏ và bốn góc vàng; bên phải là bốn heatmap thực tế từ mô hình. Vùng màu nóng biểu thị giá trị dự đoán cao. H1–H4 là thứ tự kênh đầu ra; TL/TR/BR/BL là thứ tự hình học sau sắp góc, không mặc định đồng nhất với thứ tự kênh.

![DocAligner và bốn heatmap ví dụ 1](../artifacts/scanner_dev/comparison/docaligner_heatmap_01.jpg)

Hình 7. Có bìa sách cạnh tranh: DocAligner dự đoán khung tờ giấy, IoU = 0,9920; classic chọn nhầm sách, IoU = 0. Ảnh background05/patent003/frame_0030.jpeg.

![DocAligner và bốn heatmap ví dụ 2](../artifacts/scanner_dev/comparison/docaligner_heatmap_02.jpg)

Hình 8. Giấy gần màu bàn: DocAligner dự đoán đủ bốn góc, IoU = 0,9915; classic không trả khung. Ảnh background04/letter001/frame_0001.jpeg.

Heatmap là đầu ra mạng, không phải ảnh cạnh Canny hay ảnh Otsu của trang giấy. Sau khi mạng dự đoán, adapter mới ngưỡng hóa heatmap bằng Otsu và lấy trọng tâm vùng để giải mã góc. Hai dự đoán đã được đối chiếu với tọa độ benchmark đã lưu; đây là hình minh họa, không phải phép đánh giá toàn tập mới.

### 3.4 Cắt vùng chữ dự phòng và giữ nội dung chính

Cập nhật 22/11/2026: anh_thu.png từng mất mục 3 vì chương trình chỉ giữ cụm chữ lớn nhất. Đã nối thêm các đoạn gần theo chiều dọc khi có chồng lấn ngang và nền giấy sáng liên tục; pipeline chạy lại giữ được mục 3 cùng hai dòng cuối. Không gom mọi chữ quanh ảnh. Đây là sửa trên mẫu phát triển; chưa chứng minh đã khắc phục toàn bộ lỗi giữ nội dung của FUNSD.

Luồng chung: ảnh → DocAligner → nắn nếu góc hợp lệ → tìm vùng chữ chính nếu thiếu khung hoặc ảnh nắn không đạt kiểm tra → kiểm tra chất lượng → làm rõ ảnh → lưu kết quả.

`content_scan.py` dùng hộp từ Tesseract làm bằng chứng, kết hợp các cụm nét chữ để chọn vùng có diện tích lớn nhất trong các vùng đủ hỗ trợ. Không dùng hộp bao tất cả từ trên toàn ảnh. Các vùng gần nhau được gom và thêm lề nhỏ; hai vùng lớn gần bằng nhau được cảnh báo. Đây là quy tắc hình học, chưa hiểu ngữ nghĩa trang người dùng muốn chọn.

Trong vùng đã chọn, scanner thử tìm tứ giác giấy. Chỉ nắn thêm khi đạt kiểm tra hình học và giữ hộp từ/nét chữ; nếu không thì giữ crop đã chỉnh nghiêng. Ma trận được đưa về ảnh gốc để nắn một lần, hạn chế nội suy nhiều lần. Khung này vẫn ghi là ước lượng theo nội dung, không phải DocAligner tìm góc thành công. Phần ngoài ảnh được đệm trắng và cảnh báo, không phục hồi chữ bị thiếu.

<!-- PAGEBREAK -->

### 3.5 Kiểm tra chất lượng và làm rõ ảnh

`appearance.py` kiểm tra ảnh trước tăng cường theo kích thước, vùng giấy sáng, lượng nét giống chữ và độ nét. Ảnh trắng, tối hoặc quá mờ có thể bị từ chối. Đây là bộ lọc theo quy tắc cho giấy sáng có chữ, chưa thay cho kiểm thử nhận nhầm trên ảnh không có tài liệu.

Ảnh đạt được bù nền sáng trong Lab, tăng độ đậm nét chữ, làm sắc nhẹ và giữ màu mực. Cấu hình ở `configs/scan.json`; mức làm sắc hiện tại 0,45, sigma 0,7. Nét quá nhạt, đường kẻ và hình vẽ có thể bị ảnh hưởng, nên phải đối chiếu ảnh màu. Chưa xử lý cong trang hoặc tự xác định mọi trường hợp xoay ngược 90/180 độ theo nghĩa của chữ.

Với `anh_viet.jpg`, DocAligner trả được khung để nắn trang. Với `anh_2.jpg`, điểm detector khoảng 0,0374, không có khung được chấp nhận; nhánh dự phòng chọn vùng chữ chính rồi ước lượng tứ giác và nắn lại. Quan sát cho thấy nền sáng hơn, chữ đậm hơn và vùng chính thẳng hơn so với trước.

![Trước và sau nắn vùng chữ dự phòng](../artifacts/history/scan_report_20261118/comparison.jpg)

**Hình 9. Ảnh viết tay có nhiều tờ giấy.** Trái: kết quả trước bổ sung nắn phối cảnh cho vùng chữ; phải: kết quả sau cải thiện. Đây là mốc ảnh đã lưu; cấu hình hiện tại đã chỉnh nhẹ độ sắc thêm sau mốc này.

Ảnh gốc `anh_2.jpg` bị thiếu một phần trang ở mép ảnh. Kết quả còn cảnh báo khung ước lượng và đệm trắng ngoài ảnh; giấy phụ hoặc viền thừa vẫn có thể còn. Chưa thể nói đã loại sạch mọi phần thừa hoặc đạt tương đương CamScanner. Hai ảnh chưa có nhãn góc/TXT nên chưa có IoU hoặc CER/WER; chỉ dùng kiểm tra chức năng.

Không thể phục hồi chữ nằm ngoài ảnh hoặc bị vật thể che. Nắn đúng khung cũng không tự làm chữ bị mờ thành nét thật. Cần xem ảnh màu cùng ảnh tăng cường trước khi đánh giá giữ dấu và nét mảnh.

<!-- PAGEBREAK -->

### 3.6 Bảng tiêu chí đánh giá scanner

Đã kiểm tra bổ sung ngày 19/11/2026 với cấu hình đã chốt, không điều chỉnh detector hoặc bộ làm rõ ảnh theo kết quả. Các tiêu chí dưới đây là quy ước đánh giá của dự án, không phải chứng nhận theo tiêu chuẩn công nghiệp.

| Tiêu chí và phép đo | Kết quả đã kiểm tra | Đánh giá và phạm vi |
| --- | --- | --- |
| Đúng khung trang bằng IoU ≥ 0,9 | Test SmartDoc đạt 4.201/4.202 ảnh (99,98%); mean IoU 0,9889 | Đạt trên SmartDoc; chưa xác minh trùng dữ liệu huấn luyện sẵn |
| Sai số vị trí bốn góc | Test: trung bình 2,38 px; trung vị sai số chuẩn hóa 0,098%; P95 0,190% đường chéo ảnh | Đã đo 4.202 ảnh; đối chiếu chu kỳ đỉnh, không đánh giá hướng đọc |
| Giữ nội dung sau cắt/nắn | 8 trang FUNSD: giữ đủ 864/1.583 hộp từ (54,58%); đủ nghĩa là ≥98% diện tích hộp nằm trong ảnh đầu ra | Chưa đạt mục tiêu giữ đầy đủ trang; nhánh dự phòng có thể cắt mất các khối chữ khác |
| Hình học và hướng ảnh | 24.889 khung qua bộ kiểm tra hình học; kiểm thử màu bốn góc, chống lật gương, ma trận xoay và giảm nghiêng đều đạt | Đã kiểm tra hình học và mẫu tổng hợp; chưa đo hướng đọc, cong trang và dấu tiếng Việt trên tập thực tế |
| Từ chối ảnh không phù hợp | 6/6 vùng ảnh không có tờ giấy chính bị từ chối; thêm 2/2 ảnh trắng/tối và 1/1 ảnh mờ tổng hợp bị từ chối | Mẫu nhỏ; 6 vùng âm cùng lấy từ một ảnh train, chưa phải tỷ lệ tổng quát |
| Làm rõ ảnh trước OCR | Hai ảnh tiếng Anh có TXT: ảnh tăng cường CER 0,57%, WER 4,08%; ảnh màu CER 2,76%, WER 7,14% | Có lợi trên hai ảnh cũ; chưa đủ kết luận cho tài liệu mới hoặc tiếng Việt |
| Tốc độ và độ ổn định | 14 ảnh có tài liệu: trung vị 1,095 giây, P95 3,004 giây; toàn lượt 23 mẫu không lỗi xử lý ngoài dự kiến; 51 kiểm thử đạt | Thời gian scan đã làm nóng, 1 luồng OpenCV; không gồm đọc/ghi file hoặc OCR cuối; chưa đo bộ nhớ |

**Kết luận:** detector bốn góc có kết quả tốt trên SmartDoc. Tuy nhiên, kiểm tra mới phát hiện lỗi giữ nội dung trên trang nhiều khối: ảnh được chấp nhận chất lượng chưa đồng nghĩa scan toàn trang thành công. Chưa chốt toàn bộ scanner là hoàn thiện; cần sửa cách giữ các khối chữ cùng trang trước khi đánh giá lại trên tập độc lập. Lỗi này không làm thay đổi điểm detector SmartDoc đã chốt.

<!-- PAGEBREAK -->

### 3.6.1 Cách kiểm tra và bằng chứng bổ sung

**Sai số góc:** tính khoảng cách Euclid tại bốn đỉnh rồi lấy trung bình mỗi ảnh, chia đường chéo ảnh khi chuẩn hóa. Thử bốn phép dịch chu kỳ đỉnh, giữ chiều đi quanh tứ giác, để không phạt hai khung trùng nhau chỉ vì bắt đầu từ đỉnh khác nhau. Train/validation/test có sai số trung bình lần lượt 2,38/2,34/2,38 px. P95 là phân vị 95 của sai số trung bình mỗi ảnh, không phải sai số lớn nhất. Cách đo này không kiểm tra trang có đúng hướng đọc hay không.

**Giữ chữ:** chọn trước 8 trang FUNSD theo thứ tự tên file; chạy scanner không dùng nhãn, sau đó chiếu hộp từ nhãn qua ma trận T để đo phần nằm trong khung đầu ra. Ảnh bị từ chối tính giữ 0 hộp. Tất cả 8 ảnh được chấp nhận nhưng chỉ giữ đủ 54,58% hộp từ. Ví dụ 82200067_0069 chỉ giữ 27/167 hộp: vùng dự phòng chọn một khối ở giữa, mất tiêu đề, bảng bên dưới và chữ ở vùng khác. Đây là phép đo phạm vi crop trước làm rõ, chưa đo đủ nét mực sau tăng cường.

Ảnh đối chiếu lỗi: `artifacts/scanner_dev/scanner_quality_20261119/samples/content_loss_example.jpg`. Khung đỏ là vùng thực sự được cắt, khung xanh là hộp từ nhãn; nhãn chỉ dùng vẽ/chấm sau dự đoán. FUNSD là tài liệu đã scan nhiều vùng, khác phân bố ảnh chụp SmartDoc; kết quả này kiểm tra việc giữ trang khi đầu vào chưa được khai báo là scan sẵn.

**Từ chối:** 6 vùng âm gồm bìa sách, cốc, dây và mặt bàn, đều lấy từ một frame train SmartDoc, không chứa tờ giấy chính. Tỷ lệ nhận nhầm quan sát là 0/6; không suy rộng thành scanner từ chối đúng 100%. Hai ảnh hằng trắng/tối và một ảnh chữ bị làm mờ là kiểm tra tổng hợp riêng. 14/14 ảnh có tài liệu được chấp nhận, nhưng kết quả giữ chữ phía trên cho thấy không thể dùng tỷ lệ chấp nhận để thay cho chất lượng scan.

**OCR trước và sau tăng cường:** dùng anh.jpg và anh_test_02.jpg với hai TXT hiện có; cùng crop, mô hình funsd_eng, PSM 11. Chỉ chuẩn hóa Unicode NFC và khoảng trắng; giữ hoa/thường và dấu câu. Cộng số lỗi của hai ảnh rồi chia tổng ký tự/từ nhãn, không lấy trung bình phần trăm đơn giản.

| Đầu vào OCR trên cùng crop | CER | WER |
| --- | ---: | ---: |
| Ảnh màu sau nắn | 2,76% | 7,14% |
| Ảnh xám | 3,85% | 10,88% |
| Ảnh tăng cường hiện tại | 0,57% | 4,08% |

Hai ảnh là mẫu phát triển đã có, không phải test độc lập mới. Chưa chọn lại tham số theo kết quả. Lượt audit và hash nguồn/cấu hình ở `artifacts/scanner_dev/scanner_quality_20261119/`: `results.json` giữ từng mẫu, `summary.json` giữ kết quả nhóm, `additional_metrics.json` giữ sai số góc đã ghép chu kỳ và kết quả kiểm thử. Trường corner_error trong summary gốc là sai số theo chỉ số đỉnh thô; dùng số đã ghép chu kỳ trong additional_metrics khi báo cáo.


<!-- PAGEBREAK -->

<!-- PAGEBREAK -->

<!-- PAGEBREAK -->

<!-- PAGEBREAK -->

## 4 OCR tiếng Anh và tiếng Việt cùng kết quả minh họa

### 4.1 Luồng scan và OCR đang sử dụng

Em đã nối scan với OCR tiếng Anh và bổ sung nhánh tiếng Việt. Ảnh chụp được chọn hướng đọc → DocAligner tìm khung → nắn phối cảnh hoặc chọn vùng chữ chính dự phòng → giữ bản màu → chuẩn bị ảnh → đọc từng dòng → gom bố cục → xuất TXT và JSON. Các mô hình đang dùng là mô hình có sẵn; em chưa tự huấn luyện hoặc tinh chỉnh DocAligner, RapidOCR hay Tesseract tiếng Việt trong giai đoạn này.

Ảnh màu sau cắt/nắn là nguồn cho OCR. Ảnh nhỏ được phóng tối đa 2 lần, nhắm cạnh dài 1.800 px và thêm viền 12 px; ảnh lớn giữ nguyên. scan.png là bản tăng cường để xem. Trên ba ảnh chụp cùng trang “In the Evening”, bản tăng cường làm RapidOCR phân mảnh nhiều hơn, nên luồng hiện tại giữ đầu vào màu. Không suy rộng kết luận này cho mọi engine và tài liệu.

![Hình 10. Ảnh chụp tiếng Anh sau scan và trích TXT thực tế. Đoạn văn đã đọc được nhưng vẫn có “qpiet”, “sipter”, “thą w ay”; ảnh rõ bằng mắt chưa đồng nghĩa OCR đúng.](../artifacts/ocr/report_20261123/10_english_input_text.png)

*Hình 10. Ảnh chụp tiếng Anh sau scan và trích TXT thực tế. Đoạn văn đã đọc được nhưng vẫn có “qpiet”, “sipter”, “thą w ay”; ảnh rõ bằng mắt chưa đồng nghĩa OCR đúng.*

| File | Vai trò |
| --- | --- |
| scan_color.png / ocr_input.png | Bản màu đã cắt/nắn / bản chuẩn bị thực sự đưa vào OCR khi cần. |
| scan.png | Bản tăng cường để xem; không phải đầu vào OCR cuối của luồng RapidOCR. |
| text_raw.txt / text.txt | Nội dung trước / sau gom bố cục; giữ nguyên cả từ đọc sai. |
| ocr.json / metadata.json | Khung dòng, cấu trúc bố cục / nguồn ảnh, hướng xoay, mô hình và cảnh báo. |

Ba ảnh tiếng Anh là ba lần chụp cùng một trang, đã tự xoay 90° theo chiều kim đồng hồ. Chưa có TXT chuẩn được kiểm chứng cho các ảnh này nên chỉ đánh giá trực quan, chưa công bố phần trăm đúng. Các ảnh TXT trong báo cáo được dựng từ file thật, không phải ảnh chụp giao diện VS Code.

<!-- PAGEBREAK -->

### 4.2 OCR tiếng Anh và ví dụ biểu mẫu FUNSD

Sau so sánh ngày 22/11, em chọn RapidOCR 3.10.0 với PP-OCRv6 small đã huấn luyện sẵn làm mặc định tiếng Anh; Tesseract/funsd_eng PSM 11 giữ làm đối chứng. Cả hai đọc cùng ảnh chuẩn bị của 30 trang FUNSD validation, không chạy scanner và không cắt theo nhãn lúc suy luận.

| Bộ đọc trên cùng đầu vào | CER | WER |
| --- | --- | --- |
| RapidOCR — được chọn | 6,80% | 28,65% |
| Tesseract/funsd_eng PSM 11 | 19,41% | 42,29% |

CER = (ký tự thay + thiếu + thừa) / số ký tự nhãn; WER tính tương tự trên từ, càng thấp càng tốt. Phép đo này gán từ dự đoán vào 1.649 vùng nhãn sau suy luận; 88 từ RapidOCR và 559 từ Tesseract ngoài vùng nhãn được đếm riêng, không cộng vào CER/WER vùng. Đây là validation đã dùng phát triển, chưa đo thứ tự đọc toàn trang hoặc hiểu quan hệ form.

![Hình 11. Trích đầu biểu mẫu 0000971160 và khung dòng RapidOCR. Khung chữ dùng đọc nội dung; khác khung bốn góc mép giấy của DocAligner.](../artifacts/ocr/report_20261123/11_form_input.png)

*Hình 11. Trích đầu biểu mẫu 0000971160 và khung dòng RapidOCR. Khung chữ dùng đọc nội dung; khác khung bốn góc mép giấy của DocAligner.*

![Hình 12. Trích file trước/sau gom bố cục: Date và 9/3/92 được ghép cùng hàng; Name/Phone Ext. được giữ gần giá trị.](../artifacts/ocr/report_20261123/12_form_text.png)

*Hình 12. Trích file trước/sau gom bố cục: Date và 9/3/92 được ghép cùng hàng; Name/Phone Ext. được giữ gần giá trị.*

Đánh giá trực tiếp: form dễ đối chiếu hơn khi tên trường và giá trị ở gần nhau. Dòng “QUALITY IMPROVEHENT” trong kết quả vẫn sai chữ; bố cục không sửa lỗi nhận dạng. Chế độ auto thử form khi có ít nhất hai nhãn dấu hai chấm, nếu không dùng chia cột XY-cut. layout.fields chỉ là ứng viên hình học; chưa hiểu ô gộp, checkbox hoặc bảng nhiều dòng. Điểm FUNSD phía trên đo trước gom bố cục.

<!-- PAGEBREAK -->

### 4.3 Kiểm tra giới hạn trên tài liệu khó RDTAG

Để kiểm tra cả ảnh chụp và scan, em đã chạy 20 cặp ảnh–TXT RDTAG lấy từ tập train gốc cho phát triển. Có 15 ảnh xuất kết quả và 5 ảnh bị từ chối; 5 ảnh này được tính dự đoán rỗng và giữ trong mẫu số. Tỷ lệ xuất file 15/20 không phải độ chính xác OCR.

| Cách đọc trên 20 mẫu | CER toàn trang | WER toàn trang |
| --- | --- | --- |
| RapidOCR trước gom bố cục | 72,52% | 84,02% |
| Tesseract trên đúng đầu vào đó | 82,38% | 96,61% |
| RapidOCR sau gom lại bố cục đã lưu | 69,19% | 80,82% |

Chuẩn hóa NFC, khoảng trắng và diễn giải ký hiệu xuống dòng dạng chữ trong nhãn; giữ hoa/thường và dấu câu. Hàng sau gom bố cục là sắp lại dự đoán đã lưu, không chạy lại scan/OCR. Một số trang kém hơn sau gom. Đây là mẫu phát triển đã xem, chưa phải test độc lập; một nhãn có dấu câu bất thường đã được đánh dấu nhưng không loại khỏi mẫu số.

![Hình 13. Book13 và TXT trước gom bố cục: nhiều khối lời thoại bị xen thứ tự, có từ sai. Đây là ví dụ đầu ra thô, không phải TXT sau sắp xếp; bảng phía trên ghi riêng kết quả hai bước.](../artifacts/ocr/report_20261123/13_rdtag_limit.png)

*Hình 13. Book13 và TXT trước gom bố cục: nhiều khối lời thoại bị xen thứ tự, có từ sai. Đây là ví dụ đầu ra thô, không phải TXT sau sắp xếp; bảng phía trên ghi riêng kết quả hai bước.*

Đánh giá trực tiếp: luồng hiện tại chưa xử lý ổn định tài liệu nhiều cột, tranh và vùng nền màu. Lỗi gồm cắt thiếu khối, đọc sai chữ và thứ tự đọc; bộ kiểm tra chất lượng thiên về giấy sáng có thể từ chối tài liệu nền đậm. Chênh lệch lớn với FUNSD không chứng minh một tập “sai”: FUNSD ở trên đo theo vùng trên ảnh scan sẵn, còn RDTAG đo toàn trang qua scanner. Hai điểm không thể so như cùng một phép thử.

<!-- PAGEBREAK -->

### 4.4 Bổ sung bộ đọc tiếng Việt có dấu

Sáu ảnh Trang1–Trang6 là sáu trang in của cùng một báo cáo, chưa phải sáu tài liệu độc lập. Ảnh màu sau scan còn nhìn rõ dấu nhưng bảng ký tự trong file PP-OCRv6 small cục bộ thiếu nhiều chữ như ệ, ị, ộ, ợ, ạ, ế và không có dấu tổ hợp thay thế. Bản Latin PP-OCRv5 đã thử cũng chưa giải quyết được nên không được chọn. Không chèn thêm ký tự vào từ điển ONNX khi chưa có trọng số tương ứng.

Với --lang vie, RapidOCR tìm polygon từng dòng; chương trình cắt/nắn dòng từ ảnh màu, thêm viền trắng 12 px rồi Tesseract đọc bằng mô hình vie của tessdata_best, PSM 7. Chỉ dòng rỗng mới thử PSM 13. Kết quả chuẩn hóa Unicode NFC, không tự đoán dấu hay sửa theo ngữ cảnh. Nhánh tiếng Anh tiếp tục nhận dạng bằng RapidOCR; đây là thay bộ đọc chữ, không phải thay DocAligner.

![Hình 14. Cùng pixel đầu vào Trang1: bộ đọc cũ mất dấu; bộ đọc tiếng Việt đọc được “Họ tên”, “Đỗ Thị Lan Anh”. Từ “thử” vẫn bị đọc thành “thứ”, được giữ nguyên trong hình.](../artifacts/ocr/report_20261123/14_vietnamese_before_after.png)

*Hình 14. Cùng pixel đầu vào Trang1: bộ đọc cũ mất dấu; bộ đọc tiếng Việt đọc được “Họ tên”, “Đỗ Thị Lan Anh”. Từ “thử” vẫn bị đọc thành “thứ”, được giữ nguyên trong hình.*

| Mẫu phát triển | Dòng giữ lại | Dòng còn rỗng sau thử lại |
| --- | --- | --- |
| Trang1 / Trang2 / Trang3 | 38 / 42 / 39 | 0 / 0 / 0 |
| Trang4 / Trang5 / Trang6 | 39 / 42 / 16 | 0 / 0 / 0 |
| Tổng | 216 | 0 |

Cả sáu ảnh đã chạy toàn luồng; hash ảnh đầu vào OCR trùng với lượt bộ đọc cũ. Không rỗng không có nghĩa 216 dòng đúng hoàn toàn. Cả sáu ảnh dùng content_fallback vì không có khung trang DocAligner được chấp nhận; không ghi thành sáu ca DocAligner thành công. Một trang FUNSD tiếng Anh đối chứng giữ nguyên TXT. Bộ kiểm thử hiện có 72 ca đạt, không thay thế phép đo độ chính xác trên dữ liệu mới.

<!-- PAGEBREAK -->

### 4.5 Đối chiếu trực tiếp ảnh và TXT tiếng Việt

Ví dụ dưới đây lấy đúng Trang1 và lượt người dùng đang xem: data/processed/pipeline/20261123_000320_142991/. Phần bên trái là ảnh màu đưa vào OCR; bên phải trích nguyên text.txt, bao gồm lỗi. Không thay nội dung bằng bản gõ lại đúng để làm hình minh họa.

![Hình 15. Trang1 sau cắt/nắn và văn bản OCR thực tế. Dấu và đoạn văn phần lớn đã xuất hiện; các lỗi “thứ việc”, “a›Công” và “nhằm” vẫn cần kiểm tra.](../artifacts/ocr/report_20261123/15_vietnamese_input_text.png)

*Hình 15. Trang1 sau cắt/nắn và văn bản OCR thực tế. Dấu và đoạn văn phần lớn đã xuất hiện; các lỗi “thứ việc”, “a›Công” và “nhằm” vẫn cần kiểm tra.*

| Nội dung cần đọc | Kết quả TXT | Nhận xét |
| --- | --- | --- |
| Họ tên: Đỗ Thị Lan Anh | Họ tên: Đỗ Thị Lan Anh | Đọc đúng cụm có dấu và tên riêng trong mẫu này. |
| Vị trí thử việc | Vị trí thứ việc | Nhầm dấu hỏi thành dấu sắc. |
| tránh dán nhầm sản phẩm | tránh dán nhằm sản phẩm | Đổi dấu làm thay nghĩa; không tự sửa. |
| hàm lượng / thực tế | hàm ống / tức tế | Lỗi gần nét chữ ký đè lên chữ cuối trang. |

Ở trang này text_raw.txt bằng text.txt: bước gom bố cục không sửa các từ trên. OCR JSON giữ polygon dòng và backend rapidocr_detection_tesseract_vie. Confidence là điểm mô hình hỗ trợ kiểm tra, không phải phần trăm chữ đúng; không so trực tiếp điểm Tesseract tiếng Việt với điểm RapidOCR tiếng Anh.

<!-- PAGEBREAK -->

### 4.6 Đánh giá thủ công Trang1 và lỗi mất nội dung

Đã tạo một bản chép tham chiếu thủ công từ ảnh gốc Trang1 để đối chiếu. Bản này do trợ lý chép, chưa có người thứ hai kiểm chứng; kết quả dưới đây là đo sơ bộ một trang, không phải độ chính xác chung của OCR tiếng Việt. Chưa có bộ nhãn chuẩn cho cả sáu trang.

| Phạm vi so sánh | Lỗi ký tự / nhãn | CER | Lỗi từ / nhãn | WER |
| --- | --- | --- | --- | --- |
| Toàn chữ nhìn thấy ở ảnh gốc | 34 / 2.213 | 1,54% | 17 / 496 | 3,43% |
| Chỉ thân bài còn trong ảnh scan | 17 / 2.196 | 0,77% | 13 / 492 | 2,64% |

Giữ dấu, hoa/thường và dấu câu; chuẩn hóa NFC, gộp khoảng trắng; không tính ký hiệu chấm tròn đầu dòng trong tham chiếu. Chỉ chấm nội dung nhìn thấy của trang, không lấy phần tiếp ở trang sau. Bảng toàn trang tính cả phần crop mất; bảng thân bài chỉ giúp tách lỗi bộ đọc, không thay cho kết quả toàn luồng.

![Hình 16. Ảnh gốc có “BÁO CÁO THỬ VIỆC”; ảnh OCR bắt đầu từ “Họ tên”. Đây là lỗi chọn vùng scan, OCR không thể đọc chữ đã bị cắt bỏ.](../artifacts/ocr/report_20261123/16_crop_and_ink_errors.png)

*Hình 16. Ảnh gốc có “BÁO CÁO THỬ VIỆC”; ảnh OCR bắt đầu từ “Họ tên”. Đây là lỗi chọn vùng scan, OCR không thể đọc chữ đã bị cắt bỏ.*

![Hình 17. Nét ký đè lên chữ cuối trang đi kèm lỗi “hàm ống” và “tức tế” trong TXT. Cần giữ ảnh gốc để kiểm tra khi nội dung quan trọng.](../artifacts/ocr/report_20261123/17_vietnamese_error_detail.png)

*Hình 17. Nét ký đè lên chữ cuối trang đi kèm lỗi “hàm ống” và “tức tế” trong TXT. Cần giữ ảnh gốc để kiểm tra khi nội dung quan trọng.*

Đánh giá: tiếng Việt có dấu đã cải thiện rõ trên mẫu đang xem, nhưng chưa chốt hoàn thiện. Ưu tiên giữ đủ tiêu đề và các khối chữ trước khi cải thiện bộ đọc. Tham chiếu và số lỗi nằm tại artifacts/ocr/vietnamese_20261123_manual/Trang1_reference.txt và evaluation.json.

<!-- PAGEBREAK -->

### 4.7 Các vấn đề còn tồn tại và kế hoạch kiểm chứng

| Ưu tiên | Vấn đề và bằng chứng | Việc cần làm tiếp |
| --- | --- | --- |
| 1 | Crop mất tiêu đề Trang1; audit 8 FUNSD chỉ giữ đủ 864/1.583 hộp từ. | Kiểm tra vùng nội dung so với toàn trang; mở rộng giữ các khối cùng tờ giấy, đo lại trên tập độc lập. |
| 2 | Nhầm dấu và mất nét khi chữ ký đè lên chữ; mới có tham chiếu thủ công một trang. | Rà soát TXT chuẩn cả sáu trang; thêm tài liệu Việt độc lập và chấm CER/WER có dấu. |
| 3 | Bố cục form mới gom theo hình học; nhiều cột/lời thoại còn đảo thứ tự. | Gán thứ tự đọc và cặp trường–giá trị riêng; đo đúng hàng/cột, không chỉ CER theo vùng. |
| 4 | Giấy nền màu và ảnh không có tài liệu chưa kiểm thử đủ. | Thêm ảnh âm độc lập, giấy tối/nhiều giấy/bóng/mờ; đo nhận nhầm và từ chối nhầm. |
| 5 | Chưa đánh giá đầy đủ chữ viết tay, công thức và bảng nhiều dòng. | Tách khỏi cam kết hiện tại; định nghĩa phạm vi demo là văn bản in Anh/Việt. |
| 6 | Số liệu SmartDoc chỉ phản ánh detector trên tập đã xem test; trùng tập pretrain chưa rõ. | Giữ cấu hình đã chốt; không chỉnh theo test cũ. Đánh giá toàn luồng bằng tài liệu mới. |

Kết luận hiện tại: DocAligner đạt kết quả tốt trên SmartDoc, RapidOCR phù hợp hơn mốc Tesseract cho tiếng Anh trên FUNSD validation; tiếng Việt dùng RapidOCR tìm dòng kết hợp Tesseract vie để đọc có dấu. Toàn luồng đã chạy và xuất được ảnh/TXT, nhưng giữ đủ nội dung, bố cục phức tạp và tính tổng quát vẫn chưa hoàn thiện. Không dùng số dòng, số file được xuất hoặc confidence để thay độ chính xác.

Nguồn kiểm chứng: FUNSD ở artifacts/ocr/funsd_validation_20261122/results.json; RDTAG ở artifacts/ocr/rdtag_rapidocr_20261122/results.json và layout_validation_20261122/results.json; sáu ảnh Việt ở artifacts/ocr/vietnamese_20261122/pipeline_results.json. Chỉ lấy số từ lượt complete: true. Các lượt là phát triển, không báo cáo như test độc lập mới.

Nguồn mô hình: github.com/DocsaidLab/DocAligner; github.com/RapidAI/RapidOCR; github.com/tesseract-ocr/tessdata_best. Kiểm tra ký tự nêu ở mục 4.4 áp dụng cho file trọng số cục bộ đã dùng, không khẳng định mọi phiên bản upstream đều thiếu dấu. Hash mô hình và nguồn được lưu trong JSON từng lượt.

<!-- PAGEBREAK -->

### 4.8 Demo và vị trí kết quả cần mở

Chạy từ gốc dự án với venv đã kích hoạt. Ảnh chụp đi qua scanner rồi OCR; ảnh đã scan sẵn dùng --input-type scan để tránh cắt trang lần nữa. Pipeline OCR tạo một thư mục cho mỗi lượt chạy; scan riêng mặc định cập nhật thư mục theo ảnh, chỉ thêm --new-run khi cần mốc riêng.

```powershell
python -X utf8 src/document_scanner/pipeline.py --image "data/raw/thu_ocr/Trang1.jpg" --lang vie
```

```powershell
python -X utf8 src/document_scanner/pipeline.py --image "data/raw/thu_ocr/anh.jpg" --lang eng
```

| Nội dung trình bày | Thư mục / file cần mở |
| --- | --- |
| Tiếng Việt Trang1 — ảnh và TXT cùng lượt | data/processed/pipeline/20261123_000320_142991/<br>ocr_input.png, scan.png, text.txt, ocr.json |
| Form tiếng Anh trước/sau gom bố cục | data/processed/pipeline/20261122_171500_479711/<br>text_raw.txt, text.txt, ocr.json |
| Ảnh chụp tiếng Anh “In the Evening” | data/processed/pipeline/20261122_171659_754649/<br>ocr_input.png, text.txt |
| Đánh giá thủ công Trang1 | artifacts/ocr/vietnamese_20261123_manual/<br>Trang1_reference.txt, evaluation.json |

| Thành phần cần giải thích | Mã nguồn trong src/document_scanner/ |
| --- | --- |
| Luồng ảnh chụp → scan → OCR | pipeline.py; scanner/scan_image.py |
| Khung giấy / Canny và Otsu đối chứng | scanner/docaligner.py / scanner/classic.py |
| Hướng đọc, vùng dự phòng, tăng cường | scanner/orientation.py; content_scan.py; appearance.py |
| Đầu vào OCR / RapidOCR tiếng Anh | ocr/prepare_image.py / ocr/rapid_reader.py |
| Nhận dạng tiếng Việt từng dòng | ocr/vietnamese.py |
| Gom hàng form và chia cột | ocr/layout.py |

Cách demo: mở ảnh nguồn → ảnh OCR đã cắt/nắn → text.txt → đối chiếu một cụm đúng và một cụm sai → mở metadata/ocr.json nếu được hỏi phương pháp. Với Trang1 cần chủ động chỉ lỗi mất tiêu đề; không chỉ mở thân bài tốt rồi kết luận toàn trang đúng. Bản báo cáo này cập nhật kết quả đã có, không ghi kế hoạch thành công việc đã hoàn thành.

<!-- PAGEBREAK -->
