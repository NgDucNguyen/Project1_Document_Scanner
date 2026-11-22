# Hướng dẫn thử OCR tiếng Anh với một ảnh

## Thử ảnh bị xoay ngang và bộ đọc mới — 22/11/2026

Scanner đã thêm chọn hướng đọc 0/90/180/270 độ trước detect/crop; không chọn theo riêng chiều rộng/cao. Hướng không đủ rõ được giữ nguyên và cảnh báo `reading_orientation_review`. `metadata.json` lưu `orientation`, điểm bằng chứng từng hướng và ma trận; điểm không phải độ chính xác.

Để thử bộ đọc PP-OCRv6 (môi trường riêng đã cài trên máy này), chạy:

```text
python -X utf8 src/document_scanner/pipeline.py --image "data/raw/thu_ocr/ten_anh.jpg" --ocr-engine rapidocr
```

Xem ảnh ở `scan.png`, chữ ở `text.txt`, các dòng đọc được ở `ocr.json` trong thư mục pipeline mới in trên terminal. Engine này dùng ảnh màu trước tăng cường; bản làm đậm vẫn được giữ để xem. Nó cũng cung cấp khung dòng cho nhánh crop dự phòng, nên crop có thể khác luồng Tesseract. Ba ảnh mới cùng trang "In the Evening" đã chạy được, nhưng vẫn có từ sai/dòng yếu; chưa có TXT kiểm chứng nên chưa tính CER/WER. RapidOCR hiện là mặc định; dùng --ocr-engine tesseract để đối chứng. Xem README để cài môi trường RapidOCR trên máy khác.

**Đã chốt:** không OCR bản `scan.png` làm đậm trong nhánh RapidOCR. Trên cùng ba ảnh, bản màu giữ dòng tốt hơn; ở ảnh `…5232`, bản tăng cường tách thành 48 mảnh so với 18 dòng của bản màu. Đây là đối chiếu trực quan, không phải đo độ chính xác. Nếu không cần phóng ảnh, OCR đọc thẳng `scan_color.png`; nếu cần, đọc `ocr_input.png` được tạo từ bản màu. Xem `metadata.json` → `ocr_input_image` để biết đúng file đã đọc.

Chạy ba ảnh hiện có trong **Git Bash**:

```bash
for img in data/raw/thu_ocr/179531*.jpg; do
  python -X utf8 src/document_scanner/pipeline.py --image "$img" --ocr-engine rapidocr
done
```

Ba kết quả đã chạy: `data/processed/pipeline/20261122_130927_617220/` (ảnh …5187), `20261122_131144_824146/` (…5216), `20261122_130914_317728/` (…5232). Đây là các mốc, lần chạy mới sẽ in thư mục mới. File `english_01.txt` hiện là đoạn mẫu khác nội dung “In the Evening”, không dùng nó làm nhãn cho ba ảnh này.

**Cập nhật 19/11/2026:** ảnh chụp mặc định được DocAligner tìm góc trước khi OCR; cần mô hình ONNX theo [README](../../README.md). Muốn đối chứng Canny/Otsu, thêm `--scanner-method classic`. OCR cuối mặc định là RapidOCR; Tesseract/FUNSD là đối chứng. Với `--input-type scan`, chương trình bỏ qua tìm góc và không cần DocAligner.

## 1. Chuẩn bị ảnh và văn bản chuẩn

Chọn một ảnh trang tài liệu tiếng Anh rõ chữ. Nếu là ảnh chụp, nên nhìn thấy cả bốn góc trang; hạn chế mờ, bóng và che khuất chữ. Chương trình đọc các định dạng ảnh thông dụng như JPG, JPEG và PNG.

Trong VS Code, tạo thư mục `data/raw/thu_ocr/`, rồi đặt hai file vào đó:

```text
data/raw/thu_ocr/
├── anh.jpg       # Ảnh cần kiểm tra; tên và phần mở rộng có thể khác
└── nhan.txt      # Văn bản chuẩn, tùy chọn
```

File `nhan.txt` chứa **nội dung đúng có trong ảnh**, do bạn gõ lại hoặc lấy từ tài liệu gốc. Giữ đúng chữ hoa, chữ thường và dấu câu; sắp xếp theo thứ tự mong muốn. Lưu file dưới dạng **UTF-8** trong VS Code hoặc Notepad. Khi đặt tên, chú ý tránh `nhan.txt.txt` nếu Windows đang ẩn đuôi file.

Ví dụ, nếu trong ảnh thực sự có đúng hai câu sau thì `nhan.txt` ghi:

