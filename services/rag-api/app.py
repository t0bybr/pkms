import os, json, time, hashlib, sqlite3, logging
from collections import deque
from fastapi import FastAPI, Query, Header, HTTPException, Response, Request, Depends
from pydantic import BaseModel
from typing import Optional, List
from fastapi.middleware.cors import CORSMiddleware
import lancedb
from sentence_transformers import SentenceTransformer
import requests
import redis
from rrf import reciprocal_rank_fusion
from hybrid import HybridRetriever, cache

# Pydantic Models
class Hit(BaseModel):
    id: Optional[str] = None
    path: Optional[str] = None
    title: Optional[str] = None
    text: Optional[str] = None
    code: Optional[str] = None
    path_crop: Optional[str] = None
    bbox: Optional[List[float]] = None
    page_sha: Optional[str] = None
    primary_text_id: Optional[str] = None
    nearest_heading: Optional[str] = None

class QueryResponse(BaseModel):
    answer: str
    hits: List[Hit]

class IngestStatus(BaseModel):
    processed: int
    retry_total: int
    deadletter_count: int

API_KEY=os.environ.get('API_KEY')
OLLAMA=os.environ.get('OLLAMA_URL','http://ollama:11434')
CLIP_URL=os.environ.get('CLIP_URL','http://clip-embed:8003')
INDEX_DIR=os.environ.get('INDEX_DIR','/app/index')
DATA_DIR=os.environ.get('DATA_DIR','/app/data')
REDIS_HOST=os.environ.get('REDIS_HOST','redis')
REDIS_PORT=int(os.environ.get('REDIS_PORT','6379'))
REDIS_PASSWORD=os.environ.get('REDIS_PASSWORD')

app=FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

log = logging.getLogger("rag-api")
logging.basicConfig(level=os.getenv('LOG_LEVEL','INFO'), format='%(asctime)s %(levelname)s %(name)s %(message)s')
if API_KEY == 'change_me_local_only':
    log.warning("weak API key in use; set API_KEY in environment for production")

DB=lancedb.connect(INDEX_DIR)
_names = DB.table_names()
TEXT = DB.open_table('text_v2') if 'text_v2' in _names else (DB.open_table('text_v1') if 'text_v1' in _names else None)
CODE = DB.open_table('code_v2') if 'code_v2' in DB.table_names() else (DB.open_table('code_v1') if 'code_v1' in DB.table_names() else None)
IMAGE= DB.open_table('image_v2') if 'image_v2' in DB.table_names() else (DB.open_table('image_v1') if 'image_v1' in DB.table_names() else None)
EMB=SentenceTransformer('BAAI/bge-m3')

hybrid = HybridRetriever(TEXT) if TEXT else None
metrics = {"queries_total":0, "latencies": deque(maxlen=1000)}
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True, password=REDIS_PASSWORD)

def auth(x_api_key: str = Header(None)):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(401, "unauthorized")

@app.get('/health')
def health():
    return {'ok': True}

@app.get('/metrics')
def prom():
    arr=sorted(list(metrics['latencies'])); n=len(arr)
    p50=arr[int(0.5*n)] if n else 0; p95=arr[int(0.95*n)] if n else 0
    body = f"queries_total {metrics['queries_total']}\nquery_latency_ms_p50 {p50}\nquery_latency_ms_p95 {p95}\n"
    return Response(body, media_type='text/plain')

@app.get('/cache/stats')
def cache_stats(_=Depends(auth)):
    info=r.info()
    return {
        'db0': info.get('db0',{}),
        'hits': info.get('keyspace_hits',0),
        'misses': info.get('keyspace_misses',0),
        'used_memory_human': info.get('used_memory_human','')
    }

@app.post('/cache/flush')
def cache_flush(_=Depends(auth)):
    log.info("cache_flush triggered")
    r.flushall()
    return {"ok": True}

@app.post('/bm25/rebuild')
def bm25_rebuild(_=Depends(auth)):
    if not hybrid:
        raise HTTPException(503, "No text table available")
    log.info("bm25 rebuild triggered")
    hybrid.rebuild()
    return {"ok": True}

