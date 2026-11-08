# Báo cáo OCR tiếng Anh và hướng dẫn chạy

**Cập nhật:** 08/11/2026.

## Tóm tắt tiến độ

- Đã nối scanner với OCR: ảnh chụp được tìm góc và nắn trước khi nhận dạng; ảnh đã scan có thể đưa thẳng vào OCR.
- Đã chuẩn bị các dòng chữ từ FUNSD và thử tinh chỉnh Tesseract tiếng Anh. Không dùng chữ trong SmartDoc để huấn luyện OCR.
- Đã so sánh mô hình gốc và mô hình tinh chỉnh trên ảnh FUNSD toàn trang. Với PSM 3, mô hình tinh chỉnh đạt CER 32,35% và WER 54,70% trên các vùng nhãn của 50 trang test.
- Đã chạy thử luồng scanner → OCR trên một ảnh mô phỏng; chưa đánh giá đầy đủ trên ảnh điện thoại thật. Chưa đánh giá tiếng Việt.
- **Trạng thái:** có bản tiếng Anh chạy được để thử nghiệm, nhưng kết quả còn sai nhiều và cần cải thiện. Các chỉ số này không chứng minh độ chính xác của toàn bộ hệ thống trên ảnh chụp.

Số liệu nhỏ dùng cho bảng đánh giá được lưu tại [week3_ocr_page_metrics.csv](results/week3_ocr_page_metrics.csv) để có thể xem trên GitHub. Ảnh, dữ liệu, mô hình và `artifacts/` được giữ trên máy theo `.gitignore`.

## 1. Mục tiêu và dữ liệu

Luồng sử dụng: **ảnh chụp trang giấy → tìm góc và nắn trang → OCR → lưu văn bản**. Với ảnh đã scan như FUNSD, bỏ qua bước tìm góc.

