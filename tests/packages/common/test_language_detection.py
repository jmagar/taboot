"""Tests for language detection."""

import pytest

from packages.common.language_detection import Language, detect_language, is_english


def test_detect_german() -> None:
    """Should detect German text."""
    text = "Er erhält den Tool-Namen und Eingabeparameter"
    assert detect_language(text) == Language.GERMAN


def test_detect_german_with_umlauts() -> None:
    """Should detect German text with umlauts."""
    text = "Die Größe der Dateien überschreitet das Maximum"
    assert detect_language(text) == Language.GERMAN


def test_detect_french() -> None:
    """Should detect French text."""
    text = "Voici les paramètres de la requête"
    assert detect_language(text) == Language.FRENCH


def test_detect_spanish() -> None:
    """Should detect Spanish text."""
    text = "El parámetro está configurado correctamente"
    assert detect_language(text) == Language.SPANISH


def test_detect_english() -> None:
    """Should detect English text."""
    text = "The parameter is configured correctly"
    assert detect_language(text) == Language.ENGLISH


def test_detect_japanese() -> None:
    """Should detect Japanese text."""
    text = "これは日本語のテキストです"
    assert detect_language(text) == Language.JAPANESE


def test_detect_chinese() -> None:
    """Should detect Chinese text."""
    text = "这是中文文本"
    assert detect_language(text) == Language.CHINESE


def test_detect_korean() -> None:
    """Should detect Korean text."""
    text = "이것은 한국어 텍스트입니다"
    assert detect_language(text) == Language.KOREAN


def test_detect_russian() -> None:
    """Should detect Russian text."""
    text = "Это русский текст"
    assert detect_language(text) == Language.RUSSIAN


def test_detect_arabic() -> None:
    """Should detect Arabic text."""
    text = "هذا نص عربي"
    assert detect_language(text) == Language.ARABIC


def test_is_english() -> None:
    """is_english should return correct boolean."""
    assert is_english("This is English text")
    assert not is_english("Dies ist deutscher Text")


def test_is_english_with_french() -> None:
    """is_english should return False for French text."""
    assert not is_english("Voici un texte français")


def test_short_text_returns_unknown() -> None:
    """Very short text should return UNKNOWN."""
    assert detect_language("a") == Language.UNKNOWN
    assert detect_language("") == Language.UNKNOWN
    assert detect_language("  ") == Language.UNKNOWN


def test_medium_length_text_returns_unknown() -> None:
    """Very short text (< 5 chars) should return UNKNOWN."""
    assert detect_language("hi") == Language.UNKNOWN


def test_english_default_fallback() -> None:
    """Should default to English for ambiguous text without special characters."""
    text = "This is a simple test without any special characters or accents"
    assert detect_language(text) == Language.ENGLISH


def test_mixed_content_prioritizes_special_chars() -> None:
    """Should detect language based on special characters even with English words."""
    german_with_english = "The Größe is important für this test"
    assert detect_language(german_with_english) == Language.GERMAN
