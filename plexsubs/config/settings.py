"""Pydantic settings with environment variable support."""

from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from plexsubs.config.validators import (
    parse_language_codes,
    validate_log_level,
    validate_token,
    validate_url,
)
from plexsubs.utils.constants import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_PATH_MAPPINGS,
    DEFAULT_RETRY_DELAY_SECONDS,
)
from plexsubs.utils.path_utils import parse_path_mappings


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Plex settings
    plex_url: str = Field(
        default="http://localhost:32400",
        alias="PLEX_URL",
        description="Plex server URL",
    )
    plex_token: str = Field(alias="PLEX_TOKEN", description="Plex authentication token")

    # OpenSubtitles settings
    opensubtitles_username: str = Field(
        alias="OPENSUBTITLES_USERNAME", description="OpenSubtitles username"
    )
    opensubtitles_password: str = Field(
        alias="OPENSUBTITLES_PASSWORD", description="OpenSubtitles password"
    )
    opensubtitles_api_key: str = Field(
        alias="OPENSUBTITLES_API_KEY", description="OpenSubtitles API key (required)"
    )

    # Subtitle settings
    subtitles_languages: str = Field(
        default="en",
        alias="SUBTITLES_LANGUAGES",
        description="Comma-separated list of ISO 639-1 language codes (e.g., 'en,nl,de')",
    )
    subtitles_auto_select: bool = Field(default=True, alias="SUBTITLES_AUTO_SELECT")
    subtitles_use_release_matching: bool = Field(
        default=True, alias="SUBTITLES_USE_RELEASE_MATCHING"
    )
    subtitles_upgrade_on_perfect_match: bool = Field(
        default=True, alias="SUBTITLES_UPGRADE_ON_PERFECT_MATCH"
    )
    subtitles_upgrade_on_popular: bool = Field(
        default=True,
        alias="SUBTITLES_UPGRADE_ON_POPULAR",
        description=(
            "Upgrade existing subtitles if a more popular version is found "
            "(no perfect match required)"
        ),
    )
    subtitles_popular_download_threshold: int = Field(
        default=100,
        alias="SUBTITLES_POPULAR_DOWNLOAD_THRESHOLD",
        description="Minimum download count to consider a subtitle 'popular' for upgrades",
    )
    subtitles_max_retries: int = Field(default=DEFAULT_MAX_RETRIES, alias="SUBTITLES_MAX_RETRIES")
    subtitles_retry_delay_seconds: int = Field(
        default=DEFAULT_RETRY_DELAY_SECONDS, alias="SUBTITLES_RETRY_DELAY_SECONDS"
    )

    # Server settings
    server_host: str = Field(default="0.0.0.0", alias="SERVER_HOST")
    server_port: int = Field(default=9000, alias="SERVER_PORT")
    server_webhook_path: str = Field(default="/plexsubs", alias="SERVER_WEBHOOK_PATH")
    server_debug: bool = Field(default=False, alias="SERVER_DEBUG")

    # Logging settings
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_use_colors: bool = Field(default=True, alias="LOG_USE_COLORS")
    log_json_format: bool = Field(default=False, alias="LOG_JSON_FORMAT")
    log_file: Optional[str] = Field(default=None, alias="LOG_FILE")

    # Discovery settings
    discovery_enabled: bool = Field(
        default=True,
        alias="DISCOVERY_ENABLED",
        description="Enable library discovery and path validation endpoints",
    )
    discovery_validate_on_startup: bool = Field(
        default=False,
        alias="DISCOVERY_VALIDATE_ON_STARTUP",
        description="Run path validation on startup (useful for debugging)",
    )
    discovery_test_file: Optional[str] = Field(
        default=None,
        alias="DISCOVERY_TEST_FILE",
        description="Specific file path to use for validation testing",
    )

    # Path mappings
    plex_path_mappings: Optional[str] = Field(
        default=None,
        alias="PLEX_PATH_MAPPINGS",
        description="Path mappings in format '/plex/path:/local/path,/plex2:/local2'",
    )

    # Internal path mappings storage
    _path_mappings: dict[str, str] = {}

    def model_post_init(self, __context) -> None:
        """Load path mappings after initialization."""
        if self.plex_path_mappings:
            self._path_mappings = parse_path_mappings(self.plex_path_mappings)
        else:
            # Default mapping for common Docker setups
            self._path_mappings = DEFAULT_PATH_MAPPINGS.copy()

    @property
    def path_mappings(self) -> dict[str, str]:
        """Get path mappings."""
        return self._path_mappings

    @property
    def languages_list(self) -> list[str]:
        """Get list of configured language codes."""
        return parse_language_codes(self.subtitles_languages)

    @field_validator("plex_url")
    @classmethod
    def validate_plex_url(cls, v: str) -> str:
        """Validate Plex URL format."""
        return validate_url(v, field_name="PLEX_URL")

    @field_validator("plex_token")
    @classmethod
    def validate_plex_token(cls, v: str) -> str:
        """Validate Plex token."""
        return validate_token(v, field_name="PLEX_TOKEN")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        return validate_log_level(v)


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment."""
    global _settings
    _settings = Settings()
    return _settings
