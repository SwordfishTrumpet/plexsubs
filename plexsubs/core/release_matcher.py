"""Release group extraction and matching."""

from guessit import guessit

from plexsubs.utils.logging_config import get_logger

logger = get_logger(__name__)


def extract_release_info(filename: str) -> list[str]:
    """Extract release group and quality info from filename using guessit.

    Args:
        filename: Media filename

    Returns:
        List of release info strings
    """
    try:
        result = guessit(filename)
        release_info = []

        # Get release group
        if result.get("release_group"):
            release_info.append(result["release_group"].upper())

        # Get screen size (1080p, 720p, etc.)
        if result.get("screen_size"):
            release_info.append(result["screen_size"].upper())

        # Get source (WEB-DL, BluRay, etc.)
        if result.get("source"):
            source = result["source"]
            if isinstance(source, list):
                release_info.extend([s.upper() for s in source])
            else:
                release_info.append(source.upper())

        # Get video codec
        if result.get("video_codec"):
            release_info.append(result["video_codec"].upper())

        # Remove duplicates while preserving order
        seen = set()
        unique_info = []
        for item in release_info:
            if item not in seen:
                seen.add(item)
                unique_info.append(item)

        logger.debug(f"Extracted release info: {unique_info}")
        return unique_info

    except Exception as e:
        logger.warning(f"Failed to extract release info from '{filename}': {e}")
        return []


def calculate_match_score(
    subtitle_release: str, subtitle_filename: str, media_release_groups: list[str]
) -> tuple:
    """Calculate how well a subtitle matches the media release.

    Args:
        subtitle_release: Release name from subtitle
        subtitle_filename: Filename from subtitle
        media_release_groups: Release groups from media filename

    Returns:
        Tuple of (score, is_perfect_match)
    """
    if not media_release_groups:
        return 0.0, False

    combined = f"{subtitle_release} {subtitle_filename}".upper()

    matches = 0
    for group in media_release_groups:
        if group.upper() in combined:
            matches += 1

    # Perfect match if all release groups found
    score = matches / len(media_release_groups) if media_release_groups else 0.0
    is_perfect = matches == len(media_release_groups) and matches > 0

    return score, is_perfect
