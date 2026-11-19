"""Chấm IoU dự đoán DocAligner đã lưu; chỉ mở test khi được yêu cầu đánh giá cuối."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil

import cv2
import numpy as np
import pandas as pd

from classic import polygon_iou
from geometry import validate_corners

ROOT = Path(__file__).resolve().parents[3]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-name', required=True)
    parser.add_argument('--final-test-evaluation', action='store_true',
                        help='Xác nhận chấm test sau khi đã chốt phương pháp/cấu hình.')
    args = parser.parse_args()
    if not args.final_test_evaluation:
        parser.error('Chỉ chấm test khi có --final-test-evaluation và đã được phép đánh giá cuối.')
    if not args.run_name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in args.run_name):
        parser.error('Tên lượt chỉ gồm chữ, số, gạch dưới hoặc gạch ngang.')
    output = ROOT/'artifacts/scanner_dev'/args.run_name
    if output.exists():
        raise FileExistsError('Không ghi đè lượt đã có: '+str(output))
    baseline = ROOT/'artifacts/scanner_dev/docaligner_t8_full'
    info_path = baseline/'run_info.json'
    original = json.loads(info_path.read_text(encoding='utf-8'))
    manifest_path = ROOT/'data/interim/manifest_with_split.csv'
    model_path = ROOT/'models/docaligner/fastvit_t8.onnx'
    if not original.get('complete'):
        raise ValueError('Lượt dự đoán gốc chưa hoàn tất.')
    if sha256(manifest_path) != original['manifest_sha256'] or sha256(model_path) != original['model_sha256']:
        raise ValueError('Manifest hoặc trọng số đã khác lượt dự đoán gốc.')
    manifest = pd.read_csv(manifest_path)
    predictions = pd.read_csv(baseline/'results.csv')
    if manifest.image_path.duplicated().any() or predictions.image_path.duplicated().any():
        raise ValueError('Danh sách ảnh bị trùng.')
    if set(manifest.image_path) != set(predictions.image_path):
        raise ValueError('Dự đoán thiếu hoặc thừa ảnh so với manifest.')
    if manifest.groupby('model_name')['split'].nunique().gt(1).any():
        raise ValueError('Tài liệu gốc xuất hiện trong nhiều tập.')
    if manifest.split.value_counts().to_dict() != {'train': 17495, 'test': 4202, 'val': 3192}:
        raise ValueError('Chia tập không khớp mốc đã chốt.')
    labels = ['image_path','split','bg_name','image_width','image_height'] + [c+'_'+a for c in ('tl','tr','br','bl') for a in ('x','y')]
    report = predictions.merge(manifest[labels],on=['image_path','split','bg_name'],how='left',validate='one_to_one')
    if report[labels].isna().any().any():
        raise ValueError('Không khớp nhãn hoặc thông tin ảnh.')
    # Đóng băng cấu hình và nguồn trước khi đọc điểm test, không chỉnh detector từ kết quả.
    source = output/'source'
    source.mkdir(parents=True)
    snapshots = list((ROOT/'src/document_scanner/scanner').glob('*.py'))
    snapshots += [ROOT/'src/document_scanner/pipeline.py', ROOT/'configs/scanner.json', ROOT/'configs/scan.json']
    for path in snapshots:
        destination = source/path.relative_to(ROOT)
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(path,destination)
    info = {'complete':False,'started_at':datetime.now().astimezone().isoformat(),
            'method':'docaligner_fastvit_t8','test_scored':True,'iou_threshold':0.9,
            'authorization':'User requested final evaluation after choosing the current scanner on 2026-11-19.',
            'scope':'Cached detector corners only; no full scan, fallback, appearance or OCR evaluation.',
            'original_run':str(baseline.relative_to(ROOT)),
            'original_results_sha256':sha256(baseline/'results.csv'),
            'original_run_info_sha256':sha256(info_path),
            'manifest_sha256':sha256(manifest_path),'model_sha256':sha256(model_path),
            'source_sha256':{str(p.relative_to(source)):sha256(p) for p in source.rglob('*') if p.is_file()},
            'opencv':cv2.__version__,
            'limitations':['Pretrained training overlap with SmartDoc is unverified.',
                           'Current geometry validator checked on all cached corners; inference not rerun.',
                           'Train is a project split, not a claim of training DocAligner.']}
    (output/'run_info.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
    ious, invalid = [], []
    for row in report.itertuples(index=False):
        corners = np.array([[getattr(row,f'pred_{i}_x'),getattr(row,f'pred_{i}_y')] for i in range(4)],np.float32)
        expected = np.array([[getattr(row,c+'_x'),getattr(row,c+'_y')] for c in ('tl','tr','br','bl')],np.float32)
        if not np.isfinite(expected).all() or not cv2.isContourConvex(expected):
            raise ValueError('Nhãn không hợp lệ: '+row.image_path)
        bad = False
        if str(row.detected).lower() == 'true':
            # validate_corners chỉ dùng kích thước ảnh; không cần mở lại 24.889 ảnh.
            shape_only = np.broadcast_to(np.uint8(0),(int(row.image_height),int(row.image_width),3))
            try:
                corners = validate_corners(shape_only,corners)
                value = polygon_iou(corners,expected)
            except (ValueError,cv2.error):
                bad, value = True, 0.0
        else:
            value = 0.0
        invalid.append(bad)
        ious.append(value)
    report['iou'] = ious
    report['iou_ge_0_9'] = report.iou.ge(.9)
    report['invalid_current_geometry'] = invalid
    # Điểm train/val chấm lại phải khớp phép chấm đã lưu trước khi mở test.
    prior = predictions.set_index('image_path')['iou']
    development = report[report.split.isin(['train','val'])]
    if not np.allclose(development.iou,development.image_path.map(prior),atol=1e-7):
        raise ValueError('IoU train/validation không khớp mốc cũ; không kết luận từ lượt này.')
    report.to_csv(output/'results.csv',index=False)
    summary = []
    for split,group in report.groupby('split'):
        for background,part in [('all',group),*group.groupby('bg_name')]:
            detected = part.detected.astype(str).str.lower().eq('true') & ~part.invalid_current_geometry
            summary.append({'method':'docaligner','split':split,'background':background,
                            'images':len(part),'detected':int(detected.sum()),
                            'detection_rate':float(detected.mean()),
                            'no_candidate':int(part.status.eq('no_candidate').sum()),
                            'low_confidence':int(part.status.eq('low_confidence').sum()),
                            'uncertain':int(part.status.eq('uncertain').sum()),
                            'errors':int(part.error.notna().sum()),
                            'iou_ge_0_9':int(part.iou_ge_0_9.sum()),
                            'iou_pass_rate':float(part.iou_ge_0_9.mean()),'mean_iou':float(part.iou.mean())})
    summary = pd.DataFrame(summary)
    summary.to_csv(output/'summary.csv',index=False)
    info.update(complete=True,finished_at=datetime.now().astimezone().isoformat(),images=len(report),
                invalid_current_geometry=int(sum(invalid)))
    (output/'run_info.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
    print(summary[summary.background.eq('all')].to_string(index=False))
    print('Kết quả:',output)


if __name__ == '__main__':
    main()
