"""Xem gợi ý tự động, sửa bốn góc và xoay trang bằng phím."""
import argparse
from datetime import datetime
import json
from pathlib import Path

import cv2
import numpy as np

from detect import detect_document, order_points
from geometry import build_scan

PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_ROOT = PROJECT_ROOT / "artifacts" / "week2" / "manual"
PROCESSED_ROOT = PROJECT_ROOT / "data" / "processed" / "manual"


def save_manual_result(run_name, scanned, metadata):
    # Tách ảnh cuối và thông tin chọn góc để thư mục ảnh dễ xem.
    folder = OUTPUT_ROOT / run_name
    image_folder = PROCESSED_ROOT / run_name
    folder.mkdir(parents=True)
    image_folder.mkdir(parents=True)
    scan_path = image_folder / "warped_color.png"
    if not cv2.imwrite(str(scan_path), scanned):
        raise OSError("Không lưu được ảnh scan.")
    metadata["scan_path"] = scan_path.relative_to(PROJECT_ROOT).as_posix()
    metadata["scan_path_base"] = "project"
    (folder / "corners.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    return scan_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    args = parser.parse_args()
    source_path = Path(args.image).resolve()
    image = cv2.imread(str(source_path))
    if image is None:
        raise ValueError("Không đọc được ảnh: " + str(source_path))
    detection = detect_document(image)
    auto_corners = detection["corners"]
    points = [] if auto_corners is None else auto_corners.tolist()
    manual_corrected = False
    rotation = 0
    height, width = image.shape[:2]
    scale = min(1.0, 1000 / max(height, width))
    display_width, display_height = int(round(width * scale)), int(round(height * scale))
    display = cv2.resize(image, (display_width, display_height))
    scale_x, scale_y = display_width / width, display_height / height
    window = "Select corners"
    preview_window = "Scan preview"

    def on_mouse(event, x, y, flags, param):
        nonlocal manual_corrected
        if event == cv2.EVENT_LBUTTONDOWN and len(points) < 4:
            points.append([x / scale_x, y / scale_y])
            manual_corrected = True
        elif event == cv2.EVENT_RBUTTONDOWN and points:
            points.pop()
            manual_corrected = True

    cv2.namedWindow(window, cv2.WINDOW_AUTOSIZE)
    cv2.setMouseCallback(window, on_mouse)
    print("Trạng thái tự động:", detection["status"], detection["warnings"])
    print("Đã điền góc tự động nếu tìm được. R: xóa để chọn lại.")
    print("Chọn đủ 4 góc; chương trình tự sắp thứ tự để tránh lật gương.")
    print("Chuột phải: bỏ điểm cuối | P: xem | E: xoay 90 độ | S: lưu | Q/Esc: thoát")
    try:
        while True:
            canvas = display.copy()
            ordered = order_points(points) if len(points) == 4 else np.array(points)
            draw = np.round(ordered * [scale_x, scale_y]).astype(np.int32) if len(points) else []
            for index, point in enumerate(draw):
                x, y = point
                cv2.circle(canvas, (int(x), int(y)), 6, (0, 0, 255), -1)
                cv2.putText(canvas, str(index), (int(x) + 8, int(y) - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            if len(draw) == 4:
                cv2.polylines(canvas, [draw.reshape(-1, 1, 2)], True, (0, 255, 0), 2)
            cv2.imshow(window, canvas)
            key = cv2.waitKey(20) & 0xFF
            if key in (ord("q"), 27):
                break
            if key == ord("r"):
                points.clear()
                rotation = 0
                manual_corrected = True
                continue
            if key not in (ord("p"), ord("e"), ord("s")):
                continue
            if len(points) != 4:
                print("Cần chọn đủ bốn góc.")
                continue
            if key == ord("e"):
                rotation = (rotation + 1) % 4
            # Cùng một bộ góc đã sắp thứ tự được dùng cho ảnh và cả H/T.
            corners = order_points(points)
            try:
                scanned, matrix_h, matrix_t = build_scan(image, corners, rotation)
            except (ValueError, cv2.error) as error:
                print("Góc chưa hợp lệ:", error)
                continue
            cv2.namedWindow(preview_window, cv2.WINDOW_NORMAL)
            cv2.imshow(preview_window, scanned)
            if key != ord("s"):
                continue
            metadata = {
                "source_image": str(source_path), "mode": "interactive",
                "manual_corrected": manual_corrected,
                "auto_status": detection["status"],
                "corners_before": None if auto_corners is None else auto_corners.tolist(),
                "clicked_points": points, "corners_original": corners.tolist(),
                "corner_order": "clockwise_from_min_sum_xy",
                "rotation_clockwise_degrees": rotation * 90,
                "H_source_to_warp": matrix_h.tolist(), "T_source_to_output": matrix_t.tolist(),
                "output_width": scanned.shape[1], "output_height": scanned.shape[0],
            }
            run_name = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            scan_path = save_manual_result(run_name, scanned, metadata)
            print("Ảnh sau scan:", scan_path)
            print("Thông tin chọn góc:", OUTPUT_ROOT / run_name / "corners.json")
            break
    finally:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

