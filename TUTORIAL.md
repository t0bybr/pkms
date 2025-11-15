# PKMS Python Tutorial

**Learn Python by Understanding PKMS Code**

This tutorial teaches Python fundamentals using real examples from the PKMS codebase. You'll learn both Python syntax AND how PKMS works internally.

---

## Table of Contents

1. [Python Basics](#1-python-basics)
2. [Functions & Modules](#2-functions--modules)
3. [Data Structures](#3-data-structures)
4. [Object-Oriented Programming](#4-object-oriented-programming)
5. [Type Hints & Validation](#5-type-hints--validation)
6. [File I/O & JSON](#6-file-io--json)
7. [PKMS Tools Deep Dive](#7-pkms-tools-deep-dive)
8. [Advanced Patterns](#8-advanced-patterns)
9. [Best Practices](#9-best-practices)

---

## 1. Python Basics

### 1.1 Variables & Types

**From `pkms/tools/relevance.py`:**

```python
# Line 31-35: Constants (UPPERCASE naming convention)
WEIGHT_RECENCY = 0.4  # float (decimal number)
WEIGHT_LINKS = 0.3
WEIGHT_QUALITY = 0.2
WEIGHT_USER = 0.1

# Line 38: Integer
MIN_SCORE_THRESHOLD = 0.15

# Line 50: Variable assignment inside function
HALF_LIFE_DAYS = 180.0  # Local constant
```

**What you learned:**
- `float`: Decimal numbers (e.g., `0.4`, `180.0`)
- `int`: Whole numbers (e.g., `180`)
- **Naming convention**: UPPERCASE for constants
- **Local vs Global**: Variables inside functions are local

---

### 1.2 Strings & F-Strings

**From `pkms/tools/relevance.py`:**

```python
# Line 197: F-string (formatted string)
print(f"[relevance] {ulid[:8]}... {old_score:.3f} → {new_score:.3f}")
#       ^           ^           ^              ^
#       |           |           |              |
#       f-string    variable    slice          format spec
```

**Breakdown:**
- `f"..."` - F-string prefix allows `{variable}` interpolation
- `ulid[:8]` - String slicing: first 8 characters
- `{old_score:.3f}` - Format to 3 decimal places
- `→` - Unicode character (arrows, emojis work in Python strings!)

**Try it:**
```python
name = "Pizza"
temp = 300.5

# Basic f-string
print(f"Cooking {name}")  # → Cooking Pizza

# With formatting
print(f"Temperature: {temp:.1f}°C")  # → Temperature: 300.5°C

# Expressions inside f-strings
print(f"Double temp: {temp * 2:.0f}")  # → Double temp: 601
```

---

### 1.3 Comments & Docstrings

**From `pkms/tools/relevance.py`:**

```python
# Line 1-12: Module-level docstring (triple quotes)
"""
relevance.py - Formel-basiertes Relevance-Scoring

Plan v0.3:
- Deterministisch: gleiche Inputs → gleicher Score
- Formel: 0.4*recency + 0.3*links + 0.2*quality + 0.1*user
"""

# Line 41-48: Function docstring
def compute_recency_score(record: Record, now: datetime) -> float:
    """
    Recency score based on last update time.

    Uses exponential decay: e^(-age_days / half_life)
    Half-life: 180 days (after 6 months, score is 0.5)

    Returns: 0.0 - 1.0
    """
```

**Comment Types:**
1. `#` - Inline comment (one line)
2. `"""..."""` - Docstring (documentation, multi-line)

**Best Practice:**
- Use `#` for explanations
- Use `"""..."""` for function/class documentation
- Good docstrings explain **what**, **why**, and **returns**

---

## 2. Functions & Modules

### 2.1 Function Basics

**From `pkms/lib/utils/hashing.py`:**

```python
# Line 13-19: Simple function
def compute_sha256(text: str) -> str:
    """
    Compute SHA256 hash of text.

    Returns: "sha256:{hex_digest}"
    """
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
```

**Anatomy:**
```python
def function_name(parameter: type) -> return_type:
    """Docstring"""
    # Function body
    return value
```

**Key Concepts:**
- `def` keyword starts function definition
- `:` ends the signature, indentation defines the body
- `return` sends value back to caller
- Type hints: `text: str` means "text should be a string"
- `-> str` means "this function returns a string"

---

### 2.2 Default Parameters

**From `pkms/lib/utils/language.py`:**

```python
# Line 13-23: Function with default parameter
def detect_language(text: str, fallback: str = "en") -> str:
    """
    Auto-detect language from text.

    :param text: Text to analyze
    :param fallback: Fallback language code (default: "en")
    :returns: ISO 639-1 language code (2 chars, lowercase)
    """
```

**Usage:**
```python
# Without fallback (uses default "en")
lang = detect_language("Hallo Welt")  # → "de"

# With custom fallback
lang = detect_language("短い", fallback="ja")  # → "ja"
```

**Key Point:** Parameters with `=` have default values, making them optional.

---

### 2.3 Multiple Return Values

**From `pkms/tools/archive.py`:**

```python
# Line 52-58: Function returning tuple
def find_archiveable_records(
    records: Dict[str, Record],
    now: datetime,
    min_score: float,
    min_age_days: int,
    backlink_warning_threshold: int,
) -> tuple[List[str], List[str]]:  # Returns 2 lists!
```

**Usage:**
```python
# Line 184-189: Unpacking return values
archiveable_ids, warned_ids = find_archiveable_records(
    records, now, args.min_score, args.min_age_days, args.backlink_warning
)
#      ^              ^
#      |              |
#    first return   second return
```

**Try it:**
```python
def get_name_age():
    return "Alice", 30  # Returns tuple

name, age = get_name_age()
print(f"{name} is {age}")  # → Alice is 30
```

---

### 2.4 Imports & Modules

**From `pkms/tools/relevance.py`:**

```python
# Line 17-26: Import statements
from __future__ import annotations  # Enable newer type hints

import os        # Standard library (built-in)
import sys
import json
import math
from pathlib import Path            # From specific module
from datetime import datetime, timezone  # Import multiple items

from pkms.models import Record      # Our custom module
from pkms.lib.records_io import load_all_records, save_records
```

**Import Types:**
```python
import module                 # Use as module.function()
from module import function   # Use as function() directly
from module import *          # Import everything (avoid!)
import module as alias        # Rename (e.g., import numpy as np)
```

---

## 3. Data Structures

### 3.1 Lists

**From `pkms/lib/chunking/hybrid.py`:**

```python
# Line 153-184: Building a list
chunks = []  # Empty list

for para in paragraphs:
    para = para.strip()
    if not para:
        continue  # Skip empty

    # Append to list
    chunks.append({
        "text": chunk_text,
        "section": section["section"],
        "subsection": section["subsection"],
    })

# List operations
filtered_chunks = []
for chunk in all_chunks:
    tokens = count_tokens(chunk["text"])
    if tokens >= self.min_chunk_tokens:  # Filter condition
        chunk["tokens"] = tokens
        filtered_chunks.append(chunk)

return filtered_chunks  # Return list
```

**List Basics:**
```python
# Create
my_list = []
my_list = [1, 2, 3]
my_list = ["a", "b", "c"]

# Append
my_list.append("d")  # → ["a", "b", "c", "d"]

# Access by index (0-based!)
first = my_list[0]   # → "a"
last = my_list[-1]   # → "d" (negative = from end)

# Slice
first_two = my_list[:2]   # → ["a", "b"]
last_two = my_list[-2:]   # → ["c", "d"]

# Length
count = len(my_list)  # → 4

# Loop
for item in my_list:
    print(item)
```

---

### 3.2 Dictionaries (Dicts)

**From `pkms/tools/link.py`:**

```python
# Line 55-60: Creating dict
links.append({
    "raw": match.group(0),
    "target": target,
    "display": display,
    "context": context,
})

# Line 96-101: Dict with nested dicts
lookup = {
    "id": {},
    "slug": {},
    "alias": {},
    "title": {},
}

# Line 108: Setting value
lookup["slug"][record.slug] = ulid
```

**Dict Basics:**
```python
# Create
person = {}  # Empty
person = {
    "name": "Alice",
    "age": 30,
    "tags": ["python", "dev"]
}

# Access
name = person["name"]  # → "Alice"
name = person.get("name", "Unknown")  # Safe access with default

# Set
person["age"] = 31

# Check if key exists
if "name" in person:
    print(person["name"])

# Loop over keys
for key in person:
    print(key, person[key])

# Loop over key-value pairs
for key, value in person.items():
    print(f"{key}: {value}")
```

---

### 3.3 List Comprehensions

**From `pkms/tools/relevance.py`:**

```python
# Line 266: List comprehension
scores = [r.status.relevance_score for r in records.values() if r.status]
#         ^                        ^                          ^
#         |                        |                          |
#       expression               for-loop                  condition
```

**Expanded version (equivalent):**
```python
scores = []
for r in records.values():
    if r.status:  # Condition (filter)
        scores.append(r.status.relevance_score)  # Expression
```

**More Examples:**
```python
# Square numbers
squares = [x**2 for x in range(5)]
# → [0, 1, 4, 9, 16]

# Filter even numbers
evens = [x for x in range(10) if x % 2 == 0]
# → [0, 2, 4, 6, 8]

# Extract from dict
names = [person["name"] for person in people]
```

**Why use it?** More concise and often faster than for-loops.

---

### 3.4 Dict Comprehensions

**From `pkms/tools/synth.py`:**

```python
# Line 99-109: Building dict via loop
tag_groups = {}
for ulid, record in records.items():
    for tag in (record.tags or []):
        if tag not in tag_groups:
            tag_groups[tag] = []
        tag_groups[tag].append(ulid)
```

**As dict comprehension:**
```python
# Simplified example
tag_counts = {tag: len(ulids) for tag, ulids in tag_groups.items()}
# → {"cooking": 5, "italian": 3, ...}
```

---

## 4. Object-Oriented Programming

### 4.1 Classes Basics

**From `pkms/lib/chunking/hybrid.py`:**

```python
# Line 31-52: Class definition
class HierarchicalChunker:
    """
    Splits markdown text by headings (hierarchical).
    """

    def __init__(
        self,
        max_tokens: int = 500,
        overlap_tokens: int = 50,
        min_chunk_tokens: int = 20,
    ):
        """
        Constructor (runs when creating instance)

        :param max_tokens: Maximum tokens per chunk
        """
        self.max_tokens = max_tokens      # Instance variable
        self.overlap_tokens = overlap_tokens
        self.min_chunk_tokens = min_chunk_tokens
```

**Key Concepts:**
- `class` keyword defines a class (blueprint for objects)
- `__init__` is the constructor (special method)
- `self` refers to the instance (like "this" in other languages)
- `self.max_tokens` creates an instance variable

**Usage:**
```python
# Create instance (calls __init__)
chunker = HierarchicalChunker(max_tokens=300)

# Access instance variable
print(chunker.max_tokens)  # → 300

# Call instance method
chunks = chunker.chunk(text)
```

---

### 4.2 Methods

**From `pkms/lib/chunking/hybrid.py`:**

```python
# Line 53-77: Instance method
def split_by_headings(self, text: str) -> List[Dict]:
    """
    Split markdown by headings (# Heading 1, ## Heading 2, etc.)

    Returns list of dicts with keys: text, section, subsection
    """
    # Access instance variable
    # (Note: we don't in this method, but we could)

    # Regex to find markdown headings
    heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

    # Method logic...
    return sections
```

**Method vs Function:**
- Method belongs to a class, takes `self` as first parameter
- Function is standalone
- Methods can access instance variables via `self`

---

## 5. Type Hints & Validation

### 5.1 Type Hints Basics

**From `pkms/lib/utils/hashing.py`:**

```python
# Line 13: Type hints in function signature
def compute_sha256(text: str) -> str:
    #               ^^^^  ^^^    ^^^
    #               param type    return type
```

**Common Types:**
```python
from typing import List, Dict, Optional, Union

def process_items(
    items: List[str],           # List of strings
    config: Dict[str, int],     # Dict with string keys, int values
    name: Optional[str] = None, # String or None
    value: Union[int, float] = 0  # Int OR float
) -> bool:                      # Returns boolean
    return True
```

**Why Type Hints?**
- Better IDE autocomplete
- Catch bugs early (with `mypy`)
- Self-documenting code

---

### 5.2 Pydantic Models

**From `pkms/models/record.py`:**

```python
# Line 54-76: Pydantic model (advanced class)
class Record(BaseModel):
    """Document metadata record"""

    id: str = Field(
        ...,  # Required (no default)
        pattern=r"^[0-9A-HJKMNP-TV-Z]{26}$",  # ULID pattern
        description="ULID of document"
    )

    slug: str = Field(
        ...,
        pattern=r"^[a-z0-9-]{1,60}$",
        description="URL-safe slug"
    )

    tags: List[str] = Field(
        default_factory=list,  # Default: empty list
        description="Tags (from frontmatter)"
    )
```

**What Pydantic Does:**
```python
# Validation happens automatically!
try:
    record = Record(
        id="01HAR6DP2M7G1KQ3Y3VQ8C0Q",  # Valid ULID
        slug="pizza-recipe",
        title="Pizza"
    )
    # ✅ All good!
except ValidationError as e:
    print(e)  # Shows which field failed validation
```

**Key Features:**
- Automatic type checking
- Pattern validation (regex)
- Required vs optional fields
- Default values
- Conversion (e.g., string → int)

---

### 5.3 Optional Types

**From `pkms/models/record.py`:**

```python
# Line 112-115: Optional field (can be None)
date_semantic: Optional[datetime] = Field(
    None,  # Default is None
    description="Semantic date (when event occurred)"
)

# Line 149-152: Optional nested object
agent: Optional[Agent] = Field(
    None,
    description="Agent metadata"
)
```

**Usage:**
```python
# With value
record1 = Record(..., date_semantic=datetime.now())

# Without (None)
record2 = Record(...)  # date_semantic will be None

# Checking if present
if record.date_semantic:
    print(f"Event date: {record.date_semantic}")
```

---

## 6. File I/O & JSON

### 6.1 Reading Files

**From `pkms/lib/records_io.py`:**

```python
# Line 42-49: Reading JSON file
with open(record_file, "r", encoding="utf-8") as f:
    data = json.load(f)  # Parse JSON → Python dict
    record = Record(**data)  # Create Pydantic model
```

**Breakdown:**
- `with open(...) as f:` - Context manager (auto-closes file)
- `"r"` - Read mode
- `encoding="utf-8"` - Handle UTF-8 (German umlauts, emojis, etc.)
- `json.load(f)` - Parse JSON file → dict
- `**data` - "Unpack" dict as keyword arguments

**Example:**
```python
# Traditional way (bad)
f = open("file.txt", "r")
content = f.read()
f.close()  # Easy to forget!

# Context manager (good)
with open("file.txt", "r", encoding="utf-8") as f:
    content = f.read()
# File automatically closed
```

---

### 6.2 Writing Files

**From `pkms/lib/records_io.py`:**

```python
# Line 75-79: Writing JSON file
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(record_json, f, indent=2, ensure_ascii=False, default=str)
```

**Parameters:**
- `indent=2` - Pretty-print with 2-space indentation
- `ensure_ascii=False` - Keep Unicode (German umlauts, etc.)
- `default=str` - Convert unknown types to string

**Example:**
```python
data = {
    "name": "Pizza",
    "temp": 300,
    "tags": ["italian", "cooking"]
}

# Write JSON
with open("recipe.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

# Result in recipe.json:
# {
#   "name": "Pizza",
#   "temp": 300,
#   "tags": ["italian", "cooking"]
# }
```

---

### 6.3 Path Handling

**From `pkms/tools/ingest.py`:**

```python
# Line 20: Import Path
from pathlib import Path

# Line 249: Create Path object
path = Path(args.path)

# Line 252: Check existence
if not path.exists():
    print(f"ERROR: Path does not exist: {path}")

# Line 261-265: Check if file or directory
if path.is_file():
    ingest_file(path, notes_root, records_dir)
else:
    ingest_directory(path, records_dir)
```

**Path Methods:**
```python
from pathlib import Path

p = Path("notes/pizza-recipe.md")

p.exists()       # → True/False
p.is_file()      # → True (is a file)
p.is_dir()       # → False (not a directory)
p.name           # → "pizza-recipe.md" (filename)
p.stem           # → "pizza-recipe" (without extension)
p.suffix         # → ".md" (extension)
p.parent         # → Path("notes") (directory)

# Join paths (cross-platform!)
notes_dir = Path("notes")
file_path = notes_dir / "recipe.md"  # → notes/recipe.md
```

**Why Path vs strings?** Cross-platform (`/` vs `\`), better API, type-safe.

---

## 7. PKMS Tools Deep Dive

### 7.1 How `pkms-ingest` Works

**From `pkms/tools/ingest.py`:**

```python
# Main workflow
def ingest_file(file_path: Path, notes_root: Path, records_dir: Path):
    try:
        # Step 1: Normalize (ULID, filename, language)
        normalized_path, frontmatter, body = normalize_note(file_path, notes_root)

        # Step 2: Create Record
        record = create_record(normalized_path, notes_root, frontmatter, body)

        # Step 3: Save
        save_record(record, records_dir)
    except Exception as e:
        print(f"ERROR: Failed to ingest {file_path}: {e}")
```

**Step 1: Normalize** (Lines 43-109)
```python
def normalize_note(file_path: Path, notes_root: Path):
    # Parse frontmatter (YAML + markdown body)
    frontmatter, body = parse_file(str(file_path))

    # Get IDs from filename and frontmatter
    slug_from_name, id_from_name = parse_slug_id(file_path)
    id_from_frontmatter = getattr(frontmatter, "id", None)

    # Validate ULID
    if id_from_frontmatter and not is_valid_ulid(id_from_frontmatter):
        id_from_frontmatter = None

    # Determine final ULID (frontmatter > filename > generate new)
    if id_from_frontmatter:
        id_final = id_from_frontmatter
    elif id_from_name:
        id_final = id_from_name
        frontmatter.id = id_final  # Write back
    else:
        id_final = new_id()  # Generate new ULID
        frontmatter.id = id_final

    # Auto-detect language if missing
    if not frontmatter.language:
        frontmatter.language = detect_language(body, fallback="en")

    # Rename file to slug--ULID.md format
    new_name = build_note_filename(slug_final, id_final, file_path.suffix)
    new_path = file_path.with_name(new_name)
    if new_path != file_path:
        file_path.rename(new_path)

    return new_path, frontmatter, body
```

**Key Learnings:**
- `getattr(obj, "attr", default)` - Safe attribute access
- Conditional logic for ID resolution (priority chain)
- File renaming with `Path.rename()`

---

### 7.2 How `pkms-chunk` Works

**From `pkms/lib/chunking/hybrid.py`:**

```python
# Main function (lines 236-285)
def chunk_document(doc_id: str, text: str, language: str = "en", max_tokens: int = 500):
    # Step 1: Chunk text (hierarchical + semantic)
    chunks = chunk_text(text, max_tokens=max_tokens)

    # Step 2: Add content-hash IDs
    output_chunks = []
    for idx, chunk in enumerate(chunks):
        chunk_text = chunk["text"]
        chunk_hash = compute_chunk_hash(chunk_text)  # xxhash64[:12]
        chunk_id = f"{doc_id}:{chunk_hash}"  # Composite ID

        output_chunks.append({
            "doc_id": doc_id,
            "chunk_id": chunk_id,
            "chunk_hash": chunk_hash,
            "chunk_index": idx,  # Sequential index
            "text": chunk_text,
            "tokens": chunk.get("tokens", count_tokens(chunk_text)),
            "section": chunk.get("section"),
            "subsection": chunk.get("subsection"),
            "modality": "text",
            "language": language,
        })

    return output_chunks
```

**Chunking Strategy** (lines 53-102):
```python
def split_by_headings(self, text: str):
    # Use regex to find headings
    heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

    # Find all matches
    headings = []
    for match in heading_pattern.finditer(text):
        level = len(match.group(1))  # Count # symbols
        title = match.group(2).strip()
        start = match.start()
        headings.append({"level": level, "title": title, "start": start})

    # Split text into sections between headings
    sections = []
    for i, heading in enumerate(headings):
        start_pos = heading["start"]
        end_pos = headings[i + 1]["start"] if i + 1 < len(headings) else len(text)
        section_text = text[start_pos:end_pos].strip()
        sections.append({
            "text": section_text,
            "section": heading["title"],
        })

    return sections
```

**Key Learnings:**
- `re.compile()` - Compile regex for efficiency
- `enumerate()` - Loop with index
- String slicing for text extraction

---

### 7.3 How `pkms-link` Works

**From `pkms/tools/link.py`:**

```python
# Extract wikilinks (lines 35-62)
def extract_wikilinks(text: str):
    WIKILINK_PATTERN = re.compile(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]')
    #                                  ^         ^      ^
    #                                  |         |      |
    #                                target    pipe   display

    links = []
    for match in WIKILINK_PATTERN.finditer(text):
        target = match.group(1).strip()     # [[TARGET|...]]
        display = match.group(2).strip() if match.group(2) else target

        # Extract context (±50 chars)
        start = max(0, match.start() - 50)
        end = min(len(text), match.end() + 50)
        context = text[start:end].replace('\n', ' ')

        links.append({
            "raw": match.group(0),    # Full match: [[target|display]]
            "target": target,
            "display": display,
            "context": context,
        })

    return links
```

**Resolve links** (lines 120-153):
```python
def resolve_link(target: str, lookup: Dict):
    # Priority chain:

    # 1. Try ID (exact ULID)
    if target in lookup["id"]:
        return lookup["id"][target], "id"

    # 2. Try slug
    if target in lookup["slug"]:
        return lookup["slug"][target], "slug"

    # 3. Try alias (case-insensitive)
    target_lower = target.lower()
    if target_lower in lookup["alias"]:
        return lookup["alias"][target_lower], "alias"

    # 4. Try title (case-insensitive)
    if target_lower in lookup["title"]:
        return lookup["title"][target_lower], "title"

    # Not resolved
    return None, "unresolved"
```

**Key Learnings:**
- Regex groups: `match.group(1)`, `match.group(2)`
- Conditional expressions: `x if condition else y`
- Cascading if-checks (priority chain)

---

## 8. Advanced Patterns

### 8.1 Error Handling

**From `pkms/lib/records_io.py`:**

```python
# Lines 42-52: Try-except with specific exceptions
for record_file in records_dir.glob("*.json"):
    try:
        with open(record_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            record = Record(**data)
            records[record.id] = record
    except json.JSONDecodeError as e:
        print(f"WARN: Invalid JSON in {record_file}: {e}")
        invalid_count += 1
        continue  # Skip this file
    except Exception as e:
        print(f"WARN: Could not load {record_file}: {e}")
        invalid_count += 1
        continue
```

**Exception Hierarchy:**
```python
try:
    risky_operation()
except SpecificError as e:
    # Handle specific error first
    print(f"Specific error: {e}")
except Exception as e:
    # Catch all other errors
    print(f"Generic error: {e}")
finally:
    # Always runs (cleanup)
    close_connection()
```

---

### 8.2 Context Managers

**From `pkms/lib/search/search_engine_planv3.py`:**

```python
# Line 260-272: Using context manager
with self.ix.searcher() as searcher:
    parser = MultifieldParser(["text"], self.ix.schema)
    query = parser.parse(query_text)
    whoosh_results = searcher.search(query, limit=limit)
    # ... process results ...
# Searcher automatically closed here
```

**Why Context Managers?**
- Automatic resource cleanup (file handles, connections)
- `with` ensures cleanup even if exception occurs
- Cleaner code (no manual close())

---

### 8.3 Comprehensions with Conditions

**From `pkms/tools/relevance.py`:**

```python
# Line 266: Filter + extract in one line
scores = [r.status.relevance_score for r in records.values() if r.status]
#         ^                                                    ^
#         expression                                        condition
```

**Expanded:**
```python
scores = []
for r in records.values():
    if r.status:  # Only if status exists
        scores.append(r.status.relevance_score)
```

**More Examples:**
```python
# Get all archived record IDs
archived_ids = [r.id for r in records.values() if r.status.archived]

# Get tags from all records
all_tags = [tag for r in records.values() for tag in r.tags]
#                                         ^
#                                  nested for-loop!

# Filter by language and extract titles
german_titles = [r.title for r in records.values() if r.language == "de"]
```

---

### 8.4 Decorators (Advanced)

**From `pkms/lib/embeddings.py`:**

```python
# Line 39-46: LRU Cache decorator
from functools import lru_cache

@lru_cache(maxsize=1024)
def _raw_embedding_cached(text: str, model: str) -> tuple[float, ...]:
    """
    Cached embedding function (memoization).

    If same text+model called again, return cached result.
    """
    response = ollama.embed(model=model, input=text)
    return tuple(response['embeddings'][0])
```

**What `@lru_cache` Does:**
```python
# First call
emb1 = _raw_embedding_cached("pizza", "nomic-embed-text")  # Calls Ollama

# Second call with same args
emb2 = _raw_embedding_cached("pizza", "nomic-embed-text")  # Returns cached!
# → Much faster, no API call
```

**Common Decorators:**
- `@lru_cache` - Cache function results
- `@property` - Turn method into attribute
- `@staticmethod` - Method without self
- `@classmethod` - Method with class instead of instance

---

## 9. Best Practices

### 9.1 Naming Conventions

```python
# Constants (UPPERCASE)
MAX_TOKENS = 500
WEIGHT_RECENCY = 0.4

# Functions & variables (snake_case)
def compute_relevance_score(record):
    total_score = 0.0
    return total_score

# Classes (PascalCase)
class SearchEngine:
    pass

# Private (prefix with _)
def _internal_helper():
    pass
```

---

### 9.2 Docstrings

**Good Example from `pkms/lib/records_io.py`:**

```python
def load_all_records(records_dir: Path) -> Dict[str, Record]:
    """
    Lädt alle Records aus dem records_dir.

    Args:
        records_dir: Path to directory containing Record JSON files

    Returns:
        Dict[ulid -> Record]

    Note:
        - Logs warnings for invalid files but continues loading
        - Skips files that cannot be parsed or validated
    """
```

**Format:**
- One-line summary
- Blank line
- Detailed description
- Args/Returns/Raises sections

---

### 9.3 Type Hints

**From `pkms/lib/utils/language.py`:**

```python
def detect_language(text: str, fallback: str = "en") -> str:
    #               ^^^^  ^^^  ^^^^^^^^^^^^  ^^^    ^^^
    #               param type default val   type  return
```

**Benefits:**
- IDE autocomplete
- Type checking with mypy
- Self-documentation

---

### 9.4 Error Messages

**Good Example from `pkms/tools/ingest.py`:**

```python
# Line 58-59: Descriptive error
except Exception as e:
    print(f"[ingest] ERROR: Could not parse {file_path}: {e}")
    raise
```

**Best Practices:**
- Include tool name prefix (`[ingest]`)
- Include severity (`ERROR`, `WARN`, `INFO`)
- Include context (which file failed)
- Include actual error message

---

### 9.5 Defensive Programming

**From `pkms/tools/synth.py`:**

```python
# Line 100: Defensive check (tags could be None in old records)
for tag in (record.tags or []):
    #          ^^^^^^^^^^^ Handle None
```

**More Examples:**
```python
# Check before accessing
if record.status and record.status.archived:
    handle_archived(record)

# Safe dict access
value = my_dict.get("key", default_value)

# Validate inputs
if not isinstance(text, str):
    raise TypeError("text must be a string")
```

---

## 10. Next Steps

### Practice Exercises

1. **Modify Relevance Weights**
   - Edit `pkms/tools/relevance.py`
   - Change `WEIGHT_RECENCY` to `0.5`
   - Run `pkms-relevance --verbose`
   - Observe score changes

2. **Create Custom Chunker**
   - Copy `pkms/lib/chunking/hybrid.py`
   - Modify `split_by_headings()` to also split on `---` (horizontal rule)
   - Test on your notes

3. **Add Custom Field**
   - Edit `schema/record.schema.json`
   - Add `"difficulty": {"type": "string"}`
   - Update `pkms/models/record.py`
   - Add field to frontmatter in notes

### Read the Code

Recommended reading order:
1. `pkms/lib/utils/*.py` - Simple utilities
2. `pkms/models/record.py` - Pydantic models
3. `pkms/tools/ingest.py` - Complete workflow
4. `pkms/lib/chunking/hybrid.py` - Algorithms
5. `pkms/lib/search/search_engine_planv3.py` - Complex system

### Resources

- **Python Docs**: https://docs.python.org/3/
- **Pydantic**: https://docs.pydantic.dev/
- **Type Hints**: https://mypy.readthedocs.io/
- **Pathlib**: https://docs.python.org/3/library/pathlib.html

---

**You now understand PKMS code AND Python! 🎉**

For questions, check the main [README.md](README.md) or open an issue on GitHub.
