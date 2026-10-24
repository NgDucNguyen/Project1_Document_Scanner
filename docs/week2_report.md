# Báo cáo tuần 2 tìm khung và nắn tài liệu

**Sinh viên:** Nguyễn Đức Nguyên · **MSSV:** 202416305 · **Trường:** Đại học Bách khoa Hà Nội  
**Ngày tổng hợp:** 24/10/2026 · **Phiên bản:** week2_v3  
**Phạm vi:** Bộ quét bằng OpenCV; chưa thực hiện nhận dạng chữ OCR.

Ghi chú sắp xếp ngày 25/10/2026: các hướng dẫn đã chuyển vào docs/guides; thư mục history được nén thành artifacts/week2/history.zip. Số liệu và ảnh của lần chạy đầy đủ giữ nguyên. Bản Word ngày 24/10 giữ nguyên như hồ sơ đã bàn giao; đường dẫn hướng dẫn cũ trong bản đó tra theo [mục lục hiện tại](README.md).

Ảnh cuối hiện ở [data/processed/scan](../data/processed/scan/20261024_161837_753214/), ảnh sửa tay ở [data/processed/manual](../data/processed/manual/corrected_example/). JSON từng ảnh chuyển từ outputs sang metadata trong batch. Đã cập nhật code lưu ảnh, CSV và JSON theo đường dẫn mới; không chạy lại thuật toán. [Biên bản chuyển thư mục](results/week2_storage.json) ghi số lượng ảnh, kiểm tra đường dẫn và số PNG được đối chiếu hash hoặc đọc lại. Snapshot và số liệu đo ngày 24/10 được giữ làm hồ sơ của lần chạy gốc.

## 1 Tóm tắt kết quả tuần 2

Dự án đã có luồng tự động từ ảnh màu đến bốn góc, ảnh PNG đã nắn và thông tin biến đổi hình học. Có chức năng xem gợi ý tự động, chọn lại bốn góc và xoay trang. Toàn bộ 24.889 ảnh SmartDoc hiện có đã được đưa qua bộ quét, không chỉ các ảnh minh họa.

Lượt chạy cuối tạo được **18.571 ảnh PNG**; **6.318 ảnh không tìm được tứ giác phù hợp**. Không có bản ghi lỗi đọc ảnh hoặc lỗi xử lý. Thời gian chạy là **686,76 giây**, khoảng **11 phút 27 giây**, với bốn ảnh xử lý đồng thời trên CPU. Dữ liệu PNG và JSON đầu ra chiếm khoảng **3,69 GiB**; ảnh gốc không bị thay đổi.

Trên toàn bộ validation, **1.931/3.192 ảnh đạt IoU ≥ 0,9**, tương đương **60,49%**, tăng từ **36,90%** của bản đầu. Mean IoU tăng từ **0,3627** lên **0,6521**. Bản hoàn thiện v3 giữ nguyên kết quả hình học của v2, bổ sung kiểm tra, cảnh báo, đầu ra và chạy toàn bộ dữ liệu.

Có thể chuyển sang tuần 3 với một bộ scan nền tảng hoạt động được và cơ chế sửa tay. Tuy nhiên, chưa thể kết luận bộ quét tự động đã tốt trên mọi nền: validation background04 và background05 chưa có ảnh đạt ngưỡng. Chưa đo OCR, hướng chữ tự động hay khả năng nhận biết ảnh thực tế không có giấy.

## 2 Mục tiêu tuần và phạm vi thực hiện

Theo bản đề xuất 6 tuần, tuần 2 cần có hai cách tạo ứng viên khung giấy, kiểm tra và sắp thứ tự góc, nắn phối cảnh trên ảnh gốc, sửa bốn góc và xoay 90 độ. Cần chạy ít nhất 100 ảnh development, xuất PNG, ảnh từng bước trên 10 ca, CSV IoU và thời gian, đồng thời phân tích ca lỗi.

