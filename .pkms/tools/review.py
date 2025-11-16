#!/usr/bin/env python3
"""
review.py - Review Queue Management

Manages approval/review queues for automated PKMS operations.
Used by agents and automated tools to request human review before applying changes.

Queue Structure:
    data/queue/reviews/
    ├── pending/        # Awaiting review
    ├── approved/       # Approved and applied
    └── rejected/       # Rejected, not applied

Review Types:
- tag_approval: New tags suggested by pkms-tag
- link_normalization: Link format changes by pkms-link
- archive_suggestions: Notes suggested for archival
- cleanup: Various cleanup operations

Usage:
    pkms-review list                    # List pending reviews
    pkms-review show <id>               # Show review details
    pkms-review interactive             # Interactive review session
    pkms-review approve <id>            # Approve specific review
    pkms-review reject <id>             # Reject specific review
    pkms-review approve-all --type tag  # Batch approve by type
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict
import subprocess

# Add .pkms to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.config import get_path


# ============================================================
# Review Queue Paths
# ============================================================

def get_queue_dir() -> Path:
    """Get reviews queue directory."""
    try:
        data_dir = get_path("data")
        queue_dir = data_dir / "queue" / "reviews"
    except:
        queue_dir = Path("data/queue/reviews")

    queue_dir.mkdir(parents=True, exist_ok=True)
    return queue_dir


def get_pending_dir() -> Path:
    """Get pending reviews directory."""
    pending = get_queue_dir() / "pending"
    pending.mkdir(exist_ok=True)
    return pending


def get_approved_dir() -> Path:
    """Get approved reviews directory."""
    approved = get_queue_dir() / "approved"
    approved.mkdir(exist_ok=True)
    return approved


def get_rejected_dir() -> Path:
    """Get rejected reviews directory."""
    rejected = get_queue_dir() / "rejected"
    rejected.mkdir(exist_ok=True)
    return rejected


# ============================================================
# Review Operations
# ============================================================

def create_review(
    review_type: str,
    data: dict,
    context: Optional[dict] = None
) -> str:
    """
    Create a new review request.

    Args:
        review_type: Type of review (tag_approval, link_normalization, etc.)
        data: Review-specific data
        context: Optional context (triggered_by, agent, etc.)

    Returns:
        Review ID
    """
    review_id = f"{review_type}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

    review = {
        "id": review_id,
        "type": review_type,
        "created": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
        "data": data,
        "context": context or {}
    }

    pending_file = get_pending_dir() / f"{review_id}.json"

    with open(pending_file, "w") as f:
        json.dump(review, f, indent=2, ensure_ascii=False)

    print(f"[review] Created review: {review_id}")
    return review_id


def list_pending() -> List[Dict]:
    """List all pending reviews."""
    pending_dir = get_pending_dir()
    reviews = []

    for file in sorted(pending_dir.glob("*.json")):
        with open(file) as f:
            review = json.load(f)
            reviews.append(review)

    return reviews


def get_review(review_id: str) -> Optional[Dict]:
    """Get review by ID (checks all directories)."""
    for directory in [get_pending_dir(), get_approved_dir(), get_rejected_dir()]:
        review_file = directory / f"{review_id}.json"
        if review_file.exists():
            with open(review_file) as f:
                return json.load(f)
    return None


def approve_review(review_id: str) -> bool:
    """Approve and apply review."""
    pending_file = get_pending_dir() / f"{review_id}.json"

    if not pending_file.exists():
        print(f"[review] ERROR: Review not found: {review_id}")
        return False

    with open(pending_file) as f:
        review = json.load(f)

    # Apply changes based on review type
    success = _apply_review(review)

    if success:
        # Update review status
        review["status"] = "approved"
        review["approved_at"] = datetime.now(timezone.utc).isoformat()

        # Move to approved directory
        approved_file = get_approved_dir() / f"{review_id}.json"
        with open(approved_file, "w") as f:
            json.dump(review, f, indent=2, ensure_ascii=False)

        pending_file.unlink()

        print(f"[review] ✓ Approved and applied: {review_id}")
        return True
    else:
        print(f"[review] ✗ Failed to apply review: {review_id}")
        return False


def reject_review(review_id: str, reason: Optional[str] = None) -> bool:
    """Reject review without applying."""
    pending_file = get_pending_dir() / f"{review_id}.json"

    if not pending_file.exists():
        print(f"[review] ERROR: Review not found: {review_id}")
        return False

    with open(pending_file) as f:
        review = json.load(f)

    # Update review status
    review["status"] = "rejected"
    review["rejected_at"] = datetime.now(timezone.utc).isoformat()
    if reason:
        review["rejection_reason"] = reason

    # Move to rejected directory
    rejected_file = get_rejected_dir() / f"{review_id}.json"
    with open(rejected_file, "w") as f:
        json.dump(review, f, indent=2, ensure_ascii=False)

    pending_file.unlink()

    print(f"[review] ✗ Rejected: {review_id}")
    return True


def _apply_review(review: dict) -> bool:
    """Apply review changes based on type."""
    review_type = review["type"]

    if review_type == "tag_approval":
        return _apply_tag_approval(review)
    elif review_type == "link_normalization":
        return _apply_link_normalization(review)
    else:
        print(f"[review] WARNING: Unknown review type: {review_type}")
        return False


def _apply_tag_approval(review: dict) -> bool:
    """Apply approved tags to taxonomy."""
    import toml

    new_tags = review["data"].get("new_tags", [])

    if not new_tags:
        return True

    try:
        taxonomy_file = Path(".pkms/taxonomy.toml")

        if not taxonomy_file.exists():
            print(f"[review] ERROR: taxonomy.toml not found")
            return False

        # Load taxonomy
        taxonomy = toml.load(taxonomy_file)

        # Add new tags
        existing_tags = set(taxonomy["taxonomy"]["tags"]["allowed"])
        tags_to_add = [tag for tag in new_tags if tag not in existing_tags]

        if tags_to_add:
            taxonomy["taxonomy"]["tags"]["allowed"].extend(tags_to_add)
            taxonomy["taxonomy"]["tags"]["allowed"].sort()

            # Add metadata
            if "metadata" not in taxonomy["taxonomy"]:
                taxonomy["taxonomy"]["metadata"] = {}

            for tag in tags_to_add:
                taxonomy["taxonomy"]["metadata"][tag] = {
                    "added": datetime.now(timezone.utc).isoformat(),
                    "auto_suggested": True,
                    "usage_count": review["data"].get("tag_usage", {}).get(tag, 0)
                }

            # Write back
            with open(taxonomy_file, "w") as f:
                toml.dump(taxonomy, f)

            print(f"[review] Added {len(tags_to_add)} tags to taxonomy: {', '.join(tags_to_add)}")

        return True

    except Exception as e:
        print(f"[review] ERROR: Failed to apply tag approval: {e}")
        return False


def _apply_link_normalization(review: dict) -> bool:
    """Apply link normalization changes."""
    # Placeholder - implement when pkms-link --normalize exists
    print(f"[review] Link normalization not yet implemented")
    return True


# ============================================================
# Interactive Review
# ============================================================

def interactive_review():
    """Interactive review session."""
    pending = list_pending()

    if not pending:
        print("\n✅ No pending reviews")
        return

    print(f"\n📋 {len(pending)} pending review(s)\n")

    for i, review in enumerate(pending, 1):
        print(f"{'='*60}")
        print(f"Review {i}/{len(pending)}: {review['id']}")
        print(f"{'='*60}\n")

        _show_review_details(review)

        while True:
            choice = input("\n[a]pprove / [r]eject / [s]kip / [q]uit: ").lower().strip()

            if choice == 'a':
                approve_review(review['id'])
                break
            elif choice == 'r':
                reason = input("Rejection reason (optional): ").strip()
                reject_review(review['id'], reason or None)
                break
            elif choice == 's':
                print("Skipped")
                break
            elif choice == 'q':
                print("\nReview session ended")
                return
            else:
                print("Invalid choice")

        print()


def _show_review_details(review: dict):
    """Show detailed review information."""
    print(f"Type:    {review['type']}")
    print(f"Created: {review['created']}")

    if review.get('context'):
        print(f"Context: {review['context']}")

    print(f"\nData:")

    review_type = review['type']
    data = review['data']

    if review_type == "tag_approval":
        print(f"  New tags proposed: {', '.join(data.get('new_tags', []))}")
        print(f"  Affected notes:    {data.get('affected_notes', 0)}")

        if data.get('tag_usage'):
            print(f"\n  Tag usage:")
            for tag, count in data['tag_usage'].items():
                print(f"    - {tag}: {count} note(s)")

    elif review_type == "link_normalization":
        print(f"  Links to normalize: {data.get('link_count', 0)}")
        print(f"  Format:             {data.get('target_format', '[[Title|ULID]]')}")

    else:
        # Generic data display
        print(json.dumps(data, indent=4))


# ============================================================
# CLI
# ============================================================

def cmd_list(args):
    """List pending reviews."""
    pending = list_pending()

    if not pending:
        print("✅ No pending reviews")
        return

    print(f"\n📋 {len(pending)} pending review(s):\n")

    for i, review in enumerate(pending, 1):
        review_type = review['type'].replace('_', ' ').title()
        created = review['created'][:10]  # Date only

        summary = ""
        if review['type'] == "tag_approval":
            tags = review['data'].get('new_tags', [])
            summary = f"({len(tags)} tags)"

        print(f"  {i}. {review['id']}")
        print(f"     Type: {review_type} {summary}")
        print(f"     Created: {created}\n")


def cmd_show(args):
    """Show review details."""
    review = get_review(args.id)

    if not review:
        print(f"Review not found: {args.id}")
        return

    print()
    _show_review_details(review)
    print()


def cmd_approve(args):
    """Approve review."""
    approve_review(args.id)


def cmd_reject(args):
    """Reject review."""
    reject_review(args.id, args.reason)


def cmd_approve_all(args):
    """Batch approve reviews by type."""
    pending = list_pending()

    if args.type:
        pending = [r for r in pending if r['type'] == args.type]

    if not pending:
        print("No matching reviews to approve")
        return

    print(f"Approving {len(pending)} review(s)...")

    for review in pending:
        approve_review(review['id'])


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Manage PKMS review queue"
    )

    subparsers = parser.add_subparsers(dest='command', help='Command')

    # list
    subparsers.add_parser('list', help='List pending reviews')

    # show
    show_parser = subparsers.add_parser('show', help='Show review details')
    show_parser.add_argument('id', help='Review ID')

    # interactive
    subparsers.add_parser('interactive', help='Interactive review session')

    # approve
    approve_parser = subparsers.add_parser('approve', help='Approve review')
    approve_parser.add_argument('id', help='Review ID')

    # reject
    reject_parser = subparsers.add_parser('reject', help='Reject review')
    reject_parser.add_argument('id', help='Review ID')
    reject_parser.add_argument('--reason', help='Rejection reason')

    # approve-all
    approve_all_parser = subparsers.add_parser('approve-all', help='Batch approve')
    approve_all_parser.add_argument('--type', help='Filter by review type')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == 'list':
            cmd_list(args)
        elif args.command == 'show':
            cmd_show(args)
        elif args.command == 'interactive':
            interactive_review()
        elif args.command == 'approve':
            cmd_approve(args)
        elif args.command == 'reject':
            cmd_reject(args)
        elif args.command == 'approve-all':
            cmd_approve_all(args)

    except KeyboardInterrupt:
        print("\n\nInterrupted")
        sys.exit(130)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
