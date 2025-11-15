"""
index.py - CLI for building/updating the Whoosh search index

Usage:
    pkms-index              # Update index (incremental)
    pkms-index --rebuild    # Rebuild index from scratch
    pkms-index --stats      # Show index statistics
"""

from __future__ import annotations

import sys
import json
import re
from pathlib import Path
from typing import Optional

try:
    import typer
except ImportError:
    print("Error: typer not installed. Run: pip install typer", file=sys.stderr)
    sys.exit(1)

from whoosh.index import create_in, open_dir, exists_in
from whoosh.fields import Schema, TEXT, ID, STORED

from lib.config import get_chunks_dir, get_path

app = typer.Typer(help="PKMS Search Index Management")


def _strip_wikilinks(text: str) -> str:
    """
    Remove wikilinks from text, keeping display text if present.

    Examples:
    - [[target]] → "" (removed)
    - [[target|display]] → "display" (keep display text)
    - Text with [[link]] → "Text with "

    This prevents link targets from being searchable in BM25 index.
    """
    # Pattern: [[target|display]] or [[target]]
    # Group 1: target, Group 2: |display (optional)
    pattern = r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]'

    def replace_link(match):
        display_text = match.group(2)  # Optional display text
        return display_text if display_text else ""

    return re.sub(pattern, replace_link, text)


def _get_schema() -> Schema:
    """
    Whoosh schema for chunks (same as in search_engine.py).

    Fields:
    - chunk_id: unique identifier (doc_id:chunk_hash)
    - doc_id: parent document ULID (for grouping)
    - text: chunk content (indexed AND stored for display)
    - section: heading/section name (stored for display)
    - chunk_index: for ordering within doc
    """
    return Schema(
        chunk_id=ID(stored=True, unique=True),
        doc_id=ID(stored=True),
        text=TEXT(stored=True),  # indexed AND stored for display
        section=STORED(),
        chunk_index=STORED(),
    )


