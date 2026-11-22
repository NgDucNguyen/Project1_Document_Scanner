# Project 1 — Document Scanner

**Nguyễn Đức Nguyên · MSSV 202416305 · Đại học Bách khoa Hà Nội**

Ảnh chụp → DocAligner → nắn bốn góc nếu có; nếu thiếu góc thì chọn vùng chữ chính để cắt dự phòng. Có thể chạy scanner riêng hoặc nối tiếp OCR tiếng Anh bằng RapidOCR; giữ Tesseract/FUNSD để đối chứng. **Canny/Otsu được giữ để đối chứng.** Pipeline có OCR còn kiểm tra dấu hiệu mất chữ sau nắn.

## 1. Kết quả và báo cáo cần mở

- Báo cáo hiện tại: [bản Word có ảnh minh họa](docs/bao_cao_tien_do_scanner.docx) · [bản Markdown](docs/bao_cao_tien_do_scanner.md).
- [Kế hoạch 7 ngày và việc cần làm tiếp](docs/ke_hoach_7_ngay_cai_thien_scanner.md).
- [Quy tắc làm việc dành cho AI trong dự án](AGENTS.md).
- [Bảng so sánh hai phương pháp trên toàn SmartDoc](docs/results/scanner_comparison.csv).
- Ảnh so sánh 6 ca khó: `artifacts/scanner_dev/comparison/all_corners.jpg` và `all_scans.jpg`. Trái: Canny/Otsu cải tiến; phải: DocAligner. Xanh lá: nhãn; đỏ: dự đoán.
- Ảnh scan minh họa: `data/processed/scan_examples/`; tra ảnh gốc trong `index.csv`.

| Phương pháp | Train đạt IoU ≥ 0,9 | Validation đạt IoU ≥ 0,9 | Test đạt IoU ≥ 0,9 |
| --- | ---: | ---: | ---: |
| Classic — Canny/Otsu cải tiến | 13.366/17.495 (76,40%) | 2.424/3.192 (75,94%) | Chưa chấm |
| DocAligner FastViT-T8 đã huấn luyện sẵn | **17.493/17.495 (99,99%)** | **3.192/3.192 (100%)** | **4.201/4.202 (99,98%)** |

Cả hai đã chạy detect đủ **24.889 ảnh**. Đã chốt DocAligner và chấm test cuối ngày 19/11/2026 từ dự đoán đã lưu; IoU trung bình test 0,9889. Classic test chưa chấm. Đây là detector thuần, không đánh giá toàn bộ cắt dự phòng/làm rõ ảnh/OCR. Chưa xác minh dữ liệu huấn luyện sẵn có trùng SmartDoc; các số trên không phải bằng chứng tổng quát hóa độc lập. Chưa đánh giá đầy đủ ảnh không có giấy hoặc tiếng Việt.

### Đánh giá cuối detector đã chốt

Kết quả: `artifacts/scanner_dev/docaligner_final_20261119/`, gồm dự đoán đã chấm, bảng tổng hợp và nguồn/cấu hình đóng băng. Lượt detect gốc giữ nguyên. Không điều chỉnh cấu hình theo điểm test; DocAligner là mô hình có sẵn, không huấn luyện trên tập train của dự án.

Chỉ khi cần tái hiện phép đánh giá cuối đã được cho phép, dùng tên lượt mới:

```powershell
python -X utf8 src/document_scanner/scanner/final_evaluation.py --run-name docaligner_final_recheck --final-test-evaluation
```

Lệnh chấm góc đã lưu, xác minh hash manifest/trọng số, chia tập theo tài liệu, tính cả ảnh thất bại trong mẫu số; không chạy lại mạng và không ghi đè benchmark cũ. Tập test đã được mở cho đánh giá cuối này, không còn là tập chưa xem cho các cải tiến sau.

### Kiểm định bổ sung toàn luồng scan

