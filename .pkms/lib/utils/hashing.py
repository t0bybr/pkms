"""Hashing utilities for content-addressable storage"""

import hashlib

# Try to import xxhash (faster), fallback to hashlib
try:
    import xxhash
    XXHASH_AVAILABLE = True
except ImportError:
    XXHASH_AVAILABLE = False


def compute_sha256(text: str) -> str:
    """
    Compute SHA256 hash of text.

    Returns: "sha256:{hex_digest}"
    """
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_chunk_hash(text: str) -> str:
    """
    Compute content-addressable hash for chunk ID.

    Uses xxhash64 if available (faster), otherwise SHA256.
    Returns first 12 hex chars.

    Example: "a3f2bc1d9e8f"
    """
    if XXHASH_AVAILABLE:
        h = xxhash.xxh64(text.encode("utf-8")).hexdigest()
        return h[:12]
    else:
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return h[:12]
