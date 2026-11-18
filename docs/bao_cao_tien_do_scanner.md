# Báo cáo tiến độ Document Scanner

**Sinh viên:** Nguyễn Đức Nguyên — **MSSV:** 202416305  
**Đơn vị:** Đại học Bách khoa Hà Nội — **Cập nhật:** 19/11/2026

Báo cáo trình bày kết quả định vị tài liệu trên SmartDoc và phần scan một ảnh vừa được hoàn thiện thêm: chọn vùng nội dung chính, nắn phối cảnh và tăng độ rõ chữ. Luồng scan có thể chạy riêng; pipeline hiện đã gọi chung scanner trước khi chuyển ảnh sang OCR. Các thử nghiệm ảnh mới còn ít, chưa đủ để kết luận scanner hoạt động tốt trên mọi điều kiện.

## Kết quả chính và phạm vi đánh giá

Em đã xây dựng và cải thiện scanner dựa trên Canny/Otsu, phân tích các trường hợp thất bại, sau đó tích hợp mô hình DocAligner FastViT-T8 đã huấn luyện sẵn để dự đoán bốn góc tài liệu. DocAligner hiện là phương pháp chính; scanner truyền thống được giữ để đối chứng. OCR tiếng Anh tiếp tục dùng Tesseract/FUNSD.

Hai phương pháp đã chạy detect trên cùng 24.889 ảnh SmartDoc. Bộ dữ liệu gồm 30 tài liệu gốc trên 5 nền, chia theo tài liệu thành train 17.495 ảnh, validation 3.192 ảnh và test 4.202 ảnh. Nhãn chỉ dùng chấm điểm sau dự đoán; không dùng để chọn khung khi xử lý ảnh.

| Chỉ số | Canny/Otsu cải tiến | DocAligner FastViT-T8 |
| --- | ---: | ---: |
| Trả được bốn góc trên toàn bộ dữ liệu | 20.503/24.889 | 24.889/24.889 |
| Train đạt IoU ≥ 0,9 | 13.366/17.495 (76,40%) | 17.493/17.495 (99,99%) |
| Validation đạt IoU ≥ 0,9 | 2.424/3.192 (75,94%) | 3.192/3.192 (100%) |
| IoU trung bình validation | 0,7503 | 0,9893 |

IoU là diện tích giao chia diện tích hợp giữa khung dự đoán và nhãn thật. Ảnh không trả được khung tính IoU bằng 0. Các tỷ lệ trên là đánh giá detect; chưa nắn/lưu toàn bộ 24.889 ảnh và chưa đánh giá OCR toàn bộ. Test chỉ lưu dự đoán, chưa chấm IoU.

| Nền trên validation | Canny/Otsu cải tiến đạt | DocAligner đạt |
| --- | ---: | ---: |
| background01 | 782/797 | 797/797 |
| background02 | 747/780 | 780/780 |
| background03 | 746/751 | 751/751 |
| background04 | 149/515 | 515/515 |
| background05 | 0/349 | 349/349 |

**Giới hạn cần nêu:** chưa xác minh dữ liệu huấn luyện sẵn của DocAligner có trùng SmartDoc hay không. Kết quả cao trên SmartDoc chưa chứng minh khả năng tổng quát trên tài liệu mới hoặc khả năng từ chối ảnh không có giấy. Em chưa tự huấn luyện hoặc tinh chỉnh mô hình này.

<!-- PAGEBREAK -->

## Phương pháp đã xây dựng và tích hợp

### Scanner truyền thống làm đối chứng

Mã ở `src/document_scanner/scanner/classic.py`. Ảnh được thu nhỏ cạnh dài tối đa 1.000 pixel, làm xám và làm mượt. Canny tìm cạnh, Otsu tách vùng sáng/tối; phép closing nối các khe nhỏ. Từ contour, chương trình lấy convex hull và thử xấp xỉ thành tứ giác.

Ứng viên được lọc theo tỷ lệ diện tích, vị trí so với biên ảnh, độ dài cạnh và độ bám cạnh Canny; điểm tổng hợp dùng để chọn khung. Điểm này là quy tắc so sánh, không phải xác suất khung đúng.

