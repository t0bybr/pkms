# PKMS Search Engine (Plan v0.3)

Hybrid search implementation mit RRF-Fusion und Chunk-basiertem Retrieval.

## Architektur

```
┌─────────────┐
│  Markdown   │
│   Files     │
└──────┬──────┘
       │
       ▼
┌─────────────┐      ┌──────────────┐
│  ingest.py  │─────▶│ data/records │
└─────────────┘      │   (JSON)     │
       │             └──────────────┘
       ▼
┌─────────────┐      ┌──────────────┐
│  chunk.py   │─────▶│ data/chunks  │
│ (Hybrid)    │      │   (NDJSON)   │
└─────────────┘      └──────┬───────┘
                            │
                            ▼
┌─────────────┐      ┌──────────────┐
│  embed.py   │─────▶│ data/embeddings/
│ (Ollama)    │      │   {model}/   │
└─────────────┘      │   {hash}.npy │
                     └──────────────┘
                            │
       ┌────────────────────┼────────────────────┐
       │                    │                    │
       ▼                    ▼                    ▼
┌─────────────┐      ┌──────────────┐    ┌──────────────┐
│   Whoosh    │      │  Embeddings  │    │    Chunks    │
│  (BM25)     │      │  (Cosine)    │    │  (Metadata)  │
└──────┬──────┘      └──────┬───────┘    └──────────────┘
       │                    │
       │      RRF Fusion    │
       └──────────┬──────────┘
                  ▼
           ┌──────────────┐
           │  Grouping    │
           │ (max 3 per   │
           │   doc_id)    │
           └──────┬───────┘
                  ▼
           ┌──────────────┐
           │   Results    │
           └──────────────┘
```

## Komponenten

### 1. `search_engine.py`

Haupt-Suchmaschine mit:
- **BM25**: Whoosh-Index über Chunks (keyword search)
- **Semantic**: Cosine-Similarity über Chunk-Embeddings
- **RRF**: Reciprocal Rank Fusion (k=60)
- **Grouping**: Max 3 Chunks pro doc_id

### 2. `embed_index.py`

Embedding-Builder:
- Liest Chunks aus `data/chunks/*.ndjson`
- Embeddet via Ollama (siehe `embeddings.py`)
- Schreibt `.npy` Files nach `data/embeddings/{model}/{chunk_hash}.npy`
- Incremental: Nur neue Chunks embedden
- Updated `embedding_meta` in Records

## Verwendung

### Setup

```bash
# 1. Installiere Dependencies
pip install whoosh numpy ollama

# 2. Starte Ollama mit Embedding-Modell
ollama pull nomic-embed-text

# 3. Setze Env-Variablen (optional)
export PKMS_EMBED_MODEL=nomic-embed-text
export PKMS_CHUNKS_DIR=data/chunks
export PKMS_EMB_BASE_DIR=data/embeddings
```

### Workflow

```bash
# 1. Ingest Markdown → Records + Chunks
python -m tools.ingest notes/

# 2. Chunk Markdown (hybrid: hierarchisch + semantisch)
python -m tools.chunk

# 3. Embed Chunks → .npy Files
python -m tools.embed_index

# 4. Suche
python -c "
from lib.search.search_engine import SearchEngine
from lib.embeddings import get_embedding

engine = SearchEngine(
    chunks_dir='data/chunks',
    emb_dir='data/embeddings/nomic-embed-text',
    index_dir='data/whoosh_index',
    embed_fn=get_embedding,
    group_limit=3,
)

results = engine.search('pizza ofen temperatur', k=10)
for r in results:
    print(f\"{r['chunk_id']} - {r['section']} (rrf={r['rrf_score']:.3f})\")
"
```

### Python API

```python
from lib.search.search_engine import SearchEngine
from lib.embeddings import get_embedding

# Initialize
engine = SearchEngine(
    chunks_dir="data/chunks",
    emb_dir="data/embeddings/nomic-embed-text",
    index_dir="data/whoosh_index",
    embed_fn=get_embedding,
    group_limit=3,  # Max 3 chunks per doc
)

# Search
results = engine.search("postgresql backup", k=10)

# Results format:
[
  {
    "chunk_id": "01HAR6DP:a3f2bc1d",
    "doc_id": "01HAR6DP",
    "rrf_score": 0.123,
    "bm25": 5.67,         # or None
    "semantic": 0.89,     # or None
    "source": "hybrid",   # "keyword"|"semantic"|"hybrid"
    "section": "Ofentemperatur",
    "chunk_index": 7
  },
  ...
]
```

## Features

### ✅ Chunk-basiert
- Besseres Retrieval als Dokument-Ebene
- Lange Dokumente → mehrere präzise Chunks
- Grouping verhindert Dominanz einzelner Docs

### ✅ Content-Hash IDs
- `chunk_id = doc_id:xxhash64(text)[:12]`
- Deterministisch: gleicher Text → gleiche ID
- Deduplication: gleicher Chunk in mehreren Docs = ein Embedding

### ✅ Incremental Embedding
- Nur neue/geänderte Chunks embedden
- `.npy` Check via Filesystem (schnell)
- Spart API-Calls & Zeit

### ✅ Hybrid Search
- BM25 für exakte Keyword-Matches
- Semantic für konzeptuelle Ähnlichkeit
- RRF fusioniert Rankings optimal

### ✅ Grouping
- Max N Chunks pro doc_id
- Verhindert: ein Doc monopolisiert Results
- Bessere Diversität

## Migration Path

### Aktuell: Whoosh (Prototyp)
- Lokal, einfach, keine Dependencies
- Gut für Entwicklung & Testing

### Später: Typesense (Production)
- Native Hybrid Search (BM25 + Vector in einem Query)
- Grouping via `group_by=doc_id`
- Faceting, Filtering, Blue-Green Deployment

**Migrationspfad:**
1. Interface `SearchIndex` definieren (siehe plan.md 8.1)
2. `WhooshIndex(SearchIndex)` - current
3. `TypesenseIndex(SearchIndex)` - future
4. SearchEngine nutzt Interface → austauschbar

## Schema-Konformität

Alle Datenstrukturen folgen JSON-Schemas aus `schema/`:

- **chunk.schema.json** - Chunk-Format
- **record.schema.json** - Record mit `embedding_meta`
- **embedding_meta.schema.json** - Embedding-Metadaten

Validierung:
```bash
check-jsonschema \
  --schemafile schema/chunk.schema.json \
  data/chunks/01HAR6DP.ndjson
```

## Troubleshooting

### "No chunks found"
→ Run `chunk.py` first to generate chunks from markdown

### "No embeddings loaded"
→ Run `embed_index.py` to generate .npy files

### "Whoosh index empty"
→ Check `data/chunks/*.ndjson` format (must be valid NDJSON)

### "Semantic search returns empty"
→ Check `embed_fn` is set and Ollama is running

## Performance

**Whoosh (Prototyp):**
- ~1000 chunks/sec indexing
- ~50ms BM25 query
- ~10ms cosine search (in-memory)

**Typesense (später):**
- ~10000 chunks/sec indexing
- ~5ms hybrid query
- Native grouping (keine Python-Loop)

## Nächste Schritte

1. ✅ Schemas erstellt
2. ✅ Search Engine plan-konform
3. 🔲 `chunk.py` implementieren (Hybrid Chunking)
4. 🔲 `ingest.py` implementieren (Markdown → Records)
5. 🔲 Typesense-Adapter (`index_typesense.py`)
6. 🔲 MMR-Diversifizierung
7. 🔲 ε-Exploration für Serendipität
