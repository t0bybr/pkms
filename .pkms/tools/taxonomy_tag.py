#!/usr/bin/env python3
"""
PKMS Taxonomy Tagger
Create git tags for taxonomy versions to enable easy rollback.
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime

# Python 3.11+ has tomllib in stdlib, older versions need tomli
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


def get_taxonomy_path() -> Path:
    """Get path to taxonomy.toml"""
    repo_root = Path(subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"],
        text=True
    ).strip())
    return repo_root / ".pkms" / "taxonomy.toml"


def get_latest_taxonomy_tag() -> str | None:
    """Get the latest taxonomy tag version"""
    try:
        result = subprocess.run(
            ["git", "tag", "-l", "taxonomy-v*", "--sort=-version:refname"],
            capture_output=True,
            text=True,
            check=True
        )
        tags = result.stdout.strip().split("\n")
        return tags[0] if tags and tags[0] else None
    except subprocess.CalledProcessError:
        return None


def parse_version(tag: str) -> tuple[int, int]:
    """Parse version from tag like 'taxonomy-v1.2' -> (1, 2)"""
    if not tag or not tag.startswith("taxonomy-v"):
        return (0, 0)

    version = tag.replace("taxonomy-v", "")
    parts = version.split(".")

    try:
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        return (major, minor)
    except ValueError:
        return (0, 0)


def get_next_version(current_tag: str | None, is_major: bool = False) -> str:
    """Calculate next version number"""
    if not current_tag:
        return "taxonomy-v1.0"

    major, minor = parse_version(current_tag)

    if is_major:
        return f"taxonomy-v{major + 1}.0"
    else:
        return f"taxonomy-v{major}.{minor + 1}"


def get_taxonomy_stats(taxonomy_path: Path) -> dict:
    """Get statistics about taxonomy"""
    with open(taxonomy_path, "rb") as f:
        data = tomllib.load(f)

    categories = data.get("taxonomy", {}).get("categories", {}).get("allowed", [])
    tags = data.get("taxonomy", {}).get("tags", {}).get("allowed", [])

    return {
        "categories": len(categories),
        "tags": len(tags),
        "total": len(categories) + len(tags)
    }


def get_taxonomy_changes() -> str | None:
    """Get summary of what changed in taxonomy"""
    try:
        result = subprocess.run(
            ["git", "diff", "HEAD^", "HEAD", "--", ".pkms/taxonomy.toml"],
            capture_output=True,
            text=True,
            check=True
        )

        if not result.stdout:
            return None

        # Parse diff to find added/removed tags
        added_tags = []
        removed_tags = []

        for line in result.stdout.split("\n"):
            if line.startswith("+") and not line.startswith("+++"):
                # Extract tag from line like '+ "python",'
                if '"' in line:
                    tag = line.split('"')[1]
                    if tag and tag not in ["allowed", "suggested"]:
                        added_tags.append(tag)
            elif line.startswith("-") and not line.startswith("---"):
                if '"' in line:
                    tag = line.split('"')[1]
                    if tag and tag not in ["allowed", "suggested"]:
                        removed_tags.append(tag)

        summary = []
        if added_tags:
            summary.append(f"Added {len(added_tags)} tag(s): {', '.join(added_tags[:5])}")
            if len(added_tags) > 5:
                summary[-1] += f" (and {len(added_tags) - 5} more)"

        if removed_tags:
            summary.append(f"Removed {len(removed_tags)} tag(s): {', '.join(removed_tags[:5])}")
            if len(removed_tags) > 5:
                summary[-1] += f" (and {len(removed_tags) - 5} more)"

        return "\n".join(summary) if summary else None

    except subprocess.CalledProcessError:
        return None


def create_taxonomy_tag(version: str, message: str = None, auto: bool = False):
    """Create an annotated git tag for taxonomy version"""

    # Get taxonomy stats
    taxonomy_path = get_taxonomy_path()
    stats = get_taxonomy_stats(taxonomy_path)

    # Build tag message
    if not message:
        changes = get_taxonomy_changes()
        if changes:
            message = f"Taxonomy {version}\n\n{changes}\n\nTotal: {stats['categories']} categories, {stats['tags']} tags"
        else:
            message = f"Taxonomy {version}\n\nTotal: {stats['categories']} categories, {stats['tags']} tags"

    # Check if tag already exists
    try:
        subprocess.run(
            ["git", "rev-parse", version],
            capture_output=True,
            check=True
        )
        print(f"⚠️  Tag {version} already exists")
        return False
    except subprocess.CalledProcessError:
        pass  # Tag doesn't exist, good

    # Create tag
    try:
        subprocess.run(
            ["git", "tag", "-a", version, "-m", message],
            check=True
        )
        print(f"✅ Created taxonomy tag: {version}")
        print(f"   {stats['categories']} categories, {stats['tags']} tags")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create tag: {e}")
        return False


def list_taxonomy_tags():
    """List all taxonomy tags with their info"""
    try:
        result = subprocess.run(
            ["git", "tag", "-l", "taxonomy-v*", "--sort=-version:refname"],
            capture_output=True,
            text=True,
            check=True
        )

        tags = result.stdout.strip().split("\n")
        if not tags or not tags[0]:
            print("No taxonomy tags found")
            return

        print("\nTaxonomy Version History:")
        print("=" * 60)

        for tag in tags:
            # Get tag date and message
            tag_info = subprocess.run(
                ["git", "tag", "-l", "--format=%(creatordate:short)|%(contents:subject)", tag],
                capture_output=True,
                text=True,
                check=True
            ).stdout.strip()

            date, subject = tag_info.split("|", 1) if "|" in tag_info else (tag_info, "")

            print(f"\n{tag} ({date})")
            if subject:
                print(f"  {subject}")

    except subprocess.CalledProcessError as e:
        print(f"❌ Error listing tags: {e}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="PKMS Taxonomy Git Tagging")
    parser.add_argument("action", choices=["create", "list", "auto"],
                       help="Action to perform")
    parser.add_argument("--major", action="store_true",
                       help="Increment major version (X.0) instead of minor (x.Y)")
    parser.add_argument("--version", type=str,
                       help="Specific version to use (e.g., v1.5)")
    parser.add_argument("--message", "-m", type=str,
                       help="Custom tag message")

    args = parser.parse_args()

    if args.action == "list":
        list_taxonomy_tags()
        return

    if args.action == "create" or args.action == "auto":
        # Get latest tag
        latest = get_latest_taxonomy_tag()

        if args.version:
            version = args.version
            if not version.startswith("taxonomy-v"):
                version = f"taxonomy-v{version}"
        else:
            version = get_next_version(latest, is_major=args.major)

        print(f"Creating taxonomy tag: {version}")
        if latest:
            print(f"  Previous version: {latest}")

        if args.action == "create":
            # Interactive mode
            response = input("\nProceed? [Y/n] ").strip().lower()
            if response and response != "y":
                print("Cancelled")
                return

        success = create_taxonomy_tag(version, args.message, auto=(args.action == "auto"))

        if success and args.action == "create":
            print(f"\nTo push tag: git push origin {version}")
            print(f"To view:     git show {version}")
            print(f"To rollback: git checkout {version} -- .pkms/taxonomy.toml")


if __name__ == "__main__":
    main()
