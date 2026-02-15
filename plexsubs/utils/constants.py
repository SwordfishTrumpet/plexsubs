"""Application-wide constants for professional code organization."""

# Path mappings
DEFAULT_PATH_MAPPINGS: dict[str, str] = {"/media": "/mnt/library"}

# Common mount points for media libraries
COMMON_MEDIA_MOUNTS: list[str] = ["/mnt", "/media", "/data", "/volume", "/srv"]

# Subtitle file extensions
SUBTITLE_EXTENSIONS: list[str] = [".srt", ".ass", ".ssa", ".vtt"]

# Plex webhook events to process
PROCESSABLE_EVENTS: set[str] = {"media.play", "media.resume"}

# HTTP timeouts
DEFAULT_REQUEST_TIMEOUT: int = 10
DOWNLOAD_TIMEOUT: int = 30

# Retry configuration
DEFAULT_MAX_RETRIES: int = 3
DEFAULT_RETRY_DELAY_SECONDS: int = 5
DEFAULT_BASE_RETRY_DELAY: float = 1.0

# Token expiry
TOKEN_EXPIRY_HOURS: int = 23
TOKEN_EXPIRY_SECONDS: int = TOKEN_EXPIRY_HOURS * 3600  # 82800

# Webhook session retry delays
BASE_RETRY_WAIT_SECONDS: int = 3
RETRY_WAIT_INCREMENT: int = 2
MAX_SESSION_RETRIES: int = 3


# File permissions check results
class PermissionStatus:
    """Standard permission check result statuses."""

    OK = "ok"
    NOT_FOUND = "not_found"
    NOT_READABLE = "not_readable"
    NOT_WRITABLE = "not_writable"
