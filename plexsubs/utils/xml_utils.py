"""XML parsing utilities for Plex API responses.

Provides utilities for parsing and navigating Plex XML responses,
including a fluent navigator API for clean traversal of Video → Media → Part hierarchy.
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Optional

from plexsubs.utils.logging_config import get_logger

logger = get_logger(__name__)


def parse_xml_response(response_text: str) -> Optional[ET.Element]:
    """Parse XML response text into an ElementTree root.

    Args:
        response_text: XML response text from Plex API

    Returns:
        Root Element or None if parsing fails
    """
    try:
        return ET.fromstring(response_text)
    except ET.ParseError as e:
        logger.error(f"Failed to parse XML response: {e}")
        return None


def find_video_element(root: ET.Element) -> Optional[ET.Element]:
    """Find the Video element in a Plex metadata response.

    Args:
        root: Root XML element

    Returns:
        Video element or None if not found
    """
    return root.find(".//Video")


def find_media_element(video: ET.Element) -> Optional[ET.Element]:
    """Find the Media element within a Video element.

    Args:
        video: Video XML element

    Returns:
        Media element or None if not found
    """
    return video.find("Media")


def find_part_element(media: ET.Element) -> Optional[ET.Element]:
    """Find the Part element within a Media element.

    Args:
        media: Media XML element

    Returns:
        Part element or None if not found
    """
    return media.find("Part")


def find_subtitle_streams(root: ET.Element) -> list[ET.Element]:
    """Find all subtitle stream elements in a response.

    Args:
        root: Root XML element

    Returns:
        List of Stream elements with streamType='3'
    """
    return root.findall(".//Stream[@streamType='3']")


def find_imdb_id(root: ET.Element) -> Optional[str]:
    """Extract IMDB ID from a metadata response.

    Args:
        root: Root XML element

    Returns:
        IMDB ID without prefix or None if not found
    """
    for guid in root.findall(".//Guid"):
        guid_id = guid.get("id", "")
        if guid_id.startswith("imdb://"):
            return guid_id.replace("imdb://", "")
    return None


def find_player_element(video: ET.Element) -> Optional[ET.Element]:
    """Find the Player element within a Video element.

    Args:
        video: Video XML element from session

    Returns:
        Player element or None if not found
    """
    return video.find("Player")


def find_session_element(video: ET.Element) -> Optional[ET.Element]:
    """Find the Session element within a Video element.

    Args:
        video: Video XML element from session

    Returns:
        Session element or None if not found
    """
    return video.find("Session")


@dataclass
class MediaPartData:
    """Data extracted from a Video → Media → Part hierarchy.

    Attributes:
        file_path: The file path attribute from the Part element
        part_id: The ID attribute from the Part element
        media_element: The Media element (for advanced use)
        part_element: The Part element (for subtitle stream extraction)
    """

    file_path: Optional[str] = None
    part_id: Optional[str] = None
    media_element: Optional[ET.Element] = None
    part_element: Optional[ET.Element] = None


class MediaPartNavigator:
    """Fluent navigator for Video → Media → Part XML hierarchy.

    This class eliminates the repetitive null-check pattern when traversing
    Plex XML responses. It provides a clean, chainable API for extracting
    data from the media hierarchy.

    Example:
        navigator = MediaPartNavigator(video_element)
        file_path = navigator.get_file_path()
        part_id = navigator.get_part_id()

        # Or get all data at once
        data = navigator.get_all_data()
        if data.file_path:
            process_file(data.file_path)
    """

    def __init__(self, video: ET.Element):
        """Initialize navigator with a Video element.

        Args:
            video: The Video XML element to navigate
        """
        self.video = video
        self._media: Optional[ET.Element] = None
        self._part: Optional[ET.Element] = None
        self._initialized = False

    def _initialize(self) -> None:
        """Lazy initialization - traverse the hierarchy once."""
        if self._initialized:
            return

        self._media = find_media_element(self.video)
        if self._media is not None:
            self._part = find_part_element(self._media)

        self._initialized = True

    def get_media_element(self) -> Optional[ET.Element]:
        """Get the Media element.

        Returns:
            Media element or None if not found
        """
        self._initialize()
        return self._media

    def get_part_element(self) -> Optional[ET.Element]:
        """Get the Part element.

        Returns:
            Part element or None if not found
        """
        self._initialize()
        return self._part

    def get_file_path(self) -> Optional[str]:
        """Extract file path from the Part element.

        Returns:
            File path or None if not found
        """
        self._initialize()
        if self._part is None:
            return None
        return self._part.get("file")

    def get_part_id(self) -> Optional[str]:
        """Extract part ID from the Part element.

        Returns:
            Part ID or None if not found
        """
        self._initialize()
        if self._part is None:
            return None
        return self._part.get("id")

    def get_all_data(self) -> MediaPartData:
        """Get all available data from the hierarchy.

        Returns:
            MediaPartData with all extracted information
        """
        self._initialize()
        return MediaPartData(
            file_path=self._part.get("file") if self._part else None,
            part_id=self._part.get("id") if self._part else None,
            media_element=self._media,
            part_element=self._part,
        )

    def has_media(self) -> bool:
        """Check if Media element exists.

        Returns:
            True if Media element is present
        """
        self._initialize()
        return self._media is not None

    def has_part(self) -> bool:
        """Check if Part element exists.

        Returns:
            True if Part element is present
        """
        self._initialize()
        return self._part is not None


def get_file_path_from_video(video: ET.Element) -> Optional[str]:
    """Extract file path from a Video element.

    This is a convenience function that uses MediaPartNavigator internally.

    Args:
        video: Video XML element

    Returns:
        File path or None if not found
    """
    return MediaPartNavigator(video).get_file_path()


def get_part_id_from_video(video: ET.Element) -> Optional[str]:
    """Extract part ID from a Video element.

    This is a convenience function that uses MediaPartNavigator internally.

    Args:
        video: Video XML element

    Returns:
        Part ID or None if not found
    """
    return MediaPartNavigator(video).get_part_id()
