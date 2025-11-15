"""
pkms/lib/frontmatter/core.py - Frontmatter Parsing and Writing

Handles YAML frontmatter in markdown files using a structured dataclass model.

Frontmatter Format (YAML):
    ---
    id: 01HAR6DP2M7G1KQ3Y3VQ8C0Q
    title: Pizza Neapolitana Recipe
    tags: [cooking, italian]
    language: de
    date_created: 2025-01-15T10:30:00Z
    ---

    # Markdown content here...

Supported Fields:
- id (required): ULID identifier
- title: Note title
- aliases: Alternative names for wikilink resolution
- tags: Categorization tags
- categories: Broader classification
- language: ISO language code (de, en, etc.)
- date_created: ISO 8601 timestamp
- date_updated: Last modification timestamp
- date_semantic: Semantic date (for historical notes)
- extra: Arbitrary additional fields (preserved on round-trip)

Usage:
    from pkms.lib.frontmatter.core import parse_file, write_file

    # Read file
    frontmatter, body = parse_file("notes/pizza.md")
    print(frontmatter.title)  # => "Pizza Neapolitana Recipe"
    print(frontmatter.tags)   # => ["cooking", "italian"]

    # Modify
    frontmatter.tags.append("favorite")
    frontmatter.language = "de"

    # Write back
    write_file("notes/pizza.md", frontmatter, body)

Design Notes:
- Uses dataclass for type safety and IDE autocomplete
- Preserves unknown fields in 'extra' dict (round-trip safe)
- Empty lists/None values are omitted on write (clean YAML)
- Separates structured fields from arbitrary metadata
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple
import frontmatter as frontmatter


@dataclass
class FrontmatterModel:
	"""
	Structured model for PKMS note frontmatter.

	Attributes:
		id: ULID identifier (required, 26 chars)
		title: Human-readable title
		aliases: Alternative names for [[wikilink]] resolution
		tags: Topic tags (e.g., ["python", "tutorial"])
		categories: Broader classification
		language: ISO 639-1 code (e.g., "de", "en")
		date_created: ISO 8601 timestamp (first creation)
		date_updated: ISO 8601 timestamp (last edit)
		date_semantic: Semantic date for historical notes
		extra: Additional fields not in schema (preserved)

	Example:
		>>> fm = FrontmatterModel(
		...     id="01HAR6DP2M7G1KQ3Y3VQ8C0Q",
		...     title="Pizza Recipe",
		...     tags=["cooking"],
		...     language="de"
		... )
		>>> fm.title
		'Pizza Recipe'
	"""
	id: str
	title: str | None = None
	aliases: List[str] = field(default_factory=list)
	tags: List[str] = field(default_factory=list)
	categories: List[str] = field(default_factory=list)
	language: str | None = None
	date_created: str | None = None
	date_updated: str | None = None
	date_semantic: str | None = None
	extra: Dict[str, Any] = field(default_factory=dict)

def parse_file(path: str) -> tuple[FrontmatterModel, str]:
	"""
	Parse markdown file with YAML frontmatter.

	Args:
		path: Path to markdown file (string)

	Returns:
		Tuple[FrontmatterModel, str]: (frontmatter, body)
		- frontmatter: Structured metadata model
		- body: Raw markdown content (without frontmatter)

	Raises:
		KeyError: If 'id' field is missing from frontmatter
		FileNotFoundError: If file doesn't exist
		yaml.YAMLError: If frontmatter is invalid YAML

	Example:
		>>> # File: notes/pizza.md
		>>> # ---
		>>> # id: 01HAR6DP
		>>> # title: Pizza Recipe
		>>> # tags: [cooking]
		>>> # custom_field: some value
		>>> # ---
		>>> # # Content here
		>>> fm, body = parse_file("notes/pizza.md")
		>>> fm.title
		'Pizza Recipe'
		>>> fm.tags
		['cooking']
		>>> fm.extra
		{'custom_field': 'some value'}
		>>> body
		'# Content here'

	Notes:
		- Requires 'id' field (raises KeyError if missing)
		- Unknown fields preserved in 'extra' dict
		- Empty/missing lists default to []
		- Empty/missing strings default to None
		- Uses python-frontmatter library for parsing
	"""
	post = frontmatter.load(path)
	meta = dict(post.metadata or {})

	# Check for required 'id' field with helpful error message
	if "id" not in meta:
		raise KeyError(f"Missing required 'id' field in frontmatter: {path}")

	m = FrontmatterModel(
		id=meta["id"],
		title=meta.get("title"),
		aliases=meta.get("aliases", []),
		tags=meta.get("tags", []),
		categories=meta.get("categories", []),
		language=meta.get("language"),
		date_created=meta.get("date_created"),
		date_updated=meta.get("date_updated"),
		date_semantic=meta.get("date_semantic"),
		extra={k: v for k, v in meta.items() if k not in {
			"id", "title", "aliases", "tags", "categories",
			"language", "date_created", "date_updated", "date_semantic"
		}}
	)
	return m, post.content

def write_file(path: str, frontmatter_model: FrontmatterModel, body: str) -> None:
	"""
	Write markdown file with YAML frontmatter.

	Args:
		path: Target file path (string)
		frontmatter_model: Structured metadata to write
		body: Markdown content (without frontmatter)

	Returns:
		None (writes file)

	Raises:
		OSError: If file cannot be written

	Example:
		>>> fm = FrontmatterModel(
		...     id="01HAR6DP",
		...     title="Pizza Recipe",
		...     tags=["cooking"],
		...     language="de"
		... )
		>>> body = "# Pizza\\n\\nRecipe here..."
		>>> write_file("notes/pizza.md", fm, body)

		# File contents:
		# ---
		# id: 01HAR6DP
		# title: Pizza Recipe
		# tags:
		# - cooking
		# language: de
		# ---
		#
		# # Pizza
		#
		# Recipe here...

	Behavior:
		- Merges structured fields + extra fields
		- Omits None values (clean YAML)
		- Omits empty lists (tags: [] → omitted)
		- Preserves 'id' field (required)
		- Writes in binary mode (UTF-8 encoding)

	Notes:
		- Overwrites existing file without backup
		- Always includes 'id' field (even if None - will fail)
		- Extra fields from frontmatter_model.extra are merged in
		- Empty lists converted to None before filtering
		- Uses python-frontmatter library for serialization
	"""
	meta = {
		"id": frontmatter_model.id,
		"title": frontmatter_model.title,
		"aliases": frontmatter_model.aliases or None,  # [] → None
		"tags": frontmatter_model.tags or None,
		"categories": frontmatter_model.categories or None,
		"language": frontmatter_model.language or None,
		"date_created": frontmatter_model.date_created,
		"date_updated": frontmatter_model.date_updated,
		"date_semantic": frontmatter_model.date_semantic,
		**frontmatter_model.extra  # Merge additional fields
	}
	# Filter out None values for clean YAML
	meta = {k: v for k, v in meta.items() if v is not None}
	post = frontmatter.Post(body, **meta)
	with open(path, "wb") as f:
		frontmatter.dump(post, f)
