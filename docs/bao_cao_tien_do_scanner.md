# Báo cáo tiến độ Document Scanner

**Sinh viên:** Nguyễn Đức Nguyên — **MSSV:** 202416305  
**Đơn vị:** Đại học Bách khoa Hà Nội — **Cập nhật:** 17/11/2026

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

### Pipeline dùng chung

Ảnh chụp → chọn detector → kiểm tra góc → nắn phối cảnh → kiểm tra lượng chữ → cắt nội dung dự phòng nếu cần → OCR tiếng Anh → lưu ảnh, văn bản và metadata.

`detect.py` chọn phương pháp; `geometry.py` kiểm tra góc và nắn bằng phép biến đổi phối cảnh. Khi thiếu khung hoặc khung có dấu hiệu mất chữ, `content_scan.py` dùng Tesseract tìm vùng chữ để cắt dự phòng. Vùng chữ này không phải mép giấy. Phần dự phòng còn dùng Canny/Hough để ước lượng góc nghiêng nhỏ.

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

## Kết quả còn hạn chế và tình hình OCR

So với classic, DocAligner có thêm 4.128 ảnh train đạt ngưỡng và một ảnh cũ đạt bị giảm; validation thêm 768 ảnh đạt và không mất ảnh đạt cũ. Hai ảnh train DocAligner chưa đạt là `background02/patent004/frame_0107.jpeg` (IoU 0,5060) và `background02/tax004/frame_0166.jpeg` (0,5157).

Lượt full detect DocAligner mất khoảng 56 phút; classic khoảng 14 phút. Hai lượt có thể khác tải máy nên chưa dùng làm phép đo tốc độ có kiểm soát. Trạng thái `uncertain` của DocAligner trong lượt thử cũ là cờ thử nghiệm. Mã hiện tại giữ cảnh báo `document_presence_not_verified` vì chưa đánh giá đầy đủ ảnh âm tính, không phải vì tất cả khung có IoU thấp.

### OCR tiếng Anh và vùng chữ dự phòng

Tesseract với mô hình `funsd_eng` đã tinh chỉnh vẫn là bộ đọc tiếng Anh. DocAligner chỉ thay phần tìm góc, không phải mô hình nhận dạng chữ. Lượt đo FUNSD trước đây có CER 24,61% và WER 48,97% trên 50 trang test, theo đánh giá trong các vùng nhãn; tập này đã được dùng trong quá trình phát triển nên không xem là đánh giá độc lập cuối cùng.

Đã thử DBNet cho vùng chữ dự phòng trên 54 ảnh. Trên 30 trang FUNSD, cách Tesseract giữ đủ 4.595/4.616 hộp từ (99,55%), bản DBNet + gom cụm giữ 4.092/4.616 (88,65%). Tiêu chí giữ đủ là ít nhất 98% diện tích hộp từ nằm trong crop; ảnh không tạo được crop tính giữ 0 hộp từ. Vì còn bỏ sót chữ nhỏ và chân trang, DBNet không được chọn và mã thử đã được dọn.

Sau khi gộp mã, đã chạy pipeline thật với `anh.jpg` và văn bản chuẩn:

| Scanner trước OCR | CER | WER |
| --- | ---: | ---: |
| Canny/Otsu cải tiến | 2,64% | 5,80% |
| DocAligner | 3,02% | 4,35% |

Kết quả một ảnh có hai chỉ số trái chiều, không đủ để kết luận OCR phương pháp nào tốt hơn. IoU khung trang không đo độ nét, khả năng giữ dấu hay thứ tự đọc. OCR tiếng Việt và ảnh chụp mới chưa được đánh giá đầy đủ.

### Việc cần làm tiếp