```text
My name is John.
This is a test document.
```

Nếu chưa có văn bản chuẩn, bạn vẫn chạy được OCR và tự nhìn so sánh. Muốn tính CER/WER thì cần `nhan.txt` phù hợp với ảnh. Ảnh và TXT trong `data/raw/` chỉ lưu trên máy, không được Git theo dõi.

## 2. Mở terminal

Mở thư mục gốc dự án trong VS Code. Chọn **Terminal → New Terminal**. Kích hoạt môi trường nếu terminal chưa hiện `(venv)`:

**Git Bash:**

```bash
source venv/Scripts/activate
```

**PowerShell:**

```powershell
.\venv\Scripts\Activate.ps1
```

Các lệnh phía dưới dùng `python` và chạy từ thư mục gốc dự án. Tesseract phải được cài trên máy; file cấu hình đường dẫn hiện nằm trong `src/document_scanner/ocr/recognize.py`.

## 3. Chạy ảnh chụp có file TXT

Nếu tên file đúng như ví dụ ở bước 1:

```bash
python -X utf8 src/document_scanner/pipeline.py --input-type photo --image "data/raw/thu_ocr/anh.jpg" --reference "data/raw/thu_ocr/nhan.txt"
```

Chương trình sẽ tìm góc, nắn trang, nhận dạng tiếng Anh và so sánh văn bản OCR với `nhan.txt`. Thay tên và đuôi trong lệnh cho đúng file thực tế; giữ dấu ngoặc kép nếu đường dẫn có khoảng trắng.

**Chưa có TXT:** bỏ phần `--reference`:

```bash
python -X utf8 src/document_scanner/pipeline.py --input-type photo --image "data/raw/thu_ocr/anh.jpg"
```

**Ảnh đã scan hoặc đã cắt thẳng sẵn:** dùng `--input-type scan`. Chế độ này đưa ảnh trực tiếp vào OCR, không tìm góc trang:

```bash
python -X utf8 src/document_scanner/pipeline.py --input-type scan --image "data/raw/thu_ocr/anh.jpg" --reference "data/raw/thu_ocr/nhan.txt"
```

## 4. Xem kết quả

Terminal sẽ in đường dẫn đầu ra, ví dụ `data/processed/pipeline/20261109_.../`. Mỗi lượt thành công có thư mục riêng:

- `scan.png`: ảnh sau nắn; hãy mở ảnh này trước để xem có cắt mất chữ hay chọn nhầm vùng không.
- `text.txt`: văn bản OCR. Mở và so sánh với ảnh và file chuẩn.
- `metadata.json`: nguồn ảnh, hash mô hình/mã, cấu hình scan/OCR, cảnh báo và ma trận đổi tọa độ.
- `scan_color.png`: trong nhánh RapidOCR ảnh chụp, đây là ảnh màu sau cắt/nắn được chọn cho OCR cuối; không phải ảnh chụp gốc chưa xử lý.
- `ocr.json`: Tesseract xuất từ/dòng và điểm từng từ; RapidOCR xuất khung dòng và điểm dòng, `words` rỗng. Tọa độ tính trên ảnh đầu vào OCR. Điểm không phải độ chính xác; không so thẳng điểm giữa hai engine.
- `ocr_input.png`: chỉ xuất khi ảnh nhỏ cần phóng/thêm viền. Trong nhánh RapidOCR ảnh chụp, ảnh này được tạo từ `scan_color.png`; `scan.png` tăng cường vẫn dành để xem. Metadata có `T_source_to_ocr` để đối chiếu với ảnh gốc.
- `evaluation.json`: chỉ có khi truyền `--reference`; chứa CER và WER cùng số phép sửa.

Chương trình cũng in CER và WER ra terminal khi có file chuẩn. Chỉ số càng thấp càng tốt: **CER** tính lỗi theo ký tự, **WER** tính theo từ. Các chỉ số là số phép thêm, xóa và thay chia cho số ký tự hoặc từ trong nhãn, nên đôi khi có thể lớn hơn 100%.

Phép so sánh chuẩn hóa Unicode và gộp khoảng trắng, nhưng vẫn phân biệt chữ hoa, chữ thường và dấu câu. Thứ tự đọc sai, nhãn thiếu nội dung hoặc nhãn khác ảnh đều có thể làm chỉ số tăng. Đây là phép so sánh toàn bộ văn bản một ảnh; không so trực tiếp với các chỉ số đánh giá theo vùng FUNSD trong báo cáo.

