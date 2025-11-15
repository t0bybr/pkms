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

---

## ✨ Features

### ✅ Implemented (v0.3)

| Feature | Description | Tool |
|---------|-------------|------|
| **Markdown Ingestion** | Parse frontmatter, auto-detect language, generate ULIDs | `pkms-ingest` |
| **Semantic Chunking** | Hierarchical (by headings) + semantic splitting | `pkms-chunk` |
| **Wikilink Resolution** | Bidirectional links with multiple resolution strategies | `pkms-link` |
| **Hybrid Search** | BM25 (Whoosh) + Cosine (NumPy) with RRF fusion | SearchEngine |
| **Relevance Scoring** | Formula-based: `0.4*recency + 0.3*links + 0.2*quality + 0.1*user` | `pkms-relevance` |
| **Archive Policy** | Automated archiving based on score + age thresholds | `pkms-archive` |
| **Embeddings** | Ollama integration with LRU caching and incremental updates | `pkms-embed` |
| **Git Synthesis** | Branch-based consolidation workflow | `pkms-synth` 🚧 |

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

 Markdown Files          Records            Chunks           Search
┌──────────────┐      ┌──────────────┐   ┌──────────────┐   ┌──────────┐
│   notes/     │      │ data/records/│   │ data/chunks/ │   │  Whoosh  │
│  *.md files  │─────▶│  *.json      │──▶│  *.ndjson    │──▶│  Index   │
│              │      │              │   │              │   │          │
│  [[links]]   │      │  Metadata    │   │  Searchable  │   │  BM25    │
└──────────────┘      └──────────────┘   └──────────────┘   └──────────┘
                              │                   │               │
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
├── notes/                    # 📝 Markdown files (user-managed)
│   └── slug--ULID.md
├── data/                     # 💾 Generated data (git-tracked)
│   ├── records/              # Document metadata (JSON)
│   ├── chunks/               # Text chunks (NDJSON)
│   └── embeddings/           # Embeddings (NumPy .npy)
├── schema/                   # 📋 JSON schemas
├── pkms/                     # 🐍 Python package
│   ├── models/               # Pydantic models
│   ├── lib/                  # Shared libraries
│   │   ├── chunking/         # Hierarchical + semantic chunking
│   │   ├── search/           # Hybrid search engine
│   │   ├── utils/            # Hashing, language, tokens
│   │   └── records_io.py     # Central record I/O
│   └── tools/                # CLI tools
├── tests/                    # 🧪 Unit tests
├── test_data/                # Test fixtures
└── pyproject.toml            # Package config
```

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

# Install with dev dependencies
pip install -e ".[dev]"

# Verify installation
pkms-ingest --help
```

**Optional Performance Boost:**
```bash
pip install -e ".[performance]"  # Includes xxhash, tiktoken
```

---

## 🚀 Quick Start

### 1. Create Your First Note

```bash
mkdir -p notes
cat > notes/pizza-recipe.md <<'EOF'
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

### 2. Run the Pipeline

```bash
# Ingest markdown → Records
pkms-ingest notes/

# Chunk documents
pkms-chunk data/records/

# Extract & resolve wikilinks
pkms-link --validate

# Generate embeddings (requires Ollama)
pkms-embed

# Update relevance scores
pkms-relevance
```

### 3. Search

```python
from pkms.lib.search.search_engine_planv3 import SearchEngine
from pkms.lib.embeddings import get_embedding

