# tools/embed_index.py
"""
Plan v0.3 compliant embedding indexer:
- Reads chunks from data/chunks/*.ndjson
- Writes .npy files to data/embeddings/{model}/{chunk_hash}.npy
- Incremental: only embeds new/changed chunks
- Updates embedding_meta in record JSONs
"""

from __future__ import annotations

import os
import sys
import json
from pathlib import Path
from typing import Dict, Set

import numpy as np

# Import embedding function (assumes embeddings.py in parent)
try:
    from lib.embeddings import get_embedding
except ImportError:
    # Fallback for running standalone
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from lib.embeddings import get_embedding


# Config from environment
CHUNKS_DIR = os.getenv("PKMS_CHUNKS_DIR", "data/chunks")
RECORDS_DIR = os.getenv("PKMS_RECORDS_DIR", "data/metadata")
MODEL_NAME = os.getenv("PKMS_EMBED_MODEL", "nomic-embed-text")
EMB_BASE_DIR = os.getenv("PKMS_EMB_BASE_DIR", "data/embeddings")
EMB_DIR = os.path.join(EMB_BASE_DIR, MODEL_NAME)


def load_chunks(chunks_dir: str) -> list[dict]:
    """
    Lädt alle Chunks aus .ndjson-Dateien.

    Returns: list of dicts with keys: chunk_id, chunk_hash, text, doc_id, ...
    """
    chunks = []
    chunks_path = Path(chunks_dir)

    if not chunks_path.exists():
        print(f"[embed_index] WARN: chunks directory not found: {chunks_dir}")
        return chunks

    for ndjson_file in chunks_path.glob("*.ndjson"):
        try:
            with open(ndjson_file, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                        # Validate required fields
                        if "chunk_hash" not in chunk or "text" not in chunk:
                            print(f"[embed_index] WARN: {ndjson_file}:{line_num} missing chunk_hash or text")
                            continue
                        chunks.append(chunk)
                    except json.JSONDecodeError as e:
                        print(f"[embed_index] WARN: {ndjson_file}:{line_num} - {e}")
        except Exception as e:
            print(f"[embed_index] ERROR: Could not read {ndjson_file}: {e}")

    return chunks


def get_existing_embeddings(emb_dir: str) -> Set[str]:
    """
    Returns set of chunk_hashes that already have embeddings (.npy files).
    """
    emb_path = Path(emb_dir)
    if not emb_path.exists():
        return set()

    return {npy_file.stem for npy_file in emb_path.glob("*.npy")}


def embed_chunks(
    chunks: list[dict],
    emb_dir: str,
    model: str,
    force: bool = False,
) -> Dict[str, int]:
    """
    Embeds chunks and saves to .npy files.

    :param chunks: List of chunk dicts
    :param emb_dir: Output directory for .npy files
    :param model: Embedding model name (passed to get_embedding)
    :param force: If True, re-embed even if .npy exists

    :returns: Stats dict {"embedded": N, "skipped": M}
    """
    os.makedirs(emb_dir, exist_ok=True)

    existing = set() if force else get_existing_embeddings(emb_dir)

    stats = {"embedded": 0, "skipped": 0}

    for i, chunk in enumerate(chunks):
        chunk_hash = chunk["chunk_hash"]
        text = chunk["text"]

        npy_path = Path(emb_dir) / f"{chunk_hash}.npy"

        if not force and chunk_hash in existing:
            stats["skipped"] += 1
            if (stats["embedded"] + stats["skipped"]) % 100 == 0:
                print(f"  ... {stats['embedded']} embedded, {stats['skipped']} skipped")
            continue

        try:
            vec = get_embedding(text, model=model)
            np.save(npy_path, vec)
            stats["embedded"] += 1

            if stats["embedded"] % 10 == 0:
                print(f"  ... {stats['embedded']} embedded, {stats['skipped']} skipped")

        except Exception as e:
            print(f"[embed_index] ERROR: Could not embed chunk {chunk_hash}: {e}", file=sys.stderr)

    return stats


def update_record_embedding_meta(
    records_dir: str,
    emb_dir: str,
    model: str,
    dim: int,
):
    """
    Updates embedding_meta in record JSONs.

    For each record:
    - Reads chunks (from chunk_hashes in record or by scanning chunks/)
    - Updates embedding_meta.text with: model, dim, updated_at, chunk_hashes
    """
    from datetime import datetime, timezone

    records_path = Path(records_dir)
    if not records_path.exists():
        print(f"[embed_index] WARN: records directory not found: {records_dir}")
        return

    emb_path = Path(emb_dir)
    existing_embeddings = {npy_file.stem for npy_file in emb_path.glob("*.npy")} if emb_path.exists() else set()

    updated = 0

    for record_file in records_path.glob("*.json"):
        try:
            with open(record_file, "r", encoding="utf-8") as f:
                record = json.load(f)

            doc_id = record.get("id")
            if not doc_id:
                continue

            # Find chunk_hashes for this doc (from chunks/*.ndjson)
            chunks_file = Path(CHUNKS_DIR) / f"{doc_id}.ndjson"
            chunk_hashes = []

            if chunks_file.exists():
                with open(chunks_file, "r", encoding="utf-8") as cf:
                    for line in cf:
                        if not line.strip():
                            continue
                        try:
                            chunk = json.loads(line)
                            chunk_hash = chunk.get("chunk_hash")
                            if chunk_hash and chunk_hash in existing_embeddings:
                                chunk_hashes.append(chunk_hash)
                        except json.JSONDecodeError:
                            continue

            if not chunk_hashes:
                continue

            # Update embedding_meta
            if "embedding_meta" not in record:
                record["embedding_meta"] = {}

            record["embedding_meta"]["text"] = {
                "model": model,
                "dim": dim,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "chunk_hashes": chunk_hashes,
            }

            # Write back
            with open(record_file, "w", encoding="utf-8") as f:
                json.dump(record, f, indent=2, ensure_ascii=False)

            updated += 1

        except Exception as e:
            print(f"[embed_index] ERROR: Could not update {record_file}: {e}", file=sys.stderr)

    print(f"[embed_index] Updated embedding_meta in {updated} records")


def main():
    print(f"[embed_index] Plan v0.3 Embedding Indexer")
    print(f"  Model: {MODEL_NAME}")
    print(f"  Chunks: {CHUNKS_DIR}")
    print(f"  Embeddings: {EMB_DIR}")
    print()

    # 1. Load chunks
    print("[1/3] Loading chunks...")
    chunks = load_chunks(CHUNKS_DIR)
    print(f"  → {len(chunks)} chunks loaded")

    if not chunks:
        print("[embed_index] No chunks found. Run chunk.py first!")
        return

    # 2. Embed chunks (incremental)
    print()
    print("[2/3] Embedding chunks (incremental)...")
    stats = embed_chunks(chunks, EMB_DIR, MODEL_NAME, force=False)
    print(f"  → {stats['embedded']} embedded, {stats['skipped']} skipped")

    # 3. Determine embedding dimension (from first .npy)
    emb_path = Path(EMB_DIR)
    dim = None
    for npy_file in emb_path.glob("*.npy"):
        try:
            vec = np.load(npy_file)
            dim = vec.shape[0]
            break
        except Exception:
            continue

    if dim is None:
        print("[embed_index] WARN: Could not determine embedding dimension")
        dim = 384  # Fallback

    # 4. Update record embedding_meta
    print()
    print("[3/3] Updating record embedding_meta...")
    update_record_embedding_meta(RECORDS_DIR, EMB_DIR, MODEL_NAME, dim)

    print()
    print("[embed_index] ✓ Done!")
    print(f"  Embeddings: {EMB_DIR}")


if __name__ == "__main__":
    main()
