import os, json, pathlib, requests, cv2, numpy as np
from services.ingest_worker.common.db import IMAGE, META
from services.ingest_worker.common.utils import sha256_file, save_thumbnail
from services.ingest_worker.pipelines.text import ingest_markdown

DATA_DIR=os.environ.get('DATA_DIR','/app/data')
QWEN=os.environ.get('QWEN_URL','http://qwen-vl-ocr:8001')
LAYOUT=os.environ.get('LAYOUT_URL','http://layout-detector:8002')
CLIP=os.environ.get('CLIP_URL','http://clip-embed:8003')

def _layout(path):
    with open(path,'rb') as f:
        r=requests.post(f"{LAYOUT}/detect", files={'file': f}); r.raise_for_status(); return r.json()['bboxes']

def _ocr(path):
    with open(path,'rb') as f:
        r=requests.post(f"{QWEN}/ocr", files={'file': f}, data={'mode':'text'}); r.raise_for_status(); return r.json()['text']

def _clip(path):
    with open(path,'rb') as f:
        r=requests.post(f"{CLIP}/embed_image", files={'file': f}); r.raise_for_status(); return r.json()['vector']

def _heuristic_sketch(img_bgr, text_boxes):
    mask = np.ones(img_bgr.shape[:2], dtype=np.uint8)*255
    for b in text_boxes:
        x,y,w,h = map(int, b['bbox']); cv2.rectangle(mask,(x,y),(x+w,y+h),0,-1)
    gray=cv2.cvtColor(cv2.bitwise_and(img_bgr,img_bgr,mask=mask), cv2.COLOR_BGR2GRAY)
    edges=cv2.Canny(gray,50,150); edges=cv2.dilate(edges,np.ones((3,3),np.uint8),1)
    contours,_=cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    H,W=gray.shape; regions=[]
    for c in contours:
        x,y,w,h=cv2.boundingRect(c); area=w*h
        if area<0.003*W*H: continue
        roi=edges[y:y+h,x:x+w]; dens=roi.mean()/255.0; asp=w/max(1,h)
        if dens>0.10 and 0.2<asp<5.0: regions.append({'bbox':[x,y,w,h],'cls':'figure','conf':0.5})
    return regions

def ingest_image(path: str):
    try: boxes=_layout(path)
    except: boxes=[]
    text_boxes=[b for b in boxes if b.get('cls') in ('text','title','list')]
    fig_boxes=[b for b in boxes if b.get('cls') in ('figure','table')]
    text=_ocr(path)
    img=cv2.imread(path)
    if not fig_boxes:
        fig_boxes=_heuristic_sketch(img, text_boxes)
    image_records=[]
    for b in fig_boxes:
        x,y,w,h=map(int,b['bbox'])
        crop=img[y:y+h,x:x+w]
        crop_path=os.path.join(DATA_DIR,'thumbs',f"{pathlib.Path(path).stem}_crop_{x}_{y}_{w}_{h}.jpg")
        os.makedirs(os.path.dirname(crop_path), exist_ok=True)
        cv2.imwrite(crop_path,crop)
        vec=_clip(crop_path)
        rec={
            'path_crop': crop_path,
            'bbox':[x,y,w,h],
            'page_sha': sha256_file(path),
            'primary_text_id': None,
            'nearest_heading': None,
            'clip_embedding': vec,
        }
        rec.update(META)
        image_records.append(rec)
    if image_records:
        IMAGE.add(image_records)
    sha=sha256_file(path)
    md_dir=os.path.join(DATA_DIR,'notes','_ingested'); os.makedirs(md_dir, exist_ok=True)
    md_path=os.path.join(md_dir, pathlib.Path(path).stem + '.md')
    thumb_path=os.path.join(DATA_DIR,'thumbs', pathlib.Path(path).stem + '_256.jpg')
    save_thumbnail(path, thumb_path)
    fm={
        'source_type':'image_ocr','orig_path':path,'image_sha256':sha,'page':1,
        'thumb_path':thumb_path,'tags':[]
    }
    with open(md_path,'w',encoding='utf-8') as f:
        f.write('---\n'); f.write(json.dumps(fm, ensure_ascii=False, indent=2)); f.write('\n---\n\n')
        f.write('# OCR\n\n'); f.write(text.strip())
    ingest_markdown(md_path)
