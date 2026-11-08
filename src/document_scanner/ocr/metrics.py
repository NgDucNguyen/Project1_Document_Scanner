"""Các phép đo đơn giản dùng chung khi đánh giá OCR."""
import unicodedata


def normalize_text(text):
    # Giữ chữ hoa/thường và dấu câu, chỉ chuẩn hóa Unicode và khoảng trắng.
    return " ".join(unicodedata.normalize("NFC", text).split())


def edit_distance(first, second):
    # Số phép thêm, xóa hoặc thay ít nhất; dùng được với ký tự và từ.
    previous_row = list(range(len(second) + 1))
    for i in range(1, len(first) + 1):
        current_row = [i]
        for j in range(1, len(second) + 1):
            cost = 0 if first[i - 1] == second[j - 1] else 1
            current_row.append(min(previous_row[j] + 1, current_row[j - 1] + 1,
                                   previous_row[j - 1] + cost))
        previous_row = current_row
    return previous_row[-1]


def calculate_cer(reference, prediction):
    reference, prediction = normalize_text(reference), normalize_text(prediction)
    return edit_distance(reference, prediction) / len(reference) if reference else None


def calculate_wer(reference, prediction):
    reference, prediction = normalize_text(reference).split(), normalize_text(prediction).split()
    return edit_distance(reference, prediction) / len(reference) if reference else None