Tiếng Anh mặc định dùng RapidOCR với --ocr-layout auto. Dùng --ocr-layout form cho biểu mẫu, columns cho nhiều cột, plain để giữ dòng gốc. text.txt là bản đã sắp xếp; text_raw.txt là bản gốc; ocr.json giữ layout.blocks và layout.fields (các cặp nhãn–giá trị ứng viên, cần kiểm tra). Không dựng lại ô bảng hoặc suy đoán checkbox. Muốn đối chứng Tesseract/funsd_eng/PSM 11, thêm --ocr-engine tesseract. Cách phóng ảnh nhỏ tối đa 2 lần, nhắm cạnh dài 1.800 px và viền 12 px giữ nguyên; --no-ocr-prepare để đối chứng.

## 5. Nếu tìm góc sai hoặc không tìm thấy trang

- `no_candidate`: không tìm được bốn góc trang. Chương trình sẽ thử tìm chữ, xoay gần thẳng và cắt vùng chứa chữ trước khi OCR. Nếu cũng không tìm được đủ chữ, chương trình dừng và báo lỗi.
- `content_fallback`: đã cắt theo vùng chữ, không phải khung trang được detector xác minh; có thể thử nắn tứ giác ước lượng theo nội dung. Mở `scan.png` để kiểm tra phần nội dung có bị thiếu; chữ ngoài ảnh hoặc chữ không phát hiện được có thể bị mất. Góc xoay và vùng cắt được lưu trong `metadata.json`.
- `page_crop_text_mismatch`: khung trang ban đầu chỉ có rất ít chữ, trong khi ảnh gốc có nhiều chữ hơn; chương trình thử chuyển sang vùng chữ. Đây là cảnh báo theo kinh nghiệm, không bảo đảm chọn đúng trang.
- `content_frame_broad`: khung vùng chữ chiếm ít nhất 80% ảnh, có thể đã lấy cả nền hoặc chưa tìm đúng phạm vi chữ. Mở `scan.png` và so với ảnh gốc trước khi dùng kết quả OCR.
- `uncertain`: chương trình đã có khung nhưng đưa cảnh báo. Mở `scan.png` kiểm tra; kết quả OCR vẫn có thể sai nếu khung sai.
- Nếu cần chỉnh tay, chạy lệnh sau với đúng đường dẫn ảnh:

```bash
python -X utf8 src/document_scanner/scanner/manual_scan.py --image "data/raw/thu_ocr/anh.jpg"
```

Trong cửa sổ: nhấn `R` để xóa góc gợi ý, bấm bốn góc, nhấn `P` để xem trước; `E` xoay 90 độ và `S` lưu. Terminal sẽ in đường dẫn ảnh sau scan. Sau đó đưa **đường dẫn được in ra** vào lệnh OCR sau, thay phần trong ngoặc kép:

```bash
python -X utf8 src/document_scanner/pipeline.py --input-type scan --image "DUONG_DAN_ANH_SAU_SCAN.png" --reference "data/raw/thu_ocr/nhan.txt"
```

Chọn góc bằng tay là một chế độ riêng. Kết quả này không được tính là kết quả scanner hoàn toàn tự động.

## 6. Kết quả đợt cải thiện OCR tiếng Anh

Trên cùng 30 trang validation FUNSD, PSM 11 không chuẩn bị ảnh có CER 21,04%, WER 48,01%; phóng ảnh nhỏ/thêm viền giảm còn 19,41% và 42,29%. OCR nhận toàn trang; nhãn chỉ dùng gán từ vào vùng sau OCR để chấm, không phải phép chấm thứ tự đọc toàn trang. Từ ngoài vùng nhãn đếm riêng. Hai ảnh chụp cũ chạy toàn pipeline: anh.jpg 0%/0%; anh_test_02.jpg 1,06%/7,69%. Không dùng các mẫu này làm test độc lập mới.

Kết quả có `complete: true` trong `artifacts/ocr/english_layout_20261119/`, `english_resolution_20261119/` và `english_ready_20261119/`. Mẫu benchmark photo của lượt resolution còn thử viền trên ảnh lớn; cấu hình cuối chỉ thêm viền khi phóng ảnh nhỏ, đã kiểm tra lại bằng pipeline thật trong lượt ready.

Scanner đang tạm giữ nguyên; OCR không phục hồi chữ bị scanner cắt mất. Với trang FUNSD hoặc ảnh đã cắt thẳng, dùng `--input-type scan`. Ảnh không nhãn vẫn nhận dạng được, nhưng không có CER/WER. Mẫu cảnh báo điểm thấp cần xem ảnh và chữ thực tế, không tự xóa từ điểm thấp.