Sau phân tích lỗi, em bổ sung nhánh Canny ngưỡng thấp trên ảnh xám và kênh Lab b để tìm thêm cạnh giấy nhạt. Các nhánh mới yêu cầu bằng chứng trên từng cạnh. Khung điểm thấp bị từ chối, khung yếu được gắn cảnh báo. Validation tăng từ 60,49% trước cải tiến lên 75,94%; nền 4–5 vẫn còn khó.

### DocAligner dự đoán bốn góc bằng học sâu

Mã ở `src/document_scanner/scanner/docaligner.py`. Mô hình FastViT-T8 đã huấn luyện sẵn được tải từ DocsaidLab và chạy ONNX bằng OpenCV, không cần PyTorch trong môi trường suy luận hiện tại.

1. Giữ ảnh BGR, resize 256 × 256 và chuẩn hóa chia 255.
2. Mô hình tạo bốn heatmap, mỗi heatmap thể hiện vị trí một góc.
3. Loại giá trị dưới 0,3; áp dụng Otsu trên từng heatmap.
4. Lấy vùng lớn nhất, tính trọng tâm để ra tọa độ góc trên ảnh gốc.
5. Sắp thứ tự, kiểm tra bốn góc và chuyển sang nắn phối cảnh.

DocAligner không dùng Canny để tìm góc. Otsu ở đây xử lý đầu ra mạng, khác với Otsu trên ảnh của scanner truyền thống. Adapter theo các bước upstream công bố; chưa kiểm chứng tương đương số học với toàn bộ gói Python chính thức.

### Scanner dùng chung cho hai cách chạy

`scan_image.py` cung cấp hàm `scan_document()`. Chạy riêng sẽ nhận ảnh và trả ảnh scan cùng thông tin xử lý, không xuất văn bản OCR cuối. `pipeline.py` gọi chính hàm này với đầu vào ảnh chụp rồi chuyển ảnh kết quả cho bộ nhận dạng chữ.

Luồng scan hiện tại: ảnh → DocAligner → nắn nếu góc hợp lệ → chọn vùng chữ chính nếu thiếu khung hoặc ảnh nắn không đạt kiểm tra → kiểm tra chất lượng → làm rõ ảnh → lưu kết quả. Đây là luồng đã tích hợp trong scanner, không chỉ là cách xử lý riêng của pipeline OCR.

Nhánh dự phòng vẫn gọi Tesseract để lấy vị trí các hộp từ. Các hộp từ đóng vai trò gợi ý vùng nội dung; văn bản nhận dạng ở bước này chưa phải kết quả OCR cuối. Canny/Hough còn dùng để ước lượng góc nghiêng nhỏ; Otsu hỗ trợ mặt nạ nét chữ và giấy. Nhánh Canny/Otsu truyền thống vẫn được giữ riêng trong `classic.py`.

Phần em thực hiện gồm xây dựng phương pháp truyền thống, tích hợp mô hình có sẵn, xử lý đầu ra, nối scanner/OCR và đánh giá so sánh. Không trình bày DocAligner là mô hình do em tự huấn luyện.

<!-- PAGEBREAK -->

## Minh họa các trường hợp khó

Các cặp dưới dùng tọa độ đã lưu trên cùng ảnh. Bên trái là Canny/Otsu cải tiến, bên phải là DocAligner. Đường xanh lá là nhãn thật; đường đỏ là dự đoán. Đây là ví dụ minh họa được chọn để thể hiện lỗi, không thay cho thống kê toàn bộ dữ liệu.

![Chọn nhầm sách](../artifacts/scanner_dev/comparison/01_wrong_book_corners.jpg)

**Hình 1. Chọn nhầm bìa sách.** Classic chọn sách thay vì tờ giấy, IoU = 0; DocAligner bám khung giấy với IoU = 0,9920. Góc bị che cần được mô hình suy ra, không phục hồi được chữ đã bị vật thể che.