engine = SearchEngine(
    chunks_dir="data/chunks",
    emb_dir="data/embeddings/nomic-embed-text",
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
# 1. Write notes with [[wikilinks]]
vim notes/new-idea.md

# 2. Process pipeline
pkms-ingest notes/
pkms-chunk data/records/
pkms-link
pkms-embed

# 3. Commit to git
git add notes/ data/
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

Parse markdown files and create Record JSONs.

```bash
pkms-ingest notes/              # Ingest all .md files
pkms-ingest notes/specific.md   # Single file
```

**What it does:**
- Parses frontmatter (YAML)
- Generates/validates ULIDs
- Auto-detects language if missing
- Normalizes filename to `slug--ULID.md`
- Computes SHA256 hashes
- Writes Record JSON to `data/records/{ULID}.json`

---

### pkms-chunk

Split documents into semantic chunks with content-addressable IDs.

```bash
pkms-chunk data/records/         # Chunk all records
pkms-chunk --max-tokens 500      # Custom chunk size
```

**Chunking Strategy:**
1. **Hierarchical:** Split by markdown headings (H1-H6)
2. **Semantic:** Further split large sections by paragraphs
3. **Content-Hash ID:** `doc_id:xxhash64(text)[:12]`

---

### pkms-link

Extract and resolve [[wikilinks]] bidirectionally.

```bash
pkms-link                 # Process all records
pkms-link --validate      # Show broken links
```

**Resolution Order:**
1. Exact ULID match
2. Slug match
3. Alias match (case-insensitive)
4. Title match (case-insensitive)

---

### pkms-embed

Generate embeddings via Ollama (incremental).

```bash
pkms-embed                            # Embed new chunks
pkms-embed --model nomic-embed-text   # Specify model
pkms-embed --force                    # Re-embed all
```

**Requirements:**
- Ollama running: `ollama serve`
- Model pulled: `ollama pull nomic-embed-text`

---

### pkms-relevance

Compute relevance scores using formula.

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

---

### pkms-archive

Archive low-relevance old documents.

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

Git-based synthesis workflow (experimental).

```bash
pkms-synth --find-clusters   # List related notes
pkms-synth --create 0        # Create synthesis
```

**Status:** 🚧 Framework implemented, LLM integration TODO

---

## ⚙️ Configuration

### Environment Variables

```bash
export PKMS_NOTES_DIR=notes
export PKMS_RECORDS_DIR=data/records
export PKMS_EMBED_MODEL=nomic-embed-text
export OLLAMA_HOST=http://localhost:11434
```

### Relevance Scoring Weights

Edit in `pkms/tools/relevance.py`:

```python
WEIGHT_RECENCY = 0.4
WEIGHT_LINKS = 0.3
WEIGHT_QUALITY = 0.2
WEIGHT_USER = 0.1
```

---

## 📊 Data Formats

### Markdown (Input)

**Filename:** `{slug}--{ULID}.md`

```yaml
---
id: 01HAR6DP2M7G1KQ3Y3VQ8C0Q
title: Pizza Neapolitana Recipe
tags: [cooking, italian]
language: de
---

# Content with [[wikilinks]]
```

---

### Record JSON (Metadata)

**File:** `data/records/{ULID}.json`

```json
{
  "id": "01HAR6DP2M7G1KQ3Y3VQ8C0Q",
  "slug": "pizza-neapolitana-recipe",
  "title": "Pizza Neapolitana Recipe",
  "language": "de",
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
pip install -e ".[dev]"

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
black pkms/ tests/     # Format
ruff check pkms/       # Lint
mypy pkms/             # Type checking
```

---

## 🐛 Troubleshooting

### Common Issues

**"No module named 'pydantic'"**
```bash
pip install -e .
```

**"Ollama connection refused"**
```bash
ollama serve
```

**"Invalid ULID in frontmatter"**
```bash
# Remove invalid ID, ingest will regenerate
pkms-ingest notes/file.md
```

**"Whoosh index locked"**
```bash
rm data/whoosh_index/*.lock
```

### Known Issues

See [PROBLEMS.md](PROBLEMS.md) for complete list.

**Fixed in v0.3.0:**
- ✅ Artificial relevance score minimum
- ✅ Git add wildcard issue in synth.py
- ✅ Code duplication (now centralized)

**To Be Fixed:**
- 🚧 N+1 file opens in embed_index.py
- 🚧 Missing Ollama retry logic
- 🚧 Synth tool needs LLM integration

---

## 📚 Resources

### Documentation

- **[TUTORIAL.md](TUTORIAL.md)** - Python basics with PKMS examples
- **[PROBLEMS.md](PROBLEMS.md)** - Code review findings
- **[plan.md](plan.md)** - Architectural design doc

### External Links

- [Ollama](https://ollama.ai/)
- [Pydantic](https://docs.pydantic.dev/)
- [Whoosh](https://whoosh.readthedocs.io/)

---

## 📜 License

MIT License - see LICENSE file

---

## 📝 Changelog

### v0.3.0 (2025-11-15)

**Added:**
- Complete pipeline (ingest, chunk, link, embed, relevance, archive, synth)
- JSON schemas + Pydantic models
- Hybrid search engine
- Comprehensive test suite

**Fixed:**
- ✅ 4 CRITICAL bugs
- ✅ Code duplication via `pkms/lib/records_io.py`
- ✅ Timezone-awareness
- ✅ Exception handling

**Documentation:**
- ✅ README.md
- ✅ PROBLEMS.md
- ✅ TUTORIAL.md (in progress)

---

**Happy Knowledge Managing! 🚀**

For questions, open an issue on GitHub.

---

**Note:** Old Docker/Microservices README saved as [README.docker.md](README.docker.md)
