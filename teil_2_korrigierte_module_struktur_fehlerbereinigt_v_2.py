# .pkms/lib/indexing/embedder.py
from typing import List, Optional
import requests

from ..core.config import Config
from ..logging.config import logger
from .cache import EmbeddingCache


def validate_embedding(emb: List[float], source: str = "unknown") -> List[float]:
    """Validiert Embedding-Dimension und Werte."""
    if not emb:
        raise ValueError(f"{source}: Empty embedding")

    if len(emb) != Config.EMBEDDING_DIM:
        raise ValueError(
            f"{source}: Dimension mismatch - got {len(emb)}, expected {Config.EMBEDDING_DIM}"
        )

    # Check NaN/Inf
    if any((not isinstance(x, (int, float))) or (x != x) or (abs(x) == float('inf')) for x in emb):
        raise ValueError(f"{source}: Invalid values (NaN/Inf)")

    return emb


def fetch_embeddings_from_ollama(texts: List[str]) -> List[Optional[List[float]]]:
    """Holt Embeddings von Ollama (ohne Cache)."""
    try:
        response = requests.get(f"{Config.OLLAMA_URL}/api/tags", timeout=2)
        if response.status_code != 200:
            logger.error("Ollama not available")
            return [None] * len(texts)
    except Exception as e:
        logger.error(f"Ollama offline: {e}")
        return [None] * len(texts)

    out: List[Optional[List[float]]] = []
    for text in texts:
        try:
            response = requests.post(
                f"{Config.OLLAMA_URL}/api/embeddings",
                json={"model": Config.EMBEDDING_MODEL, "prompt": text},
                timeout=30,
            )
            if response.status_code == 200:
                emb = response.json()["embedding"]
                validate_embedding(emb, "Ollama")
                out.append(emb)
            else:
                logger.warning(f"Ollama HTTP {response.status_code}")
                out.append(None)
        except Exception as e:
            logger.warning(f"Embedding failed: {e}")
            out.append(None)
    return out


def get_embeddings_batch_cached(texts: List[str]) -> List[Optional[List[float]]]:
    """Batch-Embeddings mit DuckDB-Cache."""
    if not texts:
        return []

    # 1) Cache-Hits holen
    cached = EmbeddingCache.get_batch(texts)

    # 2) Fehlende sammeln
    to_embed: List[str] = []
    idx: List[int] = []
    for i, (t, emb) in enumerate(zip(texts, cached)):
        if emb is None:
            to_embed.append(t)
            idx.append(i)

    # 3) Fehlende einbetten
    if to_embed:
        logger.info(f"Embedding {len(to_embed)}/{len(texts)} new texts")
        new_embs = fetch_embeddings_from_ollama(to_embed)
        # 4) Cache updaten (nur valide Vektoren)
        EmbeddingCache.put_batch(to_embed, new_embs)
        # 5) Zurückschreiben
        for i_pos, emb in zip(idx, new_embs):
            cached[i_pos] = emb
    else:
        logger.info(f"All {len(texts)} embeddings from cache (100% hit)")

    return cached


# .pkms/lib/indexing/indexer.py
from __future__ import annotations
import yaml
from pathlib import Path
from typing import Dict, List
import pandas as pd

from ..core.config import Config
from ..db.connection import get_cursor
from ..db.locking import IndexLock
from ..db.helpers import touch_note
from ..db.indexes import ensure_indexes, checkpoint_db
from ..logging.config import logger
from .chunker import chunk_text, add_overlap
from .embedder import get_embeddings_batch_cached


def index_all(
    incremental: bool = False,
    batch_size: int | None = None,
    verbose: bool = True,
) -> Dict:
    """
    Haupt-Indexing-Funktion: scannt working/, chunked, embed, schreibt notes/chunks.
    - Idempotent
    - DataFrame-Inserts (register + explizite Spaltenliste)
    - Rebuild FTS/VSS via ensure_indexes() (zentral)
    """
    try:
        with IndexLock():
            return _index_all_impl(incremental, batch_size, verbose)
    except RuntimeError as e:
        logger.warning(str(e))
        if verbose:
            print(f"⚠️  {e}")
        return {"error": str(e)}


