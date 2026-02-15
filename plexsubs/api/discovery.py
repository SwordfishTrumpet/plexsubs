"""Discovery and validation API endpoints."""

from fastapi import APIRouter, Depends, Request

from plexsubs.api.models import (
    DiscoveryStatusResponse,
    LibrariesListResponse,
    LibraryLocationResponse,
    LibraryResponse,
    PathMappingsSuggestionResponse,
    PathMappingSuggestionResponse,
    PathTestResponse,
    ValidationReportResponse,
)
from plexsubs.config import get_settings
from plexsubs.config.settings import Settings
from plexsubs.core.discovery import PathDiscovery
from plexsubs.plex.client import PlexClient
from plexsubs.utils.logging_config import get_logger

logger = get_logger(__name__)

# Create router
router = APIRouter()


def get_discovery_service(settings: Settings = Depends(get_settings)) -> PathDiscovery:
    """Get configured PathDiscovery service."""
    plex_client = PlexClient.from_settings(settings)
    return PathDiscovery(plex_client, settings.path_mappings)


@router.get("/libraries", response_model=LibrariesListResponse)
async def discover_libraries(
    discovery: PathDiscovery = Depends(get_discovery_service),
):
    """Get all Plex libraries with their configured paths.

    Returns:
        JSON response with library information.
    """
    libraries = discovery.discover_libraries()

    return LibrariesListResponse(
        libraries=[
            LibraryResponse(
                key=lib.key,
                title=lib.title,
                type=lib.type,
                agent=lib.agent,
                scanner=lib.scanner,
                language=lib.language,
                locations=[
                    LibraryLocationResponse(id=loc.id, path=loc.path) for loc in lib.locations
                ],
            )
            for lib in libraries
        ]
    )


@router.get("/validate-paths", response_model=ValidationReportResponse)
@router.post("/validate-paths", response_model=ValidationReportResponse)
async def validate_paths(
    request: Request,
    discovery: PathDiscovery = Depends(get_discovery_service),
    settings: Settings = Depends(get_settings),
):
    """Validate current path mappings.

    GET: Returns validation report using sample files from libraries.
    POST: Accepts JSON with "test_paths" array to test specific paths.

    Returns:
        JSON response with validation results.
    """
    # Get test paths from request or use defaults
    test_paths: list[str] | None = None
    if request.method == "POST":
        data = await request.json()
        test_paths = data.get("test_paths")

    # If no test paths provided and a specific test file is configured, use it
    if not test_paths and settings.discovery_test_file:
        test_paths = [settings.discovery_test_file]

    report = discovery.validate_path_mappings(test_paths)

    return ValidationReportResponse(
        valid=report.valid,
        summary=report.summary,
        tests=[
            PathTestResponse(
                plex_path=test.plex_path,
                mapped_path=test.mapped_path,
                exists=test.exists,
                readable=test.readable,
                writable=test.writable,
                is_file=test.is_file,
                is_directory=test.is_directory,
                error=test.error,
            )
            for test in report.tests
        ],
        suggestions=report.suggestions,
        current_mappings=settings.path_mappings,
    )


@router.get("/suggest-mappings", response_model=PathMappingsSuggestionResponse)
async def suggest_mappings(
    discovery: PathDiscovery = Depends(get_discovery_service),
    settings: Settings = Depends(get_settings),
):
    """Get auto-suggested path mappings based on library analysis.

    Returns:
        JSON response with suggested path mappings.
    """
    suggestions = discovery.suggest_path_mappings()

    return PathMappingsSuggestionResponse(
        suggestions=[
            PathMappingSuggestionResponse(
                plex_prefix=sugg.plex_prefix,
                suggested_local_prefix=sugg.suggested_local_prefix,
                confidence=sugg.confidence,
                reason=sugg.reason,
            )
            for sugg in suggestions
        ],
        current_mappings=settings.path_mappings,
    )


@router.get("/status", response_model=DiscoveryStatusResponse)
async def discovery_status(settings: Settings = Depends(get_settings)):
    """Get discovery service status and configuration.

    Returns:
        JSON response with current configuration.
    """
    return DiscoveryStatusResponse(
        enabled=settings.discovery_enabled,
        validate_on_startup=settings.discovery_validate_on_startup,
        test_file=settings.discovery_test_file,
        path_mappings=settings.path_mappings,
    )
