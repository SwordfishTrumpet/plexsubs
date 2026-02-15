"""Utils module exports."""

from plexsubs.utils.exceptions import (
    ConfigurationError,
    DownloadError,
    LanguageDetectionError,
    OpenSubtitlesError,
    PlexAPIError,
    PlexSubtitleError,
    ProviderError,
    ReleaseMatchingError,
    SubtitleNotFoundError,
)
from plexsubs.utils.http_client import AuthenticatedHTTPClient, BaseHTTPClient
from plexsubs.utils.logging_config import get_logger, setup_logging

__all__ = [
    # Exceptions
    "PlexSubtitleError",
    "ConfigurationError",
    "PlexAPIError",
    "ProviderError",
    "OpenSubtitlesError",
    "SubtitleNotFoundError",
    "DownloadError",
    "LanguageDetectionError",
    "ReleaseMatchingError",
    # HTTP Client
    "BaseHTTPClient",
    "AuthenticatedHTTPClient",
    # Logging
    "get_logger",
    "setup_logging",
]
