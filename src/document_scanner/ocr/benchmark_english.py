"""So sánh bố cục Tesseract trên validation FUNSD và hai ảnh tiếng Anh đã scan."""
import argparse
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import cv2
import numpy as np
from prepare_image import prepare_ocr_image

from evaluate_pages import read_page_words, valid_regions, score_regions, MODELS
from prepare_funsd_training import select_validation_pages
from recognize import recognize_image
from metrics import normalize_text,edit_distance

ROOT=Path(__file__).resolve().parents[3]


def write_csv(path,rows):
    with path.open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-name',required=True)
    parser.add_argument('--psms',type=int,nargs='+',default=[3,4,11],choices=[3,4,6,11])
    parser.add_argument('--prepare',action='store_true',help='Thử phóng ảnh nhỏ và thêm viền riêng trước OCR.')
    args=parser.parse_args()
    if not args.run_name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in args.run_name):
        parser.error('Tên lượt chỉ gồm chữ, số, _ và -.')
    folder=ROOT/'artifacts/ocr'/args.run_name
    if folder.exists():raise FileExistsError(str(folder))
    folder.mkdir(parents=True)
    dataset=ROOT/'data/raw/funsd/dataset/training_data'
    ids=sorted(select_validation_pages(sorted((dataset/'images').glob('*.png'))))
    info={'complete':False,'started_at':datetime.now().astimezone().isoformat(),
          'psms':args.psms,'prepare':args.prepare,'model':'funsd_eng','selection':'30 validation pages selected by existing training split; no FUNSD testing_data used for PSM selection.',
          'scope':'No scanner changes. FUNSD full-page input; annotations used only after OCR to score regions. Photo inputs are fixed enhanced crops from scanner audit.',
          'model_sha256':hashlib.sha256((ROOT/'models/funsd_english/funsd_eng.traineddata').read_bytes()).hexdigest(),
          'page_ids':ids,'samples':[],
          'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in Path(__file__).parent.glob('*.py')}}
    (folder/'run_info.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
    rows=[]
    for index,page_id in enumerate(ids,1):
        path=dataset/'images'/(page_id+'.png')
        annotation=dataset/'annotations'/(page_id+'.json')
        regions=valid_regions(json.loads(annotation.read_text(encoding='utf-8')))
        info['samples'].append({'image':str(path.relative_to(ROOT)),
                                'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                                'annotation_sha256':hashlib.sha256(annotation.read_bytes()).hexdigest()})
        for psm in args.psms:
            if args.prepare:
                image=cv2.imdecode(np.fromfile(path,np.uint8),cv2.IMREAD_COLOR)
                prepared,preparation=prepare_ocr_image(image)
                with tempfile.TemporaryDirectory(prefix='ocr_validation_') as temporary:
                    prepared_path=Path(temporary)/'input.png'
                    cv2.imencode('.png',prepared)[1].tofile(prepared_path)
                    words=read_page_words(prepared_path,MODELS['funsd'],psm)
                # Đổi về hệ tọa độ trang gốc trước khi chấm theo vùng nhãn.
                for word in words:
                    x1,y1,x2,y2=word['box']; b=preparation['border']
                    word['box']=[(x1-b)/preparation['scale_x'],(y1-b)/preparation['scale_y'],
                                 (x2-b)/preparation['scale_x'],(y2-b)/preparation['scale_y']]
            else:
                words=read_page_words(path,MODELS['funsd'],psm)
            scores,unassigned=score_regions(page_id,str(psm),regions,words)
            rows.append({'group':'funsd_val','image':page_id,'psm':psm,
                         'characters':sum(r['char_count'] for r in scores),'words':sum(r['word_count'] for r in scores),
                         'char_errors':sum(r['char_errors'] for r in scores),'word_errors':sum(r['word_errors'] for r in scores),
                         'ocr_words':len(words),'unassigned_words':len(unassigned)})
        print(f'Validation {index}/{len(ids)}: {page_id}',flush=True)
    for name,reference_name in [('anh','nhan.txt'),('anh_test_02','nhan_test_02.txt')]:
        path=ROOT/f'artifacts/scanner_dev/scanner_quality_20261119/samples/{name}_enhanced.png'
        ref_path=ROOT/'data/raw/thu_ocr'/reference_name
        ref=normalize_text(ref_path.read_text(encoding='utf-8-sig'))
        for psm in args.psms:
            if args.prepare:
                image=cv2.imdecode(np.fromfile(path,np.uint8),cv2.IMREAD_COLOR)
                prepared,_=prepare_ocr_image(image)
                with tempfile.TemporaryDirectory(prefix='ocr_photo_') as temporary:
                    prepared_path=Path(temporary)/'input.png';cv2.imencode('.png',prepared)[1].tofile(prepared_path)
                    text=recognize_image(prepared_path,'funsd_eng',psm,MODELS['funsd']['tessdata'])
            else:
                text=recognize_image(path,'funsd_eng',psm,MODELS['funsd']['tessdata'])
            (folder/f'{name}_psm{psm}.txt').write_text(text,encoding='utf-8')
            text=normalize_text(text)
            rows.append({'group':'photo_dev','image':name,'psm':psm,
                         'characters':len(ref),'words':len(ref.split()),'char_errors':edit_distance(ref,text),
                         'word_errors':edit_distance(ref.split(),text.split()),'ocr_words':len(text.split()),'unassigned_words':0})
        info['samples'].append({'image':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                                'reference_sha256':hashlib.sha256(ref_path.read_bytes()).hexdigest()})
        print('Photo:',name,flush=True)
    summary=[]
    for group in ['funsd_val','photo_dev']:
        for psm in args.psms:
            part=[r for r in rows if r['group']==group and r['psm']==psm]
            summary.append({'group':group,'psm':psm,'pages':len(part),
                            'cer':sum(r['char_errors'] for r in part)/sum(r['characters'] for r in part),
                            'wer':sum(r['word_errors'] for r in part)/sum(r['words'] for r in part),
                            'unassigned_words':sum(r['unassigned_words'] for r in part)})
    write_csv(folder/'pages.csv',rows);write_csv(folder/'summary.csv',summary)
    info.update(complete=True,finished_at=datetime.now().astimezone().isoformat())
    (folder/'run_info.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':main()