Mục 3.6 của báo cáo giữ bảng tiêu chí và kết quả audit. Lượt `artifacts/scanner_dev/scanner_quality_20261119/` có 23 mẫu: 14 ảnh có tài liệu, 6 ROI không có tờ giấy chính từ một ảnh train và 3 ca tổng hợp. Phát hiện giữ nội dung chưa đạt trên 8 trang FUNSD: 864/1.583 hộp từ được giữ đủ. Hai ảnh tiếng Anh cũ có CER/WER tốt hơn sau tăng cường. Không dùng các kết quả này để chỉnh detector đã chốt; không coi mẫu nhỏ là đánh giá độc lập.

Để tái hiện audit nhỏ, dùng tên mới:

```powershell
python -X utf8 src/document_scanner/scanner/quality_audit.py --run-name scanner_quality_recheck
```

Lệnh không quét lại 24.889 ảnh; tính sai số góc từ dự đoán đã lưu và chạy scan/OCR trên các mẫu nhỏ cố định. Nhãn dùng chấm sau scan, không tham gia chọn crop. Tập FUNSD đã scan sẵn được dùng kiểm tra giữ trang khi đưa qua scanner như ảnh đầu vào chưa rõ loại; sản phẩm vẫn có `--input-type scan` để bỏ scanner khi người dùng biết ảnh đã scan.

## 2. Cài đặt

Python 3.12 64-bit, chạy PowerShell từ thư mục gốc:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Nếu đã có venv thì chỉ cần kích hoạt. Có thể thay `python` bằng `.\venv\Scripts\python.exe` nếu không kích hoạt được.

