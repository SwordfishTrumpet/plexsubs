"""Reusable configuration validators.

Provides validation functions that can be used across the application
for consistent configuration validation.
"""

import re
from typing import Any

from plexsubs.utils.language_codes import get_supported_languages
from plexsubs.utils.logging_config import get_logger

logger = get_logger(__name__)

# Get valid ISO 639-1 language codes
VALID_ISO639_1_CODES = set(get_supported_languages())


def validate_url(url: str, field_name: str = "url") -> str:
    """Validate a URL.

    Args:
        url: URL to validate
        field_name: Name of the field for error messages

    Returns:
        Validated URL

    Raises:
        ValueError: If URL is invalid
    """
    if not url:
        raise ValueError(f"{field_name} is required")

    if not url.startswith(("http://", "https://")):
        raise ValueError(f"{field_name} must start with http:// or https://")

    return url


def validate_token(token: str, field_name: str = "token", min_length: int = 10) -> str:
    """Validate an authentication token.

    Args:
        token: Token to validate
        field_name: Name of the field for error messages
        min_length: Minimum required length

    Returns:
        Validated token

    Raises:
        ValueError: If token is invalid
    """
    if not token:
        raise ValueError(f"{field_name} is required")

    if len(token) < min_length:
        raise ValueError(f"{field_name} must be at least {min_length} characters")

    return token


def validate_language_code(code: str) -> str:
    """Validate a single language code.

    Args:
        code: ISO 639-1 language code to validate

    Returns:
        Normalized (lowercase) language code

    Raises:
        ValueError: If language code is invalid
    """
    code = code.strip().lower()

    if not code:
        raise ValueError("Language code cannot be empty")

    if code not in VALID_ISO639_1_CODES:
        raise ValueError(f"Invalid language code: {code}")

    return code


def validate_language_codes(languages: list[str]) -> list[str]:
    """Validate a list of language codes.

    Args:
        languages: List of ISO 639-1 language codes

    Returns:
        List of normalized language codes

    Raises:
        ValueError: If any language code is invalid
    """
    if not languages:
        raise ValueError("At least one language code is required")

    validated = []
    for lang in languages:
        try:
            validated.append(validate_language_code(lang))
        except ValueError as e:
            raise ValueError(f"Invalid language in list: {e}")

    return validated


def parse_language_codes(value: str | None) -> list[str]:
    """Parse comma-separated language codes.

    Args:
        value: Comma-separated language codes string

    Returns:
        List of valid ISO 639-1 codes

    Note:
        Empty/malformed entries are filtered out.
        Default: ["en"]
    """
    if not value or not value.strip():
        return ["en"]

    languages = []
    for lang in value.split(","):
        lang = lang.strip().lower()
        if lang and lang in VALID_ISO639_1_CODES:
            languages.append(lang)

    return languages if languages else ["en"]


def validate_port(port: int, field_name: str = "port") -> int:
    """Validate a port number.

    Args:
        port: Port number to validate
        field_name: Name of the field for error messages

    Returns:
        Validated port number

    Raises:
        ValueError: If port is invalid
    """
    if not isinstance(port, int):
        try:
            port = int(port)
        except (ValueError, TypeError):
            raise ValueError(f"{field_name} must be a valid integer")

    if port < 1 or port > 65535:
        raise ValueError(f"{field_name} must be between 1 and 65535")

    return port


def validate_positive_integer(value: Any, field_name: str = "value") -> int:
    """Validate a positive integer.

    Args:
        value: Value to validate
        field_name: Name of the field for error messages

    Returns:
        Validated integer

    Raises:
        ValueError: If value is not a positive integer
    """
    if not isinstance(value, int):
        try:
            value = int(value)
        except (ValueError, TypeError):
            raise ValueError(f"{field_name} must be a valid integer")

    if value < 1:
        raise ValueError(f"{field_name} must be a positive integer")

    return value


def validate_path_mappings(value: str | None) -> dict[str, str]:
    """Validate and parse path mappings string.

    Args:
        value: Path mappings string in format '/plex:/local,/plex2:/local2'

    Returns:
        Dictionary of path mappings

    Raises:
        ValueError: If format is invalid
    """
    if not value:
        return {}

    mappings = {}
    for mapping in value.split(","):
        mapping = mapping.strip()
        if not mapping:
            continue

        if ":" not in mapping:
            raise ValueError(f"Invalid path mapping format: {mapping}")

        parts = mapping.split(":", 1)
        src = parts[0].strip()
        dst = parts[1].strip()

        if not src or not dst:
            raise ValueError(f"Invalid path mapping (empty path): {mapping}")

        mappings[src] = dst

    return mappings


def validate_log_level(level: str) -> str:
    """Validate a log level.

    Args:
        level: Log level string

    Returns:
        Normalized (uppercase) log level

    Raises:
        ValueError: If log level is invalid
    """
    valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

    level = level.upper().strip()

    if level not in valid_levels:
        raise ValueError(f"Invalid log level: {level}. Must be one of: {', '.join(valid_levels)}")

    return level


def validate_boolean(value: Any, field_name: str = "value") -> bool:
    """Validate and convert a boolean value.

    Handles various boolean representations (bool, string, int).

    Args:
        value: Value to validate
        field_name: Name of the field for error messages

    Returns:
        Boolean value

    Raises:
        ValueError: If value cannot be converted to boolean
    """
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        value_lower = value.lower().strip()
        if value_lower in ("true", "1", "yes", "on"):
            return True
        if value_lower in ("false", "0", "no", "off"):
            return False
        raise ValueError(f"{field_name} must be a boolean value")

    if isinstance(value, int):
        return bool(value)

    raise ValueError(f"{field_name} must be a boolean value")


def validate_regex_pattern(pattern: str, field_name: str = "pattern") -> str:
    """Validate a regex pattern.

    Args:
        pattern: Regex pattern to validate
        field_name: Name of the field for error messages

    Returns:
        Validated pattern

    Raises:
        ValueError: If pattern is invalid
    """
    if not pattern:
        raise ValueError(f"{field_name} cannot be empty")

    try:
        re.compile(pattern)
    except re.error as e:
        raise ValueError(f"Invalid regex pattern: {e}")

    return pattern


def validate_non_empty_string(value: str, field_name: str = "value") -> str:
    """Validate a non-empty string.

    Args:
        value: String to validate
        field_name: Name of the field for error messages

    Returns:
        Stripped string

    Raises:
        ValueError: If string is empty or None
    """
    if value is None:
        raise ValueError(f"{field_name} is required")

    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")

    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field_name} cannot be empty")

    return stripped
