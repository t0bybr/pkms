import os, json, pathlib, requests, time
from common.db import TEXT, TEXT_META
from common.batch import BatchProcessor
from common.embed import embed_texts
from common.utils import http_post

DATA_DIR=os.environ.get('DATA_DIR','/app/data')
STT_URL=os.environ.get('STT_URL','http://speech-to-text:8004')

def ingest_audio(path: str):
    with open(path,'rb') as f:
        resp = http_post(f"{STT_URL}/transcribe", files={'file': f}, timeout=180)
    text = resp.json().get('text','').strip()
    if not text: return
    md_path = os.path.join(DATA_DIR, 'notes', '_audio', pathlib.Path(path).stem + '.md')
    os.makedirs(os.path.dirname(md_path), exist_ok=True)
    frontmatter = {
        'source_type': 'audio_stt',
        'orig_path': path,
        'created_at': time.strftime('%Y-%m-%d'),
        'tags': ['audio']
    }
    with open(md_path,'w',encoding='utf-8') as f:
        f.write('---\n'); f.write(json.dumps(frontmatter, ensure_ascii=False, indent=2)); f.write('\n---\n\n')
        f.write(text)
    embs = embed_texts([text])
    TEXT.add([{ 'path': md_path, 'title': pathlib.Path(md_path).stem, 'text': text, 'embedding': embs[0], **TEXT_META }])
