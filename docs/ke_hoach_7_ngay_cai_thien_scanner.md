# Cải thiện scanner — Kế hoạch và kết quả hiện tại

**Cập nhật 17/11/2026.** DocAligner là phương pháp chính; Canny/Otsu cải tiến là phương pháp đối chứng. OCR tiếng Anh giữ Tesseract/FUNSD. Báo cáo và thử nghiệm chi tiết trước khi dọn cấu trúc nằm trong [hồ sơ lịch sử](history/scanner_experiments_2026-11-17.md); các lệnh và đường dẫn cũ trong hồ sơ đó không còn là hướng dẫn hiện tại.

## 1. Tiến độ

| Ngày | Công việc | Trạng thái |
| --- | --- | --- |
| 1 | Chốt tập phát triển, lưu cấu hình và kết quả mốc | Đã làm: 200 ảnh validation, cân bằng 5 nền |
| 2 | Phân tích lỗi Canny/Otsu/contour | Đã làm: thiếu khung tốt ngay từ bước tạo ứng viên |
| 3 | Cải thiện khung, mép ngoài và từ chối khung yếu | Đã làm: thêm cạnh xám/Lab, ngưỡng từ chối và cảnh báo |
| 4 | Thử DBNet cho vùng chữ dự phòng | Đã làm: bản thử mất nội dung, giữ Tesseract; mã thử không dùng đã gỡ |
| Bổ sung | Chạy toàn SmartDoc, thử mô hình bốn góc DocAligner | Đã làm: đủ 24.889 ảnh cho cả hai phương pháp |
| 5 | Kiểm thử ảnh mới, tiếng Việt và ảnh không có giấy | Chưa hoàn thành |
| 6 | Tổng hợp lỗi và chốt cấu hình sau kiểm thử thực tế | Đang chốt DocAligner làm phương pháp chính để kiểm thử tiếp |
| 7 | Báo cáo và demo pipeline | Đã có ảnh so sánh và số liệu; bổ sung kết quả ngày 5 khi có |

## 2. Kết quả so sánh chính

| Chỉ số | Canny/Otsu cải tiến | DocAligner FastViT-T8 |
| --- | ---: | ---: |
| Detect toàn SmartDoc | 20.503/24.889 | 24.889/24.889 |
| Train đạt IoU ≥ 0,9 | 13.366/17.495 (76,40%) | **17.493/17.495 (99,99%)** |
| Validation đạt IoU ≥ 0,9 | 2.424/3.192 (75,94%) | **3.192/3.192 (100%)** |
| IoU trung bình validation | 0,7503 | **0,9893** |

Đây là lượt **detect**, chưa nắn/lưu toàn bộ 24.889 ảnh và chưa đánh giá OCR toàn bộ. Test gồm 4.202 ảnh chỉ có dự đoán, không chấm IoU. Detect được khung không đồng nghĩa khung đúng.

| Nền validation | Classic đạt | DocAligner đạt |
| --- | ---: | ---: |
| background01 | 782/797 | 797/797 |
| background02 | 747/780 | 780/780 |
| background03 | 746/751 | 751/751 |
| background04 | 149/515 | 515/515 |
| background05 | 0/349 | 349/349 |

Hai ảnh train DocAligner chưa đạt là `background02/patent004/frame_0107.jpeg` (IoU 0,5060) và `background02/tax004/frame_0166.jpeg` (0,5157). So với classic có 4.128 ảnh train mới đạt và 1 ảnh cũ đạt bị giảm; validation thêm 768 ảnh đạt và không mất ảnh đạt cũ.

**Giới hạn:** chưa xác minh dữ liệu huấn luyện sẵn của DocAligner có trùng SmartDoc. Kết quả cao chưa chứng minh khả năng tổng quát trên ảnh mới hoặc khả năng từ chối ảnh không có giấy. Chưa tự huấn luyện/tinh chỉnh DocAligner. Thời gian full detect DocAligner khoảng 56 phút, classic khoảng 14 phút trên các lượt đã chạy; tải máy có thể khác nhau.

