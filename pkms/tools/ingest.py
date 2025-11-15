"""
ingest.py - Markdown → Records

Plan v0.3 compliant:
- Parses frontmatter (python-frontmatter)
- Auto-detects language if missing (langdetect)
- Generates/validates ULIDs
- Computes hashes (SHA256)
- Writes Record JSONs to data/records/

Usage:
    python -m pkms.tools.ingest notes/
    python -m pkms.tools.ingest notes/pizza--01HAR6DP.md
"""

from __future__ import annotations

import os
import sys
import hashlib
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone
import json

# Pydantic models
from pkms.models import Record, Status

# Existing libraries
from pkms.lib.fs.paths import parse_slug_id, build_note_filename
from pkms.lib.fs.ids import new_id, is_valid_ulid
from pkms.lib.fs.slug import make_slug
from pkms.lib.frontmatter.core import parse_file, write_file, FrontmatterModel

# Language detection
try:
    from langdetect import detect, LangDetectException
except ImportError:
    print("[ingest] WARN: langdetect not installed, language auto-detection disabled")
    print("  Install with: pip install langdetect")
    detect = None
    LangDetectException = Exception


# Config
NOTES_DIR = os.getenv("PKMS_NOTES_DIR", "notes")
RECORDS_DIR = os.getenv("PKMS_RECORDS_DIR", "data/records")


def compute_sha256(text: str) -> str:
    """Compute SHA256 hash of text"""
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def detect_language(text: str, fallback: str = "en") -> str:
    """Auto-detect language from text"""
    if not detect:
        return fallback

    # Remove code blocks and short texts
    clean_text = text.strip()
    if len(clean_text) < 20:
        return fallback

    try:
        lang = detect(clean_text)
        # langdetect returns ISO 639-1 codes (de, en, fr, ...)
        return lang[:2].lower()
    except (LangDetectException, Exception):
        return fallback


def normalize_note(file_path: Path, notes_root: Path) -> tuple[Path, FrontmatterModel, str]:
    """
    Normalizes a markdown file:
    - Ensures valid ULID in frontmatter
    - Ensures filename matches pattern: slug--ULID.md
    - Auto-detects language if missing
    - Returns: (normalized_path, frontmatter, body)
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Parse frontmatter
    try:
        frontmatter, body = parse_file(str(file_path))
    except Exception as e:
        print(f"[ingest] ERROR: Could not parse {file_path}: {e}")
        raise

    # Get IDs from filename and frontmatter
    slug_from_name, id_from_name = parse_slug_id(file_path)

    id_from_frontmatter = getattr(frontmatter, "id", None)

    # Validate ULID in frontmatter
    if id_from_frontmatter and not is_valid_ulid(id_from_frontmatter):
        print(f"[ingest] WARN: Invalid ULID in frontmatter: {id_from_frontmatter}")
        id_from_frontmatter = None

    # Validate ULID in filename
    if id_from_name and not is_valid_ulid(id_from_name):
        id_from_name = None

    # Determine final ULID
    if id_from_frontmatter:
        id_final = id_from_frontmatter
    elif id_from_name:
        id_final = id_from_name
        frontmatter.id = id_final  # Write back to frontmatter
    else:
        id_final = new_id()
        frontmatter.id = id_final

    # Determine slug
    title = getattr(frontmatter, "title", None)
    if title:
        slug_final = make_slug(title)
    else:
        slug_final = make_slug(slug_from_name or "note")

    # Auto-detect language if missing
    if not frontmatter.language:
        frontmatter.language = detect_language(body, fallback="en")

    # Write back frontmatter (in case we added id or language)
    write_file(str(file_path), frontmatter, body)

    # Rename file if needed
    new_name = build_note_filename(slug_final, id_final, file_path.suffix)
    new_path = file_path.with_name(new_name)

    if new_path != file_path:
        if new_path.exists():
            raise FileExistsError(f"Target already exists: {new_path}")
        file_path.rename(new_path)
        print(f"[ingest] Renamed: {file_path.name} → {new_path.name}")

    return new_path, frontmatter, body


def create_record(file_path: Path, notes_root: Path, frontmatter: FrontmatterModel, body: str) -> Record:
    """
    Creates a Record from normalized file

    :param file_path: Absolute path to markdown file
    :param notes_root: Root directory of notes (for relative path)
    :param frontmatter: Parsed frontmatter
    :param body: Markdown content (without frontmatter)
    :returns: Record instance
    """
    # Read full file (with frontmatter) for file_hash
    with open(file_path, "r", encoding="utf-8") as f:
        full_file_content = f.read()

    # Get file stats
    stat = file_path.stat()
    created = frontmatter.date_created or datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat()
    updated = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()

    # Parse created/updated as datetime
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

    # Relative path
    rel_path = file_path.relative_to(notes_root)

    # Hashes
    content_hash = compute_sha256(body)
    file_hash = compute_sha256(full_file_content)

    # Initial status
    status = Status(
        relevance_score=1.0,  # New docs start with max relevance
        archived=False,
    )

    # Build Record
    record = Record(
        id=frontmatter.id,
        slug=slug,
        path=f"notes/{rel_path}",
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


def save_record(record: Record, records_dir: Path):
    """Saves record as JSON to records_dir/{id}.json"""
    records_dir.mkdir(parents=True, exist_ok=True)

    out_path = records_dir / f"{record.id}.json"

    # Serialize with indentation
    record_json = record.model_dump(mode="json", exclude_none=True)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(record_json, f, indent=2, ensure_ascii=False, default=str)

    print(f"[ingest] Saved: {out_path}")


def ingest_file(file_path: Path, notes_root: Path, records_dir: Path):
    """Ingests a single markdown file"""
    try:
        # Normalize (ULID, filename, language)
        normalized_path, frontmatter, body = normalize_note(file_path, notes_root)

        # Create Record
        record = create_record(normalized_path, notes_root, frontmatter, body)

        # Save
        save_record(record, records_dir)

    except Exception as e:
        print(f"[ingest] ERROR: Failed to ingest {file_path}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()


def ingest_directory(notes_dir: Path, records_dir: Path):
    """Ingests all .md files in notes_dir"""
    md_files = list(notes_dir.rglob("*.md"))

    print(f"[ingest] Found {len(md_files)} markdown files in {notes_dir}")

    for file_path in md_files:
        ingest_file(file_path, notes_dir, records_dir)

    print(f"\n[ingest] ✓ Ingested {len(md_files)} files")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Ingest markdown files to Record JSONs")
    parser.add_argument(
        "path",
        nargs="?",
        default=NOTES_DIR,
        help="Path to markdown file or directory (default: notes/)"
    )
    parser.add_argument(
        "--records-dir",
        default=RECORDS_DIR,
        help="Output directory for Record JSONs (default: data/records/)"
    )

    args = parser.parse_args()

    path = Path(args.path)
    records_dir = Path(args.records_dir)

    if not path.exists():
        print(f"[ingest] ERROR: Path does not exist: {path}", file=sys.stderr)
        sys.exit(1)

    print(f"[ingest] Plan v0.3 Ingest")
    print(f"  Input:  {path}")
    print(f"  Output: {records_dir}")
    print()

    if path.is_file():
        notes_root = path.parent
        ingest_file(path, notes_root, records_dir)
    else:
        ingest_directory(path, records_dir)


if __name__ == "__main__":
    main()
