from pathlib import Path

import cv2
import pandas as pd

from adapters import (
    INTERIM_ROOT,
    PROJECT_ROOT,
    corners_tl_tr_br_bl,
    image_path,
)


SEED = 42
OUTPUT_ROOT = PROJECT_ROOT / "artifacts" / "week1" / "overlays"
CORNER_NAMES = ("TL", "TR", "BR", "BL")


def main():
    # Đọc manifest đã có cột split.
    manifest_path = INTERIM_ROOT / "manifest_with_split.csv"
    df = pd.read_csv(manifest_path)

    # Chỉ dùng ảnh đã qua bước validation.
    df = df[df["validation_status"] == "valid"]

    selected_parts = []

    # Xử lý từng nền riêng để số ảnh giữa các nền cân bằng.
    for bg_name, bg_df in df.groupby("bg_name"):
        # Lấy một frame đại diện cho mỗi trang gốc trong nền này.
        candidates = bg_df.groupby("model_name").sample(
            n=1,
            random_state=SEED,
        )

        # Chọn tối đa 10 trang gốc khác nhau của nền này.
        selected = candidates.sample(
            n=min(10, len(candidates)),
            random_state=SEED,
        )

        selected_parts.append(selected)
        print(bg_name, ":", len(selected), "ảnh")

    samples = pd.concat(selected_parts)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    saved_count = 0

    for row in samples.itertuples(index=False):
        # Đọc ảnh gốc.
        image = cv2.imread(str(image_path(row.image_path)))

        if image is None:
            print("Không đọc được:", row.image_path)
            continue

        # Lấy góc theo thứ tự TL → TR → BR → BL.
        points = corners_tl_tr_br_bl(row).astype(int)
        contour = points.reshape(-1, 1, 2)

        # Vẽ đường xanh nối bốn góc thành khung giấy.
        cv2.polylines(
            image,
            [contour],
            isClosed=True,
            color=(0, 255, 0),
            thickness=3,
        )

        # Đánh dấu và ghi tên từng góc bằng màu đỏ.
        for corner_name, point in zip(CORNER_NAMES, points):
            x = int(point[0])
            y = int(point[1])

            cv2.circle(image, (x, y), 7, (0, 0, 255), -1)

            cv2.putText(
                image,
                corner_name,
                (x + 8, y - 8),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2,
            )

        # Đặt tên có nền, trang gốc và tên frame để dễ tìm lại.
        source_name = Path(row.image_path).stem
        filename = (
            row.bg_name
            + "_"
            + row.model_name
            + "_"
            + source_name
            + ".jpg"
        )

        output_path = OUTPUT_ROOT / filename
        saved = cv2.imwrite(str(output_path), image)

        if saved:
            saved_count += 1
        else:
            print("Không lưu được:", output_path)

    print()
    print("Đã lưu:", saved_count, "ảnh")
    print("Thư mục:", OUTPUT_ROOT)


if __name__ == "__main__":
    main()