def _index_all_impl(incremental: bool, batch_size: int | None, verbose: bool) -> Dict:
    cur = get_cursor()
    batch_size = batch_size or Config.FILE_BATCH_SIZE

    # Dateien sammeln
    files: List[Path]
    if incremental:
        row = cur.execute("SELECT value FROM meta WHERE key = 'last_full_index'").fetchone()
        if row and row[0]:
            try:
                cutoff = float(row[0])
            except ValueError:
                cutoff = 0.0
            files = [
                f for f in Config.WORKING_DIR.rglob("*.md")
                if f.stat().st_mtime > cutoff
            ]
            logger.info(f"Incremental: {len(files)} changed files")
        else:
            files = list(Config.WORKING_DIR.rglob("*.md"))
    else:
        files = list(Config.WORKING_DIR.rglob("*.md"))

    if verbose:
        print(f"🔄 Indexing {len(files)} files…")

    indexed = 0
    total_chunks = 0
    errors: List[str] = []

    # Transaktion öffnen
    cur.execute("BEGIN")
    try:
        # Batch-Schleife – NICHT den Progress-Iterator slicen
        for i in range(0, len(files), batch_size):
            batch = files[i : i + batch_size]
            res = _process_file_batch(cur, batch, verbose)
            indexed += res["indexed"]
            total_chunks += res["chunks"]
            errors.extend(res["errors"])

        # Meta-Update: last_full_index (epoch), updated_at pflegen
        import time
        cur.execute(
            """
            INSERT INTO meta(key, value) VALUES('last_full_index', ?)
            ON CONFLICT(key) DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP
            """,
            [str(time.time())],
        )

        # Commit vor Index-Rebuild
        cur.execute("COMMIT")

        # Indexe neu erstellen + optional checkpoint
        conn = cur.connection
        checkpoint_db(conn)
        ensure_indexes(conn, force=True)

        if verbose:
            print(f"\n✅ {indexed}/{len(files)} notes, {total_chunks} chunks")
            if errors:
                print(f"⚠️  {len(errors)} errors (see log)")

        logger.info(f"Indexed {indexed}/{len(files)} notes, {total_chunks} chunks")
        return {
            "total_files": len(files),
            "indexed": indexed,
            "total_chunks": total_chunks,
            "errors": errors,
        }

    except Exception as e:
        cur.execute("ROLLBACK")
        logger.error(f"Index failed: {e}", exc_info=True)
        raise


