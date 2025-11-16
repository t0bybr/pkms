#!/usr/bin/env python3
"""
PKMS MCP Server

Exposes PKMS tools via Model Context Protocol (MCP) for use with:
- Claude Desktop
- Cline (VSCode extension) + Ollama
- Other MCP-compatible agents

Usage:
    # Start server (for MCP clients)
    python mcp_server.py

Configuration (Cline/Claude Desktop):
    {
      "mcpServers": {
        "pkms": {
          "command": "python",
          "args": ["/path/to/.pkms/mcp_server.py"]
        }
      }
    }
"""

import sys
import json
from pathlib import Path

# Add .pkms to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import Tool

# Import PKMS libraries
from lib.config import get_path, get_config_value
from lib.search.search_engine import SearchEngine
from lib.embeddings import get_embedding

# Initialize server
server = Server("pkms")


# ============================================================
# Tool Definitions
# ============================================================

@server.list_tools()
async def list_tools():
    """List available PKMS tools."""
    return [
        Tool(
            name="search",
            description="Search the knowledge base using hybrid search (BM25 + semantic). Returns relevant chunks with metadata.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 10
                    },
                    "keyword_only": {
                        "type": "boolean",
                        "description": "Use only BM25 (no semantic search)",
                        "default": False
                    },
                    "semantic_only": {
                        "type": "boolean",
                        "description": "Use only semantic search (no BM25)",
                        "default": False
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_note",
            description="Retrieve a specific note by ULID or slug. Returns full content with metadata.",
            inputSchema={
                "type": "object",
                "properties": {
                    "identifier": {
                        "type": "string",
                        "description": "Note ULID or slug (e.g., '01KA4VH9X4HDR' or 'pizza-recipe')"
                    }
                },
                "required": ["identifier"]
            }
        ),
        Tool(
            name="list_notes",
            description="List all notes in the vault with their metadata (titles, tags, dates).",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of notes to return",
                        "default": 50
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by tags (optional)"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="update_metadata",
            description="Update metadata for vault notes after manual edits. Call this after modifying markdown files.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to specific file or directory (optional, defaults to entire vault)"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="rebuild_indexes",
            description="Rebuild search indexes (BM25 and embeddings). Use after adding/updating many notes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "full": {
                        "type": "boolean",
                        "description": "Full rebuild (chunk + embed + index)",
                        "default": False
                    }
                },
                "required": []
            }
        )
    ]


# ============================================================
# Tool Implementations
# ============================================================

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    """Execute PKMS tool and return result."""

    try:
        if name == "search":
            return await _search(arguments)
        elif name == "get_note":
            return await _get_note(arguments)
        elif name == "list_notes":
            return await _list_notes(arguments)
        elif name == "update_metadata":
            return await _update_metadata(arguments)
        elif name == "rebuild_indexes":
            return await _rebuild_indexes(arguments)
        else:
            return {"error": f"Unknown tool: {name}"}

    except Exception as e:
        return {"error": str(e), "type": type(e).__name__}


async def _search(args: dict):
    """Search knowledge base."""
    query = args["query"]
    limit = args.get("limit", 10)
    keyword_only = args.get("keyword_only", False)
    semantic_only = args.get("semantic_only", False)

    # Get paths
    chunks_dir = str(get_path("chunks"))
    index_dir = str(get_path("index"))

    model = get_config_value("embeddings", "model", "PKMS_EMBED_MODEL", "nomic-embed-text")
    emb_base_dir = str(get_path("embeddings"))
    emb_dir = f"{emb_base_dir}/{model}"

    # Initialize search engine
    from lib.config import get_search_config
    search_config = get_search_config()

    engine = SearchEngine(
        chunks_dir=chunks_dir,
        emb_dir=emb_dir,
        index_dir=index_dir,
        embed_fn=get_embedding,
        max_keyword_hits=search_config.get("max_keyword_hits", 50),
        max_semantic_hits=search_config.get("max_semantic_hits", 50),
        rrf_k=search_config.get("rrf_k", 60),
        group_limit=search_config.get("group_limit", 3),
        bm25_weight=search_config.get("bm25_weight", 0.5),
        semantic_weight=search_config.get("semantic_weight", 0.5),
        min_similarity=search_config.get("min_similarity", 0.3),
        min_rrf_score=search_config.get("min_rrf_score", 0.0),
    )

    # Perform search
    if keyword_only:
        results = engine._keyword_search(query, limit=limit)
    elif semantic_only:
        query_vec = get_embedding(query)
        results = engine._semantic_search(query_vec, limit=limit)
    else:
        results = engine.search(query, k=limit)

    return {
        "status": "success",
        "query": query,
        "total": len(results),
        "results": results[:limit]
    }


async def _get_note(args: dict):
    """Get specific note by ULID or slug."""
    identifier = args["identifier"]
    metadata_dir = get_path("metadata")

    # Try to find by ULID first
    metadata_file = metadata_dir / f"{identifier}.json"

    if not metadata_file.exists():
        # Try to find by slug
        for file in metadata_dir.glob("*.json"):
            with open(file) as f:
                data = json.load(f)
                if data.get("slug") == identifier:
                    metadata_file = file
                    break

    if not metadata_file.exists():
        return {"error": f"Note not found: {identifier}"}

    with open(metadata_file) as f:
        metadata = json.load(f)

    return {
        "status": "success",
        "note": metadata
    }


async def _list_notes(args: dict):
    """List all notes with metadata."""
    limit = args.get("limit", 50)
    tags_filter = args.get("tags")

    metadata_dir = get_path("metadata")
    notes = []

    for file in metadata_dir.glob("*.json"):
        with open(file) as f:
            metadata = json.load(f)

            # Filter by tags if specified
            if tags_filter:
                note_tags = set(metadata.get("tags", []))
                if not any(tag in note_tags for tag in tags_filter):
                    continue

            notes.append({
                "id": metadata["id"],
                "slug": metadata.get("slug"),
                "title": metadata.get("title"),
                "tags": metadata.get("tags", []),
                "created": metadata.get("created"),
                "updated": metadata.get("updated"),
                "path": metadata.get("path")
            })

    # Sort by updated date (newest first)
    notes.sort(key=lambda x: x.get("updated", ""), reverse=True)

    return {
        "status": "success",
        "total": len(notes),
        "notes": notes[:limit]
    }


async def _update_metadata(args: dict):
    """Update metadata for vault notes."""
    import subprocess

    path_arg = args.get("path")
    cmd = ["pkms-update", "--quiet"]

    if path_arg:
        cmd.append(path_arg)

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        return {"status": "success", "message": "Metadata updated"}
    else:
        return {"status": "error", "message": result.stderr}


async def _rebuild_indexes(args: dict):
    """Rebuild search indexes."""
    import subprocess

    full = args.get("full", False)

    if full:
        # Full rebuild: chunk + embed + index
        steps = [
            ["pkms-chunk"],
            ["pkms-embed"],
            ["pkms-index", "--rebuild"]
        ]
    else:
        # Just rebuild BM25 index
        steps = [["pkms-index", "--rebuild"]]

    results = []
    for cmd in steps:
        result = subprocess.run(cmd, capture_output=True, text=True)
        results.append({
            "command": " ".join(cmd),
            "success": result.returncode == 0,
            "output": result.stdout if result.returncode == 0 else result.stderr
        })

    success = all(r["success"] for r in results)

    return {
        "status": "success" if success else "partial",
        "steps": results
    }


# ============================================================
# Main Entry Point
# ============================================================

def main():
    """Start MCP server."""
    import asyncio
    asyncio.run(stdio_server(server))


if __name__ == "__main__":
    main()
