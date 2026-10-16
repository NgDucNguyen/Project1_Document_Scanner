import cv2
import numpy as np
import os
import math

def get_angle(x1, y1, x2, y2) -> float:
    # Tính góc lệch của đường thẳng so với trục ngang.
    deltaX = x2 - x1
    deltaY = y2 - y1
    return np.arctan2(deltaY, deltaX) * 180 / math.pi

def rotate_image(image, angle):
    # Xoay ảnh một góc xác định xung quanh tâm ảnh
    h, w = image.shape[:2]
    center = (w / 2, h / 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(image, matrix, (w, h), flags=cv2.INTER_CUBIC, borderValue=(255, 255, 255))

def denoise(img):
    # Khử nhiễu hạt giấy nhưng vẫn giữ nguyên độ sáng tự nhiên
    # return cv2.bilateralFilter(img, d=9, sigmaColor=75, sigmaSpace=75)
    return img

def align_document(img):
    # Căn chỉnh góc tài liệu chuẩn theo tài liệu mẫu.
    # Dùng medianBlur thay vì GaussianBlur để bảo toàn cạnh chữ sắc nét
    blurred = cv2.medianBlur(img, 3)
    
    edges = cv2.Canny(blurred, 80, 120)
    
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, 10, minLineLength=20, maxLineGap=10)
    
    aligned = img.copy()
    if lines is not None and len(lines) > 0:
        lines = lines.reshape(-1, 4)
        lines = sorted(lines, key=lambda l: abs(l[2] - l[0]), reverse=True)
        
        for line in lines:
            x1, y1, x2, y2 = line
            if edges.shape[1] > 0 and (abs(x2 - x1) / edges.shape[1]) > 0.25:
                deltaX = x2 - x1
                deltaY = y2 - y1
                angle = np.arctan2(deltaY, deltaX) * 180 / math.pi
                
                # Chỉ xoay khi góc lệch lớn hơn 1 độ
                if abs(angle) > 1.0:
                    h, w = img.shape[:2]
                    center = (w / 2, h / 2)
                    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
                    # Dùng INTER_LINEAR 
                    aligned = cv2.warpAffine(img, matrix, (w, h), flags=cv2.INTER_LINEAR, borderValue=(255, 255, 255))
                    break
            break
            
    return aligned

def run(image_path, output_dir="data/processed"):
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.basename(image_path)
    
    # Đọc ảnh xám gốc
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        print(f"Không thể đọc ảnh tại: {image_path}")
        return

    # Khử nhiễu và căn chỉnh góc (giữ nguyên độ sáng tự nhiên)
    img_denoised = denoise(img)
    img_final = align_document(img_denoised)

    # Lưu ảnh kết quả vào thư mục processed
    output_path = os.path.join(output_dir, base_name)
    # cv2.imwrite(output_path, img_final)
    cv2.imwrite(output_path, img_final, [cv2.IMWRITE_JPEG_QUALITY, 100])
    
    print(f"Đã xử lý xong và lưu ảnh tại: {output_path}")

if __name__ == "__main__":
    sample_dir = "data/raw/subset_2k"
    
    if os.path.exists(sample_dir):
        files = [f for f in os.listdir(sample_dir) if f.endswith(('.jpg', '.png'))]
        total_files = len(files)
        
        if total_files > 0:
            limit = len(files)
            target_files = files[:limit]
            
            for idx, filename in enumerate(target_files):
                image_path = os.path.join(sample_dir, filename)
                print(f"[{idx+1}/{len(target_files)}] Đang xử lý: {filename}")
                run(image_path)
                
            print(f"Hoàn tất chạy thử {len(target_files)} ảnh!")
        else:
            print("Chưa có file ảnh nào trong thư mục subset_2k!")
    else:
        print("Không tìm thấy thư mục dữ liệu raw!")