![Giấy gần màu nền](../artifacts/scanner_dev/comparison/03_paper_similar_to_table_corners.jpg)

**Hình 2. Giấy gần màu bàn.** Classic không trả khung; DocAligner có IoU = 0,9915. Đây là một điểm yếu của việc dựa chủ yếu vào biên và ngưỡng hóa trên ảnh.

![Khung bên trong mất lề](../artifacts/scanner_dev/comparison/04_inner_frame_lost_margin_corners.jpg)

**Hình 3. Khung bên trong làm mất lề.** Classic có IoU = 0,6416; DocAligner đạt 0,9922. Ảnh sau nắn của các ca này nằm cùng thư mục, tên kết thúc bằng `_scans.jpg`.

<!-- PAGEBREAK -->

## Những phần scan được bổ sung

### Chọn vùng tài liệu chính khi thiếu bốn góc

DocAligner có thể không trả được tứ giác khi giấy bị cắt khỏi ảnh, nền phức tạp hoặc nhiều tờ chồng nhau. Khi đó `content_scan.py` thử chỉnh nghiêng nhỏ, lấy hộp từ từ Tesseract và tìm các cụm nét chữ bằng xử lý ảnh. Chương trình chọn vùng chữ có diện tích lớn nhất trong các vùng có đủ bằng chứng chữ, thay vì lấy hình chữ nhật bao tất cả từ trên toàn ảnh.

Cụm chữ phải có hộp từ đáng tin hỗ trợ. Các vùng gần nhau được gom lại và thêm lề nhỏ để giảm cắt mất dấu. Nếu hai vùng có diện tích gần nhau, kết quả được gắn cảnh báo để xem lại. Quy tắc này giúp giảm lấy giấy phụ nhưng chưa hiểu ngữ nghĩa đâu là trang người dùng muốn chọn.

### Nắn phối cảnh cho vùng chữ dự phòng

Sau khi tìm vùng chính, scanner thử tìm tứ giác giấy trong vùng đó. Chỉ nắn thêm khi hình học phù hợp và các kiểm tra giữ hộp từ, nét chữ đạt yêu cầu. Tọa độ được đổi về ảnh gốc rồi nắn từ ảnh gốc một lần để hạn chế mờ do nội suy nhiều lần. Nếu không đủ bằng chứng, chương trình giữ crop đã chỉnh nghiêng.

Các tỷ lệ giữ hộp từ và nét chữ chỉ là tín hiệu kiểm tra nội bộ, không phải nhãn thật hoặc độ chính xác OCR. Khung dự phòng là khung ước lượng theo nội dung, không được coi như bốn góc giấy đã xác minh. Góc ngoài ảnh được đệm trắng và cảnh báo; chữ nằm ngoài ảnh chụp không thể phục hồi.

### Kiểm tra chất lượng và làm rõ chữ

`appearance.py` kiểm tra ảnh trước tăng cường: kích thước, tỷ lệ vùng giấy, lượng nét chữ và độ nét. Ảnh trắng, quá tối hoặc quá mờ có thể bị từ chối. Đây là bộ lọc theo quy tắc cho giấy sáng có chữ, chưa thay thế bộ phân loại ảnh không có tài liệu.

Ảnh đạt kiểm tra được cân bằng nền sáng trên kênh sáng Lab, tăng tương phản nét chữ và làm sắc nhẹ. Màu mực được giữ ở vùng chữ; phần nền ngoài mặt nạ được làm trắng. Cấu hình nằm trong `configs/scan.json`, hiện dùng mức làm sắc 0,45 và sigma 0,7. Ảnh trước tăng cường vẫn được lưu để đối chiếu.

Mục tiêu là chữ dễ nhìn hơn như mẫu CamScanner người dùng đưa, chưa khẳng định chất lượng tương đương ứng dụng đó. Bộ lọc có thể làm mất nét quá nhạt, đường kẻ hoặc chi tiết hình vẽ. Nắn phối cảnh chưa xử lý cong trang và chưa tự xác định mọi trường hợp xoay ngược 90/180 độ theo nghĩa của chữ.