@app.get('/ingest/status', response_model=IngestStatus)
def ingest_status(_=Depends(auth)):
    state_db=os.path.join(INDEX_DIR,'ingest_state.sqlite')
    processed=retries=0
    if os.path.exists(state_db):
        con=sqlite3.connect(state_db); cur=con.cursor()
        try:
            cur.execute('SELECT COUNT(1) FROM files'); processed=cur.fetchone()[0]
            cur.execute('SELECT COALESCE(SUM(tries),0) FROM retries'); retries=cur.fetchone()[0]
        finally:
            con.close()
    dead_dir=os.path.join(DATA_DIR,'inbox','_deadletter')
    dead_cnt=sum(1 for _ in os.scandir(dead_dir)) if os.path.isdir(dead_dir) else 0
    return {'processed': processed, 'retry_total': retries, 'deadletter_count': dead_cnt}

def _check_rate_limit(req: Request):
    try:
        limit=int(os.environ.get('RATE_LIMIT_PER_MIN','60'))
        window=60
        ip=(req.client.host if req and req.client else 'unknown')
        key=f"rl:{ip}"
        cnt=r.incr(key)
        if cnt==1:
            r.expire(key, window)
        if cnt>limit:
            raise HTTPException(429, "rate limit exceeded")
    except HTTPException:
        raise
    except Exception:
        pass

@app.get('/query', response_model=QueryResponse, response_model_exclude_none=True)
def query(q: str = Query(...), k: int = 6, request: Request = None, _=Depends(auth)):
    t0=time.perf_counter(); metrics['queries_total']+=1
    _check_rate_limit(request)
    cache_key=f"query:{hashlib.md5(q.encode()).hexdigest()}:{k}"
    cached=cache.get(cache_key)
    if cached:
        return json.loads(cached)

    qvec = EMB.encode([q], normalize_embeddings=True)[0]
    text_hits_dense = TEXT.search(qvec).limit(50).to_list() if TEXT else []
    text_hits_sparse = hybrid.search(q, k=50) if hybrid else []
    code_hits = CODE.search(qvec).limit(50).to_list() if CODE else []
    wants_sketch = any(w in q.lower() for w in ['skizze','diagramm','ablauf','schema','block'])
    image_hits = []
    if IMAGE and wants_sketch:
        try:
            # Use CLIP text encoder to match CLIP image embeddings
            headers = {'X-API-Key': API_KEY} if API_KEY else {}
            resp = requests.post(f"{CLIP_URL}/embed_text", data={'text': q}, headers=headers, timeout=20)
            resp.raise_for_status()
            clip_vec = resp.json().get('vector')
            if clip_vec:
                image_hits = IMAGE.search(clip_vec).limit(30).to_list()
        except Exception:
            image_hits = []

    id2rec={}
    def tag(prefix, lst):
        out=[]
        for i,rec in enumerate(lst):
            rid=f"{prefix}{i}"; rec['id']=rid; id2rec[rid]=rec; out.append(rec)
        return out

    fused_scores = reciprocal_rank_fusion(
        tag('td',text_hits_dense), tag('ts',text_hits_sparse), tag('c',code_hits), tag('i',image_hits)
    )
    ranked = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)[:k]
    results=[id2rec[i] for i,_ in ranked]

    ctx=[]
    for r_ in results:
        if 'text' in r_: ctx.append(f"[TEXT] {r_.get('title','')}\n{r_['text'][:1200]}")
        elif 'code' in r_: ctx.append(f"[CODE] {r_.get('path','')}\n{r_['code'][:800]}")
    prompt = (
        "<|system|>Antworte präzise auf Deutsch. Wenn unsicher, sag es. Füge am Ende nummerierte Quellen mit Pfad an.\n"
        f"<|user|>{q}\n\nKontext:\n" + "\n\n".join(ctx)
    )
    try:
        resp = requests.post(f"{OLLAMA}/api/generate", json={"model":"llama3.1:8b-instruct-q4_K_M","prompt":prompt, "stream":False}, timeout=120)
        answer = resp.json().get('response','') if resp.ok else "[LLM-Fehler]"
    except Exception as e:
        log.exception("LLM request failed")
        answer = f"[LLM-Fehler: {e}]"

    def _sanitize(rec: dict):
        r=dict(rec)
        # Drop heavy fields
        r.pop('embedding', None)
        r.pop('clip_embedding', None)
        # Trim bodies
        if 'text' in r and isinstance(r['text'], str):
            r['text']=r['text'][:800]
        if 'code' in r and isinstance(r['code'], str):
            r['code']=r['code'][:800]
        return r
    result_json={"answer": answer, "hits": [_sanitize(r_) for r_ in results]}
    cache.setex(cache_key, 3600, json.dumps(result_json))
    metrics['latencies'].append((time.perf_counter()-t0)*1000)
    return result_json

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8080, reload=False)