def _process_file_batch(cur, files_batch: List[Path], verbose: bool) -> Dict:
    """Verarbeitet einen Batch von Dateien (atomar pro Datei)."""
    indexed = 0
    total_chunks = 0
    errors: List[str] = []

    for filepath in files_batch:
        try:
            raw = Path(filepath).read_text(encoding="utf-8")
            if not raw.startswith("---"):
                errors.append(f"{filepath.name}: No frontmatter")
                continue
            parts = raw.split("---", 2)
            if len(parts) < 3:
                errors.append(f"{filepath.name}: Invalid frontmatter")
                continue

            # YAML Frontmatter
            try:
                fm = yaml.safe_load(parts[1]) or {}
                required = ["uuid", "title", "date_created", "date_modified"]
                missing = [k for k in required if k not in fm]
                if missing:
                    raise ValueError(f"Missing fields: {missing}")
            except yaml.YAMLError as e:
                errors.append(f"{filepath.name}: YAML error - {e}")
                logger.warning(f"YAML error in {filepath.name}: {e}")
                continue
            except ValueError as e:
                errors.append(f"{filepath.name}: {e}")
                logger.warning(f"Invalid frontmatter in {filepath.name}: {e}")
                continue

            content = parts[2].strip()
            note_id = fm["uuid"]

            # Note upsert (idempotent)
            cur.execute(
                """
                INSERT INTO notes (
                    id, path, title, date_created, date_modified,
                    tags, type, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    path = excluded.path,
                    title = excluded.title,
                    date_modified = excluded.date_modified,
                    tags = excluded.tags,
                    updated_at = CURRENT_TIMESTAMP
                """,
                [
                    note_id,
                    str(filepath),
                    fm["title"],
                    fm["date_created"],
                    fm["date_modified"],
                    fm.get("tags", []),
                    fm.get("type", "note"),
                    fm.get("status", "active"),
                ],
            )

            # Chunking
            chunks = chunk_text(content)
            texts_for_embedding = [
                add_overlap(ch["text"], content, ch["start_pos"]) for ch in chunks
            ]
            embs = get_embeddings_batch_cached(texts_for_embedding)

            # DataFrame vorbereiten
            rows = []
            for ch, emb in zip(chunks, embs):
                rows.append(
                    {
                        "note_id": note_id,
                        "text_raw": ch["text"],
                        "text_for_embedding": ch["text"],
                        "chunk_type": "text",
                        "start_pos": ch["start_pos"],
                        "end_pos": ch["end_pos"],
                        "section_heading": None,
                        "embedding": emb,
                    }
                )

            if rows:
                df = pd.DataFrame(rows)
                cur.register("df_chunks", df)
                try:
                    # Explizite Spaltenliste + UPSERT + Idempotenz
                    cur.execute(
                        """
                        INSERT INTO chunks (
                            note_id, text_raw, text_for_embedding,
                            chunk_type, start_pos, end_pos, section_heading, embedding
                        )
                        SELECT
                            note_id, text_raw, text_for_embedding,
                            chunk_type, start_pos, end_pos, section_heading, embedding
                        FROM df_chunks
                        ON CONFLICT(note_id, start_pos, end_pos) DO UPDATE SET
                            text_raw = excluded.text_raw,
                            text_for_embedding = excluded.text_for_embedding,
                            embedding = excluded.embedding
                        """
                    )
                finally:
                    cur.unregister("df_chunks")

            # Note-Metadaten: touch + chunk_count
            touch_note(cur.connection, note_id)
            cur.execute(
                """
                UPDATE notes
                SET chunk_count = (SELECT COUNT(*) FROM chunks WHERE note_id = ?),
                    last_indexed = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                [note_id, note_id],
            )

            indexed += 1
            total_chunks += len(chunks)

        except Exception as e:
            errors.append(f"{filepath.name}: {e}")
            logger.error(f"Error processing {filepath.name}: {e}", exc_info=True)

    return {"indexed": indexed, "chunks": total_chunks, "errors": errors}


# .pkms/lib/search/search.py
from typing import List, Dict

from ..core.config import Config
from ..db.connection import get_cursor
from ..logging.config import logger


def search_keyword(query: str, top_k: int | None = None) -> List[Dict]:
    """Keyword-Suche (FTS/BM25)."""
    k = top_k or Config.DEFAULT_TOP_K
    cur = get_cursor()

    sql = """
    SELECT 
        c.rid, c.note_id, n.title, c.text_raw, n.path, c.section_heading,
        fts_main_chunks.match_bm25(c.rid, ?) AS bm25_score
    FROM chunks c
    JOIN notes n ON c.note_id = n.id
    WHERE fts_main_chunks.match_bm25(c.rid, ?) IS NOT NULL
    ORDER BY bm25_score DESC
    LIMIT ?
    """
    rows = cur.execute(sql, [query, query, k]).fetchall()
    logger.info(f"Keyword search: '{query}' → {len(rows)} hits")
    return [
        {
            "chunk_id": r[0],
            "note_id": r[1],
            "note_title": r[2],
            "text": (r[3][:200] + "...") if len(r[3]) > 200 else r[3],
            "path": r[4],
            "section_heading": r[5],
            "score": r[6],
        }
        for r in rows
    ]


def search_semantic(query: str, top_k: int | None = None) -> List[Dict]:
    """Semantische Suche (VSS/Cosine Distance)."""
    from ..indexing.embedder import get_embeddings_batch_cached

    k = top_k or Config.DEFAULT_TOP_K
    cur = get_cursor()

    q_emb = get_embeddings_batch_cached([query])[0]
    if q_emb is None:
        logger.warning("No embedding for query; returning empty result")
        return []

    sql = """
    SELECT 
        c.rid, c.note_id, n.title, c.text_raw, n.path, c.section_heading,
        array_distance(c.embedding, ?) AS distance
    FROM chunks c
    JOIN notes n ON c.note_id = n.id
    WHERE c.embedding IS NOT NULL
    ORDER BY distance ASC
    LIMIT ?
    """

    rows = cur.execute(sql, [q_emb, k]).fetchall()
    logger.info(f"Semantic search: '{query}' → {len(rows)} hits")
    return [
        {
            "chunk_id": r[0],
            "note_id": r[1],
            "note_title": r[2],
            "text": (r[3][:200] + "...") if len(r[3]) > 200 else r[3],
            "path": r[4],
            "section_heading": r[5],
            "distance": r[6],
        }
        for r in rows
    ]
