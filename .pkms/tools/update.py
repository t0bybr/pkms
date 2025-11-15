"""
update.py - Update Metadata for Existing Vault Notes

PKMS v0.3 Metadata Update Tool:

Purpose:
- Update metadata JSONs for existing vault notes
- No file moving/renaming (unlike ingest.py)
- For use after manual edits, in pre-commit hooks, or agent workflows

Workflow:
1. Scan vault/ for markdown files
2. Extract ULID from filename
3. Parse frontmatter and body
4. Regenerate metadata JSON
5. Save to data/metadata/{ULID}.json

Usage:
    pkms-update                           # Update all vault notes
    pkms-update vault/2025-11/note.md     # Update single file
    pkms-update --vault-only              # Skip verification
"""

from __future__ import annotations

import sys
import argparse
from pathlib import Path
from typing import Optional

# Import helpers from ingest.py
from tools.ingest import create_record, save_record

# Filesystem utilities
from lib.fs.paths import parse_slug_id
from lib.frontmatter.core import parse_file

# Config
from lib.config import get_path


def update_file(file_path: Path, metadata_dir: Path, verbose: bool = True) -> bool:
    """
    Update metadata for a single vault file.

    Args:
        file_path: Path to markdown file in vault/
        metadata_dir: Directory for metadata JSONs
        verbose: Print progress messages

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Ensure file_path and metadata_dir are Path objects
        file_path = Path(file_path)
        metadata_dir = Path(metadata_dir)

        # Extract ULID from filename
        slug, ulid = parse_slug_id(file_path.stem)

        if not ulid:
            if verbose:
                print(f"[update] SKIP: No ULID in filename: {file_path.name}")
            return False

        # Parse frontmatter
        frontmatter, body, full_content = parse_file(file_path)

        # Create metadata record (reuse from ingest.py)
        record = create_record(file_path, ulid, frontmatter, body)

        # Save metadata
        save_record(record, metadata_dir)

        return True

    except Exception as e:
        if verbose:
            import traceback
            print(f"[update] ERROR: Failed to update {file_path}: {e}")
            traceback.print_exc()
        return False


def update_vault(vault_path: Optional[Path] = None, verbose: bool = True) -> tuple[int, int]:
    """
    Update metadata for all markdown files in vault.

    Args:
        vault_path: Path to vault directory (default: from config)
        verbose: Print progress messages

    Returns:
        tuple[int, int]: (success_count, total_count)
    """
    if vault_path is None:
        vault_path = get_path("vault")

    metadata_dir = get_path("metadata")

    if not vault_path.exists():
        print(f"[update] ERROR: Vault not found: {vault_path}")
        return 0, 0

    # Find all markdown files
    md_files = list(vault_path.rglob("*.md"))

    if not md_files:
        print(f"[update] No markdown files found in: {vault_path}")
        return 0, 0

    if verbose:
        print(f"\n📝 PKMS Metadata Update")
        print("=" * 60)
        print(f"Vault:    {vault_path}")
        print(f"Metadata: {metadata_dir}")
        print(f"Files:    {len(md_files)}")
        print("=" * 60)
        print()

    # Update each file
    success_count = 0
    for file_path in md_files:
        if update_file(file_path, metadata_dir, verbose=verbose):
            success_count += 1

    if verbose:
        print()
        print("=" * 60)
        print(f"📊 Summary:")
        print(f"  Updated:  {success_count}/{len(md_files)}")
        print(f"  Skipped:  {len(md_files) - success_count}")
        print("=" * 60)
        print()

        if success_count == len(md_files):
            print("✅ All metadata updated successfully!")
        elif success_count > 0:
            print(f"⚠️  {len(md_files) - success_count} files skipped")
        else:
            print("❌ No files updated")

    return success_count, len(md_files)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Update metadata for existing vault notes"
    )
    parser.add_argument(
        "path",
        nargs="?",
        help="Path to markdown file or vault directory (default: vault/)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress messages"
    )

    args = parser.parse_args()

    verbose = not args.quiet

    try:
        if args.path:
            path = Path(args.path)

            if not path.exists():
                print(f"[update] ERROR: Path not found: {path}")
                sys.exit(1)

            metadata_dir = get_path("metadata")

            if path.is_file():
                # Update single file
                if path.suffix != ".md":
                    print(f"[update] ERROR: Not a markdown file: {path}")
                    sys.exit(1)

                success = update_file(path, metadata_dir, verbose=verbose)
                sys.exit(0 if success else 1)
            else:
                # Update directory
                success_count, total_count = update_vault(path, verbose=verbose)
                sys.exit(0 if success_count == total_count else 1)
        else:
            # Update entire vault
            success_count, total_count = update_vault(verbose=verbose)
            sys.exit(0 if success_count == total_count else 1)

    except KeyboardInterrupt:
        print("\n[update] Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"[update] ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