<!-- PAGEBREAK -->

## Minh họa trên ảnh chụp thực tế mới

![Đối chiếu ảnh trước và sau cải thiện](../artifacts/history/scan_report_20261118/comparison.jpg)

**Hình 4. Ảnh viết tay có nhiều tờ giấy.** Bên trái là kết quả trước bổ sung nắn phối cảnh cho vùng chữ; bên phải là kết quả sau cải thiện. Ảnh lưu làm mốc trước/sau; mức làm sắc hiện tại đã được chỉnh nhẹ thêm sau mốc này.

### Kết quả quan sát trên hai ảnh

Với `anh_viet.jpg`, DocAligner trả được khung và scanner nắn theo bốn góc. Với `anh_2.jpg`, điểm detector khoảng 0,0374 và không có khung được chấp nhận; nhánh dự phòng chọn vùng chữ chính, ước lượng tứ giác và nắn lại. Sau xử lý, nền sáng hơn, chữ đậm hơn và vùng chính thẳng hơn so với kết quả trước.

Ảnh `anh_2.jpg` bị thiếu một phần trang ngay từ lúc chụp. Kết quả vẫn có cảnh báo khung ước lượng và đệm trắng ngoài ảnh. Một số mép giấy phụ hoặc đường viền còn có thể xuất hiện; chưa đạt mục tiêu loại sạch mọi phần thừa. Người dùng cần kiểm tra tiêu đề, dấu, chân trang và nét mảnh trên ảnh màu đối chiếu.

Đây là hai ca thử chức năng, chưa có nhãn bốn góc hoặc TXT chuẩn. Vì vậy chưa tính IoU, tỷ lệ giữ nội dung thật hoặc CER/WER cho hai ảnh này. Điểm SmartDoc ở đầu báo cáo là của lượt detect đã lưu trước các thay đổi vùng chữ và tăng cường ảnh; chưa chạy lại 24.889 ảnh với luồng scan mới.

<!-- PAGEBREAK -->

## Kết quả còn hạn chế và tình hình OCR

So với classic, DocAligner có thêm 4.128 ảnh train đạt ngưỡng và một ảnh cũ đạt bị giảm; validation thêm 768 ảnh đạt và không mất ảnh đạt cũ. Hai ảnh train DocAligner chưa đạt là `background02/patent004/frame_0107.jpeg` (IoU 0,5060) và `background02/tax004/frame_0166.jpeg` (0,5157).

Lượt full detect DocAligner mất khoảng 56 phút; classic khoảng 14 phút. Hai lượt có thể khác tải máy nên chưa dùng làm phép đo tốc độ có kiểm soát. Trạng thái `uncertain` của DocAligner trong lượt thử cũ là cờ thử nghiệm. Mã hiện tại giữ cảnh báo `document_presence_not_verified` vì chưa đánh giá đầy đủ ảnh âm tính, không phải vì tất cả khung có IoU thấp.

### OCR tiếng Anh và vùng chữ dự phòng

Tesseract với mô hình `funsd_eng` đã tinh chỉnh vẫn là bộ đọc tiếng Anh. DocAligner chỉ thay phần tìm góc, không phải mô hình nhận dạng chữ. Lượt đo FUNSD trước đây có CER 24,61% và WER 48,97% trên 50 trang test, theo đánh giá trong các vùng nhãn; tập này đã được dùng trong quá trình phát triển nên không xem là đánh giá độc lập cuối cùng.

Đã thử DBNet cho vùng chữ dự phòng trên 54 ảnh. Trên 30 trang FUNSD, cách Tesseract giữ đủ 4.595/4.616 hộp từ (99,55%), bản DBNet + gom cụm giữ 4.092/4.616 (88,65%). Tiêu chí giữ đủ là ít nhất 98% diện tích hộp từ nằm trong crop; ảnh không tạo được crop tính giữ 0 hộp từ. Vì còn bỏ sót chữ nhỏ và chân trang, DBNet không được chọn và mã thử đã được dọn.

