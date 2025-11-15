"""
pkms/lib/fs/paths.py - Filename Parsing and Note Normalization

Handles the PKMS filename convention: {slug}--{ULID}.{ext}

Functions:
- parse_slug_id(): Extract components from filename
- build_note_filename(): Construct filename from components
- normalize_existing_note(): Ensure file follows conventions
- new_note_path(): Generate path for new note

Filename Pattern:
    {slug}--{ULID}.md

    Examples:
        pizza-recipe--01HAR6DP2M7G1KQ3Y3VQ8C0Q.md
        daily-note--01JB2X5K9Q7W8M3N6P1R4T0V.md
        über-rust--01HAR6DP2M7G1KQ3Y3VQ8C0Q.md  # Before normalization
        uber-rust--01HAR6DP2M7G1KQ3Y3VQ8C0Q.md  # After normalization

Normalization Rules:
1. ULID must exist (generated if missing)
2. ULID in filename must match frontmatter
3. Slug derived from title (or filename if no title)
4. Invalid ULIDs are regenerated
5. File renamed if needed

Usage:
    from lib.fs.paths import normalize_existing_note, new_note_path
    from pathlib import Path

    # Parse existing file
    slug, ulid = parse_slug_id(Path("pizza-recipe--01HAR6DP.md"))
    # => ("pizza-recipe", "01HAR6DP")

    # Normalize existing note
    path = Path("notes/my-note.md")  # Non-standard name
    new_path = normalize_existing_note(path)
    # => Path("notes/my-note--01HAR6DP2M7G1KQ3Y3VQ8C0Q.md")

    # Generate path for new note
    path = new_note_path(Path("notes"), "Pizza Recipe")
    # => Path("notes/pizza-recipe--01JB2X5K9Q7W8M3N6P1R4T0V.md")
"""
from pathlib import Path
from typing import Tuple, Optional

from .ids import new_id, is_valid_ulid
from .slug import make_slug
from ..frontmatter.core import parse_file, write_file


def parse_slug_id(path: Path) -> Tuple[Optional[str], Optional[str]]:
	"""
	Extract slug and ULID from filename.

	Expects pattern: {slug}--{ULID}.{ext}

	Args:
		path: Path object (e.g., Path("notes/pizza--01HAR6DP.md"))

	Returns:
		Tuple[Optional[str], Optional[str]]: (slug, ulid)
		- Both can be None if pattern doesn't match
		- If no "--", entire stem is returned as slug

	Example:
		>>> parse_slug_id(Path("pizza-recipe--01HAR6DP.md"))
		('pizza-recipe', '01HAR6DP')
		>>> parse_slug_id(Path("no-id-file.md"))
		('no-id-file', None)
		>>> parse_slug_id(Path("--01HAR6DP.md"))  # Empty slug
		(None, '01HAR6DP')

	Notes:
		- Does NOT validate ULID format (use is_valid_ulid() separately)
		- Splits on first "--" only
		- Ignores file extension
	"""
	stem = path.stem  # Filename without extension
	if "--" not in stem:
		return stem, None
	slug, id_part = stem.split("--", 1)
	return slug or None, id_part or None


def build_note_filename(slug: str, id_: str, ext: str = "md") -> str:
	"""
	Construct filename from slug and ULID.

	Args:
		slug: URL-safe slug (e.g., "pizza-recipe")
		id_: ULID (e.g., "01HAR6DP2M7G1KQ3Y3VQ8C0Q")
		ext: File extension (default: "md", leading dot optional)

	Returns:
		str: Formatted filename

	Example:
		>>> build_note_filename("pizza-recipe", "01HAR6DP2M7G1KQ3Y3VQ8C0Q")
		'pizza-recipe--01HAR6DP2M7G1KQ3Y3VQ8C0Q.md'
		>>> build_note_filename("note", "01HAR6DP", ext=".txt")
		'note--01HAR6DP.txt'
		>>> build_note_filename("note", "01HAR6DP", ext="txt")
		'note--01HAR6DP.txt'

	Notes:
		- Automatically strips leading dot from extension if present
		- Does NOT validate slug or ULID format
	"""
	return f"{slug}--{id_}.{ext.lstrip('.')}"


