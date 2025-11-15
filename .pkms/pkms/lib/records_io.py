"""
records_io.py - Zentrale I/O-Funktionen für Records

Shared utilities for loading and saving Record JSON files.
Used by: relevance.py, archive.py, synth.py, link.py
"""

from __future__ import annotations

import sys
import json
from pathlib import Path
from typing import Dict, Set

from pkms.models import Record


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
    records = {}
    invalid_count = 0

    for record_file in records_dir.glob("*.json"):
        try:
            with open(record_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                record = Record(**data)
                records[record.id] = record
        except json.JSONDecodeError as e:
            print(f"[records_io] WARN: Invalid JSON in {record_file}: {e}", file=sys.stderr)
            invalid_count += 1
            continue
        except Exception as e:
            print(f"[records_io] WARN: Could not load {record_file}: {e}", file=sys.stderr)
            invalid_count += 1
            continue

    if invalid_count > 0:
        print(f"[records_io] Loaded {len(records)} records, skipped {invalid_count} invalid files", file=sys.stderr)

    return records


def save_record(record: Record, records_dir: Path) -> Path:
    """
    Speichert einen einzelnen Record als JSON.

    Args:
        record: Record to save
        records_dir: Directory to save to

    Returns:
        Path to saved file

    Raises:
        IOError: If file cannot be written
    """
    records_dir.mkdir(parents=True, exist_ok=True)
    out_path = records_dir / f"{record.id}.json"

    record_json = record.model_dump(mode="json", exclude_none=True)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(record_json, f, indent=2, ensure_ascii=False, default=str)

    return out_path


def save_records(records: Dict[str, Record], records_dir: Path, only_ids: Set[str] | None = None):
    """
    Speichert mehrere Records zurück.

    Args:
        records: Dict[ulid -> Record]
        records_dir: Directory to save to
        only_ids: Optional set of record IDs to save (for efficiency).
                  If None, saves all records.

    Note:
        - Creates records_dir if it doesn't exist
        - Overwrites existing files
    """
    records_dir.mkdir(parents=True, exist_ok=True)

    if only_ids is None:
        # Save all records
        for ulid, record in records.items():
            save_record(record, records_dir)
    else:
        # Save only specified records
        for ulid in only_ids:
            if ulid in records:
                save_record(records[ulid], records_dir)


def load_record(record_id: str, records_dir: Path) -> Record | None:
    """
    Lädt einen einzelnen Record anhand seiner ID.

    Args:
        record_id: ULID of record
        records_dir: Directory containing records

    Returns:
        Record or None if not found or invalid

    Note:
        - Returns None instead of raising exceptions for not-found files
        - Logs warnings for invalid files
    """
    record_file = records_dir / f"{record_id}.json"

    if not record_file.exists():
        return None

    try:
        with open(record_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            record = Record(**data)
            return record
    except Exception as e:
        print(f"[records_io] WARN: Could not load {record_file}: {e}", file=sys.stderr)
        return None
