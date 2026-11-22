# Báo cáo tiến độ Project 1 Document Scanner

**Sinh viên:** Nguyễn Đức Nguyên — **MSSV:** 202416305
**Đơn vị:** Đại học Bách khoa Hà Nội — **Cập nhật nội dung:** 19/11/2026
**Mục đích:** Chuẩn bị trình bày trong buổi báo cáo tuần tới, dựa trên kết quả hiện có. Ngày báo cáo cụ thể chưa chốt.

## 1 Công việc đã thực hiện

### Hustack

Giữ nội dung theo báo cáo tuần trước: hoàn thiện các bài thực hành W5 trên Hustack. Chưa bổ sung tiến độ Hustack mới trong lần cập nhật này.

### Project 1 Document Scanner

Trong giai đoạn này, em tập trung cải thiện bước tìm khung và cắt/nắn tài liệu. Nhánh scanner truyền thống Canny/Otsu được phân tích lỗi, bổ sung cạnh trên ảnh xám và kênh Lab để tăng khả năng tìm mép giấy nhạt. Sau đó em tích hợp DocAligner FastViT-T8 đã huấn luyện sẵn để so sánh trên cùng dữ liệu và chọn làm detector mặc định.

Khi DocAligner không trả khung phù hợp, scanner chuyển sang tìm vùng chữ chính bằng Tesseract kết hợp xử lý ảnh, thay vì gom tất cả chữ của các tờ giấy xung quanh. Nhánh này thử nắn phối cảnh nếu ước lượng được tứ giác đủ bằng chứng. Ảnh sau cắt được kiểm tra chất lượng và tăng độ rõ chữ; ảnh màu trước tăng cường vẫn được giữ để đối chiếu.

Scanner đã chạy độc lập được và dùng chung với pipeline OCR. Trọng tâm báo cáo lần này là định vị và tạo ảnh scan; phần OCR tiếng Anh được cập nhật ngắn để nêu khả năng nối luồng và những việc cần kiểm chứng tiếp.

## 2 Sản phẩm đạt được

| Sản phẩm | Trạng thái hiện tại |
| --- | --- |
| Scanner Canny/Otsu cải tiến | Giữ mã nguồn và kết quả làm đối chứng |
| Detector DocAligner đã huấn luyện sẵn | Là phương pháp mặc định, suy luận ONNX bằng OpenCV |
| Hai lượt detect toàn SmartDoc | Cả hai detect đủ 24.889 ảnh; DocAligner đã chấm test cuối |
| Scan một ảnh và cắt dự phòng | Đã nối chung trong scanner, thử trên hai ảnh viết tay |
| Ảnh minh họa cho báo cáo | 6 ca classic, 2 ví dụ heatmap DocAligner và 1 ảnh trước/sau |
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

## 4 OCR và kế hoạch trước buổi báo cáo tiếp theo

### 4.1 Tình hình OCR tiếng Anh

