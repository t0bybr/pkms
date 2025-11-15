"""
ingest.py - Inbox → Vault + Metadata

PKMS v0.3 Ingestion Pipeline:

Workflow:
1. Reads notes from inbox/ (unnormalized)
2. Normalizes:
   - Generates ULID (if not in filename)
   - Creates slug from title
   - Renames to {slug}--{ULID}.md
   - Auto-detects language if missing
3. Moves to vault/YYYY-MM/ (based on date_created)
4. Creates metadata JSON in data/metadata/{ULID}.json

Design:
- ULID stored ONLY in filename (single source of truth)
- Frontmatter contains only human/LLM-editable metadata
- Inbox is staging area (gitignored)
- Vault is organized by date (YYYY-MM)

Usage:
    python -m pkms.tools.ingest                    # Process inbox/
    python -m pkms.tools.ingest inbox/my-note.md   # Process single file
    python -m pkms.tools.ingest --source notes/    # Process custom directory
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime, timezone
import json

# Pydantic models
from pkms.models import Record, Status

# Filesystem utilities
from pkms.lib.fs.paths import parse_slug_id, build_note_filename
from pkms.lib.fs.ids import new_id, is_valid_ulid
from pkms.lib.fs.slug import make_slug
from pkms.lib.frontmatter.core import parse_file, write_file, FrontmatterModel

# Utilities
from pkms.lib.utils import compute_sha256, detect_language

# Config
from pkms.lib.config import get_path, get_vault_config


def get_vault_subfolder(date_created: Optional[datetime] = None) -> str:
	"""
	Get vault subfolder based on date_created.

	Args:
		date_created: Date to use for organization (defaults to now)

	Returns:
		str: Subfolder name (e.g., "2025-11")

	Example:
		>>> get_vault_subfolder(datetime(2025, 11, 15))
		'2025-11'
	"""
	vault_config = get_vault_config()

	if not vault_config.get("organize_by_date", True):
		return ""

	date_format = vault_config.get("date_format", "%Y-%m")
	date = date_created or datetime.now(timezone.utc)

	return date.strftime(date_format)


def normalize_note(
	file_path: Path,
	inbox_root: Path
) -> Tuple[Path, str, FrontmatterModel, str]:
	"""
	Normalize note from inbox to vault.

	Steps:
	1. Parse frontmatter
	2. Validate/generate ULID (from filename or new)
	3. Generate slug from title
	4. Rename file to {slug}--{ULID}.md
	5. Auto-detect language if missing
	6. Determine vault subfolder (YYYY-MM)
	7. Move to vault/

	Args:
		file_path: Path to note in inbox/
		inbox_root: Root of inbox directory

	Returns:
		Tuple[Path, str, FrontmatterModel, str]:
			- new_path: Path in vault/
			- ulid: Note ULID (from filename)
			- frontmatter: Parsed frontmatter
			- body: Markdown content

	Raises:
		FileNotFoundError: If file doesn't exist
		FileExistsError: If target path already exists
	"""
	if not file_path.exists():
		raise FileNotFoundError(f"File not found: {file_path}")

	# Parse frontmatter
	try:
		frontmatter, body = parse_file(str(file_path))
	except Exception as e:
		print(f"[ingest] ERROR: Could not parse {file_path}: {e}")
		raise

	# Get ULID from filename (or generate new)
	slug_from_name, id_from_name = parse_slug_id(file_path)

	# Validate ULID in filename
	if id_from_name and not is_valid_ulid(id_from_name):
		print(f"[ingest] WARN: Invalid ULID in filename: {id_from_name}")
		id_from_name = None

	# Determine final ULID (priority: filename > new)
	if id_from_name:
		id_final = id_from_name
	else:
		id_final = new_id()
		print(f"[ingest] Generated ULID: {id_final}")

	# Determine slug (priority: title > filename > fallback)
	title = getattr(frontmatter, "title", None)
	if title:
		slug_final = make_slug(title)
	else:
		slug_final = make_slug(slug_from_name or "note")

	# Auto-detect language if missing
	if not frontmatter.language:
		frontmatter.language = detect_language(body, fallback="en")
		print(f"[ingest] Detected language: {frontmatter.language}")

	# Determine vault subfolder (based on date_created)
	date_created = None
	if frontmatter.date_created:
		if isinstance(frontmatter.date_created, str):
			date_created = datetime.fromisoformat(frontmatter.date_created.replace("Z", "+00:00"))
		else:
			date_created = frontmatter.date_created

	subfolder = get_vault_subfolder(date_created)

	# Build target path in vault/
	vault_root = get_path("vault")
	vault_subdir = vault_root / subfolder if subfolder else vault_root
	vault_subdir.mkdir(parents=True, exist_ok=True)

	new_filename = build_note_filename(slug_final, id_final, file_path.suffix)
	new_path = vault_subdir / new_filename

	# Check for conflicts
	if new_path.exists():
		raise FileExistsError(f"Target already exists: {new_path}")

	# Write frontmatter back (language may have been added)
	write_file(str(file_path), frontmatter, body)

	# Move to vault/
	file_path.rename(new_path)
	print(f"[ingest] Moved: {file_path.name} → {new_path.relative_to(vault_root.parent)}")

	return new_path, id_final, frontmatter, body


def create_record(
	file_path: Path,
	ulid: str,
	frontmatter: FrontmatterModel,
	body: str
) -> Record:
	"""
	Create metadata record from normalized note.

	Args:
		file_path: Absolute path to note in vault/
		ulid: Note ULID (from filename)
		frontmatter: Parsed frontmatter
		body: Markdown content

	Returns:
		Record: Metadata record
	"""
	# Read full file (with frontmatter) for file_hash
	with open(file_path, "r", encoding="utf-8") as f:
		full_file_content = f.read()

	# Get file stats
	stat = file_path.stat()

	# Parse dates
	created = frontmatter.date_created or datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat()
	updated = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()

	if isinstance(created, str):
		created = datetime.fromisoformat(created.replace("Z", "+00:00"))
	if isinstance(updated, str):
		updated = datetime.fromisoformat(updated.replace("Z", "+00:00"))

	# Parse date_semantic
	date_semantic = None
	if frontmatter.date_semantic:
		if isinstance(frontmatter.date_semantic, str):
			date_semantic = datetime.fromisoformat(frontmatter.date_semantic.replace("Z", "+00:00"))
		else:
			date_semantic = frontmatter.date_semantic

	# Build slug from title
	slug = make_slug(frontmatter.title) if frontmatter.title else "note"

	# Relative path from project root
	vault_root = get_path("vault")
	rel_path = file_path.relative_to(vault_root.parent)

	# Hashes
	content_hash = compute_sha256(body)
	file_hash = compute_sha256(full_file_content)

	# Initial status
	status = Status(
		relevance_score=1.0,  # New docs start with max relevance
		archived=False,
	)

	# Build Record (ULID from filename, not frontmatter)
	record = Record(
		id=ulid,
		slug=slug,
		path=str(rel_path),
		title=frontmatter.title or "Untitled",
		tags=frontmatter.tags or [],
		aliases=frontmatter.aliases or [],
		categories=frontmatter.categories or [],
		language=frontmatter.language or "en",
		created=created,
		updated=updated,
		date_semantic=date_semantic,
		full_text=body,
		links=[],  # Will be filled by link.py
		backlinks=[],  # Will be filled by link.py
		content_hash=content_hash,
		file_hash=file_hash,
		status=status,
		doc_type="note",
	)

	return record


def save_record(record: Record, metadata_dir: Path):
	"""
	Save metadata record as JSON.

	Args:
		record: Record to save
		metadata_dir: Directory for metadata JSONs
	"""
	metadata_dir.mkdir(parents=True, exist_ok=True)

	out_path = metadata_dir / f"{record.id}.json"

	# Serialize with indentation
	record_json = record.model_dump(mode="json", exclude_none=True)

	with open(out_path, "w", encoding="utf-8") as f:
		json.dump(record_json, f, indent=2, ensure_ascii=False, default=str)

	print(f"[ingest] Saved metadata: {out_path.name}")


def ingest_file(file_path: Path, source_root: Path):
	"""
	Ingest single file from inbox/ to vault/.

	Args:
		file_path: Path to markdown file in inbox/
		source_root: Root directory (inbox/)
	"""
	try:
		metadata_dir = get_path("metadata")

		# Normalize and move to vault/
		normalized_path, ulid, frontmatter, body = normalize_note(file_path, source_root)

		# Create metadata record
		record = create_record(normalized_path, ulid, frontmatter, body)

		# Save metadata
		save_record(record, metadata_dir)

		print(f"[ingest] ✓ Ingested: {ulid}")

	except Exception as e:
		print(f"[ingest] ERROR: Failed to ingest {file_path}: {e}", file=sys.stderr)
		import traceback
		traceback.print_exc()


def ingest_directory(source_dir: Path):
	"""
	Ingest all .md files from directory.

	Args:
		source_dir: Source directory (e.g., inbox/)
	"""
	md_files = list(source_dir.rglob("*.md"))

	if not md_files:
		print(f"[ingest] No markdown files found in {source_dir}")
		return

	print(f"[ingest] Found {len(md_files)} markdown files in {source_dir}")
	print()

	for file_path in md_files:
		ingest_file(file_path, source_dir)
		print()

	print(f"[ingest] ✓ Processed {len(md_files)} files")


def main():
	import argparse

	parser = argparse.ArgumentParser(
		description="Ingest notes from inbox/ to vault/ with metadata generation"
	)
	parser.add_argument(
		"path",
		nargs="?",
		help="Path to markdown file or directory (default: inbox/)"
	)
	parser.add_argument(
		"--source",
		help="Source directory override (default: inbox/)"
	)

	args = parser.parse_args()

	# Determine source
	if args.path:
		path = Path(args.path)
	elif args.source:
		path = Path(args.source)
	else:
		path = get_path("inbox")

	if not path.exists():
		print(f"[ingest] ERROR: Path does not exist: {path}", file=sys.stderr)
		sys.exit(1)

	print(f"[ingest] PKMS v0.3 Ingestion")
	print(f"  Source: {path}")
	print(f"  Vault:  {get_path('vault')}")
	print(f"  Metadata: {get_path('metadata')}")
	print()

	if path.is_file():
		source_root = path.parent
		ingest_file(path, source_root)
	else:
		ingest_directory(path)


if __name__ == "__main__":
	main()
