"""Language detection utility using simple heuristics."""

import re
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class Language(str, Enum):
    """Supported languages for detection."""

    ENGLISH = "en"
    GERMAN = "de"
    FRENCH = "fr"
    SPANISH = "es"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    DUTCH = "nl"
    POLISH = "pl"
    RUSSIAN = "ru"
    JAPANESE = "ja"
    CHINESE = "zh"
    KOREAN = "ko"
    ARABIC = "ar"
    TURKISH = "tr"
    CZECH = "cs"
    DANISH = "da"
    SWEDISH = "sv"
    NORWEGIAN = "no"
    UNKNOWN = "unknown"


def detect_language(text: str) -> Language:
    """Detect language of text using character-based heuristics.

    Args:
        text: Text to analyze.

    Returns:
        Language enum value.
    """
    if not text or len(text.strip()) < 5:
        return Language.UNKNOWN

    text_lower = text.lower()

    # Japanese detection (hiragana, katakana, kanji) - check first as CJK overlaps with Chinese
    if re.search(r"[\u3040-\u309F\u30A0-\u30FF]", text):
        return Language.JAPANESE

    # Chinese detection (CJK unified ideographs without Japanese kana)
    if re.search(r"[\u4E00-\u9FFF]", text) and not re.search(r"[\u3040-\u309F\u30A0-\u30FF]", text):
        return Language.CHINESE

    # Korean detection (Hangul)
    if re.search(r"[\uAC00-\uD7AF]", text):
        return Language.KOREAN

    # Russian detection (Cyrillic)
    if re.search(r"[\u0400-\u04FF]", text):
        return Language.RUSSIAN

    # Arabic detection
    if re.search(r"[\u0600-\u06FF]", text):
        return Language.ARABIC

    # German detection (umlauts are strong signal, common words add confidence)
    has_german_chars = any(char in text for char in ["ä", "ö", "ü", "ß"])
    has_german_words = any(word in text_lower for word in ["der ", "die ", "das ", "und ", "ist ", "eine "])
    if has_german_chars or (has_german_words and len(text) > 20):
        return Language.GERMAN

    # French detection (specific accents are strong signal, common words need confirmation)
    has_french_specific_chars = any(char in text for char in ["è", "ê", "à", "ù", "ç"])
    has_french_e_accent = "é" in text
    has_french_words = any(word in text_lower for word in ["le ", "la ", "les ", "et ", "vous ", "un ", "une "])
    # Need either specific French chars, or é + common French words
    if has_french_specific_chars or (has_french_e_accent and has_french_words):
        return Language.FRENCH

    # Spanish detection (ñ is unique to Spanish, certain accents with common words)
    has_spanish_unique = "ñ" in text_lower
    has_spanish_accents = any(char in text for char in ["á", "í", "ó", "ú"])
    has_spanish_words = any(word in text_lower for word in ["el ", "la ", "los ", "las ", "está ", "parámetro"])
    if has_spanish_unique or (has_spanish_accents and has_spanish_words):
        return Language.SPANISH

    # Default to English if no other patterns match
    return Language.ENGLISH


def is_english(text: str) -> bool:
    """Check if text is English.

    Args:
        text: Text to check.

    Returns:
        True if text is detected as English.
    """
    return detect_language(text) == Language.ENGLISH
