"""Sắp chữ theo hình học; không sửa chữ và không dùng nhãn dữ liệu."""
import re
import statistics


def line_box(line):
    if "box" in line:
        return list(line["box"])
    points = line["polygon"]
    return [min(p[0] for p in points), min(p[1] for p in points),
            max(p[0] for p in points), max(p[1] for p in points)]


def short_label(text):
    # Chỉ nhận nhãn kết thúc bằng dấu hai chấm, không đoán ý nghĩa tên trường.
    return bool(re.search(r"[:：]\s*$", text)) and len(text) <= 55 and len(text.split()) <= 7


def inline_field(text):
    match = re.match(r"^([^:：]{1,50})[:：]\s*(\S.*)$", text)
    return match if match and len(match[1].split()) <= 7 else None


def collect_rows(items):
    """Các khung cùng đường cơ sở được giữ trên cùng hàng."""
    rows = []
    for item in sorted(items, key=lambda a: ((a["box"][1] + a["box"][3]) / 2, a["box"][0])):
        box = item["box"]
        height = box[3] - box[1]
        matches = []
        for row_index, row in enumerate(rows):
            top = statistics.median(x["box"][1] for x in row)
            bottom = statistics.median(x["box"][3] for x in row)
            overlap = min(bottom, box[3]) - max(top, box[1])
            center_gap = abs((top + bottom - box[1] - box[3]) / 2)
            # Không dùng hộp bao cả hàng: hộp cao bất thường không nối hai dòng.
            if overlap >= .5 * min(height, bottom - top) and center_gap <= .45 * max(height, bottom - top):
                matches.append((center_gap, row_index))
        if matches:
            rows[min(matches)[1]].append(item)
        else:
            rows.append([item])
    return [sorted(row, key=lambda x: x["box"][0]) for row in rows]


def whitespace_cuts(items, axis):
    intervals = sorted((x["box"][axis], x["box"][axis + 2]) for x in items)
    end = intervals[0][1]
    cuts = []
    for start, stop in intervals[1:]:
        if start > end:
            cuts.append((start - end, (start + end) / 2))
        end = max(end, stop)
    return sorted(cuts, reverse=True)


def split_columns(items, height, depth=0):
    """XY-cut: khoảng trắng đứng chia cột; khoảng ngang tách tiêu đề/đoạn."""
    if len(items) < 4 or depth >= 12:
        return [items]
    for gap, position in whitespace_cuts(items, 0):
        left = [x for x in items if x["box"][2] < position]
        right = [x for x in items if x["box"][0] > position]
        if gap >= 2 * height and len(left) >= 2 and len(right) >= 2:
            return split_columns(left, height, depth + 1) + split_columns(right, height, depth + 1)
    for gap, position in whitespace_cuts(items, 1):
        if gap >= .65 * height:
            top = [x for x in items if x["box"][3] < position]
            bottom = [x for x in items if x["box"][1] > position]
            if top and bottom:
                return split_columns(top, height, depth + 1) + split_columns(bottom, height, depth + 1)
    return [items]


def arrange_lines(lines, mode="auto"):
    if mode not in ("auto", "form", "columns", "plain"):
        raise ValueError("OCR layout phải là auto, form, columns hoặc plain.")
    items = [{"id": index, "text": line["text"], "box": line_box(line)}
             for index, line in enumerate(lines)]
    if any(len(x["box"]) != 4 or x["box"][2] <= x["box"][0] or x["box"][3] <= x["box"][1]
           for x in items):
        raise ValueError("Khung dòng OCR không hợp lệ.")
    if not items:
        return {"requested_mode": mode, "selected_mode": "plain", "text": "", "blocks": [], "fields": [], "warnings": []}
    height = statistics.median(x["box"][3] - x["box"][1] for x in items)
    labels = sum(bool(short_label(x["text"]) or inline_field(x["text"])) for x in items)
    selected = ("form" if labels >= 2 else "columns") if mode == "auto" else mode
    blocks = split_columns(items, height) if selected == "columns" else [items]
    output = []; block_results = []; fields = []
    for block_id, block in enumerate(blocks):
        rows = [[x] for x in block] if selected == "plain" else collect_rows(block)
        text_rows = []; row_results = []
        for row in rows:
            parts = []; previous = None
            for index, item in enumerate(row):
                gap = 0 if previous is None else item["box"][0] - previous["box"][2]
                paired = (selected == "form" and previous is not None and short_label(previous["text"])
                          and gap >= -height * .2 and gap <= height * 12
                          and not short_label(item["text"]) and not inline_field(item["text"]))
                if previous is not None:
                    # Các ô độc lập vẫn cách nhau; chỉ nhãn-giá trị gần nhau dùng một dấu cách.
                    parts.append(" " if paired or gap < height else "  ")
                parts.append(item["text"])
                if paired:
                    fields.append({"label": previous["text"], "value": item["text"],
                                   "line_ids": [previous["id"], item["id"]],
                                   "association": "same_row_spatial_candidate"})
                inline = inline_field(item["text"])
                if selected == "form" and inline:
                    fields.append({"label": inline[1] + ":", "value": inline[2],
                                   "line_ids": [item["id"]], "association": "inline_colon_candidate"})
                previous = item
            text = "".join(parts)
            text_rows.append(text)
            row_results.append({"text": text, "line_ids": [x["id"] for x in row]})
        box = [min(x["box"][0] for x in block), min(x["box"][1] for x in block),
               max(x["box"][2] for x in block), max(x["box"][3] for x in block)]
        block_results.append({"id": block_id, "box": box, "rows": row_results})
        output.append("\n".join(text_rows))
    return {"requested_mode": mode, "selected_mode": selected, "text": "\n\n".join(output),
            "blocks": block_results, "fields": fields,
            "warnings": [] if selected == "plain" else ["layout_geometry_review"],
            "note": "Gom hàng/cột từ khung OCR. Không phải mô hình hiểu form/bảng; liên kết trường cần kiểm tra. Không tự sửa chữ."}


def apply_layout(recognition, mode="auto"):
    """Giữ nguyên các dòng gốc, chỉ thay cách trình bày TXT."""
    result = dict(recognition)
    result["raw_text"] = recognition["text"]
    layout = arrange_lines(recognition["lines"], mode)
    result["text"] = layout["text"]
    result["layout"] = layout
    result["reading_order"] = "Geometry layout: " + layout["selected_mode"]
    result["warnings"] = list(dict.fromkeys(recognition["warnings"] + layout["warnings"]))
    return result
