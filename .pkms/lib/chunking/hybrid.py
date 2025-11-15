"""
Hybrid Chunking (hierarchisch + semantisch)

Plan v0.3:
- Hierarchical: Split by markdown headings
- Semantic: Further split large sections (optional, via LangChain)
- Content-Hash IDs: xxhash64(text)[:12]
- Overlap: 10-20% between chunks
- Token counting: tiktoken or simple word-based estimate
"""

from __future__ import annotations

import re
from typing import List, Dict, Optional
from dataclasses import dataclass

# Utilities
from lib.utils import compute_chunk_hash, count_tokens


@dataclass
class ChunkData:
    """Intermediate chunk data before converting to dict"""
    text: str
    section: Optional[str] = None
    subsection: Optional[str] = None
    chunk_index: int = 0


class HierarchicalChunker:
    """
    Splits markdown text by headings (hierarchical).

    Later can be extended with semantic splitting for large sections.
    """

    def __init__(
        self,
        max_tokens: int = 500,
        overlap_tokens: int = 50,
        min_chunk_tokens: int = 20,
    ):
        """
        :param max_tokens: Maximum tokens per chunk
        :param overlap_tokens: Overlap between consecutive chunks
        :param min_chunk_tokens: Minimum tokens for a chunk (avoid tiny chunks)
        """
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.min_chunk_tokens = min_chunk_tokens

    def split_by_headings(self, text: str) -> List[Dict]:
        """
        Split markdown by headings (# Heading 1, ## Heading 2, etc.)

        Returns list of dicts with keys: text, section, subsection
        """
        # Regex to find markdown headings
        heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

        # Find all heading positions
        headings = []
        for match in heading_pattern.finditer(text):
            level = len(match.group(1))  # Number of #
            title = match.group(2).strip()
            start = match.start()
            headings.append({
                "level": level,
                "title": title,
                "start": start,
            })

        # If no headings, treat entire text as one section
        if not headings:
            return [{"text": text.strip(), "section": None, "subsection": None}]

        # Split text into sections
        sections = []
        current_h1 = None
        current_h2 = None

        for i, heading in enumerate(headings):
            # Extract text between this heading and next
            start_pos = heading["start"]
            end_pos = headings[i + 1]["start"] if i + 1 < len(headings) else len(text)

            section_text = text[start_pos:end_pos].strip()

            # Track heading hierarchy (H1, H2)
            if heading["level"] == 1:
                current_h1 = heading["title"]
                current_h2 = None
            elif heading["level"] == 2:
                current_h2 = heading["title"]

            sections.append({
                "text": section_text,
                "section": current_h1,
                "subsection": current_h2,
            })

        return sections

    def split_large_section(self, section: Dict) -> List[Dict]:
        """
        If a section is too large, split it into smaller chunks with overlap.

        For now: simple paragraph-based splitting.
        Later: can integrate LangChain SemanticChunker here.
        """
        text = section["text"]
        tokens = count_tokens(text)

        if tokens <= self.max_tokens:
            return [section]

        # Split by paragraphs (double newline)
        paragraphs = re.split(r"\n\n+", text)

        chunks = []
        current_chunk = []
        current_tokens = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            para_tokens = count_tokens(para)

            # If single paragraph exceeds max_tokens, force split by sentences
            if para_tokens > self.max_tokens:
                # Split by sentences
                sentences = re.split(r"(?<=[.!?])\s+", para)
                for sent in sentences:
                    sent_tokens = count_tokens(sent)
                    if current_tokens + sent_tokens > self.max_tokens and current_chunk:
                        # Flush current chunk
                        chunk_text = " ".join(current_chunk)
                        chunks.append({
                            "text": chunk_text,
                            "section": section["section"],
                            "subsection": section["subsection"],
                        })
                        # Overlap: keep last sentence
                        if len(current_chunk) > 1:
                            current_chunk = [current_chunk[-1]]
                            current_tokens = count_tokens(current_chunk[0])
                        else:
                            current_chunk = []
                            current_tokens = 0

                    current_chunk.append(sent)
                    current_tokens += sent_tokens
            else:
                # Normal paragraph
                if current_tokens + para_tokens > self.max_tokens and current_chunk:
                    # Flush
                    chunk_text = "\n\n".join(current_chunk)
                    chunks.append({
                        "text": chunk_text,
                        "section": section["section"],
                        "subsection": section["subsection"],
                    })
                    # Overlap: keep last paragraph
                    if len(current_chunk) > 1:
                        current_chunk = [current_chunk[-1]]
                        current_tokens = count_tokens(current_chunk[0])
                    else:
                        current_chunk = []
                        current_tokens = 0

                current_chunk.append(para)
                current_tokens += para_tokens

        # Final chunk
        if current_chunk:
            chunk_text = "\n\n".join(current_chunk)
            chunks.append({
                "text": chunk_text,
                "section": section["section"],
                "subsection": section["subsection"],
            })

        return chunks

    def chunk(self, text: str) -> List[Dict]:
        """
        Main chunking method:
        1. Split by headings
        2. Split large sections
        3. Filter out tiny chunks
        """
        # Step 1: Hierarchical split
        sections = self.split_by_headings(text)

        # Step 2: Split large sections
        all_chunks = []
        for section in sections:
            sub_chunks = self.split_large_section(section)
            all_chunks.extend(sub_chunks)

        # Step 3: Filter out tiny chunks
        filtered_chunks = []
        for chunk in all_chunks:
            tokens = count_tokens(chunk["text"])
            if tokens >= self.min_chunk_tokens:
                chunk["tokens"] = tokens
                filtered_chunks.append(chunk)

        return filtered_chunks


def chunk_text(
    text: str,
    max_tokens: int = 500,
    overlap_tokens: int = 50,
) -> List[Dict]:
    """
    Chunk text into smaller pieces.

    Returns list of dicts with keys:
    - text: chunk content
    - section: heading name (or None)
    - subsection: sub-heading name (or None)
    - tokens: token count
    """
    chunker = HierarchicalChunker(
        max_tokens=max_tokens,
        overlap_tokens=overlap_tokens,
    )
    return chunker.chunk(text)


def chunk_document(
    doc_id: str,
    text: str,
    language: str = "en",
    max_tokens: int = 500,
) -> List[Dict]:
    """
    Chunk a document and return list of Chunk dicts (ready for NDJSON).

    Returns:
      [
        {
          "doc_id": "01HAR6DP...",
          "chunk_id": "01HAR6DP:a3f2bc1d",
          "chunk_hash": "a3f2bc1d",
          "chunk_index": 0,
          "text": "...",
          "tokens": 123,
          "section": "Introduction",
          "subsection": None,
          "modality": "text",
          "language": "de"
        },
        ...
      ]
    """
    # Chunk text
    chunks = chunk_text(text, max_tokens=max_tokens)

    # Build output dicts
    output_chunks = []
    for idx, chunk in enumerate(chunks):
        text_content = chunk["text"]
        chunk_hash = compute_chunk_hash(text_content)
        chunk_id = f"{doc_id}:{chunk_hash}"

        output_chunks.append({
            "doc_id": doc_id,
            "chunk_id": chunk_id,
            "chunk_hash": chunk_hash,
            "chunk_index": idx,
            "text": text_content,
            "tokens": chunk.get("tokens", count_tokens(text_content)),
            "section": chunk.get("section"),
            "subsection": chunk.get("subsection"),
            "modality": "text",
            "language": language,
        })

    return output_chunks
