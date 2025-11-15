# PKMS Tools

CLI-Tools für die PKMS-Pipeline (Plan v0.3).

## Pipeline-Übersicht

```
Markdown Files
     ↓
[ingest.py] → data/records/*.json (Records)
     ↓
[chunk.py]  → data/chunks/*.ndjson (Chunks)
     ↓
[embed_index.py] → data/embeddings/{model}/*.npy (Embeddings)
     ↓
[search_engine.py] → Hybrid Search (BM25 + Semantic + RRF)
```

## Tools

### 1. `ingest.py` - Markdown → Records

Liest Markdown-Dateien, parsed Frontmatter, generiert Record-JSONs.

**Features:**
- ULID-Generierung/-Validierung
- Frontmatter-Parsing (python-frontmatter)
- Auto-Language-Detection (langdetect)
- SHA256-Hashing (content + file)
- Dateinamen-Normalisierung (`slug--ULID.md`)

**Usage:**
```bash
# Gesamtes Verzeichnis
python -m tools.ingest notes/

# Einzelne Datei
python -m tools.ingest notes/pizza--01HAR6DP.md

# Custom Output
python -m tools.ingest notes/ --records-dir data/records/
```

**Input:**
```
notes/pizza-rezept.md
```

**Output:**
```
data/records/01HAR6DP2M7G1KQ3Y3VQ8C0Q.json
```

**Frontmatter-Handling:**
- `title`, `tags`, `categories`, `aliases` → übernommen
- `language` → auto-detected wenn leer, zurückgeschrieben
- `id` → ULID generiert/validiert, zurückgeschrieben
- `date_created`, `date_semantic` → optional

---

### 2. `chunk.py` - Records → Chunks

Chunked Records in kleinere Text-Abschnitte mit Content-Hash IDs.

**Features:**
- Hierarchisches Chunking (Markdown-Headings)
- Semantisches Chunking bei großen Sections (paragraph-based)
- Content-Hash IDs (`doc_id:xxhash64[:12]`)
- Token-Counting (tiktoken oder word-based estimate)
- Overlap (10-20%)
- NDJSON-Output

**Usage:**
```bash
# Alle Records chunken
python -m tools.chunk

# Custom Token-Limit
python -m tools.chunk --max-tokens 400

# Custom Pfade
python -m tools.chunk --records-dir data/records/ --chunks-dir data/chunks/
```

**Input:**
```json
// data/records/01HAR6DP.json
{
  "id": "01HAR6DP...",
  "full_text": "# Pizza\n\nBei 300°C...",
  "language": "de"
}
```

**Output:**
```json
// data/chunks/01HAR6DP.ndjson (NDJSON, 1 chunk per line)
{"doc_id":"01HAR6DP","chunk_id":"01HAR6DP:a3f2bc1d","chunk_hash":"a3f2bc1d","chunk_index":0,"text":"# Pizza\n\nBei 300°C...","tokens":123,"section":"Pizza","language":"de","modality":"text"}
{"doc_id":"01HAR6DP","chunk_id":"01HAR6DP:f9e1a2b3","chunk_hash":"f9e1a2b3","chunk_index":1,"text":"...","tokens":87,"section":"Pizza","subsection":"Teig","language":"de","modality":"text"}
```

---

### 3. `embed_index.py` - Chunks → Embeddings

Embeddet Chunks und speichert als `.npy` Files.

**Features:**
- Incremental (nur neue Chunks)
- Content-Hash basiert (Deduplication)
- `.npy` Storage (kompakt, schnell)
- Updates `embedding_meta` in Records
- Ollama-Integration

**Usage:**
```bash
# Alle Chunks embedden
python -m tools.embed_index

# Custom Modell
export PKMS_EMBED_MODEL=text-embedding-3-large
python -m tools.embed_index

# Custom Pfade
export PKMS_CHUNKS_DIR=data/chunks
export PKMS_EMB_BASE_DIR=data/embeddings
python -m tools.embed_index
```

