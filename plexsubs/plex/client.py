"""Plex API client with enhanced error handling and XML navigation."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import TYPE_CHECKING

from plexsubs.utils.exceptions import PlexAPIError
from plexsubs.utils.http_client import AuthenticatedHTTPClient
from plexsubs.utils.logging_config import get_logger
from plexsubs.utils.path_utils import apply_path_mappings
from plexsubs.utils.retry import retry_with_backoff
from plexsubs.utils.xml_utils import (
    MediaPartNavigator,
    find_imdb_id,
    find_player_element,
    find_session_element,
    find_subtitle_streams,
    find_video_element,
    parse_xml_response,
)

if TYPE_CHECKING:
    from plexsubs.config.settings import Settings

logger = get_logger(__name__)


@dataclass
class MediaInfo:
    """Media information from Plex."""

    rating_key: str
    title: str
    type: str  # 'movie' or 'episode'
    year: int | None = None
    imdb_id: str | None = None
    file_path: str | None = None


@dataclass
class SubtitleStream:
    """Subtitle stream information."""

    id: str
    language_code: str
    language: str
    codec: str
    selected: bool = False


@dataclass
class LibraryLocation:
    """Library location/path information."""

    id: str
    path: str


@dataclass
class LibrarySection:
    """Library section information."""

    key: str
    title: str
    type: str
    agent: str
    scanner: str
    language: str
    locations: list[LibraryLocation]


@dataclass
class PartStreamInfo:
    """Part ID and subtitle stream ID information."""

    part_id: str | None
    subtitle_id: str | None


class PlexClient(AuthenticatedHTTPClient):
    """Plex API client.

    Provides comprehensive access to Plex Server API for media metadata,
    subtitle management, and library operations.

    Attributes:
        path_mappings: Dictionary mapping Plex paths to local paths
    """

    def __init__(
        self,
        base_url: str,
        token: str,
        path_mappings: dict | None = None,
        **kwargs,
    ):
        """Initialize Plex client.

        Args:
            base_url: Plex server URL
            token: Plex authentication token
            path_mappings: Path mapping configuration
            **kwargs: Additional HTTP client options
        """
        super().__init__(
            base_url=base_url,
            token=token,
            auth_header_name="X-Plex-Token",
            auth_header_prefix="",
            verify_ssl=False,  # Plex uses self-signed certificates
            **kwargs,
        )
        self.path_mappings = path_mappings or {}

    @classmethod
    def from_settings(cls, settings: Settings) -> PlexClient:
        """Create a PlexClient instance from application settings.

        Args:
            settings: Application settings instance

        Returns:
            Configured PlexClient instance
        """
        return cls(
            base_url=settings.plex_url,
            token=settings.plex_token,
            path_mappings=settings.path_mappings,
        )

    def _map_path(self, file_path: str) -> str:
        """Apply path mappings to convert Plex path to local path."""
        return apply_path_mappings(file_path, self.path_mappings)

    def _get_part_stream_info(self, video: ET.Element, language_code: str) -> PartStreamInfo:
        """Extract part ID and subtitle stream ID from a video element.

        Uses the fluent XML navigator for clean traversal.

        Args:
            video: Video XML element
            language_code: Language code to search for

        Returns:
            PartStreamInfo containing part_id and subtitle_id (or None if not found)
        """
        # Use fluent navigator for clean traversal
        navigator = MediaPartNavigator(video)
        part_id = navigator.get_part_id()

        if not part_id:
            logger.warning("No part ID found in video element")
            return PartStreamInfo(part_id=None, subtitle_id=None)

        # Find subtitle stream within the Part element
        subtitle_id = None
        part_element = navigator.get_part_element()
        if part_element is not None:
            subtitle_id = self._find_subtitle_stream_id(part_element, language_code)

        return PartStreamInfo(part_id=part_id, subtitle_id=subtitle_id)

    def _find_subtitle_stream_id(self, part: ET.Element, language_code: str) -> str | None:
        """Find subtitle stream ID by language code within a Part element."""
        for stream in part.findall("Stream[@streamType='3']"):
            if stream.get("languageCode") == language_code:
                return stream.get("id")
        return None

    @retry_with_backoff(max_retries=3, exceptions=(PlexAPIError,))
    def get_media_info(self, rating_key: str) -> MediaInfo | None:
        """Get media information from Plex."""
        try:
            logger.debug(f"Fetching media info for rating key: {rating_key}")
            response = self.get(f"/library/metadata/{rating_key}")

            root = parse_xml_response(response.text)
            if root is None:
                raise PlexAPIError("Failed to parse Plex XML response")

            video = find_video_element(root)
            if video is None:
                logger.warning(f"No video element found for rating key: {rating_key}")
                return None

            media_type = video.get("type", "")
            title = video.get("title", "")

            # For episodes, use grandparent title (show name)
            if media_type == "episode":
                title = video.get("grandparentTitle", title)

            # Get IMDB ID
            imdb_id = find_imdb_id(root)

            # Get file path using fluent navigator
            navigator = MediaPartNavigator(video)
            file_path_raw = navigator.get_file_path()
            file_path = self._map_path(file_path_raw) if file_path_raw else None

            year_str = video.get("year")
            year = int(year_str) if year_str and year_str.isdigit() else None

            info = MediaInfo(
                rating_key=rating_key,
                title=title,
                type=media_type,
                year=year,
                imdb_id=imdb_id,
                file_path=file_path,
            )

            logger.info(f"Retrieved media info: {info.title} ({info.year}) - {info.type}")
            return info

        except Exception as e:
            logger.error(f"Failed to get media info: {e}")
            raise PlexAPIError(f"Failed to get media info: {e}")

    def get_subtitle_streams(self, rating_key: str) -> list[SubtitleStream]:
        """Get available subtitle streams for media."""
        try:
            response = self.get(f"/library/metadata/{rating_key}")

            root = parse_xml_response(response.text)
            if root is None:
                return []

            streams = []
            for stream in find_subtitle_streams(root):
                subtitle = SubtitleStream(
                    id=stream.get("id", ""),
                    language_code=stream.get("languageCode", ""),
                    language=stream.get("language", ""),
                    codec=stream.get("codec", ""),
                    selected=stream.get("selected", "0") == "1",
                )
                streams.append(subtitle)

            logger.debug(f"Found {len(streams)} subtitle streams")
            return streams

        except Exception as e:
            logger.error(f"Failed to get subtitle streams: {e}")
            return []

    def refresh_metadata(self, rating_key: str) -> bool:
        """Refresh Plex metadata to detect new subtitle files."""
        try:
            logger.info(f"Refreshing Plex metadata for rating key: {rating_key}")
            self.put(f"/library/metadata/{rating_key}/refresh")
            logger.info("Metadata refresh triggered successfully")
            return True

        except PlexAPIError as e:
            logger.error(f"Failed to refresh metadata: {e}")
            return False

    def _set_subtitle_by_part_id(
        self, part_id: str, subtitle_id: str, language_code: str, context: str = ""
    ) -> bool:
        """Set the subtitle stream for a specific part.

        Args:
            part_id: The part ID to set subtitle for
            subtitle_id: The subtitle stream ID to set
            language_code: Language code for logging
            context: Additional context for log messages (e.g., "active session")

        Returns:
            True if successful, False otherwise
        """
        self.put(f"/library/parts/{part_id}", params={"subtitleStreamID": subtitle_id})

        context_msg = f" ({context})" if context else ""
        logger.info(f"Set subtitle stream to {language_code} (ID: {subtitle_id}){context_msg}")
        return True

    def set_subtitle_stream(
        self,
        rating_key: str,
        language_code: str,
    ) -> bool:
        """Set the active subtitle stream."""
        try:
            # Get current streams
            response = self.get(f"/library/metadata/{rating_key}")

            root = parse_xml_response(response.text)
            if root is None:
                return False

            # Find video element
            video = find_video_element(root)
            if video is None:
                logger.warning("No video element found")
                return False

            # Get part and stream info
            info = self._get_part_stream_info(video, language_code)

            if not info.part_id:
                return False

            if not info.subtitle_id:
                logger.warning(f"No {language_code} subtitle stream found")
                return False

            # Set the subtitle stream
            return self._set_subtitle_by_part_id(info.part_id, info.subtitle_id, language_code)

        except PlexAPIError as e:
            logger.error(f"Failed to set subtitle stream: {e}")
            return False

    def get_active_sessions(self) -> list[dict]:
        """Get currently active playback sessions."""
        try:
            response = self.get("/status/sessions")

            root = parse_xml_response(response.text)
            if root is None:
                return []

            sessions = []
            for video in root.findall(".//Video"):
                session = find_session_element(video)
                if session is not None:
                    session_id = session.get("id")
                    if not session_id:
                        continue
                    player = find_player_element(video)
                    sessions.append(
                        {
                            "rating_key": video.get("ratingKey"),
                            "session_key": session_id,
                            "title": video.get("title"),
                            "player": player.get("title") if player is not None else None,
                        }
                    )

            return sessions

        except Exception as e:
            logger.error(f"Failed to get active sessions: {e}")
            return []

    def set_active_session_subtitle(
        self,
        rating_key: str,
        language_code: str,
    ) -> bool:
        """Set subtitle stream for an active playback session.

        This works during active playback, unlike set_subtitle_stream which only
        sets the default for future plays.
        """
        try:
            # Get active sessions
            sessions = self.get_active_sessions()

            # Find session for this rating key
            target_session = None
            for session in sessions:
                if session["rating_key"] == rating_key:
                    target_session = session
                    break

            if not target_session:
                logger.debug(f"No active session found for rating key {rating_key}")
                return False

            # Get session details to find subtitle streams
            response = self.get("/status/sessions")

            root = parse_xml_response(response.text)
            if root is None:
                return False

            # Find the video in sessions
            for video in root.findall(".//Video"):
                if video.get("ratingKey") == rating_key:
                    # Find the Player element
                    player = find_player_element(video)
                    if player is None:
                        logger.warning("No player found in session")
                        return False

                    machine_identifier = player.get("machineIdentifier")
                    if not machine_identifier:
                        logger.warning("No machine identifier found")
                        return False

                    # Get part and stream info using shared helper
                    info = self._get_part_stream_info(video, language_code)

                    if not info.part_id:
                        logger.warning("No part ID found in session")
                        return False

                    if not info.subtitle_id:
                        logger.debug(f"No {language_code} subtitle stream found in active session")
                        return False

                    # Set the subtitle using the shared helper
                    return self._set_subtitle_by_part_id(
                        info.part_id, info.subtitle_id, language_code, context="active session"
                    )

            return False

        except PlexAPIError as e:
            logger.error(f"Failed to set active session subtitle: {e}")
            return False

    @retry_with_backoff(max_retries=3, exceptions=(PlexAPIError,))
    def get_library_sections(self) -> list[LibrarySection]:
        """Get all library sections with their configured paths from Plex."""
        logger.debug("Fetching library sections from Plex")
        response = self.get("/library/sections")

        root = parse_xml_response(response.text)
        if root is None:
            raise PlexAPIError("Failed to parse Plex library XML response")

        libraries = []

        for directory in root.findall(".//Directory"):
            # Extract locations for this library
            locations = []
            for location in directory.findall("Location"):
                loc = LibraryLocation(
                    id=location.get("id", ""),
                    path=location.get("path", ""),
                )
                locations.append(loc)

            library = LibrarySection(
                key=directory.get("key", ""),
                title=directory.get("title", ""),
                type=directory.get("type", ""),
                agent=directory.get("agent", ""),
                scanner=directory.get("scanner", ""),
                language=directory.get("language", ""),
                locations=locations,
            )
            libraries.append(library)

        logger.info(f"Retrieved {len(libraries)} library sections from Plex")
        return libraries
