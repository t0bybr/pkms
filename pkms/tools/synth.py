"""
synth.py - Git-basierte Konsolidierung

Plan v0.3:
- Findet thematisch verwandte Notes (via Clustering/Embeddings)
- Erstellt Git-Branch (synth/{topic}-{ulid})
- Generiert Synthese-Note (TODO: LLM-Integration)
- Updates Source-Records (status.consolidated_into)
- Human-Review via Git-Diff/PR

Usage:
    python -m pkms.tools.synth --find-clusters
    python -m pkms.tools.synth --create {cluster_id}

Note: This is a framework. LLM-integration for synthesis generation
      needs to be implemented based on your requirements.
"""

from __future__ import annotations

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

from pkms.models import Record
from pkms.lib.fs.ids import new_id
from pkms.lib.fs.slug import make_slug
from pkms.lib.records_io import load_all_records


# Config
RECORDS_DIR = os.getenv("PKMS_RECORDS_DIR", "data/records")
NOTES_DIR = os.getenv("PKMS_NOTES_DIR", "notes")


def run_git_command(cmd: List[str], check: bool = True) -> subprocess.CompletedProcess:
    """Runs a git command and returns the result"""
    try:
        result = subprocess.run(
            cmd,
            check=check,
            capture_output=True,
            text=True,
        )
        return result
    except subprocess.CalledProcessError as e:
        print(f"[synth] ERROR: Git command failed: {' '.join(cmd)}", file=sys.stderr)
        print(f"  stdout: {e.stdout}", file=sys.stderr)
        print(f"  stderr: {e.stderr}", file=sys.stderr)
        raise


def find_related_notes(records: Dict[str, Record], min_cluster_size: int = 3) -> List[Dict]:
    """
    Findet thematisch verwandte Notes.

    TODO: Implement clustering via:
    - Embeddings + Cosine-Similarity
    - Link-Graph analysis (connected components)
    - Tag/Category overlap

    Returns: List of clusters
      [
        {
          "id": "cluster-1",
          "topic": "Pizza Rezepte",
          "doc_ids": ["01HAR...", "01HAR...", ...],
          "score": 0.85
        },
        ...
      ]
    """
    # Placeholder: Find by tags
    clusters = []
    tag_groups = {}

    for ulid, record in records.items():
        if record.status and record.status.archived:
            continue

        # Defensive: tags could be None in old records
        for tag in (record.tags or []):
            if tag not in tag_groups:
                tag_groups[tag] = []
            tag_groups[tag].append(ulid)

    cluster_id = 0
    for tag, doc_ids in tag_groups.items():
        if len(doc_ids) >= min_cluster_size:
            clusters.append({
                "id": f"cluster-{cluster_id}",
                "topic": tag,
                "doc_ids": doc_ids,
                "score": len(doc_ids) / 10.0,  # Placeholder
            })
            cluster_id += 1

    return clusters


def create_synth_branch(topic: str, synth_id: str) -> str:
    """
    Erstellt Git-Branch für Synthese.

    Returns: branch_name
    Raises: CalledProcessError if git operations fail
    """
    slug = make_slug(topic)
    branch_name = f"synth/{slug}-{synth_id[:8]}"

    # Check if branch already exists
    try:
        result = run_git_command(["git", "branch", "--list", branch_name], check=True)
        if branch_name in result.stdout:
            print(f"[synth] Branch already exists: {branch_name}")
            return branch_name
    except subprocess.CalledProcessError:
        print(f"[synth] ERROR: Not a git repository or git not available", file=sys.stderr)
        raise

    # Create branch
    run_git_command(["git", "checkout", "-b", branch_name])
    print(f"[synth] Created branch: {branch_name}")

    return branch_name


def generate_synthesis_content(cluster: Dict, records: Dict[str, Record]) -> str:
    """
    Generiert Synthese-Inhalt.

    TODO: Implement LLM-based synthesis:
    - Combine content from all source docs
    - Extract common themes
    - Generate cohesive synthesis
    - Cite sources

    Returns: Markdown content
    """
    # Placeholder: Simple concatenation
    lines = [
        f"# {cluster['topic']} - Synthesis",
        "",
        f"This synthesis consolidates {len(cluster['doc_ids'])} related notes.",
        "",
        "## Sources",
        "",
    ]

    for doc_id in cluster["doc_ids"]:
        record = records.get(doc_id)
        if record:
            lines.append(f"- [[{doc_id}]] - {record.title}")

    lines.extend([
        "",
        "## Content",
        "",
        "TODO: LLM-generated synthesis goes here.",
        "",
        "Key points:",
    ])

    for doc_id in cluster["doc_ids"]:
        record = records.get(doc_id)
        if record:
            # Extract first paragraph as summary
            paragraphs = record.full_text.split("\n\n")
            first_para = paragraphs[0] if paragraphs else ""
            lines.append(f"- **{record.title}**: {first_para[:100]}...")

    return "\n".join(lines)