## 3. Cách trình bày phương pháp với giáo viên

### Bước đầu: tự xây dựng và cải thiện phương pháp truyền thống

Mở `src/document_scanner/scanner/classic.py`:

1. Thu nhỏ ảnh; làm xám và làm mượt.
2. Canny tìm cạnh; Otsu tách vùng sáng/tối.
3. Closing nối khe hở, tìm contour, convex hull và xấp xỉ tứ giác.
4. Kiểm tra diện tích, biên ảnh, độ dài cạnh, mức bám cạnh và độ khớp contour.
5. Chấm điểm chọn khung; bổ sung nhánh cạnh ảnh xám ngưỡng thấp và Lab b.
6. Từ chối điểm thấp, cảnh báo khung yếu, rồi đưa góc về ảnh gốc.

Phương pháp này được giữ để chứng minh quá trình nghiên cứu và đối chứng, không bị xóa khi dùng học sâu. Ngày 3 tăng validation từ 60,49% lên 75,94%, nhưng nền khó vẫn còn lỗi.

### Bước tiếp: thử mô hình đã huấn luyện sẵn và đánh giá cùng dữ liệu

Mở `src/document_scanner/scanner/docaligner.py`:

1. Ảnh BGR resize 256×256, chuẩn hóa chia 255.
2. DocAligner FastViT-T8 sinh bốn heatmap vị trí góc.
3. Ngưỡng 0,3, Otsu trên từng heatmap, tìm vùng lớn nhất và lấy trọng tâm.
4. Sắp thứ tự góc, kiểm tra hình học; dùng `geometry.py` nắn phối cảnh.

**Không dùng Canny để tìm góc trong DocAligner.** Otsu ở đây xử lý heatmap, khác Otsu trên ảnh gốc của classic. Adapter chạy bằng OpenCV, theo tiền/hậu xử lý upstream; chưa kiểm chứng tương đương số học với toàn bộ gói Python chính thức.

