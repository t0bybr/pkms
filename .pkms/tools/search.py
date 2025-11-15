"""
search.py - CLI for hybrid search

Plan v0.3 compliant:
- Hybrid search (BM25 + Semantic with RRF fusion)
- Keyword-only or semantic-only modes
- JSON or human-readable output
- Configurable via config.toml

Usage:
    pkms-search "pizza ofen temperatur"
    pkms-search "embeddings" --limit 5
    pkms-search "python async" --keyword-only
    pkms-search "machine learning" --semantic-only
    pkms-search "git workflow" --format json
"""

from __future__ import annotations

import sys
import json
from pathlib import Path
from typing import Optional

try:
    import typer
except ImportError:
    print("Error: typer not installed. Run: pip install typer", file=sys.stderr)
    sys.exit(1)

from lib.search.search_engine import SearchEngine
from lib.embeddings import get_embedding
from lib.config import get_config_value, get_chunks_dir, get_path

app = typer.Typer(help="PKMS Hybrid Search CLI")


def _get_search_engine() -> SearchEngine:
    """Initialize SearchEngine with config.toml settings."""
    # Get paths from config
    chunks_dir = get_chunks_dir()

    try:
        index_dir = str(get_path("index"))
    except (FileNotFoundError, KeyError):
        index_dir = "data/index"

    # Get embedding model and base directory
    model = get_config_value("embeddings", "model", "PKMS_EMBED_MODEL", "nomic-embed-text")

    try:
        emb_base_dir = str(get_path("embeddings"))
    except (FileNotFoundError, KeyError):
        emb_base_dir = "data/embeddings"

    emb_dir = f"{emb_base_dir}/{model}"

    # Get search config
    try:
        from lib.config import get_search_config
        search_config = get_search_config()
        max_keyword_hits = search_config.get("max_keyword_hits", 50)
        max_semantic_hits = search_config.get("max_semantic_hits", 50)
        rrf_k = search_config.get("rrf_k", 60)
        group_limit = search_config.get("group_limit", 3)
    except Exception:
        # Fallback to defaults
        max_keyword_hits = 50
        max_semantic_hits = 50
        rrf_k = 60
        group_limit = 3

    return SearchEngine(
        chunks_dir=chunks_dir,
        emb_dir=emb_dir,
        index_dir=index_dir,
        embed_fn=get_embedding,
        max_keyword_hits=max_keyword_hits,
        max_semantic_hits=max_semantic_hits,
        rrf_k=rrf_k,
        group_limit=group_limit,
    )


def _format_human(results: list[dict], query: str, limit: int) -> None:
    """Human-readable output format."""
    if not results:
        print(f"No results found for: {query!r}")
        return

    print(f"\n🔍 Search results for: {query!r}")
    print(f"Found {len(results)} chunks (showing top {min(len(results), limit)})\n")
    print("=" * 80)

    for i, r in enumerate(results[:limit], 1):
        chunk_id = r.get("chunk_id", "")
        doc_id = r.get("doc_id", "")
        rrf_score = r.get("rrf_score", 0.0)
        bm25 = r.get("bm25")
        semantic = r.get("semantic")
        source = r.get("source", "unknown")
        section = r.get("section", "")

        print(f"\n{i}. {chunk_id}")
        print(f"   Document: {doc_id}")
        print(f"   Section:  {section or '(no section)'}")
        print(f"   Score:    RRF={rrf_score:.4f} | BM25={bm25 or 'N/A'} | Semantic={semantic or 'N/A'}")
        print(f"   Source:   {source}")

    print("\n" + "=" * 80)


def _format_json(results: list[dict], limit: int) -> None:
    """JSON output format."""
    output = {
        "total": len(results),
        "limit": limit,
        "results": results[:limit]
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(10, "--limit", "-l", help="Maximum number of results"),
    keyword_only: bool = typer.Option(False, "--keyword-only", "-k", help="Use only BM25 (no semantic)"),
    semantic_only: bool = typer.Option(False, "--semantic-only", "-s", help="Use only semantic (no BM25)"),
    format: str = typer.Option("human", "--format", "-f", help="Output format: human or json"),
):
    """
    Search your knowledge base with hybrid search.

    Examples:

        # Hybrid search (default)
        pkms-search "pizza ofen temperatur"

        # Limit results
        pkms-search "embeddings" --limit 5

        # Keyword-only (BM25)
        pkms-search "python async" --keyword-only

        # Semantic-only (cosine similarity)
        pkms-search "machine learning concepts" --semantic-only

        # JSON output
        pkms-search "git workflow" --format json
    """
    try:
        engine = _get_search_engine()
    except Exception as e:
        print(f"Error: Failed to initialize search engine: {e}", file=sys.stderr)
        print("Make sure you have run: pkms-chunk && pkms-embed", file=sys.stderr)
        sys.exit(1)

    # Perform search based on mode
    try:
        if keyword_only:
            # BM25-only search
            results = engine._keyword_search(query, limit=limit)
            # Convert to standard format
            results = [
                {
                    "chunk_id": r["chunk_id"],
                    "doc_id": r["doc_id"],
                    "rrf_score": None,
                    "bm25": r["score"],
                    "semantic": None,
                    "source": "keyword",
                    "section": r.get("section", ""),
                    "chunk_index": r.get("chunk_index", 0),
                }
                for r in results
            ]
        elif semantic_only:
            # Semantic-only search
            query_vec = get_embedding(query)
            results = engine._semantic_search(query_vec, limit=limit)
            # Convert to standard format
            results = [
                {
                    "chunk_id": r["chunk_id"],
                    "doc_id": r["doc_id"],
                    "rrf_score": None,
                    "bm25": None,
                    "semantic": r["score"],
                    "source": "semantic",
                    "section": "",
                    "chunk_index": 0,
                }
                for r in results
            ]
        else:
            # Hybrid search (default)
            results = engine.search(query, k=limit)

    except Exception as e:
        print(f"Error: Search failed: {e}", file=sys.stderr)
        sys.exit(1)

    # Format output
    if format.lower() == "json":
        _format_json(results, limit)
    else:
        _format_human(results, query, limit)


@app.command()
def info():
    """Show search engine configuration and statistics."""
    try:
        engine = _get_search_engine()
    except Exception as e:
        print(f"Error: Failed to initialize search engine: {e}", file=sys.stderr)
        sys.exit(1)

    print("\n📊 PKMS Search Engine Info\n")
    print("=" * 60)
    print(f"Chunks directory:    {engine.chunks_dir}")
    print(f"Embeddings:          {engine.emb_dir}")
    print(f"Index directory:     {engine.index_dir}")
    print(f"Loaded embeddings:   {len(engine.chunk_hashes)}")
    print(f"Max keyword hits:    {engine.max_keyword_hits}")
    print(f"Max semantic hits:   {engine.max_semantic_hits}")
    print(f"RRF parameter k:     {engine.rrf_k}")
    print(f"Group limit:         {engine.group_limit}")
    print("=" * 60)

    if engine.ix:
        print("\n✅ Whoosh index: Available")
    else:
        print("\n⚠️  Whoosh index: Not available")

    if len(engine.chunk_hashes) > 0:
        print(f"✅ Embeddings: {len(engine.chunk_hashes)} chunks indexed")
    else:
        print("⚠️  Embeddings: No embeddings found (run pkms-embed)")

    print()


def main():
    """Entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
