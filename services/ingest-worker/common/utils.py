import hashlib, os, re
from PIL import Image

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
