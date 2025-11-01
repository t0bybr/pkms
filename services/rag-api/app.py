import os, json, time, hashlib, sqlite3
from fastapi import FastAPI, Query, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
import lancedb
from sentence_transformers import SentenceTransformer
import requests
import redis
from rrf import reciprocal_rank_fusion
from hybrid import HybridRetriever, cache

API_KEY=os.environ.get('API_KEY')
OLLAMA=os.environ.get('OLLAMA_URL','http://ollama:11434')
INDEX_DIR=os.environ.get('INDEX_DIR','/app/index')
DATA_DIR=os.environ.get('DATA_DIR','/app/data')
REDIS_HOST=os.environ.get('REDIS_HOST','redis')
REDIS_PORT=int(os.environ.get('REDIS_PORT','6379'))

app=FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DB=lancedb.connect(INDEX_DIR)
TEXT = DB.open_table('text_v2') if 'text_v2' in DB.table_names() else DB.open_table('text_v1')
CODE = DB.open_table('code_v2') if 'code_v2' in DB.table_names() else (DB.open_table('code_v1') if 'code_v1' in DB.table_names() else None)
IMAGE= DB.open_table('image_v2') if 'image_v2' in DB.table_names() else (DB.open_table('image_v1') if 'image_v1' in DB.table_names() else None)
EMB=SentenceTransformer('BAAI/bge-m3')

hybrid = HybridRetriever(TEXT)
metrics = {"queries_total":0, "latencies":[]}
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

def auth(x_api_key: str = Header(None)):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(401, "unauthorized")

@app.get('/health')
def health():
    return {'ok': True}

@app.get('/metrics')
def prom():
    arr=sorted(metrics['latencies']); n=len(arr)
    p50=arr[int(0.5*n)] if n else 0; p95=arr[int(0.95*n)] if n else 0
    body = f"queries_total {metrics['queries_total']}\nquery_latency_ms_p50 {p50}\nquery_latency_ms_p95 {p95}\n"
    return Response(body, media_type='text/plain')

@app.get('/cache/stats')
def cache_stats(_=auth()):
    info=r.info()
    return {
        'db0': info.get('db0',{}),
        'hits': info.get('keyspace_hits',0),
        'misses': info.get('keyspace_misses',0),
        'used_memory_human': info.get('used_memory_human','')
    }

@app.post('/cache/flush')
def cache_flush(_=auth()):
    r.flushall()
    return {"ok": True}

@app.post('/bm25/rebuild')
def bm25_rebuild(_=auth()):
    hybrid.rebuild()
    return {"ok": True}

@app.get('/ingest/status')
def ingest_status(_=auth()):
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

@app.get('/query')
def query(q: str = Query(...), k: int = 6, _=auth()):
    t0=time.perf_counter(); metrics['queries_total']+=1
    cache_key=f"query:{hashlib.md5(q.encode()).hexdigest()}:{k}"
    cached=cache.get(cache_key)
    if cached:
        return json.loads(cached)

    qvec = EMB.encode([q], normalize_embeddings=True)[0]
    text_hits_dense = TEXT.search(qvec).limit(50).to_list() if TEXT else []
    text_hits_sparse = hybrid.search(q, k=50)
    code_hits = CODE.search(qvec).limit(50).to_list() if CODE else []
    wants_sketch = any(w in q.lower() for w in ['skizze','diagramm','ablauf','schema','block'])
    image_hits = IMAGE.search(qvec).limit(30).to_list() if (IMAGE and wants_sketch) else []

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
        answer = f"[LLM-Fehler: {e}]"

    result_json={"answer": answer, "hits": results}
    cache.setex(cache_key, 3600, json.dumps(result_json))
    metrics['latencies'].append((time.perf_counter()-t0)*1000)
    return result_json
