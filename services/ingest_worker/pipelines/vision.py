import os, json, pathlib, requests, cv2, numpy as np, logging, re, hashlib
from common.db import IMAGE, IMAGE_META
from common.utils import sha256_file, save_thumbnail, http_post, ensure_free_space
from pipelines.text import ingest_markdown
from domains.finanzamt import integrate_finanzamt

DATA_DIR=os.environ.get('DATA_DIR','/app/data')
QWEN=os.environ.get('QWEN_URL','http://qwen-vl-ocr:8001')
LAYOUT=os.environ.get('LAYOUT_URL','http://layout-detector:8002')
CLIP=os.environ.get('CLIP_URL','http://clip-embed:8003')

def _layout(path):
    with open(path,'rb') as f:
        r=http_post(f"{LAYOUT}/detect", files={'file': f}, timeout=30)
        return r.json()['bboxes']

def _ocr(path):
    with open(path,'rb') as f:
        r=http_post(f"{QWEN}/ocr", files={'file': f}, data={'mode':'text'}, timeout=120)
        return r.json()['text']

def _clip(path):
    with open(path,'rb') as f:
        r=http_post(f"{CLIP}/embed_image", files={'file': f}, timeout=30)
        return r.json()['vector']

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
    except Exception: boxes=[]
    text_boxes=[b for b in boxes if b.get('cls') in ('text','title','list')]
    fig_boxes=[b for b in boxes if b.get('cls') in ('figure','table')]
    text=_ocr(path)
    img=cv2.imread(path)
    if not fig_boxes:
        fig_boxes=_heuristic_sketch(img, text_boxes)
    image_records=[]
    base_name = pathlib.Path(path).name
    base_stem_raw = pathlib.Path(base_name).stem
    base_stem = re.sub(r'[^\w\-.]','_', base_stem_raw)
    if base_stem in ('', '.', '..'):
        base_stem = f"unnamed_{hashlib.sha256(path.encode()).hexdigest()[:8]}"
    base_stem = base_stem[:200]
    for b in fig_boxes:
        x,y,w,h=map(int,b['bbox'])
        crop=img[y:y+h,x:x+w]
        crop_path=os.path.join(DATA_DIR,'thumbs',f"{base_stem}_crop_{x}_{y}_{w}_{h}.jpg")
        os.makedirs(os.path.dirname(crop_path), exist_ok=True)
        ensure_free_space(os.path.dirname(crop_path))
        cv2.imwrite(crop_path,crop)
        vec=_clip(crop_path)
        rec={
            'path_crop': crop_path,
            'bbox':[x,y,w,h],
            'page_sha': sha256_file(path),
            'primary_text_id': None,
            'nearest_heading': None,
            'embedding': vec,
        }
        rec.update(IMAGE_META)
        image_records.append(rec)
    if image_records:
        IMAGE.add(image_records)
    sha=sha256_file(path)
    md_dir=os.path.join(DATA_DIR,'notes','_ingested'); os.makedirs(md_dir, exist_ok=True)
    md_path=os.path.join(md_dir, pathlib.Path(path).stem + '.md')
    thumb_path=os.path.join(DATA_DIR,'thumbs', base_stem + '_256.jpg')
    ensure_free_space(os.path.dirname(thumb_path))
    save_thumbnail(path, thumb_path)
    fm={
        'source_type':'image_ocr','orig_path':path,'image_sha256':sha,'page':1,
        'thumb_path':thumb_path,'tags':[]
    }
    with open(md_path,'w',encoding='utf-8') as f:
        f.write('---\n'); f.write(json.dumps(fm, ensure_ascii=False, indent=2)); f.write('\n---\n\n')
        f.write('# OCR\n\n'); f.write(text.strip())
    try:
        integrate_finanzamt(md_path, text)
    except Exception:
        logging.getLogger('ingest-vision').warning('finanzamt_integration_failed path=%s', md_path, exc_info=True)
    ingest_markdown(md_path)
