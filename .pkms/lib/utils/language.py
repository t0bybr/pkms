"""Language detection utilities"""

# Try to import langdetect
try:
    from langdetect import detect, LangDetectException
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False
    detect = None
    LangDetectException = Exception


def detect_language(text: str, fallback: str = "en") -> str:
    """
    Auto-detect language from text.

    Returns ISO 639-1 code (de, en, fr, ...).
    Falls back to 'fallback' if detection fails or langdetect not installed.

    :param text: Text to analyze
    :param fallback: Fallback language code (default: "en")
    :returns: ISO 639-1 language code (2 chars, lowercase)
    """
    if not LANGDETECT_AVAILABLE:
        return fallback

    # Remove code blocks and check text length
    clean_text = text.strip()
    if len(clean_text) < 20:
        return fallback

    try:
        lang = detect(clean_text)
        # langdetect returns ISO 639-1 codes (de, en, fr, ...)
        return lang[:2].lower()
    except (LangDetectException, Exception):
        return fallback
