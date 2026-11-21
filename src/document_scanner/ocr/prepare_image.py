"""Chuẩn bị ảnh riêng cho OCR, không cắt/nắn lại hoặc sửa nội dung trang."""
import cv2
import numpy as np


def prepare_ocr_image(image):
    height,width=image.shape[:2]
    # Chữ nhỏ trên ảnh thấp phân giải cần thêm pixel cho bộ đọc, không sinh chi tiết mới.
    scale=min(2.0,max(1.0,1800/max(height,width)))
    prepared=cv2.resize(image,None,fx=scale,fy=scale,interpolation=cv2.INTER_CUBIC) if scale>1 else image.copy()
    scale_x=prepared.shape[1]/width
    scale_y=prepared.shape[0]/height
    # Trang đã đủ lớn giữ nguyên pixel; thêm viền không cải thiện hai ảnh chụp đối chứng.
    border=12 if scale>1 else 0
    prepared=cv2.copyMakeBorder(prepared,border,border,border,border,cv2.BORDER_CONSTANT,value=(255,255,255))
    transform=np.array([[scale_x,0,border],[0,scale_y,border],[0,0,1]],np.float64)
    return prepared,{'applied':scale>1,'method':'upscale_small_page_and_white_border' if scale>1 else 'original_size',
                     'scale_x':scale_x,'scale_y':scale_y,
                     'border':border,'source_size':[width,height],
                     'output_size':[prepared.shape[1],prepared.shape[0]],'T_scan_to_ocr':transform.tolist(),
                     'note':'Chỉ nội suy và thêm viền; không khôi phục chữ mờ hoặc nội dung đã mất.'}
