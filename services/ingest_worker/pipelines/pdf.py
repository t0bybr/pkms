import os, pathlib
from pdf2image import convert_from_path
from pipelines.vision import ingest_image

DATA_DIR = os.environ.get('DATA_DIR','/app/data')

def ingest_pdf(path: str, dpi=300):
    outdir = os.path.join(DATA_DIR,'tmp','pages',pathlib.Path(path).stem)
    os.makedirs(outdir, exist_ok=True)
    pages = convert_from_path(path, dpi=dpi)
    results=[]
    for i, img in enumerate(pages, 1):
        p = os.path.join(outdir, f"p{i}.jpg")
        img.save(p, 'JPEG', quality=90)
        ingest_image(p)
        results.append(p)
    return results
