"""Centralized language code utilities using ISO 639 standards.

Uses iso639-lang library for comprehensive language support (184+ languages).
Includes minimal fallback for English language names since iso639 doesn't
accept them directly (e.g., 'dutch' -> 'nl').
"""

from iso639 import Lang
from iso639.exceptions import InvalidLanguageValue

# Minimal mapping for common English language names
# iso639 library only accepts codes, not names
_ENGLISH_NAME_MAP = {
    "dutch": "nl",
    "english": "en",
    "german": "de",
    "french": "fr",
    "spanish": "es",
    "italian": "it",
    "portuguese": "pt",
    "swedish": "sv",
    "norwegian": "no",
    "danish": "da",
    "finnish": "fi",
    "polish": "pl",
    "russian": "ru",
    "japanese": "ja",
    "korean": "ko",
    "chinese": "zh",
    "arabic": "ar",
    "hindi": "hi",
    "turkish": "tr",
    "czech": "cs",
    "hungarian": "hu",
    "romanian": "ro",
    "greek": "el",
    "hebrew": "he",
    "thai": "th",
    "indonesian": "id",
}


def _resolve_language_code(code_or_name: str) -> str:
    """Convert English name or code to ISO 639-1 code.

    Args:
        code_or_name: Language code or English name

    Returns:
        ISO 639-1 code or original string if unknown
    """
    normalized = code_or_name.lower().strip()

    # Check if it's a known English name
    if normalized in _ENGLISH_NAME_MAP:
        return _ENGLISH_NAME_MAP[normalized]

    return normalized


def get_allowed_languages(language: str) -> list[str]:
    """Get all allowed language codes for a given language.

    Returns ISO 639-1, ISO 639-2/T, ISO 639-2/B, and English name variants.

    Args:
        language: Language code or name (e.g., 'nl', 'nld', 'dutch')

    Returns:
        List of all valid codes for that language
    """
    # Resolve English names to codes first
    resolved = _resolve_language_code(language)

    try:
        lang = Lang(resolved)
        codes = [lang.pt1, lang.pt2t, lang.pt2b, lang.name.lower() if lang.name else None]
        return [c for c in codes if c]
    except InvalidLanguageValue:
        return [language.lower()]


def to_plex_language_code(language: str) -> str:
    """Convert language code to Plex format (ISO 639-2/T 3-letter code).

    Args:
        language: Language code (e.g., 'nl', 'en', 'dut')

    Returns:
        Plex-compatible 3-letter language code (ISO 639-2/T)
    """
    resolved = _resolve_language_code(language)

    try:
        lang = Lang(resolved)
        return lang.pt2t if lang.pt2t else resolved
    except InvalidLanguageValue:
        return language.lower()


def to_iso639_1(language: str) -> str | None:
    """Convert any language code to ISO 639-1 (2-letter code).

    Args:
        language: Language code (e.g., 'nl', 'nld', 'dut', 'dutch')

    Returns:
        ISO 639-1 2-letter code or None if not available
    """
    resolved = _resolve_language_code(language)

    try:
        lang = Lang(resolved)
        return lang.pt1
    except InvalidLanguageValue:
        return None


def verify_language_match(detected: str, expected: str) -> bool:
    """Check if detected language matches expected language.

    Args:
        detected: Detected language code (usually ISO 639-1 from langdetect)
        expected: Expected language code (from configuration)

    Returns:
        True if detected is in the allowed codes for expected
    """
    detected = detected.lower().strip()
    expected = expected.lower().strip()

    # Direct match
    if detected == expected:
        return True

    # Check if detected is in allowed codes for expected
    allowed = get_allowed_languages(expected)
    return detected in [a.lower() for a in allowed]


def normalize_language_code(code: str) -> str:
    """Normalize language code to ISO 639-1 standard.

    Args:
        code: Language code (e.g., 'dut', 'nld', 'dutch')

    Returns:
        Standard ISO 639-1 code (e.g., 'nl', 'en') or original if unknown
    """
    code = code.lower().strip()

    iso1 = to_iso639_1(code)
    if iso1:
        return iso1

    return code


def get_supported_languages() -> list[str]:
    """Get list of supported ISO 639-1 language codes.

    Returns all languages from the iso639 library that have 2-letter codes.
    """
    from iso639 import iter_langs

    return sorted([lang.pt1 for lang in iter_langs() if lang.pt1])


def is_valid_language(code: str) -> bool:
    """Check if a language code is valid.

    Args:
        code: Language code to validate

    Returns:
        True if the code is a valid language identifier
    """
    try:
        Lang(code.lower().strip())
        return True
    except InvalidLanguageValue:
        return False
