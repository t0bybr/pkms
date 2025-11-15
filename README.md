# PKMS - Personal Knowledge Management System

**Version:** 0.3.0
**Status:** Alpha - Active Development
**License:** MIT

A versioned, agent-compatible knowledge management system with hybrid search, semantic chunking, and git-based synthesis workflows.

---

## 📑 Table of Contents

1. [Overview](#-overview)
2. [Features](#-features)
3. [Architecture](#-architecture)
4. [Installation](#-installation)
5. [Quick Start](#-quick-start)
6. [Workflow](#-workflow)
7. [CLI Tools](#️-cli-tools)
8. [Configuration](#️-configuration)
9. [Data Formats](#-data-formats)
10. [Development](#-development)
11. [Troubleshooting](#-troubleshooting)
12. [Resources](#-resources)

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
| **ULID in Filename** | Single source of truth (not in frontmatter) | Automatic |
| **Markdown Ingestion** | Parse frontmatter, auto-detect language | `pkms-ingest` |
| **Semantic Chunking** | Hierarchical (by headings) + semantic splitting | `pkms-chunk` |
| **Wikilink Resolution** | Bidirectional links with multiple resolution strategies | `pkms-link` |
| **Hybrid Search** | BM25 (Whoosh) + Cosine (NumPy) with RRF fusion | SearchEngine |
| **Relevance Scoring** | Formula-based: `0.4*recency + 0.3*links + 0.2*quality + 0.1*user` | `pkms-relevance` |
| **Archive Policy** | Automated archiving based on score + age thresholds | `pkms-archive` |
| **Embeddings** | Ollama integration with LRU caching and incremental updates | `pkms-embed` |
| **Git Synthesis** | Branch-based consolidation workflow | `pkms-synth` 🚧 |
| **Configuration** | Centralized `.pkms/config.toml` with path resolution | Config system |

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
│ inbox/   │      │ vault/     │   │data/       │   │ data/chunks/ │   │  Whoosh  │
│  *.md    │─────▶│YYYY-MM/    │──▶│metadata/   │──▶│  *.ndjson    │──▶│  Index   │
│          │      │  {slug}--  │   │  *.json    │   │              │   │          │
│Staging   │      │  {ULID}.md │   │            │   │  Searchable  │   │  BM25    │
└──────────┘      └────────────┘   └────────────┘   └──────────────┘   └──────────┘
gitignored         git-tracked          │                   │               │
                                        │                   ▼               │
                                        │          ┌──────────────┐         │
                                        │          │ data/embed/  │         │
                                        │          │  *.npy       │         │
                                        │          │              │         │
                                        │          │  Vectors     │         │
                                        │          └──────────────┘         │
                                        │                   │               │
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
│   └── pkms/                    # Python package
│       ├── models/              # Pydantic models (Record, Chunk, etc.)
│       ├── lib/                 # Shared libraries
│       │   ├── config.py        # Configuration loader
│       │   ├── fs/              # Filesystem utilities (ULID, slug, paths)
│       │   ├── frontmatter/     # Frontmatter parsing
│       │   ├── chunking/        # Hierarchical + semantic chunking
│       │   ├── search/          # Hybrid search engine
│       │   ├── utils/           # Hashing, language detection, tokens
│       │   └── records_io.py    # Central metadata I/O
│       └── tools/               # CLI tools (ingest, chunk, embed, etc.)
│
├── inbox/                       # 📥 Staging (gitignored)
│   └── *.md                     # Unnormalized notes
│
├── vault/                       # 📝 Notes (git-tracked)
│   ├── 2025-11/                 # Organized by date (YYYY-MM)
│   │   └── {slug}--{ULID}.md
│   └── 2025-12/
│
├── data/                        # 💾 Generated data (gitignored)
│   ├── metadata/                # Metadata records (JSON)
│   │   └── {ULID}.json
│   ├── chunks/                  # Text chunks (NDJSON)
│   │   └── {ULID}.ndjson
│   ├── embeddings/              # Embeddings (NumPy .npy)
│   │   └── {model}/
│   │       └── {hash}.npy
│   ├── blobs/                   # Binary attachments (PDFs, images)
│   └── index/                   # Search index (Whoosh)
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
- ✨ `.pkms/` - Application code separated from content
- ✨ `inbox/` - Staging area for unnormalized notes (gitignored)
- ✨ `vault/` - Normalized notes organized by date (YYYY-MM)
- ✨ `data/metadata/` - Renamed from `data/records/` for clarity
- ✨ ULID **only in filename**, never in frontmatter

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

```python
from pkms.lib.search.search_engine import SearchEngine
from pkms.lib.embeddings import get_embedding
from pkms.lib.config import get_path

engine = SearchEngine(
    chunks_dir=str(get_path("chunks")),
    emb_dir=str(get_path("embeddings") / "nomic-embed-text"),
    embed_fn=get_embedding
)

results = engine.search("Pizza Teig fermentieren", k=5)
for hit in results:
    print(f"[{hit['score']:.3f}] {hit['text'][:100]}...")
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

# 4. Commit vault/ to git (inbox/ is gitignored)
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

## ⚙️ Configuration

### .pkms/config.toml

Centralized configuration file:

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
model = "nomic-embed-text"
ollama_url = "http://localhost:11434"

[search]
bm25_weight = 0.5
semantic_weight = 0.5
min_similarity = 0.3

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
from pkms.lib.config import get_path, get_vault_config, get_embeddings_config

# Get paths (resolved to absolute Path objects)
inbox_path = get_path("inbox")
vault_path = get_path("vault")
metadata_path = get_path("metadata")

# Get specific config sections
vault_config = get_vault_config()
# => {"organize_by_date": True, "date_format": "%Y-%m", ...}

emb_config = get_embeddings_config()
# => {"model": "nomic-embed-text", "ollama_url": "http://..."}
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
