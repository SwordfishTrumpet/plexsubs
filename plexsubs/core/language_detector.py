"""Language detection for subtitle verification."""

import re
from typing import Optional

from langdetect import detect

from plexsubs.utils.language_codes import verify_language_match
from plexsubs.utils.logging_config import get_logger

logger = get_logger(__name__)


def detect_subtitle_language(file_path: str) -> Optional[str]:
    """Detect the actual language of a subtitle file.

    Args:
        file_path: Path to subtitle file

    Returns:
        Detected language code or None if detection failed
    """
    try:
        # Read subtitle file
        with open(file_path, encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Clean text for detection
        text = _clean_subtitle_text(content)

        if len(text) < 50:
            logger.debug("Not enough text for language detection")
            return None

        detected = detect(text)
        logger.debug(f"Detected language: {detected}")
        return detected

    except Exception as e:
        logger.warning(f"Language detection failed: {e}")
        return None


def _clean_subtitle_text(content: str) -> str:
    """Clean subtitle content for language detection.

    Removes timing info, subtitle numbers, and HTML tags.
    """
    # Remove subtitle indices (lines that are just numbers)
    text = re.sub(r"^\d+$", "", content, flags=re.MULTILINE)

    # Remove timing lines (00:00:00,000 --> 00:00:00,000)
    text = re.sub(r"\d{2}:\d{2}:\d{2},\d{3}\s*--\u003e\s*\d{2}:\d{2}:\d{2},\d{3}", "", text)

    # Remove HTML tags
    text = re.sub(r"<[^\u003e]+>", "", text)

    # Clean up whitespace
    text = " ".join(text.split())

    return text


def verify_language(file_path: str, expected_language: str) -> bool:
    """Verify that a subtitle file matches the expected language.

    Args:
        file_path: Path to subtitle file
        expected_language: Expected language code (e.g., 'nl', 'en')

    Returns:
        True if language matches or detection unavailable, False otherwise
    """
    detected = detect_subtitle_language(file_path)

    if not detected:
        # Can't verify, assume it's correct
        return True

    if not verify_language_match(detected, expected_language):
        logger.warning(f"Language mismatch! Expected {expected_language}, got {detected}")
        return False

    logger.info(f"Language verified: {detected}")
    return True
