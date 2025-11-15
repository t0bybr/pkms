"""Token counting utilities"""

# Try to import tiktoken for accurate token counting
try:
    import tiktoken
    _tokenizer = tiktoken.get_encoding("cl100k_base")  # GPT-4 encoding
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    _tokenizer = None


def count_tokens(text: str, model: str = "gpt-4") -> int:
    """
    Count tokens in text.

    Uses tiktoken if available (accurate for GPT models),
    otherwise falls back to word count * 1.3 (rough estimate).

    :param text: Text to count tokens for
    :param model: Model name (currently ignored, uses cl100k_base)
    :returns: Token count (int)
    """
    if TIKTOKEN_AVAILABLE and _tokenizer:
        return len(_tokenizer.encode(text))
    else:
        # Fallback: word count * 1.3 (rough estimate)
        return int(len(text.split()) * 1.3)


def estimate_tokens_from_chars(char_count: int) -> int:
    """
    Rough estimate of tokens from character count.

    Rule of thumb: ~4 chars per token for English, ~2-3 for code.
    Using 3.5 as average.

    :param char_count: Number of characters
    :returns: Estimated token count
    """
    return int(char_count / 3.5)