**Bổ sung thử nghiệm 22/11/2026 (bản Markdown; bản Word vẫn là mốc báo cáo 19/11):** ba ảnh chụp cùng trang "In the Evening" có chữ xoay ngang; cấu hình cũ trả chuỗi `HHH/111` ở ảnh đã chạy được. Scanner đã thêm chọn hướng đọc bốn chiều bằng bằng chứng chữ, không ép theo khổ ảnh. Thử RapidOCR 3.10.0/ONNX Runtime 1.32.0 với PP-OCRv6 small đã scan/OCR được cả ba ảnh: khung dòng hỗ trợ hướng/crop, OCR đọc ảnh màu trước tăng cường. Văn bản đã thành đoạn có nghĩa nhưng vẫn có từ sai/dòng yếu, nhất là ảnh chữ nhỏ và có đường đen chạy qua chữ. Không có TXT chuẩn cho ba ảnh này nên chưa công bố CER/WER hoặc độ chính xác; đây là ba lần chụp một trang, không phải tập kiểm thử độc lập. Mô hình có sẵn, chưa tự huấn luyện. Mặc định Tesseract/FUNSD/PSM 11 vẫn giữ nguyên; chưa thay engine chính hay đo lại toàn bộ scanner. Lệnh và đầu ra mới trong README/hướng dẫn OCR. Mốc đối chiếu và cấu hình thử nằm ở `artifacts/ocr/new_photos_20261122/`. [Nguồn RapidOCR](https://github.com/RapidAI/RapidOCR).

Cập nhật OCR tiếng Anh ngày 19/11/2026: giữ Tesseract/funsd_eng và PSM 11 sau so sánh PSM 3, 4, 11 trên cùng 30 trang validation FUNSD. Chuẩn bị riêng ảnh OCR: ảnh nhỏ được phóng tối đa 2 lần, nhắm cạnh dài 1.800 px và thêm viền trắng 12 px; ảnh đủ lớn giữ nguyên. CER validation giảm 21,04% → 19,41%, WER giảm 48,01% → 42,29%. Đây là OCR toàn trang chấm theo vùng nhãn sau nhận dạng; không đo thứ tự đọc toàn trang, từ ngoài vùng nhãn đếm riêng. Mốc 50 trang test lịch sử đã dùng trong phát triển, không dùng để chọn lần chỉnh này.

Đã chạy thật luồng hiện tại: anh.jpg đạt CER/WER 0%/0%; anh_test_02.jpg đạt 1,06%/7,69%. Hai ảnh có TXT đều là mẫu cũ, không coi là kết quả tổng quát. Đầu ra thêm ocr.json chứa từ, dòng, tọa độ và điểm tin cậy để xem lỗi; không tự sửa từ hoặc dấu câu. Ảnh OCR phóng riêng được lưu ocr_input.png khi cần; scan.png giữ nguyên. 55 kiểm thử đạt; scanner không đổi.

DBNet đã được thử cho vùng chữ dự phòng nhưng không chọn. Trên 30 trang FUNSD với 4.616 hộp từ, Tesseract giữ 4.595 hộp (99,55%), DBNet kết hợp gom cụm giữ 4.092 hộp (88,65%). Giữ đủ nghĩa là ít nhất 98% diện tích hộp nằm trong crop; crop thất bại tính 0. Kết quả này đánh giá giữ vùng chữ, không phải tỷ lệ đọc đúng chữ.

### 4.2 Scanner riêng và khả năng nối OCR

Lệnh scan riêng gọi `scan_document()` và trả ảnh cùng metadata. `pipeline.py` đã gọi chung hàm này rồi chuyển ảnh sang `recognize_image()`. Vì vậy có thể tiếp tục cải thiện OCR mà giữ scanner hiện có. Pipeline bật thêm kiểm tra nội dung `check_content=True`; scan riêng mặc định không bật nên một số ảnh khó có thể có crop khác nhau.

Tesseract trong nhánh dự phòng chỉ lấy vị trí hộp từ; bước OCR cuối mới xuất văn bản. Mô hình tiếng Anh hiện tại chưa hoàn thiện cho chữ viết tay tiếng Việt hoặc công thức toán. Kết quả OCR hiện tại và giới hạn được ghi ở mục 4.1; chưa mở rộng sang tiếng Việt hoặc tái tạo cấu trúc bảng. Với FUNSD/ảnh đã scan sẵn phải dùng --input-type scan để không chạy lại cắt trang.

### 4.3 Việc cần làm tiếp

Phần còn thiếu: đã thống kê theo nền, nhưng chưa có thống kê định lượng riêng cho che khuất, bóng đổ, mờ và nhiều giấy. Đã thử 6 vùng âm từ một ảnh và đo OCR trên hai ảnh cũ; cần mở rộng tập độc lập. Ưu tiên khắc phục lỗi crop bỏ các khối chữ trên FUNSD, sau đó kiểm tra lại giữ nội dung và CER/WER. Đã chốt detector và chấm test cuối; giữ nguyên cấu hình sau khi xem điểm. Phần còn lại là kiểm chứng toàn luồng scan trên ảnh mới, không dùng test SmartDoc để chỉnh ngưỡng.

| Công việc | Kết quả cần có |
| --- | --- |
| Bổ sung ảnh Anh/Việt và ảnh không có giấy | Danh sách ảnh độc lập, điều kiện chụp và quy tắc chọn trang chính |
| Gán góc cho ảnh có tài liệu | Nhãn ngoài luồng dự đoán để đo IoU và tỷ lệ bỏ sót |
| Sửa crop bỏ khối chữ cùng trang | Khắc phục lỗi giữ 864/1.583 hộp từ trên 8 trang FUNSD, đánh giá lại trên tập độc lập |
| Mở rộng đánh giá OCR có TXT chuẩn | Kiểm chứng kết quả hai ảnh trên tập lớn hơn, thêm tiếng Việt có nhãn |
| Chuẩn bị demo và trao đổi với giảng viên | Một ảnh qua scan, giải thích fallback và giới hạn hiện tại |

Ưu tiên kiểm thử độc lập trước khi khẳng định scanner hoàn thiện. Chưa dùng nhãn test để chỉnh ngưỡng; chưa chạy lại toàn SmartDoc chỉ để bổ sung hình minh họa cho báo cáo.

<!-- PAGEBREAK -->

### 4.4 Demo và vị trí mã nguồn

Chạy từ gốc dự án với venv đã kích hoạt. Scan riêng, không xuất văn bản OCR cuối:

```powershell
python -X utf8 src/document_scanner/scanner/scan_image.py --image "data/raw/thu_detect/anh_2.jpg"
```

Mở `data/processed/scan/image_anh_2_b016f626/scan.png`. Cùng thư mục có `scan_color.png` để đối chiếu trước tăng cường và `region.png` để xem vùng chọn trên ảnh gốc. Metadata ở `artifacts/scans/image_anh_2_b016f626/metadata.json`.

Lệnh scan một ảnh mặc định cập nhật thư mục riêng của ảnh, tránh kết quả lặp; ghi chú của người dùng được giữ. Chỉ thêm `--new-run` khi muốn lưu một mốc mới. Benchmark vẫn dùng tên lượt riêng, không ghi đè mốc cũ.

Chạy nối scan và OCR tiếng Anh trên ảnh phù hợp:

```powershell
python -X utf8 src/document_scanner/pipeline.py --image "data/raw/thu_ocr/anh.jpg"
```

Đầu ra pipeline ở `data/processed/pipeline/<run_id>/`, gồm ảnh scan, `text.txt` và metadata. Với ảnh đã scan, dùng `--input-type scan` để bỏ qua scanner. Pipeline OCR vẫn tạo thư mục theo lượt chạy.

| Thành phần | Vị trí trong dự án |
| --- | --- |
| Canny/Otsu và chấm ứng viên | `src/document_scanner/scanner/classic.py` |
| Heatmap và giải mã góc | `src/document_scanner/scanner/docaligner.py` |
| Luồng scan dùng chung | `src/document_scanner/scanner/scan_image.py` |
| Vùng chữ dự phòng | `src/document_scanner/scanner/content_scan.py` |
| Kiểm tra và làm rõ ảnh | `scanner/appearance.py`, `configs/scan.json` |
| Nắn phối cảnh | `src/document_scanner/scanner/geometry.py` |
| Nối nhận dạng chữ | `src/document_scanner/pipeline.py`, `ocr/` |

Các đường dẫn rút gọn `scanner/`, `ocr/` tính từ `src/document_scanner/`. Hai lượt detect gốc ở `artifacts/scanner_dev/full_detection_v1/` và `docaligner_t8_full/`; lượt chấm cuối ở `artifacts/scanner_dev/docaligner_final_20261119/`. Bảng tổng hợp ở `docs/results/scanner_comparison.csv`. Sáu ca minh họa có chỉ mục trong `artifacts/scanner_dev/comparison/index.csv`; các file `_scans.jpg` cho xem kết quả sau nắn. Chỉ kết luận từ lượt có `complete: true`.

Nguồn mô hình: [DocsaidLab DocAligner](https://github.com/DocsaidLab/DocAligner), adapter tham khảo `docaligner/heatmap_reg/infer.py`. Ảnh và trọng số giữ cục bộ; mã nguồn và kết quả tổng hợp được quản lý bằng Git. Báo cáo này cập nhật nội dung hiện có, không ghi các kế hoạch tuần tới thành kết quả đã hoàn thành.