Việc hoàn thiện tập trung vào OpenCV và các phép xử lý ảnh cơ bản. Không huấn luyện mô hình, không dùng mạng nơ-ron để tìm góc, không bổ sung OCR hoặc thuật toán làm phẳng giấy cong trong tuần này. Phần xử lý đồng thời chỉ giúp chạy nhanh nhiều ảnh; không làm thay đổi cách tìm khung.

## 3 Việc đổi dữ liệu và ảnh hưởng tới dự án

### 3.1 Nguồn cũ và lý do điều chỉnh

Code cũ trong Git, commit 836946f, dùng DocCornerDataset trên Hugging Face và lấy 2.000 phần tử đầu của train. Ảnh được đặt ở data/raw/subset_2k, nhãn ở labels.csv. Cách này chưa kiểm tra đủ nhãn, chưa tách ảnh có giấy và không có giấy, chưa chia tập theo trang gốc.

Theo dataset card, is_negative=True có nghĩa là ảnh không có tài liệu; góc trống của mẫu âm là có chủ đích. Tọa độ mẫu dương thuộc dạng chuẩn hóa, nên phải đổi đúng sang pixel trước khi vẽ/nắn. Vì vậy, không kết luận rằng nguồn cũ bị lỗi chỉ vì thấy cột is_negative hoặc ô góc trống. Nguồn: [DocCornerDataset](https://huggingface.co/datasets/mapo80/DocCornerDataset/blob/main/README.md).

Bản đề xuất ngày 23/10/2026 chuyển SmartDoc thành nguồn chính để ưu tiên bài toán tìm khung trang giấy và đánh giá trực tiếp bằng nhãn bốn góc. Đây là thay đổi đã thực hiện khi chuẩn bị tuần 1; tuần 2 sử dụng tiếp nguồn mới. DocCornerDataset chỉ còn là nguồn phụ có thể kiểm tra lại sau.

### 3.2 Dữ liệu mới đang có

Nguồn đang dùng là SmartDoc 2015 Challenge 1, gói frames v2.0.0. Kho nguồn cung cấp ảnh frame và metadata; nhãn cần đọc theo tên góc. Thông tin tải và ghi nguồn xem [SmartDoc](https://github.com/jchazalon/smartdoc15-ch1-dataset).

Kiểm tra cục bộ ghi nhận 24.889 JPEG, kích thước 1920 × 1080, 30 trang gốc, 6 loại tài liệu và 5 nền. Mỗi ảnh có đường dẫn, model_name, bg_name và bốn góc pixel. CSV nguồn đã được đặt tên frames_metadata.csv. Tất cả 24.889 dòng qua bộ kiểm tra tuần 1; không có đường dẫn thiếu hoặc trùng.

Có 6.180 ảnh nền 1, 6.011 nền 2, 5.952 nền 3, 4.169 nền 4 và 2.577 nền 5. Sáu loại gồm datasheet, letter, magazine, paper, patent và tax. Đây là nhiều frame của 30 trang; không phải 24.889 trang nội dung độc lập.

### 3.3 Những điểm thay đổi so với kế hoạch

| Nội dung | Bản đề xuất | Thực tế |
| --- | --- | --- |
| Quy mô SmartDoc | Khoảng 1.500 ảnh | Dùng toàn bộ 24.889 ảnh hợp lệ |
| Trang train / val / test | Gợi ý 21 / 3 / 6 | 21 / 4 / 5, seed 42 |
| Frame train / val / test | Dự kiến 1.050 / 150 / 300 | 17.495 / 3.192 / 4.202 |
| Cách lưu manifest | JSONL và JSON chia tập | CSV cho thao tác pandas; JSON danh sách nhóm được lưu bổ sung |
| Giảm frame gần trùng | Lấy cách nhau theo thời gian | Chưa áp dụng; giữ toàn bộ frame |
| Ảnh tự chụp và ảnh âm | 180 ảnh dương, 60 ảnh âm | Chưa thu thập; đã thống nhất để phần sau |
| Nhãn OCR chi tiết | 36 ảnh | Chưa có |

Số nhóm val/test khác đề xuất do script hiện tại dùng 15% số trang với phép làm tròn: 5 test, 4 validation và phần còn lại là train. Cách chia được giữ cố định để so sánh các phiên bản; không đổi tập nhằm tăng điểm. Mọi frame của cùng model_name, trên mọi nền, đều ở cùng một tập.

CSV là lựa chọn đơn giản cho giai đoạn hiện tại. Những trường như nhãn OCR, độ khó, hướng nội dung và hash từng ảnh chưa được hoàn thiện như schema đầy đủ trong đề xuất. Đã kiểm tra trùng đường dẫn; chưa thể nói đã loại hết ảnh trùng nội dung hoặc gần trùng.

## 4 Các bước xử lý đã triển khai

### 4.1 Giữ ảnh màu và tạo bản nhỏ để tìm khung

Đọc ảnh màu gốc, thu cạnh dài xuống tối đa 1.000 pixel. Tìm góc trên bản nhỏ để giảm tính toán, nhưng nắn bằng ảnh gốc để giữ chi tiết chữ. Khi đưa tọa độ về ảnh gốc, nhân riêng tỷ lệ chiều ngang và dọc sau khi đã làm tròn kích thước.

### 4.2 Tạo hai nguồn ứng viên

Nhánh A chuyển ảnh sang xám, làm mượt Gaussian 5 × 5, tìm cạnh Canny với ngưỡng 20/60, rồi dùng closing 5 × 5 để nối các đoạn cạnh đứt nhỏ. Nhánh B dùng Otsu để chia vùng sáng/tối, rồi closing để tạo vùng ứng viên.

Canny giống như tìm đường viền; Otsu giống như tìm mảng sáng có thể là giấy. Hai cách bổ sung cho nhau. Mảng sáng có thể là nền, còn đường viền có thể thuộc sách hoặc mặt bàn, nên vẫn cần kiểm tra ứng viên.

### 4.3 Tìm và chọn tứ giác

Mỗi nhánh xét tối đa 20 contour lớn. Lấy bao lồi để giảm các chỗ lõm, thử xấp xỉ đa giác với epsilon từ 0,01 đến 0,05 lần chu vi. Chỉ giữ bốn đỉnh tạo thành tứ giác lồi.

Loại vùng quá nhỏ/lớn, sát biên ảnh hoặc có cạnh quá ngắn. Chấm điểm bằng mức cạnh dự đoán bám cạnh Canny, mức gần nhau của diện tích contour và tứ giác, cùng điểm diện tích. Công thức hiện tại là 4 × hỗ trợ cạnh + 2 × độ khớp diện tích + điểm diện tích.

Đây là quy tắc kinh nghiệm dễ giải thích, không phải xác suất đúng. Không yêu cầu bốn góc phải gần 90 độ trong ảnh chụp, vì phối cảnh có thể làm chúng xiên.

### 4.4 Sắp góc và ngăn lỗi lật gương

Sắp bốn điểm quanh tâm theo cùng một chiều; chọn điểm bắt đầu bằng tổng x+y nhỏ nhất, dùng y và x để phân xử khi bằng nhau. Kiểm tra bốn đỉnh khác nhau, hữu hạn, nằm trong ảnh, tứ giác lồi và có diện tích có dấu đúng.

Bản chọn tay ban đầu đã xuất ảnh chữ bị lật gương vì chọn điểm ngược chiều. Đã sửa bằng cách sắp thứ tự trước khi nắn và dùng chính bộ góc đó cho cả ảnh lẫn H/T. Ảnh sửa được lưu riêng; không thay vào số liệu tự động. Xoay 90 độ chỉ đổi hướng trang, không tự chữa được một ảnh đã phản chiếu.

### 4.5 Nắn phối cảnh và lưu ma trận

Ước lượng chiều rộng từ hai cạnh trên/dưới, chiều cao từ hai cạnh trái/phải. getPerspectiveTransform tính ma trận H đưa tứ giác về hình chữ nhật; warpPerspective tạo ảnh màu đã nắn.

H là bảng số 3 × 3 dùng đổi tọa độ từ ảnh gốc sang ảnh nắn. T là phép đổi tọa độ tổng sau khi xoay trang; nếu chưa xoay thì T = H. Việc lưu H/T giúp các tuần sau đưa vị trí dòng chữ về ảnh gốc.

Kích thước nắn chỉ được ước lượng từ ảnh chụp, chưa bảo đảm đúng tỷ lệ vật lý A4. Chưa làm trắng nền, tự xoay đúng hướng chữ, deskew dòng hoặc tăng độ nét.

### 4.6 Cảnh báo và sửa tay khi cần

Nếu ảnh có dấu hiệu mờ hoặc hai vùng khác nhau có điểm gần nhau, trả uncertain. Không tìm được ứng viên thì trả no_candidate. Ảnh uncertain vẫn có PNG để xem, nhưng không được hiểu là đã đúng.

Cửa sổ sửa góc điền dự đoán tự động nếu có. Người dùng chỉ chọn lại khi cần, có thể xoay và lưu. Không yêu cầu bấm tay toàn bộ dataset. Ngưỡng cảnh báo hiện là giá trị khởi đầu; 172 trong 178 ảnh validation bị cảnh báo vẫn đạt IoU, nên cảnh báo này chưa phải bộ phân loại lỗi đáng tin cậy.

## 5 Các thay đổi qua từng phiên bản

| Phiên bản | Thay đổi chính | Số ảnh validation đạt | Tỷ lệ |
| --- | --- | --- | --- |
| v1 | Canny 50/150, chọn tứ giác lồi lớn đầu tiên, epsilon 0,02 | 1.178 / 3.192 | 36,90% |
| v2 | Canny 20/60 + Otsu, bao lồi, nhiều epsilon, nhiều ứng viên và chấm điểm | 1.931 / 3.192 | 60,49% |
| v3 hiện tại | Giữ chọn khung v2; kiểm tra góc, sửa tay an toàn, cảnh báo, PNG/JSON, batch đầy đủ | 1.931 / 3.192 | 60,49% |

v2 tăng thêm 753 ảnh đạt so với v1, tương đương 23,59 điểm phần trăm. Kết quả cuối không được trình bày như một lần tăng độ chính xác nữa: v3 chủ yếu hoàn thiện luồng chạy và khả năng kiểm tra lại.

Code cũ preprocess.py dùng HoughLinesP rồi warpAffine để xoay góc. Phép đó có thể giảm nghiêng nhưng không phục hồi phối cảnh của tờ giấy. Pipeline mới tách rõ tìm bốn góc, nắn phối cảnh và xoay hướng. Hàm denoise cũ thực tế trả nguyên ảnh; không tính đó là thành quả khử nhiễu.

## 6 Cấu hình thực nghiệm

| Tham số | Giá trị |
| --- | --- |
| Cạnh dài ảnh phát hiện | Tối đa 1.000 px |
| Gaussian và closing | 5 × 5 |
| Canny | 20 và 60 |
| Tỷ lệ diện tích ứng viên | 5% đến 90% ảnh nhỏ |
| Contour mỗi nhánh | Tối đa 20 |
| Epsilon | 0,01; 0,02; 0,03; 0,04; 0,05 |
| Cạnh ngắn nhất | 20 px trên ảnh nhỏ |
| Kiểm tra cạnh | 60 điểm mỗi cạnh, khoảng cách ≤ 3 px |
| Hỗ trợ cạnh tối thiểu | 0,25 |
| Cảnh báo mờ | Phương sai Laplacian < 30 |
| Cảnh báo hai ứng viên | Chênh điểm ≤ 0,15; hai vùng có IoU < 0,90 |
| Ngưỡng đạt khi chấm | Polygon IoU ≥ 0,90 |

Cấu hình lưu tại configs/scanner.json. Môi trường thực tế: Python 3.12.14, opencv-python 5.0.0.93, NumPy 2.5.4, pandas 3.1.0, Windows 64-bit. Lượt chạy dùng bốn workers, OpenCV một luồng cho mỗi ảnh, không GPU. Thông tin hệ thống do runtime báo: AMD64 Family 25 Model 116 Stepping 1, AuthenticAMD; chưa xác minh tên thương mại CPU.

## 7 Kết quả chạy toàn bộ dữ liệu

| Tập | Trang gốc | Ảnh | Tạo PNG | Đạt IoU ≥ 0,9 | Tỷ lệ đạt |
| --- | --- | --- | --- | --- | --- |
| train | 21 | 17.495 | 13.299 | 11.186 | 63.94% |
| val | 4 | 3.192 | 2.237 | 1.931 | 60.49% |
| test | 5 | 4.202 | 3.035 | Chưa chấm | Chưa chấm |


“Tạo PNG” chỉ nói rằng bộ quét xuất được ảnh. “Đạt” yêu cầu đúng vùng giấy theo nhãn với IoU ≥ 0,9 và tạo được ảnh nắn. Train là tập đã dùng phát triển, không phải kết quả đánh giá độc lập.

Tập test được chạy suy luận theo cấu hình đã chốt trước lượt chạy. Không tính IoU test, không chọn test làm ảnh minh họa và không dùng test để chỉnh ngưỡng. Việc đã chạy suy luận test được ghi trong báo cáo; chưa có đánh giá cuối kỳ hay OCR trên test.

Trong toàn bộ 24.889 ảnh: 16.890 trạng thái ok, 1.681 uncertain, 6.318 no_candidate. Cảnh báo gồm 1.661 ca mờ và 20 ca ứng viên gần điểm. Một ảnh trạng thái ok vẫn có thể sai giấy; ví dụ bìa sách ở phần phân tích lỗi.

### 7.1 Validation theo từng nền

| Nền validation | Số ảnh | Tìm được | Đạt | Tỷ lệ đạt | IoU TB |
| --- | --- | --- | --- | --- | --- |
| background01 | 797 | 657 | 503 | 63.11% | 0.7542 |
| background02 | 780 | 703 | 698 | 89.49% | 0.8764 |
| background03 | 751 | 732 | 730 | 97.20% | 0.9548 |
| background04 | 515 | 108 | 0 | 0.00% | 0.1547 |
| background05 | 349 | 37 | 0 | 0.00% | 0.0000 |


Background02–03 cho kết quả cao hơn. Background01 còn bỏ sót hoặc chọn vùng bên trong giấy. Background04 có giấy gần màu nền, nhiều trường hợp khó tách mép. Background05 có nhiều vật thể/che khuất và khung sách cạnh tranh. Đây là nhận xét từ số liệu và ảnh minh họa, chưa phải gán nguyên nhân thủ công cho mọi ca thất bại.

Validation có 955 ảnh không tìm được giấy và 306 ảnh có khung nhưng IoU dưới 0,9. Tổng 1.261 ca chưa đạt phải được giữ trong mẫu số; không chỉ tính tỷ lệ trên 2.237 ảnh tìm được tứ giác.

### 7.2 Train theo từng nền

| Nền train | Số ảnh | Đạt | Tỷ lệ đạt |
| --- | --- | --- | --- |
| background01 | 4318 | 3198 | 74.06% |
| background02 | 4225 | 4006 | 94.82% |
| background03 | 4142 | 3958 | 95.56% |
| background04 | 2996 | 24 | 0.80% |
| background05 | 1814 | 0 | 0.00% |


Ngay trên train, nền 4 chỉ có 24/2.996 ảnh đạt và nền 5 chưa có ảnh đạt. Vì vậy, vấn đề là giới hạn của cách phát hiện hiện tại; tăng số frame chạy không tự làm thuật toán tốt hơn.

### 7.3 Thời gian xử lý

Trên validation trong lượt chạy bốn workers, thời gian tìm góc trung vị là 52,93 ms, p95 là 85,04 ms. Nắn ảnh trung vị 3,50 ms, p95 6,73 ms, tính trên ảnh nắn được. Tổng đọc ảnh, tìm góc, nắn và ghi PNG trung vị 92,08 ms, p95 142,93 ms.

p95 nghĩa là khoảng 95% mẫu có thời gian không vượt giá trị đó. Thời gian từng ảnh là thời gian thực khi chạy đồng thời, nên không cộng trực tiếp để suy ra thời gian cả batch. Tổng cả batch 686,76 giây bao gồm ghi CSV/JSON. Không tách warm-up; không so tốc độ trực tiếp với lần chạy v1/v2 có điều kiện khác.

## 8 Minh họa và phân tích lỗi

Đã lưu 10 ca validation gồm 5 đạt và 5 lỗi, có ảnh đầu vào, cạnh, mask, ứng viên, khung chọn và ảnh nắn nếu tạo được. Khung xanh lá là nhãn chuẩn, khung đỏ là dự đoán; các số 0–3 thể hiện thứ tự góc. Mười ca này dùng giải thích bằng mắt, không thay cho đánh giá trên toàn bộ dữ liệu.

| Ca | Đường dẫn trong SmartDoc | IoU | Nhận xét sau xem ảnh |
| --- | --- | --- | --- |
| 01_good | background02/tax002/frame_0089.jpeg | 0.9612 | Khung sát bốn mép giấy; vẫn còn sai số nhỏ. |
| 02_good | background03/patent003/frame_0080.jpeg | 0.9864 | Giấy tương phản với nền, dự đoán bám sát nhãn. |
| 03_good | background01/patent003/frame_0140.jpeg | 0.9918 | Giấy nghiêng nhưng các cạnh còn rõ. |
| 04_good | background03/tax002/frame_0100.jpeg | 0.9829 | Khung đạt; chữ mờ vẫn là vấn đề riêng. |
| 05_good | background02/patent003/frame_0109.jpeg | 0.9613 | Khung gần trùng nhãn dù có phối cảnh. |
| 06_failed | background01/tax002/frame_0014.jpeg | 0.7616 | Chọn vùng nhỏ bên trong tờ giấy, bỏ một phần lề. |
| 07_failed | background02/patent003/frame_0093.jpeg | 0.0000 | Không tìm được khung; giấy gần màu mặt bàn, cần xem cạnh/mask. |
| 08_failed | background05/patent003/frame_0021.jpeg | 0.0000 | Chọn nhầm bìa sách bên trái, hoàn toàn khác tờ giấy cần quét. |
| 09_failed | background05/letter001/frame_0076.jpeg | 0.0000 | Không tìm được khung; giấy bị đồ vật và dây điện che. |
| 10_failed | background04/tax002/frame_0006.jpeg | 0.0000 | Không tìm được khung; màu giấy và nền gần nhau. |


Nhóm lỗi thiếu cạnh/không tìm được ứng viên được thể hiện ở ca 07, 09 và 10. Nhóm chọn nhầm vùng gồm ca 06 (vùng trong giấy) và ca 08 (bìa sách). Ca chọn tay cũ minh họa lỗi thứ tự góc gây lật gương. Góc ngoài ảnh được kiểm tra bằng dữ liệu kiểm thử tổng hợp; không ghi là lỗi đã quan sát trong batch cuối.

Ảnh background04/letter001/frame_0001 được khôi phục từ bốn điểm người dùng đã bấm, sắp lại thứ tự và xoay để chữ đúng chiều. Vùng chọn tay có IoU khoảng 0,9766 nhưng bản cũ vẫn lật chữ, cho thấy IoU cao chưa đủ để đánh giá chất lượng ảnh scan. Không lấy góc nhãn chuẩn để tạo bản sửa này.

## 9 Kiểm tra độ ổn định và khả năng tái lập

Sáu kiểm tra tự động đã đạt: màu ở góc và ma trận qua bốn hướng xoay; sắp lại điểm bấm ngược; từ chối góc trùng/chéo/ngoài ảnh/NaN/suy biến; ảnh trống và đầu vào không hợp lệ; IoU của hai hình có giao biết trước; giữ thất bại trong mẫu số và loại test khỏi chấm điểm.

Ảnh trống dùng kiểm thử là ảnh đen và trắng tổng hợp. Việc không crash trên hai ảnh này không thay thế đánh giá trên tập ảnh âm thực tế, và không chứng minh tỷ lệ báo nhầm đạt mục tiêu 10%.

Bản chạy lưu một dòng CSV và một JSON cho mỗi ảnh; PNG chỉ có khi nắn thành công. Kiểm tra độc lập đối chiếu đường dẫn với manifest, kiểm tra rò rỉ model_name, đọc lại PNG và kiểm tra H/T. Kết quả kiểm tra chi tiết được lưu tại docs/results/week2_verification.json.

Mã phiên bản của lượt chạy: **20261024_161837_753214**. Hash SHA-256 detect.py: 4e550c59419d9ea290b1a22f4f910d9476ab3ebecbf127d38416da10bd3a2644. Bản sao nguồn và cấu hình nằm trong thư mục batch. Week 2 hiện là thay đổi cục bộ chưa commit; commit gần nhất trước tuần 2 là 50fab80. Không ghi một commit hoặc tag chưa tồn tại.

## 10 Dọn cấu trúc và các file bàn giao

Source scanner chỉ còn năm file có nhiệm vụ rõ: detect.py tìm góc, geometry.py xử lý hình học, scan.py chạy batch, manual_scan.py tương tác sửa góc, evaluate.py chấm và tạo minh họa. Đã bỏ các đoạn chạy thử đơn lẻ trong detect.py và geometry.py.

Đã xóa thư mục kết quả thử geometry, detection, scan_runs, lượt evaluation chưa hoàn tất/trùng và hai batch kiểm tra 20 ảnh. Giữ hai baseline có số liệu để chứng minh thay đổi; giữ ảnh chọn tay bị lật trong history để đối chiếu với bản sửa. Dữ liệu raw và manifest được giữ nguyên.

| Nơi lưu | Nội dung |
| --- | --- |
| configs/scanner.json | Ngưỡng thuật toán |
| docs/week2_report.md | Báo cáo chi tiết dạng văn bản |
| docs/guides/data_sources.md | Lịch sử đổi nguồn và khác biệt với kế hoạch |
| docs/guides/phase2_scanner.md | Hướng dẫn chạy và đọc đầu ra |
| docs/results/ | Chỉ số tổng hợp, danh sách nhóm, chỉ mục minh họa, kiểm tra |
| data/processed/scan/20261024_161837_753214/ | 18.571 PNG đã nắn tự động |
| data/processed/manual/corrected_example/ | Ảnh chọn tay đã sửa thứ tự và hướng |
| artifacts/week2/batch/20261024_161837_753214/ | JSON trong metadata, CSV, snapshot và minh họa |
| artifacts/week2/manual/corrected_example/ | corners.json ghi góc, xoay và đường dẫn ảnh sửa tay |
| artifacts/week2/history.zip | Baseline v1, v2 và bằng chứng cũ đã nén |
| tests/test_scanner.py | Sáu kiểm tra quan trọng |

requirements.txt chỉ giữ ba thư viện đang dùng và khóa phiên bản đã chạy. Các thư viện dành cho OCR sẽ bổ sung khi triển khai OCR. Không gỡ các gói đang cài khỏi venv; chỉ làm rõ yêu cầu cài trên máy mới.

## 11 Hướng dẫn chạy lại và sử dụng kết quả

Tại thư mục gốc, kích hoạt venv rồi chạy:

~~~powershell
python -X utf8 -u src/document_scanner/scanner/scan.py --split all --workers 4
python -X utf8 src/document_scanner/scanner/evaluate.py --examples
python -X utf8 -B -m unittest discover -s tests -v
~~~

Người mới clone cần tải SmartDoc, cài requirements và chạy các bước tuần 1 theo README trước. Nếu chỉ phát triển tuần 3, có thể dùng --split dev hoặc dùng ngay ảnh nắn của lượt hiện tại. Không cần chạy lại toàn bộ mỗi lần mở dự án.

Đọc evaluation/results_dev.csv để chọn các ảnh đạt trong train/validation cho thử nghiệm xử lý chữ. Việc chọn theo nhãn chỉ dùng tạo nhóm thí nghiệm có kiểm soát; ứng dụng thực tế không có nhãn, nên vẫn phải chịu lỗi đầu vào của detector. Đánh giá OCR trên crop tốt phải báo riêng với đánh giá toàn pipeline.

Khi cần sửa một ảnh, chạy manual_scan.py với --image; dùng gợi ý tự động hoặc chọn lại bốn góc, xem trước, xoay và lưu. Không cần sửa tay hàng nghìn ảnh để kết thúc tuần 2.

## 12 Đánh giá mức hoàn thành và việc tuần 3

| Yêu cầu tuần 2 | Hiện trạng |
| --- | --- |
| Hai nhánh ứng viên và chấm tứ giác | Đã thực hiện |
| Nắn ảnh gốc, PNG và H/T | Đã thực hiện |
| Chọn/sửa bốn góc và xoay 90 độ | Đã thực hiện; đã sửa lỗi lật gương |
| Batch ít nhất 100 ảnh development | Đã vượt: 20.687 train+val; thêm 4.202 test suy luận |
| Mười ca gồm tốt và lỗi | Đã lưu 5 tốt, 5 lỗi trên validation |
| CSV IoU và thời gian | Có đủ ca đạt và thất bại |
| Ổn định trước đầu vào/hình học sai | Sáu kiểm tra đạt; batch đầy đủ không lỗi xử lý |
| Mục tiêu ≥80% trên validation dễ | Chưa chứng minh: chưa khóa nhóm dễ từ trước; toàn val đạt 60,49% |
| Ảnh âm thực tế và OCR tiếng Việt | Chưa thực hiện, ngoài kết quả tuần 2 hiện tại |

Không chọn riêng nền tốt sau khi xem kết quả rồi gọi đó là “validation dễ đã đạt mục tiêu”. Có thể báo riêng từng nền như trên, cùng giới hạn của tập đánh giá.

Ba việc ưu tiên tuần 3: so sánh ảnh màu/xám với các cách làm rõ đơn giản trên cùng ID; tách dòng và kiểm tra không làm mất dấu/cắt mất chữ; bổ sung ảnh tiếng Việt và ảnh không giấy theo kế hoạch. Giữ riêng đầu ra tự động và sửa tay khi đánh giá. Chưa mở rộng sang mô hình phức tạp hoặc huấn luyện từ đầu.

**Kết luận:** Tuần 2 đã có bản scan nền tảng chạy đầy đủ, có bằng chứng định lượng và khả năng sửa lỗi để tiếp tục tuần 3. Chất lượng tự động còn hạn chế ở nền khó; cần báo đúng 60,49% validation, không khẳng định toàn bộ 18.571 PNG đều là trang scan đúng.

## 13 Tài liệu và bằng chứng

1. Bản đề xuất De_xuat_Project1_6_tuan.docx, điều chỉnh ngày 23/10/2026.
2. [Nguồn SmartDoc](https://github.com/jchazalon/smartdoc15-ch1-dataset) và metadata cục bộ.
3. [Schema DocCornerDataset](https://huggingface.co/datasets/mapo80/DocCornerDataset/blob/main/README.md).
4. Lịch sử Git 836946f, 4c506df, 5302ac7 và 50fab80; các bản baseline giữ trong history.
5. [Bảng số liệu cuối](results/week2_metrics.json), [theo nền](results/week2_by_background.csv), [chia nhóm](results/week2_splits.json), [kiểm tra đầu ra](results/week2_verification.json).

## Phụ lục ảnh minh họa trên máy

Các hình dưới đây và ảnh gốc chỉ lưu cục bộ, không đưa lên GitHub. Khung xanh là nhãn chuẩn, khung đỏ là dự đoán. Mã ca khớp bảng phân tích ở mục 8.

### Năm ca tìm đúng vùng giấy

![Năm ca đạt ngưỡng IoU](../artifacts/week2/report/figures/good_cases.jpg)

### Năm ca chưa đạt

![Năm ca lỗi gồm chọn sai vùng và không tìm được khung](../artifacts/week2/report/figures/failed_cases.jpg)

### Sửa thứ tự góc của ảnh chọn tay

![Trái là bản lật gương và phải là bản đã sửa](../artifacts/week2/report/figures/manual_correction.jpg)

Bản sửa dùng lại tọa độ người dùng đã chọn, sắp thứ tự và xoay để chữ đúng chiều. Không đưa ca này vào điểm tự động.
