# Báo cáo OCR tiếng Anh và hướng dẫn chạy

**Cập nhật:** 09/11/2026.

**Cấu hình tiếng Anh đang dùng:** mô hình `funsd_eng` và PSM 11 được chọn mặc định, người dùng không cần lựa chọn khi chạy. Phép so sánh PSM 3 dưới đây ghi lại cấu hình trước ngày 09/11.

## Tóm tắt tiến độ

- Đã nối scanner với OCR: ảnh chụp được tìm góc và nắn trước khi nhận dạng; ảnh đã scan có thể đưa thẳng vào OCR.
- Đã chuẩn bị các dòng chữ từ FUNSD và thử tinh chỉnh Tesseract tiếng Anh. Không dùng chữ trong SmartDoc để huấn luyện OCR.
- Đã so sánh mô hình gốc và mô hình tinh chỉnh trên ảnh FUNSD toàn trang. Với PSM 3, mô hình tinh chỉnh đạt CER 32,35% và WER 54,70% trên các vùng nhãn của 50 trang test.
- Đã chạy thử luồng scanner → OCR trên ảnh mô phỏng và một số ảnh thực tế; chưa đánh giá đầy đủ trên tập ảnh điện thoại thật có nhãn. Chưa đánh giá tiếng Việt.
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

Pipeline tiếng Anh hiện chọn **mô hình FUNSD và PSM 11** làm cấu hình mặc định. PSM 11 cho chỉ số vùng thấp hơn trong các phép thử này, nhưng tìm chữ rải rác và không bảo đảm thứ tự đọc. PSM 6 coi ảnh là một khối chữ và kém hơn trên validation này. Không có chỉ số nào ở đây chứng minh thứ tự các đoạn là đúng.

### Thử tăng tương phản trước OCR

Ngày 09/11, thử chuyển ảnh sang thang xám và tăng tương phản cục bộ bằng OpenCV CLAHE (`clipLimit=2`, `tileGridSize=8×8`), dùng cùng mô hình FUNSD và PSM 11. Hai ảnh cá nhân được đo trên toàn bộ văn bản chuẩn; FUNSD được đo riêng trong các vùng có nhãn theo cách ở mục 3.

| Dữ liệu | CER ảnh hiện tại | CER sau CLAHE | WER ảnh hiện tại | WER sau CLAHE |
| --- | ---: | ---: | ---: | ---: |
| `anh.jpg`, sau scanner | 2,64% | 1,51% | 5,80% | 3,62% |
| `anh_test_02.jpg`, sau scanner | 3,91% | 1,90% | 12,18% | 9,62% |
| 30 trang FUNSD validation, vùng nhãn | 21,04% | 21,56% | 48,01% | 47,95% |

Trên FUNSD, số lỗi ký tự giảm ở 13 trang, tăng ở 16 trang và giữ nguyên ở 1 trang. Hai ảnh cá nhân và tập validation đều đã được dùng trong các lần thử trước, không phải tập kiểm tra độc lập. Vì kết quả không tốt hơn nhất quán, **chưa bật CLAHE mặc định**. Với `anh_thu.png` không có nhãn, quan sát OCR vẫn có lỗi như nhầm `AI` và dấu đầu dòng; không thể tính CER/WER một cách đáng tin cậy.

Trên hai ảnh người dùng thử ngày 09/11, cùng mô hình FUNSD: ảnh 1 có CER 0% với PSM 3 và 2,64% với PSM 11; ảnh 2 có CER 9,83% với PSM 3 và 3,91% với PSM 11. PSM 11 giữ được tiêu đề và cuối trang ở ảnh 2 nhưng có thêm ký tự thừa. Đây là hai mẫu nhỏ và đã được dùng để chọn cấu hình, không phải đánh giá độc lập. Quyết định dùng PSM 11 cần được kiểm tra tiếp trên ảnh mới, đặc biệt thứ tự đọc.

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

Mỗi lượt ghi `scan.png`, `text.txt`, `metadata.json` vào `data/processed/pipeline/<run_id>/`. Nếu không tìm được khung trang, pipeline thử xoay và cắt vùng chữ; trường hợp không tìm được đủ chữ, chương trình báo lỗi và dừng. Vùng chữ không phải mép trang và không nắn phối cảnh; xem `scan.png` để kiểm tra. Mô hình FUNSD được chọn mặc định và tên mô hình được ghi trong metadata; nếu thiếu mô hình, chương trình báo lỗi để khôi phục. Nếu truyền file chuẩn qua `--reference`, kết quả CER/WER được lưu trong `evaluation.json`.

