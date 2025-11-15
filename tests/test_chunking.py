"""Tests for chunking module"""

import pytest
from pkms.lib.chunking import chunk_document, chunk_text


class TestChunking:
    def test_chunk_simple_text(self):
        text = "This is a simple text without headings."
        chunks = chunk_text(text, max_tokens=100)

        assert len(chunks) >= 1
        assert "text" in chunks[0]
        assert "tokens" in chunks[0]

    def test_chunk_with_headings(self):
        text = """# Heading 1

Content for heading 1.

## Heading 2

Content for heading 2.
"""
        chunks = chunk_text(text, max_tokens=100)

        assert len(chunks) >= 2
        # Check that sections are tracked
        sections = [c.get("section") for c in chunks]
        assert any(s for s in sections)

    def test_chunk_document_returns_proper_format(self):
        doc_id = "01HABCDEF123456789"
        text = "Test content"

        chunks = chunk_document(doc_id, text, language="en")

        assert len(chunks) >= 1
        chunk = chunks[0]

        assert "doc_id" in chunk
        assert "chunk_id" in chunk
        assert "chunk_hash" in chunk
        assert "chunk_index" in chunk
        assert "text" in chunk
        assert "tokens" in chunk
        assert "language" in chunk

        assert chunk["doc_id"] == doc_id
        assert chunk["language"] == "en"
        assert ":" in chunk["chunk_id"]  # Format: doc_id:hash

    def test_chunk_hash_deterministic(self):
        doc_id = "01HABCDEF123456789"
        text = "Same text"

        chunks1 = chunk_document(doc_id, text)
        chunks2 = chunk_document(doc_id, text)

        assert chunks1[0]["chunk_hash"] == chunks2[0]["chunk_hash"]
