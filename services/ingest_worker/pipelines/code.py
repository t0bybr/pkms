import pathlib
from common.db import CODE, CODE_META
from common.batch import BatchProcessor

batch = BatchProcessor(
    table=CODE,
    field_map=lambda r: r,
    batch_size=24,
    flush_seconds=3.0
)

SUPPORTED={'.py','.js','.ts','.tsx','.cpp','.c','.h','.java','.rs','.go','.sh','.ps1','.rb'}

def ingest_code(path: str):
    ext = pathlib.Path(path).suffix.lower()
    if ext not in SUPPORTED: return
    with open(path,'r',encoding='utf-8',errors='ignore') as f:
        code=f.read()
    lines=code.splitlines(); chunks=[]
    for i in range(0, len(lines), 80):
        ch="\n".join(lines[i:i+80])
        if ch.strip(): chunks.append(ch)
    for ch in chunks:
        rec={'path': path, 'code': ch}
        rec.update(CODE_META)
        batch.add(rec)
    batch.flush()
