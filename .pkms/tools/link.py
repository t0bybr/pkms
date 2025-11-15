"""
link.py - Wikilink-Extraktion & bidirektionales Tracking

Plan v0.3 compliant:
- Extrahiert [[wikilinks]] aus Markdown
- Resolved Links (slug/id/alias → ULID)
- Bidirektional: Schreibt links + backlinks in Records
- Validierung (warnt bei broken links)

Usage:
    python -m pkms.tools.link
    python -m pkms.tools.link --validate
"""

from __future__ import annotations

import os
import sys
import re
import json
from pathlib import Path
from typing import List, Dict, Optional
from collections import defaultdict

from models import Record, Link
from lib.records_io import load_all_records, save_records


# Config
RECORDS_DIR = os.getenv("PKMS_RECORDS_DIR", "data/metadata")

# Wikilink patterns
WIKILINK_PATTERN = re.compile(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]')


def extract_wikilinks(text: str) -> List[Dict]:
    """
    Extrahiert Wikilinks aus Markdown-Text.

    Patterns:
    - [[target]] - Simple link
    - [[target|display]] - Link with display text

    Returns: List of dicts with keys: raw, target, display, context
    """
    links = []
    for match in WIKILINK_PATTERN.finditer(text):
        target = match.group(1).strip()
        display = match.group(2).strip() if match.group(2) else target

        # Get context (±50 chars around link)
        start = max(0, match.start() - 50)
        end = min(len(text), match.end() + 50)
        context = text[start:end].replace('\n', ' ')

        links.append({
            "raw": match.group(0),
            "target": target,
            "display": display,
            "context": context,
        })

    return links


def build_lookup_maps(records: Dict[str, Record]) -> Dict[str, Dict[str, str]]:
    """
    Baut Lookup-Maps für Link-Resolution.

    Returns:
      {
        "id": {ulid -> ulid},
        "slug": {slug -> ulid},
        "alias": {alias -> ulid},
        "title": {title -> ulid}
      }
    """
    lookup = {
        "id": {},
        "slug": {},
        "alias": {},
        "title": {},
    }

    for ulid, record in records.items():
        # ID lookup (trivial)
        lookup["id"][ulid] = ulid

        # Slug lookup
        lookup["slug"][record.slug] = ulid

        # Alias lookup
        for alias in record.aliases:
            lookup["alias"][alias.lower()] = ulid

        # Title lookup (case-insensitive)
        lookup["title"][record.title.lower()] = ulid

    return lookup


def resolve_link(target: str, lookup: Dict[str, Dict[str, str]]) -> tuple[Optional[str], str]:
    """
    Resolved einen Wikilink-Target zu einem ULID.

    Resolution-Reihenfolge:
    1. Exact ULID match
    2. Slug match
    3. Alias match
    4. Title match (case-insensitive)

    Returns: (resolved_ulid, link_type)
      link_type: "id" | "slug" | "alias" | "title" | None
    """
    target_clean = target.strip()

    # 1. Try ID
    if target_clean in lookup["id"]:
        return lookup["id"][target_clean], "id"

    # 2. Try slug
    if target_clean in lookup["slug"]:
        return lookup["slug"][target_clean], "slug"

    # 3. Try alias (case-insensitive)
    target_lower = target_clean.lower()
    if target_lower in lookup["alias"]:
        return lookup["alias"][target_lower], "alias"

    # 4. Try title (case-insensitive)
    if target_lower in lookup["title"]:
        return lookup["title"][target_lower], "title"

    # Not resolved
    return None, "unresolved"


def process_links(records: Dict[str, Record], validate: bool = False) -> tuple[int, int]:
    """
    Verarbeitet alle Links in allen Records.

    1. Extrahiert Wikilinks aus full_text
    2. Resolved Links → ULIDs
    3. Schreibt forward links in Source-Record
    4. Schreibt backlinks in Target-Record
    5. Validiert (optional)

    Returns: (total_links, broken_links)
    """
    lookup = build_lookup_maps(records)

    # Clear existing links/backlinks
    for record in records.values():
        record.links = []
        record.backlinks = []

    # Collect forward links
    total_links = 0
    broken_links = 0

    for source_id, record in records.items():
        wikilinks = extract_wikilinks(record.full_text)

        for wl in wikilinks:
            target_id, link_type = resolve_link(wl["target"], lookup)

            resolved = target_id is not None
            if not resolved:
                broken_links += 1
                if validate:
                    print(f"[link] WARN: Broken link in {source_id}: {wl['raw']}")

            link = Link(
                raw=wl["raw"],
                type=link_type if link_type != "unresolved" else "slug",  # Default to slug
                target=target_id,
                resolved=resolved,
                context=wl["context"][:200],  # Limit to 200 chars
            )

            record.links.append(link)
            total_links += 1

    # Build backlinks
    for source_id, record in records.items():
        for link in record.links:
            if link.resolved and link.target:
                target_record = records.get(link.target)
                if target_record:
                    backlink = Link(
                        raw=link.raw,
                        type=link.type,
                        target=source_id,  # Backlink points back to source
                        resolved=True,
                        context=link.context,
                    )
                    target_record.backlinks.append(backlink)

    return total_links, broken_links


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Extract and resolve wikilinks")
    parser.add_argument(
        "--records-dir",
        default=RECORDS_DIR,
        help="Directory with Record JSONs (default: data/metadata/)"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate links and warn about broken ones"
    )

    args = parser.parse_args()

    records_dir = Path(args.records_dir)

    if not records_dir.exists():
        print(f"[link] ERROR: Records directory does not exist: {records_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"[link] Plan v0.3 Link Processing")
    print(f"  Records: {records_dir}")
    print(f"  Validate: {args.validate}")
    print()

    # Load records
    print("[1/3] Loading records...")
    records = load_all_records(records_dir)
    print(f"  → {len(records)} records loaded")

    # Process links
    print()
    print("[2/3] Processing links...")
    total_links, broken_links = process_links(records, validate=args.validate)
    print(f"  → {total_links} links found")
    if broken_links > 0:
        print(f"  → {broken_links} broken links ⚠️")

    # Save updated records
    print()
    print("[3/3] Saving records...")
    save_records(records, records_dir)
    print(f"  → {len(records)} records updated")

    # Summary
    print()
    print("[link] ✓ Done!")
    print(f"  Forward links: {total_links}")
    print(f"  Broken links: {broken_links}")

    if broken_links > 0:
        print()
        print("  Run with --validate to see broken links")

    sys.exit(0 if broken_links == 0 else 1)


if __name__ == "__main__":
    main()