def normalize_existing_note(path: Path) -> Path:
	"""
	Normalize existing note to PKMS conventions.

	NOTE: ULID is stored ONLY in filename, not in frontmatter.

	Ensures:
	1. Valid ULID exists in filename (or generated)
	2. Filename matches pattern: {slug}--{ULID}.{ext}
	3. Slug derived from title (if available)

	Args:
		path: Path to existing markdown file

	Returns:
		Path: New path (may be same as input if no changes needed)

	Raises:
		FileNotFoundError: If file doesn't exist
		FileExistsError: If target rename path already exists

	Example:
		>>> # File: notes/my-note.md
		>>> # Frontmatter: title: "Pizza Recipe"
		>>> path = normalize_existing_note(Path("notes/my-note.md"))
		>>> print(path)
		notes/pizza-recipe--01HAR6DP2M7G1KQ3Y3VQ8C0Q.md

	Behavior:
		- Reads frontmatter and body
		- Validates/generates ULID (priority: filename > new)
		- Validates/generates slug (priority: title > filename > "note")
		- Writes frontmatter back (unchanged)
		- Renames file if needed

	Notes:
		- Modifies file in-place (writes frontmatter)
		- Atomic rename (fails if target exists)
		- Invalid ULID in filename is ignored, new one generated
		- ULID is NEVER in frontmatter (single source of truth = filename)
	"""
	if not path.exists():
		raise FileNotFoundError(path)

	slug_from_name, id_from_name = parse_slug_id(path)
	frontmatter, body = parse_file(str(path))

	# Validate filename ULID (permissive - just ignore if invalid)
	if id_from_name and not is_valid_ulid(id_from_name):
		id_from_name = None

	# Determine final ULID (priority: filename > new)
	if id_from_name:
		id_final = id_from_name
	else:
		id_final = new_id()

	# Determine final slug (priority: title > filename > fallback)
	title = getattr(frontmatter, "title", None)
	if title:
		slug_final = make_slug(title)
	else:
		slug_final = make_slug(slug_from_name or "note")

	# Write frontmatter back (unchanged, no ULID in frontmatter)
	write_file(str(path), frontmatter, body)

	# Build new filename
	new_name = build_note_filename(slug_final, id_final, path.suffix)
	new_path = path.with_name(new_name)

	# Rename if needed
	if new_path != path:
		if new_path.exists():
			raise FileExistsError(f"Target already exists: {new_path}")
		path.rename(new_path)

	return new_path


def new_note_path(
	root: Path,
	title: str,
	ext: str = "md",
) -> Path:
	"""
	Generate path for new note (without creating file).

	Creates:
	- New ULID
	- Slug from title
	- Full path: {root}/{slug}--{ULID}.{ext}

	Args:
		root: Directory for note (e.g., Path("notes"))
		title: Note title (e.g., "Pizza Recipe")
		ext: File extension (default: "md")

	Returns:
		Path: Full path for new note (file NOT created)

	Example:
		>>> path = new_note_path(Path("notes"), "Pizza Recipe")
		>>> print(path)
		notes/pizza-recipe--01HAR6DP2M7G1KQ3Y3VQ8C0Q.md
		>>> path.exists()
		False  # File not created yet

		>>> # With custom extension
		>>> path = new_note_path(Path("docs"), "My Document", ext="txt")
		>>> print(path)
		docs/my-document--01JB2X5K9Q7W8M3N6P1R4T0V.txt

	Usage:
		# Typical workflow
		path = new_note_path(Path("notes"), "My Idea")
		path.write_text("---\\nid: " + path.stem.split("--")[1] + "\\n---\\n\\n# Content")

	Notes:
		- Generates new ULID on each call
		- Does NOT check if file already exists
		- Does NOT create the file (caller must write)
		- Thread-safe (ULID generation is monotonic)
	"""
	id_ = new_id()
	slug = make_slug(title)
	filename = build_note_filename(slug, id_, ext)
	return root / filename