# PKMS Implementierungsplan v2.6 – Teil 1: Basis & Architektur (aktualisiert)

**Version:** 2.6.0  
**Datum:** 2025‑11‑11  
**Status:** Production‑Ready – Lauffähig, testbar, robust, daemon‑ready  
**Teil:** 1 von 4

---

## 0. Was ist neu in diesem Update (vs. v2.2 / frühere Drafts)

**Breaking/Behavioral**
- Search‑API liefert **Dicts** statt Tuples (einheitlich zu Teil 2): Keys `chunk_id, note_id, note_title, text, path, section_heading, score|distance`.
- Entfernt: SQL‑Cast `?::FLOAT[768]` – DuckDB akzeptiert Parameter als `FLOAT[]`; Dim‑Validierung findet in Python statt.
- Einheitliches DB‑Zugriffs‑Pattern: **`get_cursor()`** überall in Lese/Schreibpfaden (Thread‑Safety).  
- `logger`‑Import ist **`from ..logging.config import logger`** (keine `..logging.logger`).

**Spec/Docs**
- Titel + Changelog auf **v2.6.0** konsolidiert.
- **Schema‑Header/Meta** auf v2.6 gehoben (`schema_version = '2.6'`).
- `init_db.py` zeigt jetzt nach Schema‑Load ein **`ensure_indexes(..., force=True)`**.
- CLI‑Beispiele aktualisiert (Dict‑Ergebnisse, kein Tuple‑Unpacking mehr).

---

## 1. Projektstruktur (unverändert zu v2.6)

```text
pkms/
└── .pkms/
    ├── lib/
    │   ├── core/
    │   │   └── config.py
    │   ├── db/
    │   │   ├── connection.py   # get_connection/get_cursor
    │   │   ├── locking.py      # File Locking
    │   │   ├── indexes.py      # FTS/VSS Index Management
    │   │   └── helpers.py      # Note Update Tracking (touch_note/s)
    │   ├── logging/
    │   │   └── config.py       # logger
    │   ├── indexing/
    │   │   ├── indexer.py      # Chunk/Note Indexer (Beispiel)
    │   │   └── cache.py        # Embedding Cache
    │   ├── search/
    │   │   └── search.py       # FTS & VSS Search (API liefert Dicts)
    │   └── cli/
    │       └── commands.py     # CLI Commands
    ├── db/                     # Runtime DB (nicht versioniert)
    │   ├── index.duckdb
    │   └── .index.lock
    ├── log/                    # Logs (nicht versioniert)
    │   └── pkms.log
    ├── schema.sql              # Schema Definition (versioniert)
    ├── init_db.py              # Entry Point (versioniert)
    ├── requirements.txt        # Dependencies (versioniert)
    └── testing/
        └── test_e2e.py
```

---

## 2. Dependencies (Ausschnitt)

```txt
# Core
duckdb>=0.10.2
pyyaml>=6.0
requests>=2.31.0
click>=8.1.0
pandas>=2.0.0

# Optional
rich>=13.0          # Progress bar
portalocker>=2.7.0  # nur Windows (extras), Cross‑Platform Locking
```

---

## 3. Zentrale Konfiguration (`core/config.py`)

```python
from pathlib import Path
import os

class Config:
    REPO_ROOT = Path(os.getenv('PKMS_ROOT', Path.cwd()))

    WORKING_DIR = REPO_ROOT / 'working'
    SOURCE_DIR = REPO_ROOT / 'source'
    PKMS_DIR = REPO_ROOT / '.pkms'
    DB_DIR = PKMS_DIR / 'db'
    LOG_DIR = PKMS_DIR / 'log'
    DB_PATH = DB_DIR / 'index.duckdb'

    # Embedding (eine Quelle der Wahrheit)
    EMBEDDING_MODEL = 'nomic-embed-text:v1.5'
    EMBEDDING_DIM = 768
    OLLAMA_URL = 'http://localhost:11434'

    # Indexing
    CHUNK_SIZE = 1000
    OVERLAP_SIZE = 200
    DEFAULT_TOP_K = 10
    EMBEDDING_BATCH_SIZE = 64
    FILE_BATCH_SIZE = 50

    @classmethod
    def recompute_from_env(cls):
        cls.REPO_ROOT = Path(os.getenv('PKMS_ROOT', Path.cwd()))
        cls.WORKING_DIR = cls.REPO_ROOT / 'working'
        cls.SOURCE_DIR = cls.REPO_ROOT / 'source'
        cls.PKMS_DIR = cls.REPO_ROOT / '.pkms'
        cls.DB_DIR = cls.PKMS_DIR / 'db'
        cls.LOG_DIR = cls.PKMS_DIR / 'log'
        cls.DB_PATH = cls.DB_DIR / 'index.duckdb'

    @classmethod
    def ensure_dirs(cls):
        for d in [cls.WORKING_DIR, cls.SOURCE_DIR, cls.DB_DIR, cls.LOG_DIR]:
            d.mkdir(parents=True, exist_ok=True)
```

---

