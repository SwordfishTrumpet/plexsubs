"""Environment and system utilities."""

import os


def is_running_in_docker() -> bool:
    """Check if running inside a Docker container."""
    return os.path.exists("/.dockerenv")