**Input:**
```
data/chunks/01HAR6DP.ndjson
```

**Output:**
```
data/embeddings/nomic-embed-text/a3f2bc1d.npy
data/embeddings/nomic-embed-text/f9e1a2b3.npy
```

**Record Update:**
```json
// data/records/01HAR6DP.json (updated)
{
  "id": "01HAR6DP...",
  "embedding_meta": {
    "text": {
      "model": "nomic-embed-text",
      "dim": 768,
      "updated_at": "2025-11-15T10:30:00Z",
      "chunk_hashes": ["a3f2bc1d", "f9e1a2b3"]
    }
  }
}
```

---

## Dependencies

```bash
# Core
pip install pydantic python-frontmatter langdetect

# Optional (empfohlen)
pip install xxhash tiktoken

# Embedding
pip install ollama

# Search
pip install whoosh numpy
```

Siehe `requirements.txt` für vollständige Liste.

---

## Workflow-Beispiel

```bash
# 1. Setup
mkdir -p notes data/{records,chunks,embeddings}

# 2. Markdown erstellen/kopieren
echo "---
title: Pizza Rezept
tags: [kochen]
---

# Pizza

Bei 300°C wird der Teig knusprig.
" > notes/pizza.md

# 3. Ingest
python -m tools.ingest notes/

# Output:
# [ingest] Renamed: pizza.md → pizza-rezept--01HAR6DP2M7G1KQ3Y3VQ8C0Q.md
# [ingest] Saved: data/records/01HAR6DP2M7G1KQ3Y3VQ8C0Q.json

# 4. Chunk
python -m tools.chunk

# Output:
# [chunk] Saved 2 chunks → data/chunks/01HAR6DP2M7G1KQ3Y3VQ8C0Q.ndjson

# 5. Embed (requires Ollama running)
python -m tools.embed_index

# Output:
# [embed_index] 2 embedded, 0 skipped
# [embed_index] Updated embedding_meta in 1 records

# 6. Search
python -c "
from lib.search.search_engine import SearchEngine
from lib.embeddings import get_embedding

engine = SearchEngine(
    chunks_dir='data/chunks',
    emb_dir='data/embeddings/nomic-embed-text',
    index_dir='data/whoosh_index',
    embed_fn=get_embedding,
)

results = engine.search('pizza ofen', k=5)
for r in results:
    print(f\"{r['chunk_id']} - {r['section']} (rrf={r['rrf_score']:.3f})\")
"
```

---

## Schema-Validierung

```bash
# Install validator
pip install check-jsonschema

# Validate Record
check-jsonschema \
  --schemafile schema/record.schema.json \
  data/records/01HAR6DP2M7G1KQ3Y3VQ8C0Q.json

# Validate Chunks (NDJSON)
jq -c '.' data/chunks/01HAR6DP2M7G1KQ3Y3VQ8C0Q.ndjson | while read line; do
  echo "$line" | check-jsonschema --schemafile schema/chunk.schema.json -
done
```

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'pkms'"

→ Install in editable mode: `pip install -e .`

oder setze PYTHONPATH:
```bash
export PYTHONPATH=/home/user/pkms:$PYTHONPATH
```

### "langdetect not installed"

→ Install: `pip install langdetect`

oder setze Language manuell im Frontmatter:
```yaml
---
title: My Note
language: en
---
```

### "xxhash not installed"

→ Fallback auf SHA256 (langsamer aber funktioniert)

Install für bessere Performance: `pip install xxhash`

### "tiktoken not installed"

→ Fallback auf word-count * 1.3

Install für präzises Token-Counting: `pip install tiktoken`

---

## Nächste Schritte

- [ ] `link.py` - Wikilink-Erkennung & bidirektionales Tracking
- [ ] `relevance.py` - Formel-basiertes Relevance-Scoring
- [ ] `synth.py` - Git-basierter Konsolidierungs-Workflow
- [ ] `index_typesense.py` - Typesense-Adapter (Migration von Whoosh)
