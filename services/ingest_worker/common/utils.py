import hashlib, os, re, time, shutil
from PIL import Image
Image.MAX_IMAGE_PIXELS = int(os.getenv('MAX_IMAGE_PIXELS','178956970'))

import requests, os

def http_post(url, *, files=None, data=None, json=None, timeout=30, retries=3, backoff=0.5, headers=None):
    last_err=None
    api_key=os.environ.get('API_KEY')
    base_headers={'X-API-Key': api_key} if api_key else {}
    if headers:
        base_headers.update(headers)
    for i in range(retries):
        try:
            resp = requests.post(url, files=files, data=data, json=json, headers=base_headers, timeout=timeout)
            resp.raise_for_status()
            return resp
        except Exception as e:
            last_err=e
            time.sleep(backoff*(2**i))
    raise last_err

def ensure_free_space(dir_path: str, min_free_mb: int = None):
    if min_free_mb is None:
        min_free_mb = int(os.getenv('MIN_FREE_MB','100'))
    free = shutil.disk_usage(dir_path).free
    if free < min_free_mb*1024*1024:
        raise OSError(f"insufficient disk space in {dir_path}: {free} bytes free")

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda: f.read(1<<20), b''):
            h.update(chunk)
    return h.hexdigest()

def save_thumbnail(src_path: str, dst_path: str, size=(256,256)):
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    img = Image.open(src_path).convert('RGB')
    img.thumbnail(size)
    img.save(dst_path, quality=80)

def split_markdown_sections(text: str):
    sections=[]; current=[]; header=""
    for line in text.splitlines():
        if re.match(r"^#{1,3} ", line):
            if current:
                sections.append((header, "\n".join(current).strip()))
                current=[]
            header=line.strip()
        else:
            current.append(line)
    if current:
        sections.append((header, "\n".join(current).strip()))
    return sections
