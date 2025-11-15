"""
chunk.py - Records → Chunks

Plan v0.3 compliant:
- Reads Record JSONs from data/records/
- Applies hybrid chunking (hierarchical + semantic)
- Generates content-hash chunk IDs
- Writes NDJSON to data/chunks/{doc_id}.ndjson

Usage:
    python -m pkms.tools.chunk
    python -m pkms.tools.chunk --max-tokens 400
"""

from __future__ import annotations

import os
import sys
import json
from pathlib import Path

from pkms.lib.chunking import chunk_document


# Config
RECORDS_DIR = os.getenv("PKMS_RECORDS_DIR", "data/records")
CHUNKS_DIR = os.getenv("PKMS_CHUNKS_DIR", "data/chunks")


def load_record(record_path: Path) -> dict:
    """Load a Record JSON"""
    with open(record_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_chunks(chunks: list[dict], chunks_dir: Path, doc_id: str):
    """Save chunks as NDJSON to chunks_dir/{doc_id}.ndjson"""
    chunks_dir.mkdir(parents=True, exist_ok=True)

    out_path = chunks_dir / f"{doc_id}.ndjson"

    with open(out_path, "w", encoding="utf-8") as f:
        for chunk in chunks:
            json.dump(chunk, f, ensure_ascii=False)
            f.write("\n")

    print(f"[chunk] Saved {len(chunks)} chunks → {out_path}")


def chunk_record(record_path: Path, chunks_dir: Path, max_tokens: int):
    """Process a single Record and generate chunks"""
    try:
        record = load_record(record_path)

        doc_id = record["id"]
        text = record["full_text"]
        language = record.get("language", "en")

        # Generate chunks
        chunks = chunk_document(
            doc_id=doc_id,
            text=text,
            language=language,
            max_tokens=max_tokens,
        )

        # Save to NDJSON
        save_chunks(chunks, chunks_dir, doc_id)

    except Exception as e:
        print(f"[chunk] ERROR: Failed to chunk {record_path}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()


def chunk_all_records(records_dir: Path, chunks_dir: Path, max_tokens: int):
    """Process all Records in records_dir"""
    record_files = list(records_dir.glob("*.json"))

    print(f"[chunk] Found {len(record_files)} records in {records_dir}")

    for record_path in record_files:
        chunk_record(record_path, chunks_dir, max_tokens)

    print(f"\n[chunk] ✓ Chunked {len(record_files)} records")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Chunk records into smaller pieces")
    parser.add_argument(
        "--records-dir",
        default=RECORDS_DIR,
        help="Input directory with Record JSONs (default: data/records/)"
    )
    parser.add_argument(
        "--chunks-dir",
        default=CHUNKS_DIR,
        help="Output directory for chunk NDJSON files (default: data/chunks/)"
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=500,
        help="Maximum tokens per chunk (default: 500)"
    )

    args = parser.parse_args()

    records_dir = Path(args.records_dir)
    chunks_dir = Path(args.chunks_dir)

    if not records_dir.exists():
        print(f"[chunk] ERROR: Records directory does not exist: {records_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"[chunk] Plan v0.3 Chunking")
    print(f"  Input:  {records_dir}")
    print(f"  Output: {chunks_dir}")
    print(f"  Max tokens: {args.max_tokens}")
    print()

    chunk_all_records(records_dir, chunks_dir, args.max_tokens)


if __name__ == "__main__":
    main()
