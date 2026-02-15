"""Path utilities for mapping and manipulation."""

import os
from pathlib import Path

from plexsubs.utils.constants import DEFAULT_PATH_MAPPINGS


def apply_path_mappings(file_path: str, path_mappings: dict[str, str]) -> str:
    """Apply path mappings to convert a path using configured mappings.

    Args:
        file_path: Original file path
        path_mappings: Dictionary of path mappings {old_path: new_path}

    Returns:
        Mapped file path
    """
    for old_path, new_path in path_mappings.items():
        if file_path.startswith(old_path):
            return file_path.replace(old_path, new_path, 1)
    return file_path


def parse_path_mappings(value: str | None) -> dict[str, str]:
    """Parse path mappings from string.

    Format: /media:/mnt/library,/data:/mnt/data

    Args:
        value: Path mappings string

    Returns:
        Dictionary of path mappings
    """
    if not value:
        return DEFAULT_PATH_MAPPINGS.copy()

    mappings = {}
    for mapping in value.split(","):
        if ":" in mapping:
            src, dst = mapping.split(":", 1)
            mappings[src.strip()] = dst.strip()

    return mappings if mappings else DEFAULT_PATH_MAPPINGS.copy()


def check_file_permissions(file_path: str) -> dict[str, bool]:
    """Check file/directory permissions.

    Args:
        file_path: Path to check

    Returns:
        Dictionary with exists, readable, writable, is_file, is_directory status
    """
    result = {
        "exists": False,
        "readable": False,
        "writable": False,
        "is_file": False,
        "is_directory": False,
    }

    try:
        path_obj = Path(file_path)
        result["exists"] = path_obj.exists()

        if result["exists"]:
            result["is_file"] = path_obj.is_file()
            result["is_directory"] = path_obj.is_dir()

            if result["is_file"]:
                result["readable"] = os.access(file_path, os.R_OK)
                result["writable"] = os.access(path_obj.parent, os.W_OK)
            elif result["is_directory"]:
                result["readable"] = os.access(file_path, os.R_OK)
                result["writable"] = os.access(file_path, os.W_OK)

    except OSError:
        pass

    return result
