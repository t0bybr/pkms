import json, os, hashlib, pickle
from rank_bm25 import BM25Okapi
import redis

INDEX_DIR=os.environ.get('INDEX_DIR','/app/index')
REDIS_HOST=os.environ.get('REDIS_HOST','redis')
REDIS_PORT=int(os.environ.get('REDIS_PORT','6379'))

cache = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=False)

class HybridRetriever:
    def __init__(self, db_text):
        self.db_text=db_text
        self.bm25=None
        # Write BM25 cache to a writable path (rag-api runs read-only mounts)
        self.cache_path=os.path.join('/tmp','bm25_index.pkl')
        self._load_or_build()

    def _load_or_build(self):
        if os.path.exists(self.cache_path):
            with open(self.cache_path,'rb') as f:
                self.bm25=pickle.load(f)
        else:
            self.rebuild()

    def rebuild(self):
        corpus=self.db_text.to_list()
        docs=[x['text'] for x in corpus]
        tokenized=[d.lower().split() for d in docs]
        self.bm25=BM25Okapi(tokenized)
        with open(self.cache_path,'wb') as f:
            pickle.dump(self.bm25,f)

    def search(self, query:str, k:int=30):
        key=f"bm25:{hashlib.md5(query.encode()).hexdigest()}:{k}"
        cached=cache.get(key)
        if cached:
            return json.loads(cached)
        scores=self.bm25.get_scores(query.lower().split())
        import numpy as np
        idx=np.argsort(scores)[-k:][::-1]
        corpus=self.db_text.to_list()
        hits=[corpus[i] for i in idx]
        cache.setex(key, 3600, json.dumps(hits))
        return hits
