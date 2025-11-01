import os, pathlib
from common.utils import split_markdown_sections
from common.db import TEXT, TEXT_META
from common.batch import BatchProcessor

DATA_DIR=os.environ.get('DATA_DIR','/app/data')

batch = BatchProcessor(
    table=TEXT,
    field_map=lambda r: r,
    batch_size=24,
    flush_seconds=3.0
)

def ingest_markdown(path: str):
    with open(path,'r',encoding='utf-8') as f:
        raw=f.read()
    sections = split_markdown_sections(raw) or [(pathlib.Path(path).stem, raw)]
    for header, body in sections:
        if not body.strip(): continue
        rec={'path': path, 'title': header or pathlib.Path(path).stem, 'text': body}
        rec.update(TEXT_META)
        batch.add(rec)
    batch.flush()
