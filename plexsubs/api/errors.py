"""Unified error handling for API endpoints.

Provides standardized error handling across all API endpoints
with consistent response formats and proper HTTP status codes.
"""

from typing import Any, Callable

from fastapi import Request
from fastapi.responses import JSONResponse

from plexsubs.api.models import ErrorResponse
from plexsubs.utils.exceptions import (
    ConfigurationError,
    DownloadError,
    LanguageDetectionError,
    OpenSubtitlesError,
    PlexAPIError,
    PlexSubtitleError,
    ProviderError,
    ReleaseMatchingError,
    SubtitleNotFoundError,
)
from plexsubs.utils.logging_config import get_logger

logger = get_logger(__name__)


# Mapping of exceptions to HTTP status codes and error codes
EXCEPTION_HANDLERS: dict[type[Exception], tuple[int, str]] = {
    ConfigurationError: (500, "CONFIGURATION_ERROR"),
    PlexAPIError: (503, "PLEX_API_ERROR"),
    ProviderError: (503, "PROVIDER_ERROR"),
    OpenSubtitlesError: (503, "OPENSUBTITLES_ERROR"),
    SubtitleNotFoundError: (404, "SUBTITLE_NOT_FOUND"),
    DownloadError: (500, "DOWNLOAD_ERROR"),
    LanguageDetectionError: (500, "LANGUAGE_DETECTION_ERROR"),
    ReleaseMatchingError: (500, "RELEASE_MATCHING_ERROR"),
}


def create_error_response(
    message: str, code: str = "ERROR", details: dict[str, Any] | None = None
) -> JSONResponse:
    """Create a standardized error response.

    Args:
        message: Human-readable error message
        code: Machine-readable error code
        details: Optional additional details

    Returns:
        JSONResponse with consistent error structure
    """
    error_data = ErrorResponse(error=message, code=code, details=details)
    return JSONResponse(
        content=error_data.model_dump(exclude_none=True),
        status_code=_get_status_code_from_message(message),
    )


def _get_status_code_from_message(message: str) -> int:
    """Determine appropriate status code from error message."""
    message_lower = message.lower()

    if "not found" in message_lower or "no suitable" in message_lower:
        return 404
    elif "unauthorized" in message_lower or "authentication" in message_lower:
        return 401
    elif "invalid" in message_lower or "bad request" in message_lower:
        return 400
    elif "timeout" in message_lower:
        return 504
    else:
        return 500


def handle_exception(exc: Exception, operation: str = "") -> JSONResponse:
    """Handle any exception and return standardized error response.

    Args:
        exc: The exception that occurred
        operation: Description of the operation that failed

    Returns:
        JSONResponse with standardized error format
    """
    # Log the error
    operation_msg = f" during {operation}" if operation else ""
    logger.error(f"Error{operation_msg}: {exc}")

    # Get error code and status from exception type
    exc_type = type(exc)
    if exc_type in EXCEPTION_HANDLERS:
        status_code, error_code = EXCEPTION_HANDLERS[exc_type]
    elif isinstance(exc, PlexSubtitleError):
        status_code, error_code = (500, "PLEXSUBS_ERROR")
    else:
        status_code, error_code = (500, "INTERNAL_ERROR")

    # Create response
    error_data = ErrorResponse(
        error=str(exc),
        code=error_code,
    )

    return JSONResponse(
        content=error_data.model_dump(exclude_none=True),
        status_code=status_code,
    )


def api_error_handler(operation: str) -> Callable:
    """Decorator for consistent API endpoint error handling.

    This decorator wraps FastAPI endpoint functions to provide
    consistent error handling and response formatting.

    Args:
        operation: Description of the operation for error logging

    Example:
        @router.get("/libraries")
        @api_error_handler("fetching libraries")
        async def get_libraries():
            # Function body - exceptions are automatically handled
            return await fetch_libraries()
    """

    def decorator(func: Callable) -> Callable:
        async def async_wrapper(*args, **kwargs) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as exc:
                return handle_exception(exc, operation)

        def sync_wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                return handle_exception(exc, operation)

        # Return appropriate wrapper based on function type
        import asyncio

        if asyncio.iscoroutinefunction(func):
            async_wrapper.__name__ = func.__name__
            async_wrapper.__doc__ = func.__doc__
            return async_wrapper
        else:
            sync_wrapper.__name__ = func.__name__
            sync_wrapper.__doc__ = func.__doc__
            return sync_wrapper

    return decorator


# FastAPI exception handlers for specific exception types


async def plex_api_error_handler(request: Request, exc: PlexAPIError) -> JSONResponse:
    """Handle Plex API errors."""
    return handle_exception(exc, "Plex API communication")


async def provider_error_handler(request: Request, exc: ProviderError) -> JSONResponse:
    """Handle provider errors."""
    return handle_exception(exc, "subtitle provider")


async def subtitle_not_found_handler(request: Request, exc: SubtitleNotFoundError) -> JSONResponse:
    """Handle subtitle not found errors."""
    return handle_exception(exc, "subtitle search")


async def configuration_error_handler(request: Request, exc: ConfigurationError) -> JSONResponse:
    """Handle configuration errors."""
    return handle_exception(exc, "configuration validation")


def register_exception_handlers(app) -> None:
    """Register all exception handlers with a FastAPI application.

    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(PlexAPIError, plex_api_error_handler)
    app.add_exception_handler(ProviderError, provider_error_handler)
    app.add_exception_handler(OpenSubtitlesError, provider_error_handler)
    app.add_exception_handler(SubtitleNotFoundError, subtitle_not_found_handler)
    app.add_exception_handler(ConfigurationError, configuration_error_handler)

    # Add generic PlexSubtitleError handler for any unhandled custom exceptions
    async def generic_error_handler(request: Request, exc: PlexSubtitleError) -> JSONResponse:
        return handle_exception(exc)

    app.add_exception_handler(PlexSubtitleError, generic_error_handler)