Ảnh và văn bản kết quả thử cũ đã dọn ngày 09/11/2026; có thể chạy lại để tạo kết quả mới. File mô hình và dữ liệu nằm trên máy, không được Git theo dõi; máy khác cần cài Tesseract, dữ liệu và mô hình tương ứng.

Đã kiểm tra thêm luồng `photo` bằng **một ảnh mô phỏng** tạo từ trang FUNSD. Scanner báo `uncertain` do có nhiều ứng viên, nhưng tứ giác chọn được có IoU 0,9976 với góc mô phỏng; OCR đọc được văn bản và vẫn có lỗi. Ảnh thử và đầu ra cũ đã dọn. Đây chỉ là một ảnh tổng hợp, chưa chứng minh chất lượng với ảnh điện thoại thật.

Với ảnh `data/raw/thu_ocr/anh_thu.png`, scanner không tìm được trang đầy đủ nên pipeline xoay khoảng -7,39° và dùng vùng chữ để cắt. OCR đọc được các đoạn chính nhưng còn nhầm ký tự và dấu đầu dòng. Đầu ra thử cũ đã dọn; ảnh này không có nhãn nên chỉ kiểm tra bằng mắt, không đưa ra chỉ số chính xác.

### Việc còn lại trước khi chốt tiếng Anh

1. Chuẩn bị một tập ảnh mới chưa dùng để chọn cấu hình, đa dạng văn bản, góc chụp, độ sáng và chất lượng ảnh; mỗi ảnh có TXT chuẩn đúng thứ tự, dấu câu và nội dung nhìn thấy.
2. Chạy cả luồng `photo` → scanner → OCR trên tập ảnh đó. Ghi lại ảnh scanner lỗi, ảnh cắt mất chữ, và số ảnh OCR thành công; kiểm tra riêng các ảnh dùng `content_fallback`.
3. Tính tổng CER/WER trên toàn bộ văn bản theo số phép sửa và độ dài nhãn; xem thêm từng ảnh, thứ tự đọc, chữ bị thiếu và ký tự thừa. Không chỉ dựa vào điểm trung bình hoặc FUNSD.
4. Nếu thay đổi tiền xử lý hoặc mô hình, chọn cấu hình bằng tập phát triển và kiểm tra lại một lần trên tập độc lập. Ghi rõ kết quả và giới hạn trước khi chuyển sang tiếng Việt.

### Thử bổ sung: 20 ảnh thật từ RDTAG-1.0

