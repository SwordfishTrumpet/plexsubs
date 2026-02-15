"""Provider base class and interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class SubtitleResult:
    """Represents a found subtitle."""

    id: str
    language: str
    release: str
    filename: str
    download_url: Optional[str] = None
    download_params: Optional[dict] = None
    is_perfect_match: bool = False
    provider: str = ""
    score: float = 0.0
    download_count: int = 0

    def __repr__(self) -> str:
        return (
            f"SubtitleResult(id={self.id}, lang={self.language}, "
            f"perfect_match={self.is_perfect_match}, downloads={self.download_count})"
        )


class BaseProvider(ABC):
    """Abstract base class for subtitle providers."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.name = self.__class__.__name__.replace("Provider", "").lower()

    @abstractmethod
    def search(
        self,
        title: str,
        year: Optional[int] = None,
        imdb_id: Optional[str] = None,
        language: str = "nl",
        release_groups: Optional[list[str]] = None,
        filename: Optional[str] = None,
    ) -> tuple[list[SubtitleResult], Optional[str]]:
        """Search for subtitles.

        Args:
            title: Media title
            year: Release year
            imdb_id: IMDB identifier
            language: Language code (e.g., 'nl', 'en')
            release_groups: List of release group names for matching
            filename: Original media filename

        Returns:
            Tuple of (list of subtitle results, auth token if applicable)
        """
        pass

    @abstractmethod
    def download(
        self, subtitle: SubtitleResult, output_path: str, token: Optional[str] = None
    ) -> bool:
        """Download a subtitle.

        Args:
            subtitle: Subtitle result to download
            output_path: Path to save the subtitle file
            token: Authentication token if required

        Returns:
            True if successful, False otherwise
        """
        pass

    def is_available(self) -> bool:
        """Check if provider is available/enabled."""
        return self.enabled
