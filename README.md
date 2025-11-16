# PKMS - Personal Knowledge Management System

**Version:** 0.3.1
**Status:** Alpha - Active Development
**License:** MIT

A versioned, agent-compatible knowledge management system with hybrid search, semantic chunking, automated tagging, review queues, and MCP agent integration.

---

## 📑 Table of Contents

1. [Overview](#-overview)
2. [Features](#-features)
3. [Architecture](#-architecture)
4. [Installation](#-installation)
5. [Quick Start](#-quick-start)
6. [Workflow](#-workflow)
7. [CLI Tools](#️-cli-tools)
8. [Agent Integration](#-agent-integration)
9. [Configuration](#️-configuration)
10. [Data Formats](#-data-formats)
11. [Development](#-development)
12. [Troubleshooting](#-troubleshooting)
13. [Resources](#-resources)

---

## 🎯 Overview

PKMS v0.3 is a **Personal Knowledge Management System** designed for:

- **Researchers** managing large collections of markdown notes
- **Developers** building knowledge bases with semantic search
- **AI Agents** that need structured, versioned knowledge access
- **Teams** collaborating on documentation with git workflows

### Key Design Principles

1. **Git-Native** - All data is git-trackable (NDJSON, markdown, .npy)
2. **Content-Addressable** - Chunk IDs based on content hashes (deduplication)
3. **Agent-Compatible** - Structured schemas for LLM integration
4. **Hybrid Search** - Combines BM25 keyword + semantic embeddings
5. **Incremental** - Only reprocess changed files
6. **Inbox Workflow** - Staging area for unnormalized notes → vault

---

## ✨ Features

### ✅ Implemented (v0.3)

| Feature | Description | Tool |
|---------|-------------|------|
| **Inbox → Vault** | Staging workflow with auto-normalization | `pkms-ingest` |
| **Vault Updates** | Update metadata for existing vault files | `pkms-update` |
| **ULID in Filename** | Single source of truth (not in frontmatter) | Automatic |
| **Markdown Ingestion** | Parse frontmatter, auto-detect language | `pkms-ingest` |
| **Semantic Chunking** | Hierarchical (by headings) + semantic splitting | `pkms-chunk` |
| **Wikilink Resolution** | Bidirectional links with multiple resolution strategies | `pkms-link` |
| **Embeddings** | Ollama integration with LRU caching and incremental updates | `pkms-embed` |
| **Search Indexing** | Incremental Whoosh BM25 index with German stemming | `pkms-index` |
| **Hybrid Search** | BM25 (Whoosh) + Cosine (NumPy) with weighted RRF fusion | `pkms-search` |
| **LLM Tagging** | Automated tag suggestions using Ollama with taxonomy control | `pkms-tag` |
| **Review Queue** | Git-native approval workflow for automated operations | `pkms-review` |
| **Relevance Scoring** | Formula-based: `0.4*recency + 0.3*links + 0.2*quality + 0.1*user` | `pkms-relevance` |
| **Archive Policy** | Automated archiving based on score + age thresholds | `pkms-archive` |
| **MCP Server** | Model Context Protocol server for AI agent integration | MCP Server |
| **Git Synthesis** | Branch-based consolidation workflow | `pkms-synth` 🚧 |
| **Configuration** | Centralized `.pkms/config.toml` with ENV override support | Config system |

### 🚧 In Progress

- **Typesense Integration** - Replace Whoosh with native hybrid search (planned)
- **LLM Synthesis** - Automated note consolidation (placeholder implemented)
- **Embedding Clustering** - Graph-based related note discovery (tag-based MVP)

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      PKMS Pipeline                          │
└─────────────────────────────────────────────────────────────┘

   Inbox              Vault            Metadata          Chunks           Search
┌──────────┐      ┌────────────┐   ┌────────────┐   ┌──────────────┐   ┌──────────┐
│ inbox/   │      │ vault/     │   │data/       │   │ data/chunks/ │   │data/index│
│  *.md    │─────▶│YYYY-MM/    │──▶│metadata/   │──▶│  *.ndjson    │──▶│  Whoosh  │
│          │      │  {slug}--  │   │  *.json    │   │              │   │          │
│Staging   │      │  {ULID}.md │   │            │   │  Searchable  │   │  BM25    │
└──────────┘      └────────────┘   └────────────┘   └──────────────┘   └──────────┘
gitignored         git-tracked      git-tracked       git-tracked      gitignored
                                        │                   │               │
                                        │                   ▼               │
                                        │          ┌──────────────┐         │
                                        │          │ data/embed/  │         │
                                        │          │  *.npy       │         │
                                        │          │              │         │
                                        │          │  Vectors     │         │
                                        │          └──────────────┘         │
                                        │           git-tracked              │
                                        ▼                   ▼               ▼
                                 ┌──────────────────────────────────────────┐
                                 │         Hybrid Search Engine             │
                                 │    (BM25 + Semantic + RRF Fusion)        │
                                 └──────────────────────────────────────────┘
```

### Directory Structure

```
pkms/
├── .pkms/                       # ⚙️ Application code & config
│   ├── config.toml              # Centralized configuration
│   ├── pyproject.toml           # Python package config
│   ├── requirements.txt         # Dependencies
│   ├── models/                  # Pydantic models (Record, Chunk, etc.)
│   ├── lib/                     # Shared libraries
│   │   ├── config.py            # Configuration loader
│   │   ├── fs/                  # Filesystem utilities (ULID, slug, paths)
│   │   ├── frontmatter/         # Frontmatter parsing
│   │   ├── chunking/            # Hierarchical + semantic chunking
│   │   ├── search/              # Hybrid search engine
│   │   ├── utils/               # Hashing, language detection, tokens
│   │   └── records_io.py        # Central metadata I/O
│   └── tools/                   # CLI tools (ingest, chunk, embed, search, etc.)
│
├── inbox/                       # 📥 Staging (gitignored)
│   └── *.md                     # Unnormalized notes
│
├── vault/                       # 📝 Notes (git-tracked)
│   ├── 2025-11/                 # Organized by date (YYYY-MM)
│   │   └── {slug}--{ULID}.md
│   └── 2025-12/
│
├── data/                        # 💾 Generated data (mostly git-tracked)
│   ├── metadata/                # Metadata records (JSON) - git-tracked
│   │   └── {ULID}.json
│   ├── chunks/                  # Text chunks (NDJSON) - git-tracked
│   │   └── {ULID}.ndjson
│   ├── embeddings/              # Embeddings (NumPy .npy) - git-tracked
│   │   └── {model}/
│   │       └── {hash}.npy
│   ├── queue/                   # Review queue (pending/approved/rejected) - git-tracked
│   │   └── reviews/
│   ├── blobs/                   # Binary attachments - gitignored
│   └── index/                   # Search index (Whoosh) - gitignored
│
├── schema/                      # 📋 JSON schemas
├── tests/                       # 🧪 Unit tests
├── test_data/                   # Test fixtures
│
├── README.md                    # This file
├── TUTORIAL.md                  # Python basics with PKMS examples
├── PROBLEMS.md                  # Code review findings
└── .gitignore
```

**Key Changes in v0.3:**
- ✨ `.pkms/` - Application code separated from content (flat structure: lib/, models/, tools/)
- ✨ `inbox/` - Staging area for unnormalized notes (gitignored)
- ✨ `vault/` - Normalized notes organized by date (YYYY-MM)
- ✨ `data/metadata/` - Renamed from `data/records/` for clarity
- ✨ ULID **only in filename**, never in frontmatter
- ✨ Centralized `config.toml` with ENV variable override support

---

## 📦 Installation

### Prerequisites

- **Python 3.10+** (tested on 3.11, 3.12)
- **Git** (for version control)
- **Ollama** (optional, for embeddings)
  - Install: https://ollama.ai/
  - Pull model: `ollama pull nomic-embed-text`

### Install PKMS

```bash
# Clone repository
git clone https://github.com/yourusername/pkms.git
cd pkms

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install from .pkms/ directory
pip install -e .pkms/

# Or install with dev dependencies
pip install -e ".pkms/[dev]"

# Verify installation
pkms-ingest --help
```

**Optional Performance Boost:**
```bash
pip install -e ".pkms/[performance]"  # Includes xxhash, tiktoken
```

---

## 🚀 Quick Start

### 1. Create Your First Note (in Inbox)

```bash
mkdir -p inbox
cat > inbox/pizza-recipe.md <<'EOF'
---
title: Pizza Neapolitana Recipe
tags: [cooking, italian]
language: de
---

# Pizza Neapolitana

Bei 300°C wird der Pizzastein optimal heiß.

## Zutaten
- 500g Mehl (Tipo 00)
- 10g Salz
- 300ml Wasser

## Zubereitung
Den Teig [[kneten|gut durchkneten]] und [[fermentieren|24h fermentieren lassen]].
Siehe auch [[ofen-temperatur]] für Details.
EOF
```

**Note:** No `id` field in frontmatter! ULID will be in filename only.

### 2. Run the Pipeline

```bash
# Ingest: inbox/ → vault/YYYY-MM/ + metadata
pkms-ingest

# Chunk documents
pkms-chunk

# Extract & resolve wikilinks
pkms-link --validate

# Generate embeddings (requires Ollama)
pkms-embed

# Build search index (BM25)
pkms-index

# Update relevance scores
pkms-relevance
```

**After ingestion:**
```bash
ls vault/2025-11/
# pizza-neapolitana-recipe--01HAR6DP2M7G1KQ3Y3VQ8C0Q.md

ls data/metadata/
# 01HAR6DP2M7G1KQ3Y3VQ8C0Q.json
```

### 3. Search

```bash
# Simple search
pkms-search "pizza teig fermentieren"

# Limit results
pkms-search "embeddings" --limit 5

# JSON output
pkms-search "machine learning" --format json
```

---

## 📋 Workflow

### Daily Workflow (Note-Taking)

```bash
# 1. Write notes in inbox/ (no ULID needed)
vim inbox/new-idea.md

# 2. Ingest → automatically moves to vault/YYYY-MM/
pkms-ingest

# 3. Process pipeline
pkms-chunk
pkms-link
pkms-embed
pkms-index

# 4. Search your notes
pkms-search "my topic"

# 5. Commit vault/ to git (inbox/ is gitignored)
git add vault/ data/metadata/
git commit -m "Add new idea"
git push
```

### Weekly Workflow (Maintenance)

```bash
# Update scores
pkms-relevance

# Archive old notes
pkms-archive --dry-run  # Preview
pkms-archive            # Apply

# Find synthesis candidates
pkms-synth --find-clusters
```

---

## 🛠️ CLI Tools

### pkms-ingest

**Inbox → Vault + Metadata**

Parse markdown files from inbox/, normalize, move to vault/, and create metadata.

```bash
pkms-ingest                     # Process inbox/
pkms-ingest inbox/specific.md   # Single file
pkms-ingest --source notes/     # Custom source directory
```

**What it does:**
- Reads notes from `inbox/` (unnormalized)
- Generates ULID (if not in filename)
- Creates slug from title
- Renames to `{slug}--{ULID}.md`
- Auto-detects language if missing
- Moves to `vault/YYYY-MM/` (based on `date_created`)
- Creates metadata JSON in `data/metadata/{ULID}.json`

**ULID Strategy:**
- Priority: filename > generate new
- **Never** in frontmatter (single source of truth = filename)

---

### pkms-update

**Update metadata for existing vault files**

Update metadata records for notes already in the vault (without moving them).

```bash
pkms-update                          # Update all vault files
pkms-update vault/2025-11/note.md    # Update single file
pkms-update vault/2025-11/           # Update specific directory
```

**What it does:**
- Reads existing notes from `vault/`
- Parses frontmatter and content
- Updates metadata JSON in `data/metadata/{ULID}.json`
- Does NOT move files (unlike `pkms-ingest`)

**When to use:**
- After manually editing vault notes
- After changing frontmatter (tags, title, etc.)
- When metadata is out of sync with content

**Note:** Use `pkms-ingest` for inbox → vault, use `pkms-update` for vault → metadata updates.

---

### pkms-chunk

**Metadata → Chunks**

Split documents into semantic chunks with content-addressable IDs.

```bash
pkms-chunk                       # Chunk all metadata
pkms-chunk --max-tokens 500      # Custom chunk size
```

**Chunking Strategy:**
1. **Hierarchical:** Split by markdown headings (H1-H6)
2. **Semantic:** Further split large sections by paragraphs
3. **Content-Hash ID:** `doc_id:xxhash64(text)[:12]`

**Configuration:** See `[chunking]` section in `.pkms/config.toml`

---

### pkms-link

**Extract and resolve [[wikilinks]] bidirectionally.**

```bash
pkms-link                 # Process all metadata
pkms-link --validate      # Show broken links
```

**Resolution Order:**
1. Exact ULID match
2. Slug match
3. Alias match (case-insensitive)
4. Title match (case-insensitive)

---

### pkms-embed

**Generate embeddings via Ollama (incremental).**

```bash
pkms-embed                            # Embed new chunks
pkms-embed --model nomic-embed-text   # Specify model
pkms-embed --force                    # Re-embed all
```

**Requirements:**
- Ollama running: `ollama serve`
- Model pulled: `ollama pull nomic-embed-text`

**Configuration:** See `[embeddings]` in `.pkms/config.toml`

---

### pkms-index

**Build or update the Whoosh search index.**

```bash
pkms-index              # Incremental update (default)
pkms-index --rebuild    # Rebuild entire index from scratch
pkms-index stats        # Show index statistics
```

**What it does:**
- Reads all `.ndjson` chunk files from `data/chunks/`
- Builds/updates the Whoosh BM25 index for keyword search
- Incremental by default (only adds new chunks)
- Use `--rebuild` after structural changes or corruption

**When to run:**
- After `pkms-chunk` (to make chunks searchable)
- If search returns no BM25 results (`BM25=N/A`)
- After deleting/modifying chunk files

**Note:** Search will auto-create the index on first run, but this tool allows manual control.

---

### pkms-search

**Hybrid search CLI (BM25 + Semantic).**

```bash
pkms-search "pizza teig fermentieren"            # Hybrid search (default)
pkms-search "embeddings" --limit 5               # Limit results
pkms-search "python async" --keyword-only        # BM25 only
pkms-search "machine learning" --semantic-only   # Semantic only
pkms-search "git workflow" --format json         # JSON output
pkms-search info                                 # Show engine stats
```

**Search Modes:**
- **Hybrid (default):** Combines BM25 + semantic with RRF fusion
- **Keyword-only (`-k`):** Only BM25 search (fast, exact matches)
- **Semantic-only (`-s`):** Only vector similarity (conceptual matches)

**Output Formats:**
- **Human (default):** Pretty-printed results with scores
- **JSON (`--format json`):** Machine-readable output

**Configuration:** See `[search]` in `.pkms/config.toml`

---

### pkms-tag

**Automated tagging with LLM assistance**

Use Ollama to analyze notes and suggest tags based on content and taxonomy.

```bash
pkms-tag                         # Tag all notes (interactive mode)
pkms-tag vault/note.md           # Tag single note
pkms-tag --only-empty            # Only notes without tags
pkms-tag --queue                 # Queue suggestions for review
pkms-tag --auto                  # Apply tags automatically (use with caution!)
pkms-tag --verify                # Re-analyze existing tags
pkms-tag --suggest-new           # Allow suggesting tags not in taxonomy
```

**Modes:**
- **Interactive (default):** Show suggestions, ask for approval
- **Queue (`--queue`):** Create review for later approval (automated workflows)
- **Auto (`--auto`):** Apply tags directly without review (use carefully!)

**What it does:**
1. Reads note title and content
2. Sends to Ollama LLM with taxonomy context
3. Gets tag and category suggestions with confidence score
4. Shows suggestions for approval (or queues/auto-applies based on mode)
5. Updates frontmatter if approved

**Requirements:**
- Ollama running with a chat model (e.g., `qwen2.5-coder:latest`)
- Taxonomy file: `.pkms/taxonomy.toml`

**Configuration:** See `[llm]` in `.pkms/config.toml`

**Example output:**
```
File: pizza-recipe.md
Title: Pizza Neapolitana

Suggested tags:     cooking, italian, recipe, pizza
Suggested category: cooking
Confidence:         0.89

[a]pprove / [r]eject / [e]dit / [s]kip:
```

---

### pkms-review

**Review queue for automated operations**

Manage pending reviews created by automated tools (like `pkms-tag --queue`).

```bash
pkms-review list              # Show all pending reviews
pkms-review interactive       # Review pending items interactively
pkms-review show <id>         # Show specific review details
pkms-review approve <id>      # Approve specific review
pkms-review reject <id>       # Reject specific review
```

**What it does:**
- Lists pending reviews created by automated operations
- Shows details about suggested changes
- Allows approval/rejection of changes
- Automatically applies approved changes (e.g., updating taxonomy)

**Review types:**
- `tag_approval` - New tag suggestions from `pkms-tag`
- (More types can be added by tools)

**Example workflow:**
```bash
# 1. Auto-tag notes (creates review)
pkms-tag --queue

# 2. Review suggestions
pkms-review list
# → 1 pending: tag_approval_20251116_143022 (5 new tags)

# 3. Approve interactively
pkms-review interactive
# → Shows each new tag with usage count
# → [a]pprove / [r]eject for each

# 4. Changes are applied automatically
# → taxonomy.toml updated with approved tags
```

**Configuration:** Reviews stored in `data/queue/reviews/`

---

### pkms-relevance

**Compute relevance scores using formula.**

```bash
pkms-relevance            # Update all scores
pkms-relevance --verbose  # Show changes
```

**Formula:**
```
relevance = 0.4 * recency + 0.3 * links + 0.2 * quality + 0.1 * user

Where:
- recency  = e^(-age_days / 180)  # 6-month half-life
- links    = log(1 + backlinks) / log(101)  # Log-scale
- quality  = word_score + has_links + media
- user     = human_edited + agent_reviewed
```

**Configuration:** See `[relevance]` in `.pkms/config.toml`

---

### pkms-archive

**Archive low-relevance old documents.**

```bash
pkms-archive --dry-run    # Preview (safe)
pkms-archive              # Apply
```

**Policy:**
```
Archive if:
  relevance_score < 0.3
  AND age > 365 days
  AND NOT already archived
```

**Important:** Never deletes files, only sets `status.archived = true`

---

### pkms-synth

**Git-based synthesis workflow (experimental).**

```bash
pkms-synth --find-clusters   # List related notes
pkms-synth --create 0        # Create synthesis
```

**Status:** 🚧 Framework implemented, LLM integration TODO

---

## 🤖 Agent Integration

PKMS can be integrated with AI agents via the **Model Context Protocol (MCP)** server. This allows agents like Cline (VSCode) or Claude Desktop to search, read, and update your knowledge base.

### MCP Server

The MCP server exposes 5 core tools:

| Tool | Description |
|------|-------------|
| `search` | Search the knowledge base (hybrid BM25 + semantic) |
| `get_note` | Retrieve specific note by ULID |
| `list_notes` | List all notes with optional filters |
| `update_metadata` | Update metadata for vault files |
| `rebuild_indexes` | Rebuild search indexes |

### Quick Setup

**1. Install MCP dependencies:**
```bash
pip install -e ".pkms/[mcp]"
```

**2. Configure your agent:**

**For Cline (VSCode):**
```json
{
  "mcpServers": {
    "pkms": {
      "command": "python",
      "args": ["/absolute/path/to/pkms/.pkms/mcp_server.py"],
      "env": {
        "PKMS_ROOT": "/absolute/path/to/pkms"
      }
    }
  }
}
```

**For Claude Desktop:**
```json
{
  "mcpServers": {
    "pkms": {
      "command": "python",
      "args": ["/absolute/path/to/pkms/.pkms/mcp_server.py"],
      "env": {
        "PKMS_ROOT": "/absolute/path/to/pkms"
      }
    }
  }
}
```

**3. Restart your agent** and start using PKMS tools!

### Example Usage

Once configured, you can ask your agent:

- "Search for notes about pizza recipes"
- "Show me the note with ULID 01HAR6DP..."
- "List all notes from November 2025"
- "Update metadata for all vault files"
- "Rebuild the search index"

### Advanced Setup

See **[.pkms/MCP_SETUP.md](.pkms/MCP_SETUP.md)** for detailed setup instructions, troubleshooting, and Docker integration.

---

## ⚙️ Configuration

### .pkms/config.toml

Centralized configuration file with **ENV variable override support**.

**Priority chain:** `ENV variable > config.toml > hardcoded default`

This allows you to:
- Configure defaults in `config.toml` for local development
- Override with ENV variables in Docker/CI environments
- Fall back to sensible defaults if neither is set

```toml
[paths]
inbox = "inbox"
vault = "vault"
metadata = "data/metadata"
chunks = "data/chunks"
embeddings = "data/embeddings"
blobs = "data/blobs"
index = "data/index"

[vault]
organize_by_date = true
date_format = "%Y-%m"          # YYYY-MM for monthly folders
date_field = "date_created"    # Options: date_created, date_updated, date_semantic

[embeddings]
# Recommended for German: jina/jina-embeddings-v2-base-de:latest
model = "jina/jina-embeddings-v2-base-de:latest"
ollama_url = "http://localhost:11434"

[llm]
# Chat model for LLM operations (tagging, summarization, etc.)
# Recommended: qwen2.5-coder (fast, good at analysis), llama3.1, mistral
model = "qwen2.5-coder:latest"
ollama_url = "http://localhost:11434"
temperature = 0.3           # Lower = more deterministic (0.0-1.0)
max_tokens = 2000

[search]
bm25_weight = 0.5           # Weight for BM25 in hybrid search (0.0-1.0)
semantic_weight = 0.5       # Weight for semantic in hybrid search (0.0-1.0)
min_similarity = 0.2        # Minimum semantic similarity threshold (lowered for better recall)
min_rrf_score = 0.0005      # Minimum RRF score to show (filters noise)
max_keyword_hits = 50       # Max BM25 results before fusion
max_semantic_hits = 50      # Max semantic results before fusion
rrf_k = 60                  # RRF parameter (higher = smoother fusion)
group_limit = 3             # Max results per document

[relevance]
weight_recency = 0.4
weight_links = 0.3
weight_quality = 0.2
weight_user = 0.1
recency_half_life_days = 90.0

[chunking]
strategy = "fixed"             # Options: fixed, semantic
chunk_size = 512
chunk_overlap = 64
min_chunk_size = 100

[git]
auto_commit = false
auto_push = false
```

### Accessing Configuration in Code

```python
from lib.config import get_path, get_vault_config, get_embeddings_config

# Get paths (resolved to absolute Path objects)
inbox_path = get_path("inbox")
vault_path = get_path("vault")
metadata_path = get_path("metadata")

# Get specific config sections
vault_config = get_vault_config()
# => {"organize_by_date": True, "date_format": "%Y-%m", ...}

emb_config = get_embeddings_config()
# => {"model": "nomic-embed-text", "ollama_url": "http://..."}

# Get config values with ENV override support
from lib.config import get_config_value
model = get_config_value("embeddings", "model", "PKMS_EMBED_MODEL", "nomic-embed-text")
# Priority: PKMS_EMBED_MODEL env var > config.toml [embeddings] model > "nomic-embed-text"
```

---

## 📊 Data Formats

### Markdown (Vault)

**Filename:** `{slug}--{ULID}.md`

**IMPORTANT:** ULID is **ONLY** in filename, **NOT** in frontmatter!

```yaml
---
title: Pizza Neapolitana Recipe
tags: [cooking, italian]
language: de
---

# Content with [[wikilinks]]
```

**Notice:** No `id` field! ULID is extracted from filename.

---

### Metadata JSON

**File:** `data/metadata/{ULID}.json`

```json
{
  "id": "01HAR6DP2M7G1KQ3Y3VQ8C0Q",
  "slug": "pizza-neapolitana-recipe",
  "title": "Pizza Neapolitana Recipe",
  "language": "de",
  "path": "vault/2025-11/pizza-neapolitana-recipe--01HAR6DP.md",
  "full_text": "...",
  "content_hash": "sha256:abc123...",
  "status": {
    "relevance_score": 0.82,
    "archived": false
  },
  "links": [...],
  "backlinks": [...]
}
```

---

### Chunk NDJSON (Searchable Units)

**File:** `data/chunks/{doc_id}.ndjson`

```json
{"chunk_id":"01HAR6DP:a3f2bc1d9e8f","text":"# Pizza...","tokens":87}
{"chunk_id":"01HAR6DP:b7d4e9a2c1f3","text":"## Zutaten...","tokens":42}
```

---

### Embedding .npy (Vectors)

**File:** `data/embeddings/{model}/{chunk_hash}.npy`

NumPy binary array, shape `(384,)` for nomic-embed-text

---

## 🧪 Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".pkms/[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=pkms --cov-report=html
```

### Test Data

See `test_data/README.md`:
- **notes_good/**: Valid examples with bidirectional links
- **notes_problematic/**: Edge cases (broken links, invalid ULID, etc.)

### Code Quality

```bash
black .pkms/pkms/ tests/     # Format
ruff check .pkms/pkms/       # Lint
mypy .pkms/pkms/             # Type checking
```

---

## 🐛 Troubleshooting

### Common Issues

**"No module named 'pkms'"**
```bash
pip install -e .pkms/
```

**"Could not find .pkms/ directory"**
```bash
# Make sure you're running from project root
cd /path/to/pkms
pkms-ingest
```

**"Ollama connection refused"**
```bash
ollama serve
```

**"module 'ulid' has no attribute 'new'"**
```bash
# Wrong ulid package - reinstall correct one
pip uninstall ulid ulid-py
pip install python-ulid>=2.0.0
```

**"Whoosh index locked"**
```bash
rm data/index/*.lock
```

### Known Issues

See [PROBLEMS.md](PROBLEMS.md) for complete list.

**Fixed in v0.3.0:**
- ✅ Artificial relevance score minimum
- ✅ Git add wildcard issue in synth.py
- ✅ Code duplication (now centralized)
- ✅ ULID in frontmatter (removed - filename only)

**To Be Fixed:**
- 🚧 N+1 file opens in embed_index.py
- 🚧 Missing Ollama retry logic
- 🚧 Synth tool needs LLM integration

---

## 📚 Resources

### Documentation

- **[TUTORIAL.md](TUTORIAL.md)** - Python basics with PKMS examples
- **[TAGGING_GUIDE.md](TAGGING_GUIDE.md)** - Automated tagging, taxonomy, and review workflows
- **[.pkms/MCP_SETUP.md](.pkms/MCP_SETUP.md)** - MCP server setup for agent integration
- **[PROBLEMS.md](PROBLEMS.md)** - Code review findings
- **[plan.md](plan.md)** - Architectural design doc (may be outdated)

### External Links

- [Ollama](https://ollama.ai/)
- [Pydantic](https://docs.pydantic.dev/)
- [Whoosh](https://whoosh.readthedocs.io/)
- [python-ulid](https://pypi.org/project/python-ulid/)

---

## 📜 License

MIT License - see LICENSE file

---

## 📝 Changelog

### v0.3.1 (2025-11-16)

**Added:**
- ✨ **pkms-update** - Update metadata for existing vault files
- ✨ **pkms-tag** - LLM-based automated tagging with Ollama
- ✨ **pkms-review** - Git-native review queue for automated operations
- ✨ **MCP Server** - Model Context Protocol server for agent integration
- ✨ **taxonomy.toml** - Controlled vocabulary for consistent tagging
- ✨ **[llm]** config section - Separate chat model configuration
- ✨ **German stemming** - Whoosh BM25 with German language support
- ✨ **Weighted RRF** - Configurable weights for hybrid search fusion
- ✨ **Git hooks** - post-merge hook for review notifications
- ✨ **Cline integration** - user-prompt-submit-hook for review checks

**Changed:**
- 🔄 Embedding model → `jina/jina-embeddings-v2-base-de:latest` (German-optimized)
- 🔄 min_similarity → 0.2 (lowered for better recall)
- 🔄 Search filtering → Filter before limit (not after)
- 🔄 Debug output → stderr (for clean JSON output)
- 🔄 .gitignore → Track metadata, chunks, embeddings, queue (only ignore index, blobs)

**Fixed:**
- ✅ Semantic search quality for German text
- ✅ pkms-update Path object handling
- ✅ parse_file unpacking (2 values, not 3)
- ✅ min_similarity filtering order
- ✅ SearchEngine missing min_similarity parameter

**Documentation:**
- ✅ Updated README.md with new tools
- ✅ Added MCP_SETUP.md for agent integration
- ✅ Added review queue workflow documentation
- ✅ Updated configuration examples

### v0.3.0 (2025-11-15)

**Added:**
- ✨ Inbox → Vault workflow with auto-normalization
- ✨ ULID only in filename (removed from frontmatter)
- ✨ `.pkms/` directory structure (code/config separation)
- ✨ Centralized configuration (`.pkms/config.toml`)
- ✨ Config system (`pkms/lib/config.py`)
- ✨ Date-based vault organization (`vault/YYYY-MM/`)
- ✨ Complete pipeline (ingest, chunk, link, embed, relevance, archive, synth)
- ✨ JSON schemas + Pydantic models
- ✨ Hybrid search engine
- ✨ Comprehensive test suite

**Changed:**
- 🔄 `data/records/` → `data/metadata/` (clarity)
- 🔄 Moved code to `.pkms/pkms/`
- 🔄 Moved config files to `.pkms/`

**Fixed:**
- ✅ 4 CRITICAL bugs (see PROBLEMS.md)
- ✅ Code duplication via `pkms/lib/records_io.py`
- ✅ Timezone-awareness
- ✅ Exception handling
- ✅ ULID API (changed from `ulid.new()` to `ULID()`)

**Documentation:**
- ✅ README.md (this file)
- ✅ PROBLEMS.md
- ✅ TUTORIAL.md
- ✅ Comprehensive docstrings

---

**Happy Knowledge Managing! 🚀**

For questions, open an issue on GitHub.

---

**Note:** Old Docker/Microservices README saved as [README.docker.md](README.docker.md)
