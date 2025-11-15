# PKMS Test Data

Test data for PKMS pipeline testing.

## Structure

```
test_data/
├── notes_good/          # Well-formed markdown files
│   ├── pizza-recipe.md  # Complete frontmatter, valid links
│   └── ofen-temperatur.md  # Links back to pizza-recipe
└── notes_problematic/   # Edge cases and problematic files
    ├── broken-links.md      # Contains non-existent link targets
    ├── no-frontmatter.md    # Missing YAML frontmatter
    ├── very-short.md        # Very short content (tests chunking)
    └── invalid-ulid.md      # Invalid ULID in frontmatter
```

## Test Cases

### Good Cases (`notes_good/`)

**pizza-recipe.md:**
- Complete YAML frontmatter
- Multiple wikilinks (some with display text)
- Bidirectional links with ofen-temperatur.md
- German language content
- Multiple headings (tests hierarchical chunking)

**ofen-temperatur.md:**
- Valid frontmatter
- Links back to pizza-recipe
- Short content (tests minimum chunk size)

### Problematic Cases (`notes_problematic/`)

**broken-links.md:**
- Tests link validation
- Contains 3 broken wikilinks
- Should generate warnings with `--validate`

**no-frontmatter.md:**
- Tests auto-generation of frontmatter
- Should get auto-generated ULID
- Mixed language content (tests language detection)

**very-short.md:**
- Tests minimum content handling
- Should still chunk properly
- Tests relevance scoring for short docs

**invalid-ulid.md:**
- Contains invalid ULID string
- Should be regenerated as valid ULID
- Tests ULID validation logic

## Running Tests

```bash
# Ingest good notes
python -m pkms.tools.ingest test_data/notes_good/

# Ingest problematic notes (should handle gracefully)
python -m pkms.tools.ingest test_data/notes_problematic/

# Chunk all
python -m pkms.tools.chunk --records-dir data/records/

# Link processing with validation
python -m pkms.tools.link --validate

# Full pipeline test
python -m pkms.tools.ingest test_data/notes_good/
python -m pkms.tools.chunk
python -m pkms.tools.link
python -m pkms.tools.relevance
```

## Expected Outcomes

### Good Notes
- ✅ All should process without errors
- ✅ Links should resolve correctly
- ✅ Bidirectional links established
- ✅ Chunks generated with proper IDs

### Problematic Notes
- ⚠️ broken-links.md: 3 warnings about unresolved links
- ✅ no-frontmatter.md: Auto-generated ULID, language detected
- ✅ very-short.md: Processes but low relevance score
- ⚠️ invalid-ulid.md: ULID regenerated, warning logged

## Unit Tests

Run unit tests with pytest:

```bash
pytest tests/ -v
```

Run with coverage:

```bash
pytest tests/ --cov=pkms --cov-report=html
```

## Integration Testing

Full pipeline integration test:

```bash
# Clean slate
rm -rf data/

# Run full pipeline
python -m pkms.tools.ingest test_data/notes_good/
python -m pkms.tools.chunk
python -m pkms.tools.link
python -m pkms.tools.embed  # Requires Ollama running
python -m pkms.tools.relevance

# Verify outputs
ls data/records/  # Should have 2 JSON files
ls data/chunks/   # Should have 2 NDJSON files
ls data/embeddings/nomic-embed-text/  # Should have multiple .npy files

# Test search
python -c "
from pkms.lib.search.search_engine_planv3 import SearchEngine
from pkms.lib.embeddings import get_embedding

engine = SearchEngine(
    chunks_dir='data/chunks',
    emb_dir='data/embeddings/nomic-embed-text',
    index_dir='data/whoosh_index',
    embed_fn=get_embedding,
)

results = engine.search('pizza ofen temperatur', k=5)
for r in results:
    print(f\"{r['chunk_id']} - rrf={r['rrf_score']:.3f}\")
"
```
