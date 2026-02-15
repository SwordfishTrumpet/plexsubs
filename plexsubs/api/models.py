"""Pydantic models for API responses.

Provides standardized response models for all API endpoints,
ensuring consistent structure and automatic OpenAPI documentation.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standardized error response model."""

    error: str = Field(..., description="Error message")
    code: str = Field("ERROR", description="Error code for programmatic handling")
    details: Optional[dict[str, Any]] = Field(None, description="Additional error details")


class SuccessResponse(BaseModel):
    """Standardized success response model."""

    status: str = Field("success", description="Response status")
    data: Optional[dict[str, Any]] = Field(None, description="Response data")


class LibraryLocationResponse(BaseModel):
    """Library location response model."""

    id: str = Field(..., description="Location ID")
    path: str = Field(..., description="Filesystem path")


class LibraryResponse(BaseModel):
    """Library section response model."""

    key: str = Field(..., description="Library key/ID")
    title: str = Field(..., description="Library title")
    type: str = Field(..., description="Library type (movie, show, etc.)")
    agent: str = Field(..., description="Metadata agent")
    scanner: str = Field(..., description="Library scanner")
    language: str = Field(..., description="Library language")
    locations: list[LibraryLocationResponse] = Field(..., description="Library locations")


class LibrariesListResponse(BaseModel):
    """Response model for library listing endpoint."""

    libraries: list[LibraryResponse] = Field(..., description="List of libraries")


class PathTestResponse(BaseModel):
    """Path test result response model."""

    plex_path: str = Field(..., description="Original Plex path")
    mapped_path: str = Field(..., description="Mapped local path")
    exists: bool = Field(..., description="Whether path exists")
    readable: bool = Field(..., description="Whether path is readable")
    writable: bool = Field(..., description="Whether path is writable")
    is_file: bool = Field(..., description="Whether path is a file")
    is_directory: bool = Field(..., description="Whether path is a directory")
    error: Optional[str] = Field(None, description="Error message if test failed")


class ValidationReportResponse(BaseModel):
    """Path validation report response model."""

    valid: bool = Field(..., description="Whether all tests passed")
    summary: dict[str, int] = Field(..., description="Test summary statistics")
    tests: list[PathTestResponse] = Field(..., description="Individual test results")
    suggestions: list[str] = Field(..., description="Helpful suggestions based on results")
    current_mappings: dict[str, str] = Field(..., description="Current path mappings")


class PathMappingSuggestionResponse(BaseModel):
    """Path mapping suggestion response model."""

    plex_prefix: str = Field(..., description="Plex path prefix")
    suggested_local_prefix: str = Field(..., description="Suggested local path")
    confidence: str = Field(..., description="Confidence level (high, medium, low)")
    reason: str = Field(..., description="Explanation for the suggestion")


class PathMappingsSuggestionResponse(BaseModel):
    """Response model for path mapping suggestions."""

    suggestions: list[PathMappingSuggestionResponse] = Field(..., description="List of suggestions")
    current_mappings: dict[str, str] = Field(..., description="Current path mappings")


class DiscoveryStatusResponse(BaseModel):
    """Discovery service status response model."""

    enabled: bool = Field(..., description="Whether discovery is enabled")
    validate_on_startup: bool = Field(..., description="Whether validation runs on startup")
    test_file: Optional[str] = Field(None, description="Configured test file path")
    path_mappings: dict[str, str] = Field(..., description="Current path mappings")


class ConfigResponse(BaseModel):
    """Configuration response model (without secrets)."""

    plex_url: str = Field(..., description="Plex server URL")
    languages: list[str] = Field(..., description="Configured language codes")
    auto_select: bool = Field(..., description="Whether auto-select is enabled")
    use_release_matching: bool = Field(..., description="Whether release matching is enabled")


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Application version")


class WebhookResponse(BaseModel):
    """Webhook event response model."""

    status: str = Field(..., description="Response status")
    subtitle: Optional[str] = Field(None, description="Downloaded subtitle path")
    language: Optional[str] = Field(None, description="Subtitle language")
    provider: Optional[str] = Field(None, description="Subtitle provider")
    upgraded: bool = Field(False, description="Whether existing subtitle was upgraded")


class WebhookIgnoredResponse(BaseModel):
    """Response when webhook event is ignored."""

    status: str = Field("ignored", description="Response status")
    event: str = Field(..., description="Event type that was ignored")


class WebhookErrorResponse(BaseModel):
    """Webhook error response model."""

    status: str = Field("error", description="Response status")
    message: str = Field(..., description="Error message")
