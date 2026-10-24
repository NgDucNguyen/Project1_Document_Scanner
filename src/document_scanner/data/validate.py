import cv2
import numpy as np

from adapters import (
    INTERIM_ROOT,
    corners_tl_tr_br_bl,
    image_path,
    load_metadata,
)

def validate_row(row):
    path = image_path(row.image_path)

    # Kiểm tra file ảnh có tồn tại không.
    if not path.is_file():
        return "missing_image", None, None

    image = cv2.imread(str(path), cv2.IMREAD_COLOR)

    if image is None:
        return "unreadable_image", None, None

    # shape trả về chiều cao, chiều rộng và số kênh màu.
    height, width = image.shape[:2]

    # Lấy bốn góc của tài liệu theo thứ tự TL, TR, BR, BL.
    points = corners_tl_tr_br_bl(row)

    # Kiểm tra tọa độ có bị thiếu hoặc lỗi
    if not np.isfinite(points).all():
        return "non_finite_corner", width, height

    # Bốn góc phải là bốn vị trí khác nhau.
    if len(np.unique(points, axis=0)) != 4:
        return "duplicate_corner", width, height

    # Tách tọa độ x và y để kiểm tra chúng có nằm trong ảnh không.
    x = points[:, 0]
    y = points[:, 1]

    if (x < 0).any() or (x >= width).any():
        return "corner_outside_image", width, height

    if (y < 0).any() or (y >= height).any():
        return "corner_outside_image", width, height

    # OpenCV cần mảng điểm có dạng (4, 1, 2).
    contour = points.reshape(-1, 1, 2)

    # Loại tứ giác suy biến hoặc có diện tích không quá 1 pixel vuông.
    if cv2.contourArea(contour) <= 1:
        return "zero_area", width, height

    # Tứ giác phải lồi, không bị gấp hoặc tự cắt.
    if not cv2.isContourConvex(contour):
        return "non_convex", width, height

    # Qua được tất cả kiểm tra thì ảnh và nhãn hợp lệ.
    return "valid", width, height

def main():
    df = load_metadata()
    results = []

    for index, row in enumerate(df.itertuples(index=False), start=1):
        status, width, height = validate_row(row)
        results.append((status, width, height))

        if index % 1000 == 0:
            print("Đã kiểm tra", index, "/", len(df))

    # Thêm kết quả kiểm tra và kích thước ảnh vào bảng.
    df[["validation_status", "image_width", "image_height"]] = results

    # Tạo thư mục data/interim nếu chưa có.
    INTERIM_ROOT.mkdir(parents=True, exist_ok=True)

    manifest_path = INTERIM_ROOT / "manifest.csv"
    invalid_path = INTERIM_ROOT / "invalid_rows.csv"

    # manifest.csv chứa tất cả ảnh và trạng thái của chúng.
    df.to_csv(manifest_path, index=False)

    # invalid_rows.csv chỉ chứa những dòng có vấn đề.
    df[df["validation_status"] != "valid"].to_csv(
        invalid_path,
        index=False,
    )

    # In thống kê để bạn kiểm tra nhanh.
    print()
    print("Kết quả kiểm tra:")
    print(df["validation_status"].value_counts())
    print("Manifest:", manifest_path)
    print("Các dòng lỗi:", invalid_path)

if __name__ == "__main__":
    main()