def create_synthesis(
    cluster: Dict,
    records: Dict[str, Record],
    notes_dir: Path,
    records_dir: Path,
) -> str:
    """
    Erstellt Synthese-Note.

    Returns: synth_id (ULID)
    """
    synth_id = new_id()
    topic = cluster["topic"]
    slug = make_slug(topic)

    # Create branch
    branch_name = create_synth_branch(topic, synth_id)

    # Generate synthesis content
    content = generate_synthesis_content(cluster, records)

    # Create frontmatter
    now = datetime.now(timezone.utc).isoformat()
    frontmatter = f"""---
id: {synth_id}
title: {topic} - Synthesis
tags: [synthesis, {topic}]
date_created: {now}
---

"""

    full_content = frontmatter + content

    # Write synthesis note
    filename = f"{slug}-synthesis--{synth_id}.md"
    note_path = notes_dir / filename

    with open(note_path, "w", encoding="utf-8") as f:
        f.write(full_content)

    print(f"[synth] Created synthesis note: {note_path}")

    # Update source records (set consolidated_into)
    modified_record_paths = []
    for doc_id in cluster["doc_ids"]:
        record = records.get(doc_id)
        if record and record.status:
            record.status.consolidated_into = synth_id
            # Optionally archive
            # record.status.archived = True

            # Save updated record
            out_path = records_dir / f"{doc_id}.json"
            record_json = record.model_dump(mode="json", exclude_none=True)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(record_json, f, indent=2, ensure_ascii=False, default=str)

            modified_record_paths.append(str(out_path))

    # Git add - add each file individually (wildcard doesn't work without shell=True)
    run_git_command(["git", "add", str(note_path)])
    for record_path in modified_record_paths:
        run_git_command(["git", "add", record_path])

    sources_list = "\n".join(f"- {doc_id}" for doc_id in cluster['doc_ids'])
    commit_msg = f"""synth: Consolidate {len(cluster['doc_ids'])} notes about {topic}

Sources:
{sources_list}

Synthesis: {synth_id}

Agent: synth-v1.0.0
Confidence: {cluster['score']:.2f}
Review required: true
"""

    run_git_command(["git", "commit", "-m", commit_msg])

    print(f"[synth] Committed to branch: {branch_name}")
    print(f"[synth] Review via: git diff main..{branch_name}")

    return synth_id


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Consolidate related notes")
    parser.add_argument(
        "--records-dir",
        default=RECORDS_DIR,
        help="Directory with Record JSONs (default: data/records/)"
    )
    parser.add_argument(
        "--notes-dir",
        default=NOTES_DIR,
        help="Directory for markdown notes (default: notes/)"
    )
    parser.add_argument(
        "--find-clusters",
        action="store_true",
        help="Find and list clusters of related notes"
    )
    parser.add_argument(
        "--create",
        type=int,
        metavar="CLUSTER_ID",
        help="Create synthesis for cluster (use ID from --find-clusters)"
    )
    parser.add_argument(
        "--min-cluster-size",
        type=int,
        default=3,
        help="Minimum cluster size (default: 3)"
    )

    args = parser.parse_args()

    records_dir = Path(args.records_dir)
    notes_dir = Path(args.notes_dir)

    if not records_dir.exists():
        print(f"[synth] ERROR: Records directory does not exist: {records_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"[synth] Plan v0.3 Synthesis Tool")
    print(f"  Records: {records_dir}")
    print(f"  Notes: {notes_dir}")
    print()

    # Load records
    print("[1/2] Loading records...")
    records = load_all_records(records_dir)
    print(f"  → {len(records)} records loaded")

    # Find clusters
    print()
    print("[2/2] Finding clusters...")
    clusters = find_related_notes(records, min_cluster_size=args.min_cluster_size)
    print(f"  → {len(clusters)} clusters found")

    if args.find_clusters:
        print()
        print("Clusters:")
        for i, cluster in enumerate(clusters):
            print(f"  [{i}] {cluster['topic']} - {len(cluster['doc_ids'])} docs (score: {cluster['score']:.2f})")
        print()
        print("Use --create N to create synthesis for cluster N")
        return

    if args.create is not None:
        if args.create >= len(clusters):
            print(f"[synth] ERROR: Cluster {args.create} not found", file=sys.stderr)
            sys.exit(1)

        cluster = clusters[args.create]
        print()
        print(f"Creating synthesis for: {cluster['topic']}")
        synth_id = create_synthesis(cluster, records, notes_dir, records_dir)
        print()
        print(f"[synth] ✓ Done! Synthesis ID: {synth_id}")
        print()
        print("Next steps:")
        print("  1. Review the synthesis")
        print("  2. Merge when ready: git merge --no-ff synth/...")
        return

    print()
    print("Use --find-clusters to list clusters or --create N to create synthesis")


if __name__ == "__main__":
    main()