def _index_chunks(chunks_dir: str, index_dir: str, rebuild: bool = False) -> dict:
    """
    Build or update the Whoosh index from chunk NDJSON files.

    Returns:
        Statistics dict with counts
    """
    chunks_path = Path(chunks_dir)
    if not chunks_path.exists():
        print(f"Error: Chunks directory not found: {chunks_dir}", file=sys.stderr)
        print("Run: pkms-chunk", file=sys.stderr)
        sys.exit(1)

    # Create index directory if needed
    index_path = Path(index_dir)
    if not index_path.exists():
        index_path.mkdir(parents=True, exist_ok=True)

    # Rebuild or update?
    if rebuild and exists_in(index_dir):
        print("🔄 Rebuilding index from scratch...")
        import shutil
        shutil.rmtree(index_dir)
        index_path.mkdir(parents=True, exist_ok=True)

    # Open or create index
    if exists_in(index_dir):
        ix = open_dir(index_dir)
        print("📂 Opening existing index...")
        mode = "update"
    else:
        schema = _get_schema()
        ix = create_in(index_dir, schema)
        print("✨ Creating new index...")
        mode = "create"

    # Collect all chunk IDs from NDJSON files
    all_chunk_ids = set()
    chunk_data = []

    ndjson_files = list(chunks_path.glob("*.ndjson"))
    if not ndjson_files:
        print(f"⚠️  No NDJSON files found in {chunks_dir}", file=sys.stderr)
        print("Run: pkms-chunk", file=sys.stderr)
        return {"indexed": 0, "errors": 0, "files": 0, "mode": mode}

    print(f"📖 Reading {len(ndjson_files)} chunk files...")

    errors = 0
    for ndjson_file in ndjson_files:
        try:
            with open(ndjson_file, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                        chunk_id = chunk["chunk_id"]
                        all_chunk_ids.add(chunk_id)

                        # Combine section + text for searchability
                        section = chunk.get("section", "")
                        text = chunk["text"]
                        combined = f"{section}\n{text}" if section else text

                        # Strip wikilinks from searchable text
                        searchable_text = _strip_wikilinks(combined)

                        chunk_data.append({
                            "chunk_id": chunk_id,
                            "doc_id": chunk["doc_id"],
                            "text": searchable_text,
                            "section": section,
                            "chunk_index": chunk.get("chunk_index", 0),
                        })
                    except (json.JSONDecodeError, KeyError) as e:
                        errors += 1
                        print(f"⚠️  {ndjson_file.name}:{line_num} - {e}", file=sys.stderr)
        except Exception as e:
            errors += 1
            print(f"⚠️  Could not read {ndjson_file}: {e}", file=sys.stderr)

    if not chunk_data:
        print("❌ No valid chunks found!", file=sys.stderr)
        return {"indexed": 0, "errors": errors, "files": len(ndjson_files), "mode": mode}

    # Get existing chunk IDs from index (for incremental update)
    existing_ids = set()
    if mode == "update":
        with ix.searcher() as searcher:
            for doc in searcher.all_stored_fields():
                existing_ids.add(doc.get("chunk_id"))

    # Determine which chunks to add
    if mode == "create" or rebuild:
        chunks_to_add = chunk_data
        print(f"📝 Indexing {len(chunks_to_add)} chunks...")
    else:
        chunks_to_add = [c for c in chunk_data if c["chunk_id"] not in existing_ids]
        if chunks_to_add:
            print(f"📝 Adding {len(chunks_to_add)} new chunks...")
        else:
            print("✅ Index is up to date (no new chunks)")

    # Index chunks
    if chunks_to_add:
        writer = ix.writer()
        for chunk in chunks_to_add:
            try:
                writer.add_document(**chunk)
            except Exception as e:
                errors += 1
                print(f"⚠️  Failed to index {chunk['chunk_id']}: {e}", file=sys.stderr)
        writer.commit()

    return {
        "indexed": len(chunks_to_add),
        "total": len(all_chunk_ids),
        "existing": len(existing_ids),
        "errors": errors,
        "files": len(ndjson_files),
        "mode": mode,
    }


@app.command()
def build(
    rebuild: bool = typer.Option(False, "--rebuild", "-r", help="Rebuild index from scratch"),
):
    """
    Build or update the search index.

    By default, performs incremental update (only new chunks).
    Use --rebuild to recreate the entire index.

    Examples:
        pkms-index              # Incremental update
        pkms-index --rebuild    # Full rebuild
    """
    # Get paths from config
    chunks_dir = get_chunks_dir()

    try:
        index_dir = str(get_path("index"))
    except (FileNotFoundError, KeyError):
        index_dir = "data/index"

    print(f"\n🔍 PKMS Index Builder")
    print(f"{'=' * 60}")
    print(f"Chunks directory: {chunks_dir}")
    print(f"Index directory:  {index_dir}")
    print(f"{'=' * 60}\n")

    try:
        stats = _index_chunks(chunks_dir, index_dir, rebuild=rebuild)
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Print summary
    print(f"\n{'=' * 60}")
    print("📊 Summary:")
    print(f"  Mode:           {stats['mode']}")
    print(f"  Files read:     {stats['files']}")
    print(f"  Total chunks:   {stats['total']}")
    if stats['mode'] == 'update' and not rebuild:
        print(f"  Already indexed: {stats['existing']}")
    print(f"  Newly indexed:  {stats['indexed']}")
    if stats['errors'] > 0:
        print(f"  Errors:         {stats['errors']}")
    print(f"{'=' * 60}")

    if stats['indexed'] > 0:
        print("\n✅ Index updated successfully!")
    elif stats['total'] > 0:
        print("\n✅ Index is up to date!")
    else:
        print("\n⚠️  No chunks found. Run: pkms-chunk")


@app.command()
def stats():
    """Show index statistics."""
    try:
        index_dir = str(get_path("index"))
    except (FileNotFoundError, KeyError):
        index_dir = "data/index"

    if not exists_in(index_dir):
        print(f"❌ No index found at: {index_dir}", file=sys.stderr)
        print("Run: pkms-index", file=sys.stderr)
        sys.exit(1)

    ix = open_dir(index_dir)

    print(f"\n📊 Index Statistics")
    print(f"{'=' * 60}")
    print(f"Location:     {index_dir}")
    print(f"Documents:    {ix.doc_count_all()}")
    print(f"Last updated: {ix.last_modified()}")
    print(f"{'=' * 60}\n")

    # Sample some documents
    with ix.searcher() as searcher:
        doc_ids = set()
        for doc in searcher.all_stored_fields():
            doc_ids.add(doc.get("doc_id"))

        print(f"Unique documents: {len(doc_ids)}")
        print(f"Total chunks:     {ix.doc_count_all()}")

        if doc_ids:
            print(f"\nSample documents:")
            for doc_id in list(doc_ids)[:5]:
                print(f"  - {doc_id}")


def main():
    """Entry point for CLI."""
    # If no arguments, run build
    # Otherwise use typer app
    if len(sys.argv) == 1:
        # No args → run build (incremental)
        build(rebuild=False)
    else:
        app()


if __name__ == "__main__":
    main()
