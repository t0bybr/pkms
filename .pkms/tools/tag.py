#!/usr/bin/env python3
"""
tag.py - Automated Tagging with LLM

Analyzes notes and suggests/applies tags using an LLM (Ollama).
Ensures tag consistency using taxonomy.toml.

Modes:
- Interactive: Suggest tags, ask for approval
- Queue: Suggest tags, queue for review (for automated workflows)
- Auto: Apply tags directly (use with caution!)

Usage:
    pkms-tag                         # Tag all notes (interactive)
    pkms-tag vault/note.md           # Tag single note
    pkms-tag --only-empty            # Only notes without tags
    pkms-tag --queue                 # Queue suggestions for review
    pkms-tag --verify                # Verify existing tags still fit
    pkms-tag --suggest-new           # Allow suggesting new tags
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Optional, List, Dict, Tuple
import toml

# Add .pkms to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.config import get_path, get_config_value
from lib.frontmatter.core import parse_file, write_file
from lib.fs.paths import parse_slug_id
from models import FrontmatterModel

# Import review system
from tools.review import create_review


# ============================================================
# Taxonomy
# ============================================================

def load_taxonomy() -> dict:
    """Load taxonomy configuration."""
    taxonomy_file = Path(".pkms/taxonomy.toml")

    if not taxonomy_file.exists():
        print("[tag] WARNING: taxonomy.toml not found, using empty taxonomy")
        return {
            "taxonomy": {
                "categories": {"allowed": []},
                "tags": {"allowed": []},
                "suggestions": {},
                "metadata": {}
            }
        }

    return toml.load(taxonomy_file)


def get_allowed_tags(taxonomy: dict) -> List[str]:
    """Get list of allowed tags."""
    return taxonomy.get("taxonomy", {}).get("tags", {}).get("allowed", [])


def get_allowed_categories(taxonomy: dict) -> List[str]:
    """Get list of allowed categories."""
    return taxonomy.get("taxonomy", {}).get("categories", {}).get("allowed", [])


def get_suggestions_for_category(taxonomy: dict, category: str) -> List[str]:
    """Get suggested tags for a category."""
    return taxonomy.get("taxonomy", {}).get("suggestions", {}).get(category, [])


# ============================================================
# LLM Tagging
# ============================================================

def suggest_tags_llm(
    title: str,
    body: str,
    taxonomy: dict,
    allow_new: bool = False
) -> Tuple[List[str], str, float]:
    """
    Use LLM to suggest tags and category.

    Args:
        title: Note title
        body: Note body text
        taxonomy: Taxonomy configuration
        allow_new: Allow suggesting tags not in taxonomy

    Returns:
        (tags, category, confidence)
    """
    import ollama

    allowed_tags = get_allowed_tags(taxonomy)
    allowed_categories = get_allowed_categories(taxonomy)

    # Build prompt
    if allow_new:
        tag_instructions = f"Use existing tags when possible: {', '.join(allowed_tags[:20])}\nYou may suggest new tags if needed."
    else:
        tag_instructions = f"Choose ONLY from these tags: {', '.join(allowed_tags)}"

    prompt = f"""Analyze this note and suggest classification:

Title: {title}
Content: {body[:1000]}

Categories (choose one): {', '.join(allowed_categories)}
{tag_instructions}

Return JSON only:
{{
  "category": "...",
  "tags": ["tag1", "tag2", "tag3"],
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation"
}}