[RDTAG-1.0](https://ilocr.iiit.ac.in/icdar_2024_rdtag/dataset.html) có ảnh tài liệu tiếng Anh chụp bằng kính Aria và văn bản chuẩn toàn trang. Nguồn công bố miễn phí cho học thuật và nghiên cứu; kiểm tra lại điều kiện trước khi phân phối. Mẫu tải ngày 09/11 gồm 20 cặp ảnh/TXT, chọn từ 5 gói của **training set** gốc, cố gắng lấy khác mã trang và không dùng để huấn luyện mô hình của dự án. Thông tin nguồn và lựa chọn nằm trong `data/raw/rdtag_sample/source.json`; ảnh trong `images/`, nhãn trong `references/`. Đây là **tập phát triển**, không phải tập đánh giá độc lập cuối cùng, vì kết quả được xem để định hướng cải thiện. Ảnh chụp bằng kính, nhiều trang sách và tạp chí, không đại diện đầy đủ cho ảnh điện thoại một trang giấy.

Chạy pipeline `photo`, `funsd_eng`, PSM 11 trên 20 ảnh:

| Kết quả | Số ảnh |
| --- | ---: |
| Có đầu ra OCR | 18 |
| Dừng vì không tìm được khung hoặc đủ chữ | 2 |
| Trong 18 ảnh có đầu ra: dùng vùng chữ | 10 |
| Trong 18 ảnh có đầu ra: detector báo `ok` | 8 |

**Có đầu ra hoặc báo `ok` không có nghĩa là quét đúng.** Ví dụ `3_Book15_37_in_far_68.jpg` báo `ok` nhưng ảnh `scan.png` thực tế là một phần nền, không phải trang chữ. Phải kiểm tra ảnh sau scan khi phân tích lỗi.

So sánh toàn bộ văn bản dự đoán với TXT gốc sau chuẩn hóa Unicode và khoảng trắng cho CER tổng **84,61%** và WER tổng **104,15%**; với 2 lượt dừng, quy ước dự đoán rỗng để tính thiếu toàn bộ nhãn. Đây là kết quả toàn luồng trên mẫu khó, **không phải độ lỗi riêng của mô hình OCR**: còn ảnh hưởng bởi khung sai, phần trang không nhìn thấy, chất lượng ảnh, nhiều cột và thứ tự đọc. Nhãn gốc `2_Magazine2_55_in_close_2.txt` còn chứa một chuỗi dấu `;` và dấu chấm lặp bất thường, nên cần rà nhãn trước khi dùng các chỉ số này để kết luận hoặc công bố. WER có thể trên 100% vì có cả phép thêm từ. Nguồn RDTAG cũng cho biết chữ thuộc hình, biểu đồ không nằm trong nhãn.

Kết quả theo từng ảnh của hai lượt được giữ trong [rdtag_development_comparison.csv](results/rdtag_development_comparison.csv). Ảnh và văn bản đầu ra cũ đã dọn. Cần ưu tiên kiểm tra/cải thiện phát hiện trang trước khi kết luận rằng chỉ riêng OCR gây lỗi lớn.

### Rà soát vùng cắt và chạy lại

Sau khi xem ảnh gốc và ảnh cắt của cả 20 mẫu, phát hiện các lỗi: detector có thể bắt nhầm nền dù báo `ok`; ước lượng nghiêng có thể dựa vào đường thẳng của nền; khung theo chữ có thể lấy quá rộng hoặc chỉ lấy một phần trang. Với ảnh chụp, pipeline đã được bổ sung các kiểm tra kinh nghiệm:

- Nếu ảnh nắn có rất ít ký tự đáng tin cậy trong khi ảnh gốc có nhiều hơn rõ rệt, thử dùng vùng chữ và ghi `page_crop_text_mismatch`. Đây chỉ là tín hiệu, không chứng minh vùng chữ đúng.
- So sánh chữ trên ảnh gốc và ảnh đã xoay. Nếu ảnh xoay mất phần lớn ký tự đáng tin cậy, dùng góc 0°. Điểm phụ thuộc Tesseract và có thể bị ảnh hưởng bởi chữ hoặc nhiễu ở nền.
- Nếu khung theo chữ chiếm từ 80% ảnh trở lên, ghi `content_frame_broad` để yêu cầu kiểm tra. Khi dùng vùng chữ vẫn cần kiểm tra ảnh, kể cả khi không có cảnh báo này.

Chạy lại cùng 20 ảnh và cùng nhãn, trước khi bổ sung cảnh báo diện tích (cảnh báo chỉ thay đổi metadata, không thay đổi ảnh/OCR):

| Chỉ số | Trước chỉnh | Sau chỉnh |
| --- | ---: | ---: |
| Có đầu ra OCR | 18/20 | 20/20 |
| CER tổng | 84,61% | 78,02% |
| WER tổng | 104,15% | 128,33% |

Hai lượt dừng trước chỉnh được tính dự đoán rỗng. Sau chỉnh, CER giảm trên 7 ảnh, tăng trên 1 ảnh và không đổi trên 12 ảnh; WER tổng tăng do một số ảnh lấy thêm nhiều từ không thuộc nhãn. **Không thể nói chất lượng đã cải thiện toàn diện hoặc các khung đã cắt đúng.** Ví dụ ảnh `3_Book15_37_in_far_68.jpg` không còn cắt riêng nền, nhưng ảnh sau cắt vẫn chứa nhiều nền. Nhãn bất thường và các giới hạn nêu trên vẫn áp dụng; mẫu này đã dùng điều chỉnh ngưỡng nên không phải kiểm thử độc lập.

Kết quả theo từng ảnh của lượt mới nằm trong [bảng so sánh](results/rdtag_development_comparison.csv); ảnh và văn bản đầu ra đã dọn. Hai ảnh có nhãn riêng `anh.jpg` và `anh_test_02.jpg` được chạy lại, CER lần lượt vẫn là 2,64% và 3,91%. Cần thêm tập ảnh mới độc lập và nhãn đã rà soát trước khi chốt chất lượng. Đặc biệt cần cải thiện chọn vùng chữ để giảm nhiễu nền mà không cắt mất nội dung.

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