Ở lượt thử trước khi bổ sung bộ làm rõ ảnh hiện tại, đã chạy pipeline với `anh.jpg` và văn bản chuẩn:

| Scanner trước OCR | CER | WER |
| --- | ---: | ---: |
| Canny/Otsu cải tiến | 2,64% | 5,80% |
| DocAligner | 3,02% | 4,35% |

Các số liệu OCR trên là mốc lịch sử, chưa đo lại sau thay đổi scanner và bộ làm rõ ảnh. Kết quả một ảnh có hai chỉ số trái chiều, không đủ để kết luận OCR phương pháp nào tốt hơn. IoU khung trang không đo độ nét, khả năng giữ dấu hay thứ tự đọc. OCR tiếng Việt và ảnh chụp mới chưa được đánh giá đầy đủ. FUNSD tiếng Anh không chứng minh khả năng đọc chữ viết tay tiếng Việt hoặc công thức toán trong hai ảnh mới.

### Việc cần làm tiếp

1. Chuẩn bị tập ảnh mới có tài liệu tiếng Việt/Anh, nền khó và ảnh không có giấy.
2. Gán bốn góc cho ảnh có tài liệu; quy định rõ sách, nhiều tờ giấy và vật che được xử lý thế nào.
3. Đo IoU, tỷ lệ không tìm thấy và nhận nhầm; kiểm tra mất tiêu đề, chân trang và dấu tiếng Việt.
4. Dùng một số ảnh có TXT chuẩn để đánh giá OCR sau cắt/nắn; chưa tự động chọn cấu hình theo nhãn test.

<!-- PAGEBREAK -->

## Quản lý dự án và cách tái hiện

Đã gộp mô hình mới vào scanner chính, giữ classic làm đối chứng và gỡ các script thử không còn dùng. `docs/results/` chỉ giữ bảng so sánh chính và danh sách 200 ảnh phát triển. Hồ sơ cũ ở `docs/history/`; hai lượt detect toàn bộ và ảnh so sánh được giữ riêng. Sau xác nhận của người dùng, đã xóa 258 file thử và mô hình DBNet không dùng, khoảng 100 MB.

Sau thay đổi dùng chung scanner và chống tạo kết quả lặp, 51 kiểm thử đã đạt. Sau lần chỉnh làm sắc nhẹ gần nhất, 11 kiểm thử liên quan đã đạt; chưa chạy lại toàn bộ bộ kiểm thử sau lần chỉnh này. Kiểm thử bao gồm hình học, chọn cụm chữ, kiểm tra ảnh kém chất lượng và quản lý đầu ra; không thay cho kiểm thử thực tế độc lập.

### Chạy scan riêng

Chạy từ gốc dự án với venv đã kích hoạt:

```powershell
python -X utf8 src/document_scanner/scanner/scan_image.py --image "data/raw/thu_detect/anh_2.jpg"
```

Ảnh cuối nằm ở `data/processed/scan/image_anh_2_b016f626/scan.png`. Cùng thư mục có `scan_color.png` để xem trước tăng cường và `region.png` để kiểm tra vùng chọn. Metadata nằm ở `artifacts/scans/image_anh_2_b016f626/metadata.json`.

Mặc định mỗi đường dẫn ảnh có một thư mục kết quả ổn định, chạy lại cập nhật các file do scanner quản lý. Các ghi chú riêng được giữ. Dùng `--new-run` khi chủ động muốn tạo lịch sử mới. Quy tắc này áp dụng cho lệnh scan một ảnh; pipeline OCR vẫn tạo thư mục theo từng lượt chạy.

Các kết quả scan thử trùng đã được dọn, giữ mốc trước/sau trong `artifacts/history/scan_report_20261118/`. Dữ liệu gốc, trọng số và hai lượt benchmark toàn bộ vẫn được giữ.

### Nơi lưu kết quả để kiểm chứng