Guidelines:
- Choose 3-5 most relevant tags
- Category should be broad classification
- Tags should be specific and descriptive
- Confidence: how certain you are (0.0 = unsure, 1.0 = very sure)
"""

    try:
        # Get LLM model from config
        model = get_config_value("llm", "model", "PKMS_LLM_MODEL", "qwen2.5-coder:latest")
        temperature = get_config_value("llm", "temperature", "PKMS_LLM_TEMPERATURE", 0.3)

        # Get Ollama URL
        ollama_url = get_config_value("llm", "ollama_url", "OLLAMA_HOST", "http://localhost:11434")

        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            format="json",
            options={
                "temperature": temperature
            }
        )

        result = json.loads(response['message']['content'])

        tags = result.get('tags', [])
        category = result.get('category', '')
        confidence = result.get('confidence', 0.5)

        # Filter to allowed tags if not allow_new
        if not allow_new:
            tags = [t for t in tags if t in allowed_tags]

        # Validate category
        if category not in allowed_categories:
            category = allowed_categories[0] if allowed_categories else ""

        return tags, category, confidence

    except Exception as e:
        print(f"[tag] ERROR: LLM tagging failed: {e}")
        return [], "", 0.0


# ============================================================
# Tagging Operations
# ============================================================

def tag_note(
    file_path: Path,
    mode: str = "interactive",
    allow_new: bool = False,
    verify: bool = False
) -> Optional[Dict]:
    """
    Tag a single note.

    Args:
        file_path: Path to markdown file
        mode: "interactive", "queue", or "auto"
        allow_new: Allow suggesting new tags
        verify: Verify existing tags (re-tag mode)

    Returns:
        Dict with tagging result or None
    """
    try:
        # Parse note
        frontmatter, body = parse_file(file_path)

        # Skip if already tagged (unless verify mode)
        if not verify and frontmatter.tags and len(frontmatter.tags) > 0:
            return None

        # Load taxonomy
        taxonomy = load_taxonomy()

        # Suggest tags
        suggested_tags, suggested_category, confidence = suggest_tags_llm(
            title=frontmatter.title or file_path.stem,
            body=body,
            taxonomy=taxonomy,
            allow_new=allow_new
        )

        if not suggested_tags:
            print(f"[tag] No tags suggested for: {file_path.name}")
            return None

        # Check for new tags (not in taxonomy)
        allowed_tags = set(get_allowed_tags(taxonomy))
        new_tags = [t for t in suggested_tags if t not in allowed_tags]

        result = {
            "file": str(file_path),
            "suggested_tags": suggested_tags,
            "suggested_category": suggested_category,
            "new_tags": new_tags,
            "confidence": confidence,
            "existing_tags": frontmatter.tags or [],
            "existing_categories": frontmatter.categories or []
        }

        # Handle based on mode
        if mode == "interactive":
            return _interactive_tag_approval(file_path, frontmatter, body, result)
        elif mode == "queue":
            return result  # Caller will queue
        elif mode == "auto":
            # Apply directly (only non-new tags in strict mode)
            tags_to_apply = suggested_tags if allow_new else [t for t in suggested_tags if t in allowed_tags]
            _apply_tags(file_path, frontmatter, body, tags_to_apply, [suggested_category])
            return result
        else:
            return result

    except Exception as e:
        print(f"[tag] ERROR: Failed to tag {file_path.name}: {e}")
        return None


def _interactive_tag_approval(
    file_path: Path,
    frontmatter: FrontmatterModel,
    body: str,
    result: dict
) -> dict:
    """Interactive approval for suggested tags."""
    print(f"\n{'='*60}")
    print(f"File: {file_path.name}")
    print(f"Title: {frontmatter.title or '(no title)'}")
    print(f"{'='*60}\n")

    print(f"Suggested tags:     {', '.join(result['suggested_tags'])}")
    print(f"Suggested category: {result['suggested_category']}")
    print(f"Confidence:         {result['confidence']:.2f}")

    if result['existing_tags']:
        print(f"Existing tags:      {', '.join(result['existing_tags'])}")

    if result['new_tags']:
        print(f"\n⚠️  NEW tags (not in taxonomy): {', '.join(result['new_tags'])}")

    while True:
        choice = input("\n[a]pprove / [r]eject / [e]dit / [s]kip: ").lower().strip()

        if choice == 'a':
            _apply_tags(
                file_path,
                frontmatter,
                body,
                result['suggested_tags'],
                [result['suggested_category']]
            )
            result['applied'] = True
            return result
        elif choice == 'r':
            print("Rejected")
            result['applied'] = False
            return result
        elif choice == 'e':
            tags_input = input("Tags (comma-separated): ").strip()
            category_input = input("Category: ").strip()

            if tags_input:
                tags = [t.strip() for t in tags_input.split(',')]
                _apply_tags(file_path, frontmatter, body, tags, [category_input] if category_input else [])
                result['applied'] = True
                return result
        elif choice == 's':
            print("Skipped")
            result['applied'] = False
            return result
        else:
            print("Invalid choice")


def _apply_tags(
    file_path: Path,
    frontmatter: FrontmatterModel,
    body: str,
    tags: List[str],
    categories: List[str]
):
    """Apply tags to note frontmatter."""
    frontmatter.tags = tags
    frontmatter.categories = categories

    write_file(file_path, frontmatter, body)

    print(f"[tag] ✓ Applied tags to: {file_path.name}")


# ============================================================
# Bulk Operations
# ============================================================

def tag_vault(
    vault_path: Optional[Path] = None,
    mode: str = "interactive",
    only_empty: bool = False,
    allow_new: bool = False,
    verify: bool = False
) -> Dict:
    """
    Tag all notes in vault.

    Returns:
        Summary dict with stats
    """
    if vault_path is None:
        vault_path = get_path("vault")

    if not vault_path.exists():
        print(f"[tag] ERROR: Vault not found: {vault_path}")
        return {}

    # Find all markdown files
    md_files = list(vault_path.rglob("*.md"))

    print(f"\n📝 PKMS Tagging")
    print("=" * 60)
    print(f"Vault: {vault_path}")
    print(f"Files: {len(md_files)}")
    print(f"Mode:  {mode}")
    print("=" * 60)
    print()

    results = []
    new_tags_summary = {}

    for file_path in md_files:
        result = tag_note(file_path, mode=mode, allow_new=allow_new, verify=verify)

        if result:
            results.append(result)

            # Track new tags
            for tag in result.get('new_tags', []):
                new_tags_summary[tag] = new_tags_summary.get(tag, 0) + 1

    # Summary
    tagged_count = sum(1 for r in results if r.get('applied', False))

    print()
    print("=" * 60)
    print(f"📊 Summary:")
    print(f"  Processed: {len(results)}/{len(md_files)}")
    print(f"  Tagged:    {tagged_count}")

    if new_tags_summary and mode == "queue":
        print(f"  New tags:  {len(new_tags_summary)}")

    print("=" * 60)
    print()

    # Create review if new tags found in queue mode
    if mode == "queue" and new_tags_summary:
        review_id = create_review(
            review_type="tag_approval",
            data={
                "new_tags": list(new_tags_summary.keys()),
                "tag_usage": new_tags_summary,
                "affected_notes": sum(new_tags_summary.values())
            },
            context={
                "triggered_by": "pkms-tag --queue",
                "timestamp": str(Path().absolute())
            }
        )

        print(f"[tag] Created review: {review_id}")
        print(f"[tag] Run 'pkms-review interactive' to approve")

    return {
        "total": len(md_files),
        "processed": len(results),
        "tagged": tagged_count,
        "new_tags": new_tags_summary
    }


# ============================================================
# CLI
# ============================================================

def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Tag PKMS notes using LLM analysis"
    )

    parser.add_argument(
        "path",
        nargs="?",
        help="Path to markdown file or vault directory (default: vault/)"
    )
    parser.add_argument(
        "--only-empty",
        action="store_true",
        help="Only tag notes without existing tags"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Re-analyze and verify existing tags"
    )
    parser.add_argument(
        "--queue",
        action="store_true",
        help="Queue suggestions for review (for automated workflows)"
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Apply tags automatically without review"
    )
    parser.add_argument(
        "--suggest-new",
        action="store_true",
        help="Allow suggesting tags not in taxonomy"
    )

    args = parser.parse_args()

    # Determine mode
    if args.queue:
        mode = "queue"
    elif args.auto:
        mode = "auto"
    else:
        mode = "interactive"

    try:
        if args.path:
            path = Path(args.path)

            if not path.exists():
                print(f"[tag] ERROR: Path not found: {path}")
                sys.exit(1)

            if path.is_file():
                # Tag single file
                result = tag_note(
                    path,
                    mode=mode,
                    allow_new=args.suggest_new,
                    verify=args.verify
                )

                if result and result.get('new_tags') and mode == "queue":
                    # Create review for single file
                    create_review(
                        review_type="tag_approval",
                        data={
                            "new_tags": result['new_tags'],
                            "tag_usage": {tag: 1 for tag in result['new_tags']},
                            "affected_notes": 1
                        },
                        context={"triggered_by": f"pkms-tag {path}"}
                    )

            else:
                # Tag directory
                tag_vault(
                    path,
                    mode=mode,
                    only_empty=args.only_empty,
                    allow_new=args.suggest_new,
                    verify=args.verify
                )
        else:
            # Tag entire vault
            tag_vault(
                mode=mode,
                only_empty=args.only_empty,
                allow_new=args.suggest_new,
                verify=args.verify
            )

    except KeyboardInterrupt:
        print("\n\n[tag] Interrupted")
        sys.exit(130)
    except Exception as e:
        print(f"[tag] ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
