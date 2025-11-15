"""Tests for utility modules"""

import pytest
from pkms.lib.utils import (
    compute_sha256,
    compute_chunk_hash,
    detect_language,
    count_tokens,
)


class TestHashing:
    def test_sha256_format(self):
        result = compute_sha256("test")
        assert result.startswith("sha256:")
        assert len(result) == 71  # "sha256:" + 64 hex chars

    def test_sha256_deterministic(self):
        h1 = compute_sha256("pizza")
        h2 = compute_sha256("pizza")
        assert h1 == h2

    def test_sha256_different_inputs(self):
        h1 = compute_sha256("pizza")
        h2 = compute_sha256("pasta")
        assert h1 != h2

    def test_chunk_hash_format(self):
        result = compute_chunk_hash("test")
        assert len(result) == 12
        assert all(c in "0123456789abcdef" for c in result)

    def test_chunk_hash_deterministic(self):
        h1 = compute_chunk_hash("pizza")
        h2 = compute_chunk_hash("pizza")
        assert h1 == h2

    def test_chunk_hash_different_inputs(self):
        h1 = compute_chunk_hash("pizza")
        h2 = compute_chunk_hash("pasta")
        assert h1 != h2


class TestLanguage:
    def test_detect_german(self):
        text = "Das ist ein deutscher Text mit mehreren Wörtern."
        lang = detect_language(text)
        assert lang == "de"

    def test_detect_english(self):
        text = "This is an English text with several words."
        lang = detect_language(text)
        assert lang == "en"

    def test_short_text_fallback(self):
        text = "Hi"
        lang = detect_language(text, fallback="fr")
        assert lang == "fr"

    def test_empty_text_fallback(self):
        text = ""
        lang = detect_language(text, fallback="de")
        assert lang == "de"


class TestTokens:
    def test_count_tokens_positive(self):
        text = "Hello world, this is a test."
        tokens = count_tokens(text)
        assert tokens > 0
        assert isinstance(tokens, int)

    def test_count_tokens_empty(self):
        text = ""
        tokens = count_tokens(text)
        assert tokens == 0

    def test_count_tokens_deterministic(self):
        text = "Pizza bei 300°C"
        t1 = count_tokens(text)
        t2 = count_tokens(text)
        assert t1 == t2

    def test_count_tokens_scales(self):
        short = "Hello"
        long = "Hello " * 100
        assert count_tokens(long) > count_tokens(short)
