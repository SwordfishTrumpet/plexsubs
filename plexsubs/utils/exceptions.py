"""Custom exceptions for Plex Subtitle Webhook."""


class PlexSubtitleError(Exception):
    """Base exception for all errors."""

    pass


class ConfigurationError(PlexSubtitleError):
    """Configuration validation or loading error."""

    pass


class PlexAPIError(PlexSubtitleError):
    """Plex API communication error."""

    pass


class ProviderError(PlexSubtitleError):
    """Base exception for subtitle provider errors."""

    def __init__(self, message: str, provider: str = None):
        super().__init__(message)
        self.provider = provider


class OpenSubtitlesError(ProviderError):
    """OpenSubtitles API error."""

    def __init__(self, message: str):
        super().__init__(message, provider="opensubtitles")


class SubtitleNotFoundError(PlexSubtitleError):
    """Subtitle not found for media."""

    pass


class DownloadError(PlexSubtitleError):
    """Subtitle download failed."""

    pass


class LanguageDetectionError(PlexSubtitleError):
    """Language detection failed."""

    pass


class ReleaseMatchingError(PlexSubtitleError):
    """Release group matching failed."""

    pass
