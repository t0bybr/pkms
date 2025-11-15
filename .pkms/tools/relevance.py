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

from models import Record
from lib.records_io import load_all_records, save_records
from lib.config import get_records_dir, get_relevance_config


# Config
RECORDS_DIR = get_records_dir()

# Load relevance config (config.toml overrides these defaults)
_rel_config = get_relevance_config()

# Scoring weights (from config.toml with fallback to defaults)
WEIGHT_RECENCY = _rel_config.get("weight_recency", 0.4)
WEIGHT_LINKS = _rel_config.get("weight_links", 0.3)
WEIGHT_QUALITY = _rel_config.get("weight_quality", 0.2)
WEIGHT_USER = _rel_config.get("weight_user", 0.1)

# Recency decay parameter (from config)
RECENCY_HALF_LIFE_DAYS = _rel_config.get("recency_half_life_days", 90.0)

# Minimum score threshold
MIN_SCORE_THRESHOLD = 0.15


def compute_recency_score(record: Record, now: datetime) -> float:
    """
    Recency score based on last update time.

    Uses exponential decay: e^(-age_days / half_life)
    Half-life configured in config.toml (default: 90 days)

    Returns: 0.0 - 1.0
    """
    # Ensure timezone-aware comparison
    updated = record.updated
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    age_seconds = (now - updated).total_seconds()
    age_days = age_seconds / 86400.0

    # Exponential decay (uses global RECENCY_HALF_LIFE_DAYS from config)
    score = math.exp(-age_days / RECENCY_HALF_LIFE_DAYS)

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

    # Human edited (explicit True check for optional bool)
    if record.status.human_edited is True:
        score += 0.5

    # Agent reviewed
    if record.agent and record.agent.reviewed is True:
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

    Note: MIN_SCORE_THRESHOLD is NOT applied here - it's only used for archiving policy.
    Artificially raising scores would defeat the purpose of relevance scoring.
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

    # Clamp to [0.0, 1.0] - no artificial minimum
    relevance = max(0.0, min(1.0, relevance))

    return relevance


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


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Update relevance scores")
    parser.add_argument(
        "--records-dir",
        default=RECORDS_DIR,
        help="Directory with Record JSONs (default: data/metadata/)"
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

    # Note: MIN_SCORE_THRESHOLD is for documentation/archiving policy only.
    # It's NOT used in score computation (see compute_relevance_score).
    min_score_threshold = args.min_score

    records_dir = Path(args.records_dir)

    if not records_dir.exists():
        print(f"[relevance] ERROR: Records directory does not exist: {records_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"[relevance] Plan v0.3 Relevance Scoring")
    print(f"  Records: {records_dir}")
    print(f"  Archive threshold: {min_score_threshold} (used by archive.py, not by scoring)")
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

    # Stats (with error handling)
    try:
        scores = [r.status.relevance_score for r in records.values() if r.status]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        min_score_val = min(scores) if scores else 0.0
        max_score_val = max(scores) if scores else 0.0

        print(f"  → Average score: {avg_score:.3f}")
        print(f"  → Range: {min_score_val:.3f} - {max_score_val:.3f}")
    except Exception as e:
        print(f"[relevance] WARN: Could not compute stats: {e}", file=sys.stderr)

    # Save
    print()
    print("[3/3] Saving records...")
    save_records(records, records_dir)
    print(f"  → {len(records)} records updated")

    print()
    print("[relevance] ✓ Done!")


if __name__ == "__main__":
    main()