- **SmartDoc:** phát triển và đánh giá scanner. Không dùng chữ nhỏ hoặc mờ trong SmartDoc để huấn luyện OCR.
- **FUNSD:** các biểu mẫu tiếng Anh đã scan, có nhãn vùng và từ; dùng chuẩn bị dữ liệu và đánh giá OCR. Ảnh FUNSD không phải ảnh từ scanner của dự án. Nguồn: [FUNSD](https://guillaumejaume.github.io/FUNSD/), đọc [điều khoản sử dụng](https://guillaumejaume.github.io/FUNSD/work/).
- **Ảnh chụp thật:** cần kiểm tra riêng toàn bộ luồng, bao gồm tìm góc, nắn ảnh và OCR. Không thể suy ra chất lượng ảnh chụp từ chỉ số FUNSD.

## 2. Chuẩn bị và tinh chỉnh mô hình

Từ FUNSD `training_data`, chương trình chọn vùng nhãn giống một dòng chữ, kiểm tra sự khớp giữa nhãn vùng và từ, hình học và độ tương phản. Chia **theo trang**: 119 trang train và 30 trang validation, không trùng trang. Tạo được 2.511 dòng train và 624 dòng validation.

Lượt tinh chỉnh lấy 720 dòng train ứng viên theo trang và giữ 607 dòng sau khi đối chiếu với OCR gốc (CER không quá 15%). Cách lọc này thiên về dòng mô hình gốc đã đọc tương đối tốt; không bảo đảm chữ đều nét hoặc nhãn hoàn toàn đúng. Validation gồm 180 dòng và không lọc theo kết quả OCR. Tesseract `eng` từ [tessdata_best](https://github.com/tesseract-ocr/tessdata_best) được huấn luyện tiếp 400 vòng lặp.

| So sánh trên 180 dòng validation, PSM 7 | CER | WER |
| --- | ---: | ---: |
| `eng` cài sẵn trên máy | 13,34% | 41,24% |
| `eng` gốc từ tessdata_best | 12,93% | 40,23% |
| Mô hình tinh chỉnh FUNSD | 12,02% | 35,89% |

Đây là đánh giá trên dòng được cắt sẵn theo nhãn; không phải kết quả toàn trang. Chi tiết nằm tại `artifacts/week3/funsd_finetune/20261108_221457_330844/validation.csv` và `training.log`. Mô hình lưu tại `models/funsd_english/funsd_eng.traineddata`.

## 3. Đánh giá OCR toàn trang

Tesseract nhận **toàn bộ ảnh**, không được cấp tọa độ nhãn. Sau đó, từ OCR được gán vào vùng nhãn nếu ít nhất 50% diện tích khung từ nằm trong vùng. Tính CER/WER bằng tổng số phép sửa ký tự/từ trong các vùng chia cho tổng số ký tự/từ nhãn. Vùng có nhãn nhưng OCR bỏ sót vẫn được tính lỗi.

Từ OCR nằm ngoài vùng được chú thích được thống kê riêng, **không tính vào CER/WER**, vì FUNSD có thể không gán nhãn tất cả chữ trên ảnh. Vì vậy đây là chỉ số trên **các vùng có nhãn sau khi OCR toàn trang**, không phải CER/WER của toàn bộ văn bản trang. Phép đo cũng chưa kiểm tra thứ tự đọc giữa các vùng, có thể chịu ảnh hưởng bởi chất lượng nhãn và cách gán tọa độ.

| Tập | Cấu hình | Trang | Vùng nhãn | CER | WER | Từ OCR ngoài vùng nhãn |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Validation | `eng` cài sẵn, PSM 3 | 30 | 1.649 | 26,46% | 52,68% | 300 / 3.992 |
| Validation | FUNSD, PSM 3 | 30 | 1.649 | 24,54% | 49,57% | 241 / 4.015 |
| Validation | FUNSD, PSM 6 | 30 | 1.649 | 34,91% | 57,43% | 661 / 4.011 |
| Validation | FUNSD, PSM 11 | 30 | 1.649 | 21,04% | 48,01% | 253 / 4.273 |
| Test | `eng` cài sẵn, PSM 3 | 50 | 2.270 | 32,68% | 56,35% | 595 / 7.151 |
| Test | FUNSD, PSM 3 | 50 | 2.270 | 32,35% | 54,70% | 512 / 7.168 |
| Test, thử thêm | FUNSD, PSM 11 | 50 | 2.270 | 24,61% | 48,97% | 568 / 8.055 |

Trên máy có mô hình FUNSD, pipeline tự chọn mô hình này cho tiếng Anh. **PSM 3 được giữ làm mặc định** để đọc trang thông thường. PSM 11 cho chỉ số vùng thấp hơn trong phép thử, nhưng tìm chữ rải rác và không bảo đảm thứ tự đọc; dùng `--psm 11` khi cần thử biểu mẫu nhiều ô. PSM 6 coi ảnh là một khối chữ và kém hơn trên validation này. Không có chỉ số nào ở đây chứng minh thứ tự các đoạn là đúng.

So sánh PSM 3 trên 50 trang test, mô hình FUNSD có ít lỗi ký tự hơn ở 29 trang nhưng nhiều lỗi hơn ở 21 trang so với `eng` cài sẵn. Chênh lệch CER tổng hợp là nhỏ; không thể kết luận mô hình mới tốt hơn trên mọi trang.

Tập test đã từng được xem ở thử nghiệm vùng chữ trước và đã được dùng cho phép thử PSM 11 bổ sung; validation cũng có 12 trang từng dùng chọn cấu hình ban đầu. Do đó không coi các kết quả trên là đánh giá mù cuối cùng. Cần một tập tài liệu mới, có nhãn, để kết luận khả năng tổng quát và đánh giá ảnh chụp → scanner → OCR.

Các bảng tổng hợp và chi tiết nằm trong `artifacts/week3/page_evaluation/` **trên máy thực hiện**, không được đưa lên GitHub. Mỗi lượt có `summary.csv` (tổng hợp), `pages.csv` (từng trang), `regions.csv` (nhãn và dự đoán từng vùng) và `run_info.json`. Bảng tổng hợp nhỏ được đưa vào `docs/results/week3_ocr_page_metrics.csv`. Mã đánh giá là `src/document_scanner/ocr/evaluate_pages.py`.

## 4. Chạy thử

Tại thư mục gốc dự án, sau khi kích hoạt venv và cài Tesseract:

```powershell
# Ảnh FUNSD đã scan: OCR trực tiếp.
python -X utf8 src/document_scanner/pipeline.py --input-type scan --image data/raw/funsd/dataset/testing_data/images/82092117.png

# Ảnh chụp: thay bằng đường dẫn ảnh của bạn; chương trình tìm góc rồi OCR.
python -X utf8 src/document_scanner/pipeline.py --input-type photo --image duong_dan_den_anh.jpg
```

Mỗi lượt ghi `scan.png`, `text.txt`, `metadata.json` vào `data/processed/pipeline/<run_id>/`. Nếu không tìm được khung tài liệu, chương trình báo lỗi và dừng. Nếu thiếu mô hình FUNSD, chế độ `auto` dùng `eng` cài trong Tesseract; tên mô hình được in trong terminal và ghi vào metadata. Dùng `--ocr-model standard` để chủ động chọn mô hình gốc, hoặc `--ocr-model funsd` để bắt buộc có mô hình mới. Thêm `--psm 11` để thử chế độ chữ rải rác.

Xem mẫu PSM 3 tại `data/processed/pipeline/20261108_223324_385340/` và PSM 11 tại `data/processed/pipeline/20261108_223403_692612/`. File mô hình và dữ liệu nằm trên máy, không được Git theo dõi; máy khác cần cài Tesseract, dữ liệu và mô hình tương ứng.

Đã kiểm tra thêm luồng `photo` bằng **một ảnh mô phỏng** tạo từ trang FUNSD: đầu vào `data/interim/ocr_demo/photo_funsd_synthetic.png`, đầu ra `data/processed/pipeline/20261108_224156_780002/`. Scanner báo `uncertain` do có nhiều ứng viên, nhưng tứ giác chọn được có IoU 0,9976 với góc mô phỏng; OCR đọc được văn bản và vẫn có lỗi. Đây chỉ là một ảnh tổng hợp, chưa chứng minh chất lượng với ảnh điện thoại thật.

## 5. Cấu trúc và dọn dẹp

```text
src/document_scanner/
├── pipeline.py                    # Nối scanner với OCR
└── ocr/
    ├── recognize.py               # Gọi Tesseract cho một ảnh
    ├── metrics.py                 # Chuẩn hóa, CER và WER
    ├── prepare_funsd_training.py  # Tạo dòng chữ và chia theo trang
    ├── finetune_funsd.py          # Tinh chỉnh và so sánh trên dòng
    └── evaluate_pages.py          # Đánh giá ảnh toàn trang FUNSD
```

Các thử nghiệm trước và kết quả minh họa đã gộp vào `artifacts/week3/history/ocr_experiments_20261108.zip`. Đã xóa bản sao ảnh dòng và file LSTM trung gian; giữ manifest, kết quả, mô hình và checkpoint cuối. Dữ liệu gốc và ảnh chụp của người dùng không bị xóa. Nếu cần tạo lại ảnh dòng để huấn luyện:

```powershell
python -X utf8 src/document_scanner/ocr/prepare_funsd_training.py
python -X utf8 -u src/document_scanner/ocr/finetune_funsd.py --data data/interim/funsd_ocr_lines/THU_MUC_VUA_TAO
```

Cần cài Tesseract có công cụ huấn luyện và đặt mô hình gốc `eng.traineddata` của tessdata_best trong `models/tessdata_best/`. Lượt huấn luyện mới lưu kết quả và mô hình trong `artifacts/week3/funsd_finetune/<run_id>/`, không tự thay mô hình đang dùng.

Để chạy lại đánh giá toàn trang:

```powershell
python -X utf8 -u src/document_scanner/ocr/evaluate_pages.py --split val --methods eng funsd --psm 3
python -X utf8 -u src/document_scanner/ocr/evaluate_pages.py --split test --methods eng funsd --psm 3
```

Không dùng lại tập test như một tập để liên tục điều chỉnh; cần dữ liệu độc lập cho lần đánh giá cuối.