| Nội dung | Đường dẫn trong dự án |
| --- | --- |
| Bảng so sánh chính | `docs/results/scanner_comparison.csv` |
| Tập phát triển cố định | `docs/results/scanner_dev_manifest.csv` |
| Detect toàn bộ bằng classic | `artifacts/scanner_dev/full_detection_v1/` |
| Detect toàn bộ bằng DocAligner | `artifacts/scanner_dev/docaligner_t8_full/` |
| Ảnh so sánh SmartDoc | `artifacts/scanner_dev/comparison/` |
| Ảnh scan hiện tại | `data/processed/scan/image_<tên>_<hash>/` |

Các lượt benchmark có `results.csv`, `summary.csv`, `run_info.json` và snapshot nguồn; chỉ kết luận từ lượt có `complete: true`. Ảnh, dữ liệu gốc, trọng số và artifacts lưu trên máy; GitHub giữ mã và số liệu tổng hợp. Hướng dẫn vận hành ở README, lịch việc tiếp theo ở kế hoạch 7 ngày.

<!-- PAGEBREAK -->

## Kết nối scanner với OCR và bước tiếp theo

### Luồng hiện có

Chạy scan riêng: ảnh chụp → `scan_document()` → ảnh scan và metadata.

Chạy toàn pipeline: ảnh chụp → cùng `scan_document()` → `recognize_image()` → ảnh scan, văn bản và metadata.

Scanner đã tách được trách nhiệm khỏi nhận dạng chữ. Sau này có thể cải thiện hoặc thay bộ OCR trong `ocr/` mà vẫn dùng ảnh đầu ra scanner. Pipeline hiện có kiểm tra nội dung bổ sung qua `check_content=True`; lệnh scan riêng mặc định không bật bước này, vì vậy hai cách chạy có thể chọn crop khác nhau trên một số ảnh khó.

### Lệnh chạy cả scan và OCR

```powershell
python -X utf8 src/document_scanner/pipeline.py --image "data/raw/thu_ocr/anh.jpg"
```

Kết quả ở `data/processed/pipeline/<run_id>/`: `scan.png`, `text.txt`, `metadata.json`; có thêm `evaluation.json` khi cung cấp `--reference`. Lệnh này dùng bộ OCR tiếng Anh hiện tại, không phải OCR tiếng Việt viết tay hoàn chỉnh.

### Chỉ OCR ảnh đã scan

```powershell
python -X utf8 src/document_scanner/pipeline.py --image "data/processed/scan/image_anh_2_b016f626/scan.png" --input-type scan
```

Lệnh trên bỏ qua scanner và dùng đúng ảnh scan đã chọn làm đầu vào nhận dạng. Có thể dùng để kiểm tra kết nối kỹ thuật; nội dung viết tay tiếng Việt và công thức trong ảnh này chưa phù hợp để kết luận chất lượng bộ OCR tiếng Anh.

Trước khi chọn ảnh tăng cường làm đầu vào OCR mặc định lâu dài, cần so sánh cùng bộ TXT chuẩn giữa ảnh màu sau nắn và ảnh tăng cường. Chữ nhìn rõ hơn chưa đảm bảo CER/WER tốt hơn. Giai đoạn tiếp theo ưu tiên kiểm thử vùng cắt, sau đó đánh giá lại OCR tiếng Anh và mở rộng tiếng Việt.

### Nguồn mô hình và kết luận

Nguồn: [DocsaidLab DocAligner](https://github.com/DocsaidLab/DocAligner); tiền/hậu xử lý tham khảo `docaligner/heatmap_reg/infer.py` của upstream. Tên mô hình là heatmap FastViT-T8, không phải mô hình DBNet tìm chữ và không phải mô hình OCR.

DocAligner cải thiện rõ kết quả định vị khung trang trên SmartDoc và đã được chọn làm scanner chính để tiếp tục kiểm thử. Canny/Otsu được giữ để thể hiện quá trình phát triển và làm mốc so sánh. Bước tiếp theo ưu tiên kiểm thử dữ liệu mới và ảnh không có tài liệu trước khi khẳng định khả năng sử dụng tổng quát.
