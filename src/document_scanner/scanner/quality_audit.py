"""Kiểm tra bổ sung scanner đã chốt trên mẫu nhỏ; không chỉnh ngưỡng từ kết quả."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

import cv2
import numpy as np
import pandas as pd

if __package__ in (None, ''):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scanner.scan_image import scan_document, ScanRejected
from scanner.appearance import enhance_document
from ocr.recognize import recognize_image, TESSERACT_PATH
from ocr.metrics import normalize_text, edit_distance

ROOT=Path(__file__).resolve().parents[3]


def hash_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_image(path):
    image=cv2.imdecode(np.fromfile(path,dtype=np.uint8),cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError('Không đọc được ảnh: '+str(path))
    return image


def save_image(path,image):
    cv2.imencode(path.suffix,image)[1].tofile(path)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-name',required=True)
    args=parser.parse_args()
    if not args.run_name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in args.run_name):
        parser.error('Tên lượt chỉ dùng chữ, số, _ và -.')
    output=ROOT/'artifacts/scanner_dev'/args.run_name
    if output.exists():
        raise FileExistsError('Không ghi đè: '+str(output))
    output.mkdir(parents=True)
    samples=output/'samples'; samples.mkdir()
    source=output/'source'; source.mkdir()
    for path in [*Path(__file__).parent.glob('*.py'),*list((ROOT/'src/document_scanner/ocr').glob('*.py')),ROOT/'configs/scanner.json',ROOT/'configs/scan.json']:
        target=source/path.relative_to(ROOT); target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(path,target)
    info={'complete':False,'started_at':datetime.now().astimezone().isoformat(),
          'scope':'Post-freeze diagnostic audit; small existing samples, no threshold tuning.',
          'run_name':args.run_name,'python':platform.python_version(),'opencv':cv2.__version__,
          'opencv_threads':1,'model_sha256':hash_file(ROOT/'models/docaligner/fastvit_t8.onnx'),
          'ocr_model_sha256':hash_file(ROOT/'models/funsd_english/funsd_eng.traineddata'),
          'tesseract':subprocess.run([str(TESSERACT_PATH),'--version'],capture_output=True,text=True).stdout.splitlines()[0],
          'source_sha256':{str(p.relative_to(source)):hash_file(p) for p in source.rglob('*') if p.is_file()}}
    (output/'run_info.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
    cv2.setNumThreads(1)
    # Sai số góc chỉ chấm dự đoán đã đóng băng, không chạy lại hoặc chỉnh mô hình.
    cached=ROOT/'artifacts/scanner_dev/docaligner_final_20261119/results.csv'
    final_info=json.loads(cached.with_name('run_info.json').read_text(encoding='utf-8'))
    if not final_info['complete']:
        raise ValueError('Lượt chấm cuối chưa hoàn tất.')
    frame=pd.read_csv(cached)
    corner={}
    for split,part in frame.groupby('split'):
        pred=part[[f'pred_{i}_{a}' for i in range(4) for a in ('x','y')]].to_numpy().reshape(-1,4,2)
        expected=part[[f'{c}_{a}' for c in ('tl','tr','br','bl') for a in ('x','y')]].to_numpy().reshape(-1,4,2)
        # Nhãn và đầu ra có thể bắt đầu từ hai đỉnh khác nhau trên cùng tứ giác.
        # So 4 phép dịch chu kỳ, giữ chiều đi quanh đa giác; không đo hướng đọc.
        distance=np.stack([np.linalg.norm(pred-np.roll(expected,k,axis=1),axis=2).mean(axis=1)
                           for k in range(4)]).min(axis=0)
        normalized=distance/np.hypot(part.image_width,part.image_height)*100
        corner[split]={'images':len(part),'mean_corner_error_px':float(distance.mean()),
                       'median_mean_corner_error_pct_diagonal':float(np.median(normalized)),
                       'p95_mean_corner_error_pct_diagonal':float(np.percentile(normalized,95)),
                       'invalid_geometry':int(part.invalid_current_geometry.sum())}
    records=[]; ocr=[]; words=[]
    model_dir=ROOT/'models/funsd_english'
    # Hai ảnh có TXT người dùng, bốn ảnh thực tế khác và tám trang FUNSD cố định.
    paths=[ROOT/'data/raw/thu_ocr'/name for name in ['anh.jpg','anh_test_02.jpg','anh_thu.png','anh_tu_chup.jpg']]
    paths += [ROOT/'data/raw/thu_detect'/name for name in ['anh_viet.jpg','anh_2.jpg']]
    funsd=ROOT/'data/raw/funsd/dataset/testing_data'
    paths += sorted((funsd/'images').glob('*.png'))[:8]
    jobs=[]
    for path in paths:
        jobs.append({'name':path.stem,'group':'funsd' if path.parent.parent==funsd else 'photo',
                     'source':str(path.relative_to(ROOT)),'source_sha256':hash_file(path),
                     'image':read_image(path),'expected_accept':True})
    # Các ROI đã xem trên ảnh nguồn: không có tờ giấy chính, không đưa nhãn vào scanner.
    negative_source=ROOT/'data/raw/smartdoc/background05/patent003/frame_0030.jpeg'
    base=read_image(negative_source)
    regions={'book_cover':[130,160,620,760],'cup':[1510,20,1910,425],
             'table_bottom':[650,820,1300,1030],'cord_table':[1390,580,1910,830],
             'table_left':[20,790,600,1010],'table_top':[650,0,1350,130]}
    for name,(x1,y1,x2,y2) in regions.items():
        image=base[y1:y2,x1:x2].copy(); save_image(samples/(name+'.png'),image)
        jobs.append({'name':name,'group':'real_negative_roi','source':str(negative_source.relative_to(ROOT)),
                     'source_sha256':hash_file(negative_source),'roi':[x1,y1,x2,y2],
                     'image':image,'expected_accept':False})
    for name,value in [('blank_white',255),('flat_dark',25)]:
        image=np.full((700,500,3),value,np.uint8); save_image(samples/(name+'.png'),image)
        jobs.append({'name':name,'group':'synthetic_invalid','source':'generated_constant',
                     'image':image,'expected_accept':False})
    page=np.full((700,500,3),255,np.uint8)
    for y in range(60,660,35):
        cv2.putText(page,'Document scanner quality test',(25,y),cv2.FONT_HERSHEY_SIMPLEX,.65,(30,30,30),1)
    page=cv2.GaussianBlur(page,(101,101),25); save_image(samples/'heavy_blur.png',page)
    jobs.append({'name':'heavy_blur','group':'synthetic_blur','source':'generated_blurred_text',
                 'image':page,'expected_accept':False})
    # Một lượt làm nóng, không dùng kết quả vào thống kê tốc độ.
    try:
        scan_document(jobs[0]['image'],language='funsd_eng',tessdata_dir=model_dir)
    except ScanRejected:
        pass
    for job in jobs:
        image=job.pop('image'); record=dict(job)
        started=time.perf_counter()
        try:
            color,scan_info=scan_document(image,language='funsd_eng',tessdata_dir=model_dir,enhance=False)
            enhanced,enhancement=enhance_document(color)
            record.update(accepted=True,status=scan_info['scanner_status'],info=scan_info)
        except ScanRejected as error:
            color=enhanced=None
            record.update(accepted=False,status=error.info.get('scanner_status'),info=error.info)
        except Exception as error:
            color=enhanced=None
            record.update(accepted=False,status='processing_error',error=str(error))
        record['scan_ms']=(time.perf_counter()-started)*1000
        records.append(record)
        print(job['name'],record['status'],round(record['scan_ms']),'ms',flush=True)
        # Đo giữ diện tích hộp từ thật bằng ma trận scan; không dùng nhãn chọn crop.
        if job['group']=='funsd':
            annotation=funsd/'annotations'/(job['name']+'.json')
            labels=json.loads(annotation.read_text(encoding='utf-8'))
            boxes=[w['box'] for block in labels['form'] for w in block['words'] if w['text'].strip() and w['box'][2]>w['box'][0] and w['box'][3]>w['box'][1]]
            kept=0
            if color is not None:
                height,width=color.shape[:2]
                boundary=np.array([[0,0],[width-1,0],[width-1,height-1],[0,height-1]],np.float32)
                transform=np.array(record['info']['T_source_to_output'],np.float64)
                for x1,y1,x2,y2 in boxes:
                    polygon=np.array([[[x1,y1],[x2,y1],[x2,y2],[x1,y2]]],np.float32)
                    projected=cv2.perspectiveTransform(polygon,transform)[0]
                    area=cv2.contourArea(projected)
                    intersection,_=cv2.intersectConvexConvex(projected,boundary)
                    kept+=area>0 and intersection/area>=.98
            words.append({'image':job['name'],'annotation_sha256':hash_file(annotation),
                          'word_boxes':len(boxes),'retained_98pct':int(kept),'accepted':record['accepted']})
        if job['name'] in ['anh','anh_test_02']:
            reference_path=ROOT/'data/raw/thu_ocr'/('nhan.txt' if job['name']=='anh' else 'nhan_test_02.txt')
            reference=normalize_text(reference_path.read_text(encoding='utf-8-sig'))
            variants={'color':color,'gray':None if color is None else cv2.cvtColor(color,cv2.COLOR_BGR2GRAY),'enhanced':enhanced}
            for variant,variant_image in variants.items():
                if variant_image is None: prediction=''
                else:
                    variant_path=samples/(job['name']+'_'+variant+'.png'); save_image(variant_path,variant_image)
                    prediction=recognize_image(variant_path,'funsd_eng',11,model_dir)
                    (samples/(job['name']+'_'+variant+'.txt')).write_text(prediction,encoding='utf-8')
                prediction=normalize_text(prediction)
                ocr.append({'image':job['name'],'variant':variant,'reference_sha256':hash_file(reference_path),
                            'characters':len(reference),'words':len(reference.split()),
                            'char_edits':edit_distance(reference,prediction),
                            'word_edits':edit_distance(reference.split(),prediction.split())})
    groups={}
    for group in sorted(set(r['group'] for r in records)):
        part=[r for r in records if r['group']==group]
        groups[group]={'images':len(part),'accepted':sum(r['accepted'] for r in part),
                       'processing_errors':sum(r['status']=='processing_error' for r in part),
                       'scan_ms_median':float(np.median([r['scan_ms'] for r in part])),
                       'scan_ms_p95':float(np.percentile([r['scan_ms'] for r in part],95))}
    combined={}
    for variant in ['color','gray','enhanced']:
        part=[r for r in ocr if r['variant']==variant]
        combined[variant]={'cer':sum(r['char_edits'] for r in part)/sum(r['characters'] for r in part),
                           'wer':sum(r['word_edits'] for r in part)/sum(r['words'] for r in part)}
    summary={'corner_error':corner,'groups':groups,'ocr_two_existing_photos':combined,
             'retention_funsd':{'pages':len(words),'boxes':sum(w['word_boxes'] for w in words),
                               'kept':sum(w['retained_98pct'] for w in words)},
             'limitations':['No thresholds changed after final test.',
                            'Negative ROIs are six correlated crops of one SmartDoc train frame, not an independent negative dataset.',
                            'FUNSD pages and English photos are existing development material, not new blind test.',
                            'Word-box retention measures crop coverage before enhancement, not preservation of every glyph after enhancement.',
                            'Runtime excludes disk writes and final OCR; small sample, one CPU thread, warmed model.',
                            'Natural Vietnamese reading direction and diacritic preservation lack independent ground truth.']}
    (output/'results.json').write_text(json.dumps({'records':records,'retention':words,'ocr':ocr},ensure_ascii=False,indent=2),encoding='utf-8')
    (output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    info.update(complete=True,finished_at=datetime.now().astimezone().isoformat(),images=len(records),
                final_predictions_sha256=hash_file(cached))
    (output/'run_info.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':
    main()
