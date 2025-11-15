"""
archive.py - Policy-basierte Archivierung

Plan v0.3:
- Policy-basiert: relevance_score < threshold & age > min_age
- Setzt status.archived = true (löscht nie!)
- Warnt bei vielen Backlinks (wichtige Docs)
- Dry-run Mode für Testing

Usage:
    python -m pkms.tools.archive
    python -m pkms.tools.archive --dry-run
    python -m pkms.tools.archive --min-score 0.3 --min-age-days 365
"""

from __future__ import annotations

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List

from pkms.models import Record


# Config
RECORDS_DIR = os.getenv("PKMS_RECORDS_DIR", "data/records")

# Default policy
DEFAULT_MIN_SCORE = 0.3
DEFAULT_MIN_AGE_DAYS = 365  # 1 year
DEFAULT_BACKLINK_WARNING_THRESHOLD = 5


def load_all_records(records_dir: Path) -> Dict[str, Record]:
    """Lädt alle Records"""
    records = {}
    for record_file in records_dir.glob("*.json"):
        try:
            with open(record_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                record = Record(**data)
                records[record.id] = record
        except Exception as e:
            print(f"[archive] WARN: Could not load {record_file}: {e}", file=sys.stderr)

    return records


def find_archiveable_records(
    records: Dict[str, Record],
    now: datetime,
    min_score: float,
    min_age_days: int,
    backlink_warning_threshold: int,
) -> tuple[List[str], List[str]]:
    """
    Findet Records die archiviert werden sollen.

    Policy:
    - relevance_score < min_score
    - age > min_age_days
    - not already archived

    Returns: (archiveable_ids, warned_ids)
      archiveable_ids: Can be archived
      warned_ids: Should be archived but have many backlinks
    """
    archiveable = []
    warned = []

    min_age = timedelta(days=min_age_days)

    for ulid, record in records.items():
        # Skip already archived
        if record.status.archived:
            continue

        # Check relevance score
        if record.status.relevance_score >= min_score:
            continue

        # Check age
        age = now - record.created
        if age < min_age:
            continue

        # Check backlinks
        backlink_count = len(record.backlinks)

        if backlink_count >= backlink_warning_threshold:
            # Warn but don't archive automatically
            warned.append(ulid)
        else:
            archiveable.append(ulid)

    return archiveable, warned


def archive_records(
    records: Dict[str, Record],
    archive_ids: List[str],
    dry_run: bool = False,
) -> int:
    """
    Archiviert Records (setzt archived=true).

    Returns: Number of records archived
    """
    archived_count = 0

    for ulid in archive_ids:
        record = records.get(ulid)
        if not record:
            continue

        if dry_run:
            print(f"[archive] [DRY-RUN] Would archive: {ulid} ({record.title})")
        else:
            record.status.archived = True
            print(f"[archive] Archived: {ulid} ({record.title})")

        archived_count += 1

    return archived_count


def save_records(records: Dict[str, Record], records_dir: Path):
    """Speichert alle Records zurück"""
    for ulid, record in records.items():
        out_path = records_dir / f"{ulid}.json"

        record_json = record.model_dump(mode="json", exclude_none=True)

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(record_json, f, indent=2, ensure_ascii=False, default=str)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Archive old, low-relevance records")
    parser.add_argument(
        "--records-dir",
        default=RECORDS_DIR,
        help="Directory with Record JSONs (default: data/records/)"
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=DEFAULT_MIN_SCORE,
        help=f"Minimum relevance score (default: {DEFAULT_MIN_SCORE})"
    )
    parser.add_argument(
        "--min-age-days",
        type=int,
        default=DEFAULT_MIN_AGE_DAYS,
        help=f"Minimum age in days (default: {DEFAULT_MIN_AGE_DAYS})"
    )
    parser.add_argument(
        "--backlink-warning",
        type=int,
        default=DEFAULT_BACKLINK_WARNING_THRESHOLD,
        help=f"Warn if backlinks >= threshold (default: {DEFAULT_BACKLINK_WARNING_THRESHOLD})"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be archived without actually doing it"
    )

    args = parser.parse_args()

    records_dir = Path(args.records_dir)

    if not records_dir.exists():
        print(f"[archive] ERROR: Records directory does not exist: {records_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"[archive] Plan v0.3 Archive Tool")
    print(f"  Records: {records_dir}")
    print(f"  Policy: score < {args.min_score}, age > {args.min_age_days} days")
    print(f"  Backlink warning: >= {args.backlink_warning}")
    print(f"  Mode: {'DRY-RUN' if args.dry_run else 'LIVE'}")
    print()

    # Load records
    print("[1/4] Loading records...")
    records = load_all_records(records_dir)
    print(f"  → {len(records)} records loaded")

    # Find archiveable
    print()
    print("[2/4] Finding archiveable records...")
    now = datetime.now(timezone.utc)
    archiveable_ids, warned_ids = find_archiveable_records(
        records,
        now,
        args.min_score,
        args.min_age_days,
        args.backlink_warning,
    )

    print(f"  → {len(archiveable_ids)} records can be archived")
    print(f"  → {len(warned_ids)} records have many backlinks (warned)")

    # Show warnings
    if warned_ids:
        print()
        print("[!] Records with many backlinks:")
        for ulid in warned_ids[:10]:  # Show max 10
            record = records[ulid]
            backlinks = len(record.backlinks)
            print(f"    {ulid} - {record.title} ({backlinks} backlinks)")
        if len(warned_ids) > 10:
            print(f"    ... and {len(warned_ids) - 10} more")

    # Archive
    print()
    print("[3/4] Archiving...")
    archived_count = archive_records(records, archiveable_ids, dry_run=args.dry_run)

    # Save
    if not args.dry_run:
        print()
        print("[4/4] Saving records...")
        save_records(records, records_dir)
        print(f"  → {len(records)} records saved")

    print()
    print("[archive] ✓ Done!")
    print(f"  Archived: {archived_count}")
    print(f"  Warned: {len(warned_ids)}")

    if args.dry_run:
        print()
        print("  This was a dry-run. Run without --dry-run to actually archive.")


if __name__ == "__main__":
    main()
