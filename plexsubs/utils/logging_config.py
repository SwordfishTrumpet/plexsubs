"""Structured logging configuration with color-coded package prefixes."""

import logging
import sys
from typing import Optional

# Color codes for terminal output
COLORS = {
    "WEBHOOK": "\033[36m",  # Cyan
    "PLEX": "\033[34m",  # Blue
    "OPENSUBTITLES": "\033[32m",  # Green
    "CORE": "\033[37m",  # White
    "CONFIG": "\033[90m",  # Gray
    "ERROR": "\033[31m",  # Red
    "WARNING": "\033[33m",  # Yellow
    "RESET": "\033[0m",  # Reset
}

# Package name mapping to extract from module paths
PACKAGE_NAMES = {
    "plexsubs": "CORE",
    "plexsubs.main": "WEBHOOK",
    "plexsubs.config": "CONFIG",
    "plexsubs.providers.opensubtitles": "OPENSUBTITLES",
    "plexsubs.plex.client": "PLEX",
    "plexsubs.plex.webhook": "WEBHOOK",
    "plexsubs.core": "CORE",
}


def get_package_name(logger_name: str) -> str:
    """Extract package name from logger name."""
    # Direct mapping
    if logger_name in PACKAGE_NAMES:
        return PACKAGE_NAMES[logger_name]

    # Try to match prefix
    for prefix, name in PACKAGE_NAMES.items():
        if logger_name.startswith(prefix):
            return name

    # Default to CORE
    return "CORE"


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds color-coded package prefixes."""

    def __init__(self, fmt: Optional[str] = None, use_colors: bool = True):
        super().__init__(fmt or "%(message)s")
        self.use_colors = use_colors and sys.stdout.isatty()

    def format(self, record: logging.LogRecord) -> str:
        # Extract package name from logger name
        package = get_package_name(record.name)

        # Get color for package
        color = COLORS.get(package, COLORS["CORE"])
        reset = COLORS["RESET"] if self.use_colors else ""

        # Format the prefix
        if self.use_colors:
            prefix = f"{color}[{package}]{reset}"
        else:
            prefix = f"[{package}]"

        # Format the message
        record.message = record.getMessage()

        # Add level color for errors/warnings
        if record.levelno >= logging.ERROR:
            level_color = COLORS["ERROR"] if self.use_colors else ""
            level_name = f"{level_color}[ERROR]{reset}" if self.use_colors else "[ERROR]"
            formatted = f"{prefix} {level_name} {record.message}"
        elif record.levelno >= logging.WARNING:
            level_color = COLORS["WARNING"] if self.use_colors else ""
            level_name = f"{level_color}[WARN]{reset}" if self.use_colors else "[WARN]"
            formatted = f"{prefix} {level_name} {record.message}"
        else:
            formatted = f"{prefix} {record.message}"

        return formatted


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        import json
        from datetime import datetime

        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "package": get_package_name(record.name),
            "message": record.getMessage(),
        }

        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)

        return json.dumps(log_data)


_logging_initialized = False


def setup_logging(
    level: str = "INFO",
    use_colors: bool = True,
    json_format: bool = False,
    log_file: Optional[str] = None,
    force: bool = False,
) -> None:
    """Setup logging configuration.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        use_colors: Whether to use colored output
        json_format: Whether to output JSON format
        log_file: Optional file path for logging
        force: If True, reconfigure even if already initialized
    """
    global _logging_initialized

    # Skip if already initialized and not forcing
    if _logging_initialized and not force:
        return

    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    root_logger.handlers = []

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))

    if json_format:
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(ColoredFormatter(use_colors=use_colors))

    root_logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(file_handler)

    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

    _logging_initialized = True


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