1. Chuẩn bị tập ảnh mới có tài liệu tiếng Việt/Anh, nền khó và ảnh không có giấy.
2. Gán bốn góc cho ảnh có tài liệu; quy định rõ sách, nhiều tờ giấy và vật che được xử lý thế nào.
3. Đo IoU, tỷ lệ không tìm thấy và nhận nhầm; kiểm tra mất tiêu đề, chân trang và dấu tiếng Việt.
4. Dùng một số ảnh có TXT chuẩn để đánh giá OCR sau cắt/nắn; chưa tự động chọn cấu hình theo nhãn test.

<!-- PAGEBREAK -->

## Quản lý dự án và cách tái hiện

Đã gộp mô hình mới vào scanner chính, giữ classic làm đối chứng và gỡ các script thử không còn dùng. `docs/results/` chỉ giữ bảng so sánh chính và danh sách 200 ảnh phát triển. Hồ sơ cũ ở `docs/history/`; hai lượt detect toàn bộ và ảnh so sánh được giữ riêng. Sau xác nhận của người dùng, đã xóa 258 file thử và mô hình DBNet không dùng, khoảng 100 MB.

35 kiểm thử đạt sau khi gộp mã. Đã đối chiếu hai detector trên ba ca khó, kiểm tra hình học 24.889 bộ góc DocAligner đã lưu và chạy thử batch hai ảnh cùng đánh giá/lưu minh họa. Đây là kiểm tra tích hợp, không thay số liệu full.

### Chạy một ảnh và đối chứng

Chạy từ thư mục gốc, venv đã kích hoạt:

```powershell
python -X utf8 src/document_scanner/pipeline.py --image "data/raw/thu_ocr/anh.jpg"
python -X utf8 src/document_scanner/pipeline.py --image "data/raw/thu_ocr/anh.jpg" --scanner-method classic
```

Kết quả mới ở `data/processed/pipeline/<run_id>/`: `scan.png`, `text.txt`, `metadata.json`; thêm `evaluation.json` khi có tham số `--reference`. Đầu vào đã scan sẵn dùng `--input-type scan`, bỏ qua tìm góc.

### File dùng để kiểm chứng và báo cáo

| Nội dung | Đường dẫn trong dự án |
| --- | --- |
| Bảng so sánh toàn bộ | `docs/results/scanner_comparison.csv` |
| Danh sách phát triển cố định | `docs/results/scanner_dev_manifest.csv` |
| Kết quả classic đầy đủ | `artifacts/scanner_dev/full_detection_v1/` |
| Kết quả DocAligner đầy đủ | `artifacts/scanner_dev/docaligner_t8_full/` |
| Ảnh so sánh khung và sau nắn | `artifacts/scanner_dev/comparison/` |
| Ảnh scan minh họa riêng | `data/processed/scan_examples/` |
| Kế hoạch sắp tới | `docs/ke_hoach_7_ngay_cai_thien_scanner.md` |
| Quy tắc dành cho AI làm việc trong dự án | `AGENTS.md` |

Các lượt detect lưu `results.csv`, `summary.csv`, `run_info.json` và snapshot nguồn. `complete: true` xác nhận hoàn tất. Ảnh, trọng số và artifacts chỉ lưu trên máy, không có trong GitHub; kết quả tổng hợp và mã nguồn được quản lý bằng Git.

### Nguồn mô hình và kết luận

Nguồn: [DocsaidLab DocAligner](https://github.com/DocsaidLab/DocAligner); tiền/hậu xử lý tham khảo `docaligner/heatmap_reg/infer.py` của upstream. Tên mô hình là heatmap FastViT-T8, không phải mô hình DBNet tìm chữ và không phải mô hình OCR.

DocAligner cải thiện rõ kết quả định vị khung trang trên SmartDoc và đã được chọn làm scanner chính để tiếp tục kiểm thử. Canny/Otsu được giữ để thể hiện quá trình phát triển và làm mốc so sánh. Bước tiếp theo ưu tiên kiểm thử dữ liệu mới và ảnh không có tài liệu trước khi khẳng định khả năng sử dụng tổng quát.