**Mô hình DocAligner:** tải [FastViT-T8 ONNX từ liên kết upstream](https://drive.google.com/uc?export=download&id=1W88oOkHjMza6xXbDxrG8k_C-Tf2aYKJ4), đặt tại `models/docaligner/fastvit_t8.onnx` (khoảng 13,17 MB). SHA-256 đã thử: `950070fd4a46e25d46db7c35d0ed77612d9063f70d4543c7c504f0da6a943a89`. Nguồn: [DocsaidLab/DocAligner](https://github.com/DocsaidLab/DocAligner). Không cần PyTorch; dự án chạy ONNX bằng OpenCV.

**OCR:** cài Tesseract tại `C:\Program Files\Tesseract-OCR\tesseract.exe`. Mô hình tiếng Anh đã tinh chỉnh nằm ở `models/funsd_english/funsd_eng.traineddata` trên máy hiện tại. Nhánh đối chứng Tesseract gốc dùng `--ocr-engine tesseract --ocr-model standard`; xem [hướng dẫn OCR](docs/guides/thu_ocr_mot_anh.md) và [báo cáo OCR lịch sử](docs/history/week3_ocr_report.md) để tái tạo mô hình tinh chỉnh.

Ảnh dữ liệu và trọng số mô hình chỉ giữ cục bộ, không có trong GitHub. Thiếu DocAligner thì tải mô hình hoặc chọn `classic`; chương trình không âm thầm thay phương pháp.

## 3. Chạy một ảnh

### Thử OCR học sâu trên ảnh chụp mới (22/11/2026)

`--ocr-engine rapidocr` dùng RapidOCR 3.10.0/ONNX Runtime 1.32.0 với các mô hình đi kèm: PP-OCRv6 small cho detect/recognize và bộ phân loại hướng dòng v2.0. Đã được người dùng chọn làm OCR mặc định sau so sánh FUNSD; Tesseract/FUNSD/PSM 11 giữ làm đối chứng. Chưa có CER/WER trên ba ảnh mới; chúng là ba lần chụp cùng một trang, không phải ba tài liệu độc lập.

Luồng thử dùng khung dòng RapidOCR cho chọn hướng đọc và crop dự phòng, sau đó đọc ảnh màu trước tăng cường. `scanner/orientation.py` thử bốn hướng, chỉ xoay khi có bằng chứng chữ vượt ngưỡng và hơn rõ hướng thứ hai. Không ép mọi tài liệu ngang thành dọc. DocAligner/Canny/Otsu không được thay mô hình hay điều chỉnh theo các ảnh này.

**Đã chốt đầu vào RapidOCR ngày 22/11:** giữ ảnh màu sau cắt/nắn để OCR; `scan.png` làm đậm chỉ để xem. Đã đối chiếu cả hai bản trên cùng ba ảnh, cùng mô hình và cùng cách phóng/thêm viền. Bản tăng cường sinh thêm lỗi và phân mảnh dòng; ở ảnh `…5232`, số dòng từ 18 thành 48. Số dòng không phải độ chính xác; chưa có TXT chuẩn nên chưa chấm CER/WER. Bằng chứng: `artifacts/ocr/scan_vs_color_20261122_154834/comparison.json` (`complete: true`). Quyết định này dành cho RapidOCR; đầu vào nhánh Tesseract đối chứng giữ cách cũ.

```text
Ảnh gốc → chọn hướng → detect/cắt/nắn → scan_color.png
                                        ├→ tăng cường → scan.png để xem
                                        └→ phóng/thêm viền khi cần → OCR → text.txt
```

Cài riêng một lần từ gốc dự án (cùng lệnh dùng được trong Git Bash hoặc PowerShell):

```text
python -m venv artifacts/ocr/runtime
artifacts/ocr/runtime/Scripts/python.exe -m pip install rapidocr==3.10.0 onnxruntime==1.32.0
```

Chạy cả scan và OCR:

```text
python -X utf8 src/document_scanner/pipeline.py --image "data/raw/thu_ocr/ten_anh.jpg" --ocr-engine rapidocr
```

Trong thư mục pipeline mới: `scan.png` để xem, `scan_color.png` là ảnh màu trước tăng cường, `ocr_input.png` là đầu vào OCR khi có phóng ảnh, `text.txt` là nội dung thật và `ocr.json` chứa các khung **dòng**, điểm dòng và hash trọng số. Không có hộp từ của RapidOCR; `word_count` chỉ đếm theo khoảng trắng. Giữ cả dòng điểm thấp và gắn cảnh báo, không tự sửa nội dung. Không dùng `--psm`, `--tessdata-dir` với engine này. Venv riêng nằm trong artifacts, không push GitHub.

Nguồn: [RapidOCR](https://github.com/RapidAI/RapidOCR). Các kết quả SmartDoc và OCR ngày 19/11 là mốc cũ, không phải phép đo lại cho luồng thử ngày 22/11.

**Sửa crop dự phòng 22/11/2026:** cụm chữ chính được nối với các đoạn gần theo chiều dọc khi chúng chồng lấn ngang và khoảng trống giữa chúng có nền giấy sáng liên tục. Không lấy hộp bao mọi chữ trong ảnh. Ảnh `anh_thu.png` đã giữ lại mục 3 ở cuối trang; đây là sửa trên mẫu phát triển, chưa chứng minh giữ đủ nội dung cho mọi ảnh.

**Scan tự động một ảnh, không xuất văn bản OCR:**

```powershell
python -X utf8 src/document_scanner/scanner/scan_image.py --image "data/raw/thu_detect/anh_2.jpg"
```

Lệnh tự nối DocAligner và cắt dự phòng. Phần dự phòng tìm các cụm nét chữ trên nền sáng, dùng hộp từ Tesseract làm bằng chứng rồi chọn **một vùng có diện tích lớn nhất**, không lấy hộp bao tất cả chữ trong ảnh. Không có vùng đủ bằng chứng thì báo thất bại. Đây là quy tắc chọn vùng, chưa bảo đảm hiểu đúng trang chính trong mọi ảnh nhiều giấy.

Mỗi ảnh có một thư mục cố định `data/processed/scan/image_<tên>_<mã_đường_dẫn>/`: `scan.png` (đã tăng cường), `scan_color.png` (ảnh màu trước tăng cường) và `region.png` (vùng cắt trên ảnh gốc). Metadata ở thư mục cùng tên trong `artifacts/scans/`. Với `anh_2.jpg`, mở `data/processed/scan/image_anh_2_b016f626/scan.png`. Không tạo `text.txt`; Tesseract chỉ lấy hộp chữ khi cần cắt dự phòng.

**Chạy lại cùng ảnh sẽ cập nhật kết quả tại chỗ, không sinh thư mục thời gian mới.** Nếu lần chạy mới thất bại, ảnh thành công cũ được bỏ để tránh xem nhầm. Các file ghi chú riêng không bị xóa. Ảnh khác cùng tên được phân biệt bằng mã đường dẫn. Chỉ thêm `--new-run` khi chủ động muốn lưu một lượt lịch sử riêng; benchmark theo lô vẫn giữ cách lưu riêng từng lượt.

Scanner kiểm tra vùng cắt **trước tăng cường**: kích thước, vùng giấy sáng, nét giống chữ và độ sắc nét. Nếu khung trang không đạt, thử vùng chữ dự phòng; đầu ra vẫn không đạt thì từ chối, không lưu ảnh scan thành công. Các ngưỡng trong `configs/scan.json` mới là heuristic cho giấy sáng có chữ, chưa phải bộ phân loại ảnh không có tài liệu đáng tin cậy.

Nhánh dự phòng hiện thử tìm tứ giác từ mặt nạ giấy trong vùng nội dung chính và nắn phối cảnh nếu qua kiểm tra giữ hộp chữ/nét ảnh. Kết quả vẫn ghi là `content_fallback`, kèm `content_detection.perspective_refinement`; đây là khung ước lượng theo nội dung, không phải DocAligner đã tìm góc thành công. Nếu không đủ bằng chứng thì giữ cách xoay/cắt cũ.

Ảnh được bù độ sáng trong Lab, tăng độ đậm và dùng mặt nạ nét cục bộ để làm trắng nền; ảnh chữ đầu ra vẫn giữ các mức màu. Thêm `--no-enhance` để giữ ảnh màu trước tăng cường. Lọc nền có thể làm mất chi tiết rất nhạt hoặc hình vẽ; phải đối chiếu `scan_color.png`. Giấy phụ chạm trang chính vẫn có thể còn, không coi tô trắng nền là đã tách đúng trang. `--detect-only` giữ phép thử detector thuần, không chạy bước chất lượng/tăng cường mới.

Thêm `--detect-only` để chỉ kiểm tra detector, tắt cắt dự phòng; `--method both` so sánh hai phương pháp riêng. File thử cũ `detect_image.py` đã được thay bằng `scan_image.py`; các kết quả cũ ở `data/processed/detect/` được giữ để đối chiếu. Xem [sổ ghi chú detect](docs/guides/ghi_chu_detect.md) để ghi các ca thử.

Mặc định dùng DocAligner rồi OCR tiếng Anh:

```powershell
python -X utf8 src/document_scanner/pipeline.py --image "data/raw/thu_ocr/anh.jpg"
```

Chạy cùng ảnh bằng Canny/Otsu để so sánh:

```powershell
python -X utf8 src/document_scanner/pipeline.py --image "data/raw/thu_ocr/anh.jpg" --scanner-method classic
```

Đầu ra ở `data/processed/pipeline/<run_id>/`: `scan.png`, `text.txt`, `metadata.json`; thêm `evaluation.json` khi có `--reference "đường/dẫn/nhãn.txt"`. Với ảnh đã scan sẵn, dùng `--input-type scan` để bỏ qua tìm góc. OCR tiếng Anh mặc định là RapidOCR, bố cục auto; funsd_eng/PSM 11 giữ trong nhánh --ocr-engine tesseract. Với `--ocr-engine rapidocr`, OCR cuối đọc `scan_color.png` hoặc bản phóng từ ảnh này, không đọc `scan.png` tăng cường. `metadata.json` ghi chính xác tên ảnh OCR ở `ocr_input_image`. Có 69 kiểm thử đạt sau bổ sung bố cục ngày 22/11; không cần chạy lại benchmark khi chỉ sửa tài liệu.

### Bố cục form và nhiều cột ngày 22 tháng 11

RapidOCR là bộ đọc mặc định. Trên 30 trang FUNSD validation cùng đầu vào đã chuẩn bị, RapidOCR đạt CER 6,80%, WER 28,65%; Tesseract/funsd_eng/PSM 11 đạt 19,41% và 42,29%. Chấm theo vùng nhãn sau OCR toàn trang, không dùng nhãn để cắt ảnh. Đây là validation đã dùng phát triển, không phải test độc lập; chưa đo đúng quan hệ ô form. Lượt: `artifacts/ocr/funsd_validation_20261122/results.json`.

`--ocr-layout auto` mặc định: khi có từ hai nhãn dạng dấu hai chấm, thử gom theo hàng form; trường hợp khác thử chia cột bằng khoảng trắng XY-cut. `form` ghép khung cùng hàng, `columns` ưu tiên đọc từng cột, `plain` giữ thứ tự RapidOCR gốc. Đây là heuristic hình học, không phải mô hình hiểu bảng/form; có thể chọn sai nên luôn lưu `text_raw.txt` và cảnh báo `layout_geometry_review`.

```text
python -X utf8 src/document_scanner/pipeline.py --image "data/raw/funsd/dataset/training_data/images/716552.png" --input-type scan --ocr-layout form
python -X utf8 src/document_scanner/pipeline.py --image "data/raw/thu_ocr/anh.jpg" --ocr-layout columns
python -X utf8 src/document_scanner/pipeline.py --image "data/raw/thu_ocr/anh.jpg" --ocr-engine tesseract
```

`text.txt` là văn bản đã sắp xếp; `text_raw.txt` giữ nguyên thứ tự dòng OCR. `ocr.json` giữ khung dòng gốc, `layout.blocks` và các cặp nhãn–giá trị ứng viên trong `layout.fields` kèm ID dòng. Không suy đoán ô trống, trạng thái checkbox hoặc tự sửa chữ; giá trị nhiều dòng và bảng phức tạp còn cần kiểm thử. OCR đã tự phát hiện/cắt từng dòng bên trong bộ đọc; bố cục mới gom các kết quả dòng, chưa thêm mô hình nhận dạng ô bảng.

### OCR tiếng Anh hiện tại

Mặc định dùng RapidOCR. Mốc Tesseract `funsd_eng` trước đó được giữ để đối chiếu. Trên 30 trang validation FUNSD, chuẩn bị ảnh nhỏ giúp CER 21,04% → 19,41%, WER 48,01% → 42,29% (chấm theo vùng nhãn sau OCR toàn trang, chưa đo thứ tự đọc). PSM 11 tốt hơn PSM 3/4 trên tập này; hai ảnh chụp cũ đã chạy toàn pipeline đạt CER/WER 0%/0% và 1,06%/7,69%. Đây là kết quả phát triển, không phải test độc lập mới.

Mở `text.txt` để xem chữ; `ocr.json` để kiểm tra từ, dòng và tọa độ trên ảnh OCR. Điểm tin cậy Tesseract không phải độ chính xác. Dùng `--input-type scan` cho FUNSD/ảnh đã scan để bỏ bước cắt trang. OCR không sửa lỗi scanner làm mất chữ.

Lệnh đối chứng chuẩn bị ảnh: thêm `--no-ocr-prepare`. Các lượt so sánh ở `artifacts/ocr/english_layout_20261119/`, `english_resolution_20261119/`; xác nhận cấu hình cuối và demo thật ở `english_ready_20261119/`. Xem [hướng dẫn OCR](docs/guides/thu_ocr_mot_anh.md).

## 4. Kiểm tra detect theo lô

Lệnh dưới **không lưu ảnh scan, không chạy OCR**; đặt tên mới cho mỗi lần chạy:

```powershell
python -X utf8 src/document_scanner/scanner/benchmark_detection.py --method docaligner --run-name doc_full_v2 --workers 4
python -X utf8 src/document_scanner/scanner/benchmark_detection.py --method classic --run-name classic_full_v2 --workers 4
```

Kết quả ở `artifacts/scanner_dev/<run_name>/`: `results.csv`, `summary.csv`, `run_info.json` và snapshot nguồn. `complete: true` nghĩa là đã chạy xong. Không chấm nhãn test. Mỗi worker DocAligner dùng mạng riêng để tránh truy cập đồng thời một mạng.

Muốn kiểm tra nhanh đúng 200 ảnh phát triển:

```powershell
python -X utf8 src/document_scanner/scanner/benchmark.py --method docaligner --run-name doc_dev_v2
```

Muốn **tạo ảnh scan** theo lô, có thể bắt đầu với 20 ảnh validation:

```powershell
python -X utf8 src/document_scanner/scanner/scan.py --method docaligner --split val --limit 20 --workers 4
```

Ảnh cuối: `data/processed/scan/<run_id>/`. Metadata/CSV: `artifacts/scans/<run_id>/`. Bỏ `--limit` và đổi `--split all` nếu chủ động muốn tạo ảnh cho toàn bộ dữ liệu. Chấm kết quả scan bằng `python -X utf8 src/document_scanner/scanner/evaluate.py`; chỉ chấm train/val.

## 5. Cấu trúc cần nắm

```text
src/document_scanner/
  pipeline.py                # Nối scanner, cắt dự phòng và OCR
  data/                      # Nạp, kiểm tra và chia tập dữ liệu
  scanner/
    detect.py                # Chọn phương pháp, điểm gọi chung
    docaligner.py            # Mô hình bốn góc mặc định
    classic.py               # Canny/Otsu và các cải tiến truyền thống
    geometry.py              # Kiểm tra góc và nắn phối cảnh
    scan_image.py            # Scanner một ảnh dùng chung, CLI scan không xuất OCR
    content_scan.py          # Cắt vùng chữ dự phòng bằng Tesseract
    scan.py                  # Tạo ảnh scan theo lô
    manual_scan.py           # Công cụ sửa góc bằng tay khi cần
    evaluate.py              # Chấm IoU kết quả scan
    benchmark.py             # Kiểm chứng tập phát triển cố định
    benchmark_detection.py   # Detect toàn bộ, không sinh ảnh
  ocr/                       # Tesseract, chỉ số và huấn luyện OCR đã làm
docs/                        # Báo cáo hiện tại, hướng dẫn, kết quả nhỏ
  history/                   # Báo cáo và bảng thử nghiệm cũ, không dùng để chạy
artifacts/scanner_dev/        # Hai lượt detect hoàn chỉnh và ảnh so sánh
artifacts/history/            # Kết quả cũ đã gom để có thể khôi phục
data/raw/                    # Ảnh và nhãn gốc
data/processed/              # Ảnh scan minh họa và đầu ra mới
models/                      # Trọng số đang dùng trên máy
```

Mã DBNet và các script thử trung gian đã gỡ khỏi luồng hiện tại vì không được chọn. Hồ sơ thử nghiệm giữ trong `docs/history/`. Sau xác nhận của người dùng, đã xóa các lượt thử trung gian, ảnh đầu ra cũ và mô hình DBNet không dùng (khoảng 100 MB). `artifacts/history/` chỉ giữ hồ sơ các tuần trước; hai lượt detect toàn bộ và bộ ảnh so sánh hiện tại vẫn được giữ riêng.

Kiểm thử: `python -X utf8 -m unittest discover -s tests`. Xem [hướng dẫn scanner](docs/guides/phase2_scanner.md) để giải thích Canny/Otsu, heatmap và trạng thái cảnh báo.