Phần dự án thực hiện: tích hợp mô hình, xử lý đầu ra, kiểm tra hình học, nối scanner/OCR và đánh giá so sánh. Phải ghi rõ sử dụng mô hình có sẵn của [DocsaidLab](https://github.com/DocsaidLab/DocAligner), không nhận là tự huấn luyện.

### Phần dùng chung

- `detect.py`: chọn phương pháp, mặc định DocAligner.
- `geometry.py`: kiểm tra bốn góc hợp lệ, tính phép biến đổi và nắn ảnh, hạn chế lật gương.
- `pipeline.py`: nối phát hiện góc → nắn → kiểm tra lượng chữ → cắt dự phòng nếu cần → OCR.
- `content_scan.py`: cắt vùng chữ bằng Tesseract khi thiếu khung; có bước Canny/Hough để ước lượng góc nhỏ. Vùng chữ dự phòng không phải dự đoán mép giấy.
- `ocr/recognize.py`: gọi Tesseract. Mô hình đọc tiếng Anh vẫn là FUNSD đã tinh chỉnh; chưa thay OCR bằng DocAligner.

## 4. File cần mở khi báo cáo

| Mục đích | Đường dẫn |
| --- | --- |
| Bảng số liệu chính | `docs/results/scanner_comparison.csv` |
| Danh sách 200 ảnh phát triển | `docs/results/scanner_dev_manifest.csv` |
| So sánh khung ở 6 ca khó | `artifacts/scanner_dev/comparison/all_corners.jpg` |
| So sánh ảnh sau nắn ở 6 ca khó | `artifacts/scanner_dev/comparison/all_scans.jpg` |
| Từng cặp ảnh lớn và nguồn tương ứng | `artifacts/scanner_dev/comparison/index.csv` và các JPG cạnh đó |
| Ảnh scan minh họa riêng từng phương pháp | `data/processed/scan_examples/`, tra `index.csv` |
| Kết quả detect classic đầy đủ | `artifacts/scanner_dev/full_detection_v1/` |
| Kết quả detect DocAligner đầy đủ | `artifacts/scanner_dev/docaligner_t8_full/` |

Các lượt full giữ nguyên CSV từng ảnh, snapshot nguồn, hash và `run_info.json`; không sửa điểm hoặc xóa ca lỗi. Cờ `uncertain` trong lượt DocAligner cũ được gắn vì là thử nghiệm. Mã hiện tại dùng cảnh báo `document_presence_not_verified` vì chưa kiểm thử đầy đủ ảnh không có giấy; cảnh báo này không phải điểm IoU thấp.

## 5. Chạy và việc tiếp theo

Chạy DocAligner mặc định:

```powershell
python -X utf8 src/document_scanner/pipeline.py --image "data/raw/thu_ocr/anh.jpg"
```

Chạy đối chứng Canny/Otsu:

```powershell
python -X utf8 src/document_scanner/pipeline.py --image "data/raw/thu_ocr/anh.jpg" --scanner-method classic
```

Lệnh detect toàn bộ hiện dùng chung một file, thay cho `try_docaligner.py` đã gộp:

```powershell
python -X utf8 src/document_scanner/scanner/benchmark_detection.py --method docaligner --run-name doc_full_v2 --workers 4
```

Không cần chạy lại để chứng minh kết quả đã có. Ngày 5 nên kiểm thử ảnh mới, tiếng Việt, nền khó và ảnh không có giấy; gán góc cho ảnh có tài liệu và đo tỷ lệ nhận nhầm ở ảnh âm tính. Xem [README](../README.md) để cài mô hình và các lệnh khác.

## 6. Dọn cấu trúc

- Đã gộp mã thử DocAligner vào mô-đun scanner chính; bỏ script thử riêng.
- Đã gỡ mã/thử nghiệm DBNet không được chọn; Tesseract vẫn là cắt dự phòng duy nhất.
- Báo cáo cũ và bảng chi tiết chuyển vào `docs/history/`; chỉ hai bảng cần dùng giữ ở `docs/results/`.
- Sau khi người dùng xác nhận phạm vi xóa, đã xóa vĩnh viễn ba thư mục `artifacts/history/scanner_trials`, `artifacts/history/processed_trials`, `artifacts/history/unused_models`: 258 file, khoảng 100 MB. Đây là lượt thử trung gian, ảnh đầu ra cũ và mô hình DBNet không dùng. Hai lượt detect đầy đủ, ảnh so sánh chính và hồ sơ các tuần trước vẫn được giữ riêng.
- Ảnh gốc, nhãn, manifest toàn bộ và mô hình OCR tiếng Anh được giữ. Không push ảnh/trọng số lên GitHub.

### Kiểm chứng sau khi gộp mã

- 35 kiểm thử đạt, bao gồm chọn đúng phương pháp và không đọc nhãn test để chấm.
- Hai detector tái tạo tọa độ lưu trước đó trên ba ca khó; không đổi công thức classic khi tách file.
- Kiểm tra lại hình học của toàn bộ 24.889 bộ góc DocAligner đã lưu: không có bộ góc không hợp lệ.
- Chạy pipeline thật với cả DocAligner và classic trên `anh.jpg`, có ảnh, TXT, metadata và đánh giá. CER lần lượt 3,02% và 2,64%; WER 4,35% và 5,80%. Mẫu nhỏ này có kết quả trái chiều giữa các chỉ số, tiếp tục cho thấy IoU tốt hơn không tự bảo đảm OCR tốt hơn.
- Chạy thử batch 2 ảnh validation bằng DocAligner, lưu/nắn và `evaluate.py --examples` thành công. Đây chỉ là kiểm tra tích hợp sau dọn cấu trúc, không thay thế số liệu full đã có.
