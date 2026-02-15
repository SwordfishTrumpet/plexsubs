"""Core module exports."""

from plexsubs.core.discovery import PathDiscovery
from plexsubs.core.language_detector import (
    detect_subtitle_language,
    verify_language,
)
from plexsubs.core.release_matcher import (
    calculate_match_score,
    extract_release_info,
)
from plexsubs.core.subtitle_manager import SubtitleManager

__all__ = [
    "SubtitleManager",
    "PathDiscovery",
    "extract_release_info",
    "calculate_match_score",
    "detect_subtitle_language",
    "verify_language",
]