## 4. Logging (`logging/config.py`)

```python
import logging
from logging.handlers import RotatingFileHandler
from ..core.config import Config

def setup_logging(level=logging.INFO):
    Config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        Config.LOG_DIR / 'pkms.log', maxBytes=5_000_000, backupCount=3
    )
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[file_handler, logging.StreamHandler()]
    )
    return logging.getLogger('pkms')

logger = setup_logging()
```

**Import‑Konvention:** `from ..logging.config import logger`

---

## 5. DB‑Connection & Cursor (`db/connection.py`)

```python
import duckdb, threading, os
from ..core.config import Config
from ..logging.config import logger

_conn = None
_conn_lock = threading.Lock()
_local = threading.local()

def get_connection() -> duckdb.DuckDBPyConnection:
    global _conn
    if _conn is None:
        with _conn_lock:
            if _conn is None:
                _conn = duckdb.connect(str(Config.DB_PATH))
                _conn.execute("INSTALL 'fts'; LOAD 'fts';")
                _conn.execute("INSTALL 'vss'; LOAD 'vss';")
                if os.getenv('ALLOW_VSS_PERSISTENCE', 'false').lower() == 'true':
                    _conn.execute("SET hnsw_enable_experimental_persistence = true;")
                    logger.warning("HNSW persistence ENABLED (experimental)")
                else:
                    logger.info("HNSW persistence DISABLED (default)")
    return _conn

def get_cursor():
    if not hasattr(_local, 'cursor') or _local.cursor is None:
        _local.cursor = get_connection().cursor()
    return _local.cursor
```

**Leitlinie:** In allen Query‑Pfaden **`get_cursor()`** benutzen.

---

## 6. Schema (`schema.sql`, v2.6)

> FTS/VSS‑Indexe **nicht** im Schema – werden zentral in `db/indexes.py` gebaut.

```sql
-- PKMS Database Schema v2.6
CREATE SEQUENCE IF NOT EXISTS seq_chunk_id START 1 INCREMENT 1;

CREATE TABLE IF NOT EXISTS meta (
    key VARCHAR PRIMARY KEY,
    value VARCHAR NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO meta (key, value) VALUES
    ('schema_version', '2.6'),
    ('embedding_model', 'nomic-embed-text:v1.5'),
    ('embedding_dim', '768'),
    ('initialized_at', CAST(CURRENT_TIMESTAMP AS VARCHAR))
ON CONFLICT(key) DO NOTHING;

CREATE TABLE IF NOT EXISTS notes (
    id UUID PRIMARY KEY,
    path VARCHAR UNIQUE NOT NULL,
    title VARCHAR NOT NULL,
    type VARCHAR DEFAULT 'note',
    status VARCHAR DEFAULT 'active',
    date_created TIMESTAMP NOT NULL,
    date_modified TIMESTAMP NOT NULL,
    last_indexed TIMESTAMP,
    tags VARCHAR[],
    topics VARCHAR[],
    backlinks_count INTEGER DEFAULT 0,
    chunk_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_notes_path ON notes(path);
CREATE INDEX idx_notes_date_modified ON notes(date_modified);

CREATE TABLE IF NOT EXISTS chunks (
    rid BIGINT PRIMARY KEY DEFAULT nextval('seq_chunk_id'),
    note_id UUID NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    text_raw VARCHAR NOT NULL,
    text_for_embedding VARCHAR,
    chunk_type VARCHAR DEFAULT 'text',
    start_pos INTEGER NOT NULL,
    end_pos INTEGER NOT NULL,
    section_heading VARCHAR,
    embedding FLOAT[768],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(note_id, start_pos, end_pos)
);
CREATE INDEX idx_chunks_note_id ON chunks(note_id);

CREATE TABLE IF NOT EXISTS embedding_cache (
    text_hash VARCHAR NOT NULL,
    model VARCHAR NOT NULL,
    text_sample VARCHAR(100),
    embedding FLOAT[768],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    hit_count INTEGER DEFAULT 0,
    PRIMARY KEY (text_hash, model)
);
CREATE INDEX idx_cache_last_used ON embedding_cache(last_used);
```

---

## 7. Index‑Management (`db/indexes.py` – zentral)

- `ensure_indexes(conn, force: bool=False)` baut **FTS** idempotent neu (Drop/Create).  
- **VSS** wird je nach Persistence neu aufgebaut.  
- Nach großen Batches optional `checkpoint_db(conn)`.

```python
def ensure_indexes(conn, *, force=False):
    has_chunks = conn.execute("SELECT COUNT(*)>0 FROM chunks").fetchone()[0]
    if not has_chunks and not force:
        return
    conn.execute("PRAGMA drop_fts_index('chunks');")
    conn.execute("PRAGMA create_fts_index('chunks','rid','text_raw','section_heading', overwrite=1);")
    # VSS (HNSW) – Implementierung wie gehabt
```

---

## 8. Init‑Flow (`init_db.py`)

