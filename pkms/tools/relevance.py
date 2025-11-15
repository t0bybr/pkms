"""
relevance.py - Formel-basiertes Relevance-Scoring

Plan v0.3:
- Deterministisch: gleiche Inputs → gleicher Score
- Formel: 0.4*recency + 0.3*links + 0.2*quality + 0.1*user
- Updated status.relevance_score in Records
- Periodic Job (z.B. täglich via cron)

Usage:
    python -m pkms.tools.relevance
    python -m pkms.tools.relevance --min-score 0.15
"""

from __future__ import annotations

import os
import sys
import json
import math
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict

from pkms.models import Record


# Config
RECORDS_DIR = os.getenv("PKMS_RECORDS_DIR", "data/records")

# Scoring weights (can be tuned)
WEIGHT_RECENCY = 0.4
WEIGHT_LINKS = 0.3
WEIGHT_QUALITY = 0.2
WEIGHT_USER = 0.1

# Minimum score threshold
MIN_SCORE_THRESHOLD = 0.15


def compute_recency_score(record: Record, now: datetime) -> float:
    """
    Recency score based on last update time.

    Uses exponential decay: e^(-age_days / half_life)
    Half-life: 180 days (after 6 months, score is 0.5)

    Returns: 0.0 - 1.0
    """
    HALF_LIFE_DAYS = 180.0

    age_seconds = (now - record.updated).total_seconds()
    age_days = age_seconds / 86400.0

    # Exponential decay
    score = math.exp(-age_days / HALF_LIFE_DAYS)

    return max(0.0, min(1.0, score))


def compute_link_score(record: Record) -> float:
    """
    Link score based on backlink count (PageRank-like).

    Uses log-scale: log(1 + backlinks) / log(1 + max_backlinks)
    Assumes max_backlinks = 100 for normalization.

    Returns: 0.0 - 1.0
    """
    MAX_BACKLINKS = 100.0

    backlink_count = len(record.backlinks)

    if backlink_count == 0:
        return 0.0

    # Log-scale
    score = math.log(1 + backlink_count) / math.log(1 + MAX_BACKLINKS)

    return max(0.0, min(1.0, score))


def compute_quality_score(record: Record) -> float:
    """
    Quality score based on content properties.

    Factors:
    - Word count (longer = better, up to ~2000 words)
    - Has media (TODO: check for images/code blocks)
    - Has links (outgoing links indicate thoroughness)

    Returns: 0.0 - 1.0
    """
    word_count = len(record.full_text.split())
    link_count = len(record.links)

    # Word count score (sigmoid, peak at 2000 words)
    OPTIMAL_WORDS = 2000.0
    word_score = min(1.0, word_count / OPTIMAL_WORDS)

    # Link score (has outgoing links = more thorough)
    link_score = 1.0 if link_count > 0 else 0.0

    # TODO: Media score (check for images, code blocks)
    media_score = 0.5  # Placeholder

    # Weighted average
    quality = (
        0.5 * word_score +
        0.3 * link_score +
        0.2 * media_score
    )

    return max(0.0, min(1.0, quality))


def compute_user_score(record: Record) -> float:
    """
    User score based on manual actions.

    Factors:
    - Human edited (manually refined content)
    - Agent reviewed (human verified agent output)
    - TODO: Starred/bookmarked (future feature)

    Returns: 0.0 - 1.0
    """
    score = 0.0

    # Human edited
    if record.status.human_edited:
        score += 0.5

    # Agent reviewed
    if record.agent and record.agent.reviewed:
        score += 0.3

    # TODO: Starred/bookmarked
    # if record.starred:
    #     score += 0.2

    return max(0.0, min(1.0, score))


def compute_relevance_score(record: Record, now: datetime) -> float:
    """
    Computes relevance score using weighted formula.

    Formula:
      relevance = 0.4*recency + 0.3*links + 0.2*quality + 0.1*user

    Returns: 0.0 - 1.0
    """
    recency = compute_recency_score(record, now)
    links = compute_link_score(record)
    quality = compute_quality_score(record)
    user = compute_user_score(record)

    relevance = (
        WEIGHT_RECENCY * recency +
        WEIGHT_LINKS * links +
        WEIGHT_QUALITY * quality +
        WEIGHT_USER * user
    )

    # Clamp to [MIN_SCORE_THRESHOLD, 1.0]
    relevance = max(MIN_SCORE_THRESHOLD, min(1.0, relevance))

    return relevance


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
            print(f"[relevance] WARN: Could not load {record_file}: {e}", file=sys.stderr)

    return records


def update_relevance_scores(records: Dict[str, Record], now: datetime, verbose: bool = False):
    """
    Updates relevance scores for all records.

    Modifies records in-place.
    """
    for ulid, record in records.items():
        old_score = record.status.relevance_score
        new_score = compute_relevance_score(record, now)

        record.status.relevance_score = new_score

        if verbose and abs(new_score - old_score) > 0.01:
            print(f"[relevance] {ulid[:8]}... {old_score:.3f} → {new_score:.3f}")


def save_records(records: Dict[str, Record], records_dir: Path):
    """Speichert alle Records zurück"""
    for ulid, record in records.items():
        out_path = records_dir / f"{ulid}.json"

        record_json = record.model_dump(mode="json", exclude_none=True)

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(record_json, f, indent=2, ensure_ascii=False, default=str)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Update relevance scores")
    parser.add_argument(
        "--records-dir",
        default=RECORDS_DIR,
        help="Directory with Record JSONs (default: data/records/)"
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=MIN_SCORE_THRESHOLD,
        help="Minimum score threshold (default: 0.15)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show score changes"
    )

    args = parser.parse_args()

    global MIN_SCORE_THRESHOLD
    MIN_SCORE_THRESHOLD = args.min_score

    records_dir = Path(args.records_dir)

    if not records_dir.exists():
        print(f"[relevance] ERROR: Records directory does not exist: {records_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"[relevance] Plan v0.3 Relevance Scoring")
    print(f"  Records: {records_dir}")
    print(f"  Min threshold: {args.min_score}")
    print(f"  Weights: recency={WEIGHT_RECENCY}, links={WEIGHT_LINKS}, quality={WEIGHT_QUALITY}, user={WEIGHT_USER}")
    print()

    # Load records
    print("[1/3] Loading records...")
    records = load_all_records(records_dir)
    print(f"  → {len(records)} records loaded")

    # Update scores
    print()
    print("[2/3] Computing relevance scores...")
    now = datetime.now(timezone.utc)
    update_relevance_scores(records, now, verbose=args.verbose)

    # Stats
    scores = [r.status.relevance_score for r in records.values()]
    avg_score = sum(scores) / len(scores) if scores else 0.0
    min_score = min(scores) if scores else 0.0
    max_score = max(scores) if scores else 0.0

    print(f"  → Average score: {avg_score:.3f}")
    print(f"  → Range: {min_score:.3f} - {max_score:.3f}")

    # Save
    print()
    print("[3/3] Saving records...")
    save_records(records, records_dir)
    print(f"  → {len(records)} records updated")

    print()
    print("[relevance] ✓ Done!")


if __name__ == "__main__":
    main()
