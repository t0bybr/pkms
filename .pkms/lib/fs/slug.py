"""
pkms/lib/fs/slug.py - URL-safe Slug Generation

Converts arbitrary titles to filesystem-safe slugs for use in filenames.

Features:
- Lowercase normalization
- Unicode transliteration (ä → a, ü → u, etc.)
- Special character removal
- Hyphen-separated words
- Length limiting with smart truncation
- Fallback for empty slugs

Example transformations:
    "Pizza Neapolitana Recipe" → "pizza-neapolitana-recipe"
    "Über 100 Rezepte" → "uber-100-rezepte"
    "C++ vs. Rust" → "c-vs-rust"
    "   ---   " → "note"  # Fallback

Usage:
    from lib.fs.slug import make_slug

    # Basic usage
    slug = make_slug("My Great Idea")
    # => "my-great-idea"

    # Unicode handling
    slug = make_slug("Café München")
    # => "cafe-munchen"

    # Custom length limit
    slug = make_slug("Very Long Title That Needs Truncation", max_len=20)
    # => "very-long-title-that"

Filename pattern: {slug}--{ULID}.md
    Example: "pizza-recipe--01HAR6DP2M7G1KQ3Y3VQ8C0Q.md"
"""
from slugify import slugify as _slugify


def make_slug(title: str, max_len: int = 60) -> str:
	"""
	Convert title to URL-safe slug with length limit.

	Args:
		title: Original title (can contain Unicode, spaces, special chars)
		max_len: Maximum slug length (default: 60)

	Returns:
		str: Lowercase, hyphen-separated slug (or "note" if empty)

	Example:
		>>> make_slug("Pizza Neapolitana Recipe")
		'pizza-neapolitana-recipe'
		>>> make_slug("Über 100 Rezepte")
		'uber-100-rezepte'
		>>> make_slug("C++ vs. Rust")
		'c-vs-rust'
		>>> make_slug("Very Long Title", max_len=10)
		'very-long'
		>>> make_slug("   ---   ")
		'note'

	Notes:
		- Uses python-slugify for transliteration
		- Strips leading/trailing hyphens
		- Truncates at max_len, ensuring no trailing hyphen
		- Returns "note" as fallback if slug is empty
		- Preserves numbers and basic punctuation
	"""
	s = _slugify(title, lowercase=True)
	s = s.strip("-")
	if len(s) > max_len:
		s = s[:max_len].rstrip("-")
	return s or "note"