```python
from lib.db.connection import get_connection
from lib.db.indexes import ensure_indexes
from lib.logging.config import logger

with open('.pkms/schema.sql', 'r', encoding='utf-8') as f:
    schema = f.read()

conn = get_connection()
conn.execute(schema)
logger.info('Schema loaded')

# WICHTIG: nach Schema‑Load Indexe erzwingen
ensure_indexes(conn, force=True)
logger.info('Indexes ensured')
```

---

## 9. Search‑API (`search/search.py`, Rückgabe = Dicts)

```python
from typing import List, Dict
from ..db.connection import get_cursor
from ..core.config import Config
from ..logging.config import logger


def search_keyword(query: str, top_k: int | None = None) -> List[Dict]:
    k = top_k or Config.DEFAULT_TOP_K
    cur = get_cursor()
    sql = """
    SELECT c.rid, c.note_id, n.title, c.text_raw, n.path, c.section_heading,
           fts_main_chunks.match_bm25(c.rid, ?) AS bm25_score
    FROM chunks c
    JOIN notes n ON n.id = c.note_id
    WHERE fts_main_chunks.match_bm25(c.rid, ?) IS NOT NULL
    ORDER BY bm25_score DESC
    LIMIT ?
    """
    rows = cur.execute(sql, [query, query, k]).fetchall()
    return [{
        'chunk_id': r[0], 'note_id': r[1], 'note_title': r[2],
        'text': (r[3][:200] + '...') if len(r[3])>200 else r[3],
        'path': r[4], 'section_heading': r[5], 'score': r[6]
    } for r in rows]


def search_semantic(query: str, top_k: int | None = None) -> List[Dict]:
    from ..indexing.embedder import get_embeddings_batch_cached
    k = top_k or Config.DEFAULT_TOP_K
    cur = get_cursor()
    q_emb = get_embeddings_batch_cached([query])[0]
    if q_emb is None:
        logger.warning('No embedding for query; returning empty result')
        return []
    rows = cur.execute(
        """
        SELECT c.rid, c.note_id, n.title, c.text_raw, n.path, c.section_heading,
               array_distance(c.embedding, ?) AS distance
        FROM chunks c
        JOIN notes n ON n.id = c.note_id
        WHERE c.embedding IS NOT NULL
        ORDER BY distance ASC
        LIMIT ?
        """, [q_emb, k]
    ).fetchall()
    return [{
        'chunk_id': r[0], 'note_id': r[1], 'note_title': r[2],
        'text': (r[3][:200] + '...') if len(r[3])>200 else r[3],
        'path': r[4], 'section_heading': r[5], 'distance': r[6]
    } for r in rows]
```

---

## 10. CLI‑Ausschnitte (`cli/commands.py`)

```python
import click
from ..core.config import Config
from ..search.search import search_keyword, search_semantic

@click.group()
def cli():
    Config.recompute_from_env()
    Config.ensure_dirs()
    # sanfter Index‑Check beim Start
    from ..db.indexes import ensure_indexes
    from ..db.connection import get_connection
    try:
        ensure_indexes(get_connection(), force=False)
    except Exception:
        pass

@cli.command()
@click.argument('query')
@click.option('--k', default=10, type=int)
def ksearch(query, k):
    results = search_keyword(query, k)
    if not results:
        click.echo('No results found.'); raise SystemExit(1)
    for i, r in enumerate(results, 1):
        click.echo(f"{i}. {r['note_title']} [{r['score']:.3f}]")
        click.echo(f"   {r['path']}")
        if r['section_heading']:
            click.echo(f"   Section: {r['section_heading']}")
        click.echo(f"   {r['text'][:150]}...\n")

@cli.command()
@click.argument('query')
@click.option('--k', default=10, type=int)
def ssearch(query, k):
    results = search_semantic(query, k)
    if not results:
        click.echo('No results found.'); raise SystemExit(1)
    for i, r in enumerate(results, 1):
        click.echo(f"{i}. {r['note_title']} [dist={r['distance']:.4f}]")
        click.echo(f"   {r['path']}")
        if r['section_heading']:
            click.echo(f"   Section: {r['section_heading']}")
        click.echo(f"   {r['text'][:150]}...\n")
```

---

## 11. Backup/Restore (Hinweis)

- Nach Restore **immer** `checkpoint_db(conn)` + `ensure_indexes(conn, force=True)`.
- UTC‑Zeitstempel strikt; Parquet‑Split berücksichtigen (E2E‑Test prüft das).

---

## 12. CI‑Gate

```bash
python .pkms/init_db.py && python .pkms/testing/test_e2e.py
```

---

## 13. Migrationsnotizen (kurz)

- Falls bestehender Code Tuples von `search.py` erwartet → Call‑Sites auf Dict‑Zugriff umstellen.
- Entferne manuelle FTS/VSS‑PRAGMAs aus Anwendungs‑Code; Index‑Pflege zentral halten.
- In allen Modulen den `logger` aus `logging/config.py` importieren.
- Schema‑Version in produktiven DBs optional über `UPDATE meta SET value='2.6' WHERE key='schema_version';` heben (nur, wenn ihr sie monitoren wollt).

