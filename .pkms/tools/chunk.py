"""
chunk.py - Metadata → Chunks

PKMS v0.3 Chunking Pipeline:

Workflow:
1. Reads metadata JSONs from data/metadata/
2. Applies hybrid chunking (hierarchical + semantic)
3. Generates content-hash chunk IDs (xxhash64)
4. Writes NDJSON to data/chunks/{doc_id}.ndjson

Design:
- Chunks are content-addressable (ID = hash of content)
- Multiple chunking strategies supported (fixed, semantic)
- Git-friendly NDJSON format (one chunk per line)
- Configuration from .pkms/config.toml

Usage:
    python -m pkms.tools.chunk
    python -m pkms.tools.chunk --max-tokens 400
"""

from __future__ import annotations

import sys
import json
from pathlib import Path

from lib.chunking import chunk_document
from lib.config import get_path, get_chunking_config


def load_record(record_path: Path) -> dict:
	"""
	Load metadata record JSON.

	Args:
		record_path: Path to metadata JSON file

	Returns:
		dict: Record data
	"""
	with open(record_path, "r", encoding="utf-8") as f:
		return json.load(f)


def save_chunks(chunks: list[dict], chunks_dir: Path, doc_id: str):
	"""
	Save chunks as NDJSON.

	Args:
		chunks: List of chunk dicts
		chunks_dir: Output directory
		doc_id: Document ULID
	"""
	chunks_dir.mkdir(parents=True, exist_ok=True)

	out_path = chunks_dir / f"{doc_id}.ndjson"

	with open(out_path, "w", encoding="utf-8") as f:
		for chunk in chunks:
			json.dump(chunk, f, ensure_ascii=False)
			f.write("\n")

	print(f"[chunk] Saved {len(chunks)} chunks → {out_path.name}")


def chunk_record(record_path: Path, chunks_dir: Path, max_tokens: int):
	"""
	Process single metadata record and generate chunks.

	Args:
		record_path: Path to metadata JSON
		chunks_dir: Output directory for chunks
		max_tokens: Maximum tokens per chunk
	"""
	try:
		record = load_record(record_path)

		doc_id = record["id"]
		text = record["full_text"]
		language = record.get("language", "en")

		# Generate chunks
		chunks = chunk_document(
			doc_id=doc_id,
			text=text,
			language=language,
			max_tokens=max_tokens,
		)

		# Save to NDJSON
		save_chunks(chunks, chunks_dir, doc_id)

	except Exception as e:
		print(f"[chunk] ERROR: Failed to chunk {record_path.name}: {e}", file=sys.stderr)
		import traceback
		traceback.print_exc()


def chunk_all_records(metadata_dir: Path, chunks_dir: Path, max_tokens: int):
	"""
	Process all metadata records.

	Args:
		metadata_dir: Directory with metadata JSONs
		chunks_dir: Output directory for chunks
		max_tokens: Maximum tokens per chunk
	"""
	record_files = list(metadata_dir.glob("*.json"))

	if not record_files:
		print(f"[chunk] No metadata files found in {metadata_dir}")
		return

	print(f"[chunk] Found {len(record_files)} metadata files")
	print()

	for record_path in record_files:
		chunk_record(record_path, chunks_dir, max_tokens)

	print(f"\n[chunk] ✓ Chunked {len(record_files)} records")


def main():
	import argparse

	parser = argparse.ArgumentParser(
		description="Chunk metadata records into smaller pieces"
	)
	parser.add_argument(
		"--metadata-dir",
		help="Input directory with metadata JSONs (default: from config)"
	)
	parser.add_argument(
		"--chunks-dir",
		help="Output directory for chunk NDJSON files (default: from config)"
	)
	parser.add_argument(
		"--max-tokens",
		type=int,
		help="Maximum tokens per chunk (default: from config)"
	)

	args = parser.parse_args()

	# Load config
	chunking_config = get_chunking_config()

	# Determine paths
	metadata_dir = Path(args.metadata_dir) if args.metadata_dir else get_path("metadata")
	chunks_dir = Path(args.chunks_dir) if args.chunks_dir else get_path("chunks")

	# Determine max_tokens
	max_tokens = args.max_tokens or chunking_config.get("chunk_size", 512)

	if not metadata_dir.exists():
		print(f"[chunk] ERROR: Metadata directory does not exist: {metadata_dir}", file=sys.stderr)
		sys.exit(1)

	print(f"[chunk] PKMS v0.3 Chunking")
	print(f"  Strategy: {chunking_config.get('strategy', 'fixed')}")
	print(f"  Input:    {metadata_dir}")
	print(f"  Output:   {chunks_dir}")
	print(f"  Max tokens: {max_tokens}")
	print()

	chunk_all_records(metadata_dir, chunks_dir, max_tokens)


if __name__ == "__main__":
	main()
