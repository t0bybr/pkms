# PKMS Utilities

Shared utility functions used across PKMS tools and libraries.

## Modules

### `hashing.py` - Content-Addressable Hashing

**Functions:**

- `compute_sha256(text: str) -> str`
  - Computes SHA256 hash with "sha256:" prefix
  - Used for: content_hash, file_hash in Records
  - Example: `"sha256:a3f2bc1d9e8f..."`

- `compute_chunk_hash(text: str) -> str`
  - Computes content-addressable chunk hash (first 12 hex chars)
  - Uses xxhash64 if available (faster), falls back to SHA256
  - Used for: chunk_id generation
  - Example: `"a3f2bc1d9e8f"`

**Dependencies:**
- `xxhash` (optional, recommended for performance)

**Usage:**
```python
from lib.utils import compute_sha256, compute_chunk_hash

content_hash = compute_sha256("Pizza bei 300°C")
# "sha256:abc123..."

chunk_hash = compute_chunk_hash("Pizza bei 300°C")
# "a3f2bc1d9e8f"
```

---

### `language.py` - Language Detection

**Functions:**

- `detect_language(text: str, fallback: str = "en") -> str`
  - Auto-detects language from text
  - Returns ISO 639-1 code (de, en, fr, ...)
  - Falls back to `fallback` if detection fails or text too short
  - Requires `langdetect` package (optional)

**Dependencies:**
- `langdetect` (optional, falls back gracefully)

**Usage:**
```python
from lib.utils import detect_language

lang = detect_language("Das ist ein deutscher Text")
# "de"

lang = detect_language("This is English text")
# "en"

# Short text falls back to default
lang = detect_language("Hi", fallback="en")
# "en"
```

---

### `tokens.py` - Token Counting

**Functions:**

- `count_tokens(text: str, model: str = "gpt-4") -> int`
  - Counts tokens in text
  - Uses tiktoken (cl100k_base) if available (accurate for GPT models)
  - Falls back to word count * 1.3 (rough estimate)
  - Used for: chunk size management, context window checks

- `estimate_tokens_from_chars(char_count: int) -> int`
  - Rough estimate from character count
  - Rule of thumb: ~3.5 chars per token
  - Useful for quick estimates without parsing

**Dependencies:**
- `tiktoken` (optional, recommended for accuracy)

**Usage:**
```python
from lib.utils import count_tokens, estimate_tokens_from_chars

tokens = count_tokens("Das ist ein Test mit mehreren Wörtern.")
# 12 (with tiktoken) or ~9 (fallback)

tokens = estimate_tokens_from_chars(1000)
# ~286
```

---

## Installation

**All dependencies (recommended):**
```bash
pip install xxhash tiktoken langdetect
```

**Minimal (all utilities fall back gracefully):**
```bash
# No extra dependencies needed - fallbacks work
```

**Performance comparison:**

| Utility | With Package | Fallback | Speed |
|---------|-------------|----------|-------|
| `compute_chunk_hash` | xxhash | SHA256 | ~10x faster |
| `count_tokens` | tiktoken | word*1.3 | ~5x faster |
| `detect_language` | langdetect | returns fallback | N/A |

---

## Design Principles

1. **Graceful Degradation** - All utilities work without optional dependencies
2. **DRY** - Single source of truth for common operations
3. **Performance** - Use fast libraries when available, sensible fallbacks
4. **Testability** - Pure functions, easy to test in isolation
5. **Reusability** - Used across tools, libs, and scripts

---

## Usage Across PKMS

**ingest.py:**
- `compute_sha256()` - for content_hash, file_hash
- `detect_language()` - auto-detect if frontmatter missing

**chunk.py / chunking/hybrid.py:**
- `compute_chunk_hash()` - generate content-addressable chunk IDs
- `count_tokens()` - manage chunk sizes

**embed_index.py:**
- Potentially `count_tokens()` for validation

**Future (link.py, relevance.py, synth.py):**
- All utilities available for reuse

---

## Testing

```python
# tests/test_utils.py
from lib.utils import compute_sha256, compute_chunk_hash, detect_language, count_tokens

def test_sha256():
    assert compute_sha256("test").startswith("sha256:")
    assert len(compute_sha256("test")) == 71  # "sha256:" + 64 hex chars

def test_chunk_hash():
    h1 = compute_chunk_hash("pizza")
    h2 = compute_chunk_hash("pizza")
    assert h1 == h2  # Deterministic
    assert len(h1) == 12

def test_language_detection():
    assert detect_language("Das ist Deutsch") == "de"
    assert detect_language("This is English") == "en"
    assert detect_language("Hi", fallback="fr") == "fr"

def test_token_counting():
    tokens = count_tokens("Hello world")
    assert tokens > 0
    assert isinstance(tokens, int)
```

---

## Adding New Utilities

When adding a new utility:

1. Create module in `pkms/lib/utils/`
2. Add to `__init__.py` exports
3. Document in this README
4. Add tests
5. Use graceful degradation for optional deps

Example:
```python
# pkms/lib/utils/new_util.py
"""New utility description"""

try:
    import optional_package
    AVAILABLE = True
except ImportError:
    AVAILABLE = False

def my_function(arg: str) -> str:
    """Doc string"""
    if AVAILABLE:
        return optional_package.fast_method(arg)
    else:
        return fallback_method(arg)
```
