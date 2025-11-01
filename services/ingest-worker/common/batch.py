import time
from .embed import embed_texts

class BatchProcessor:
    def __init__(self, table, field_map, batch_size=32, flush_seconds=5.0):
        self.table=table
        self.field_map=field_map
        self.batch_size=batch_size
        self.flush_seconds=flush_seconds
        self.buf=[]
        self.last=time.time()
    def add(self, item):
        self.buf.append(item)
        if len(self.buf)>=self.batch_size or (time.time()-self.last)>=self.flush_seconds:
            self.flush()
    def flush(self):
        if not self.buf: return
        recs=[self.field_map(x) for x in self.buf]
        texts=[r['text'] if 'text' in r else r.get('code','') for r in recs]
        embs=embed_texts(texts)
        for r,e in zip(recs, embs): r['embedding']=e
        self.table.add(recs)
        self.buf=[]; self.last=time.time()
