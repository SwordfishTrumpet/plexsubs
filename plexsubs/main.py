"""Main FastAPI application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse

from plexsubs import __version__
from plexsubs.api.discovery import router as discovery_router
from plexsubs.api.errors import register_exception_handlers
from plexsubs.api.models import (
    ConfigResponse,
    HealthResponse,
    WebhookIgnoredResponse,
)
from plexsubs.config import get_settings
from plexsubs.core import SubtitleManager
from plexsubs.core.discovery import PathDiscovery
from plexsubs.plex import PlexClient, WebhookHandler
from plexsubs.utils import get_logger, setup_logging

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application lifespan events."""
    # Startup
    settings = get_settings()

    logger.info("=" * 60)
    logger.info(f"plexsubs - Plex Subtitle Webhook Server v{__version__}")
    logger.info("=" * 60)
    logger.info(f"Plex URL: {settings.plex_url}")
    logger.info(f"Languages: {', '.join(settings.languages_list)}")
    logger.info(f"Auto-select: {settings.subtitles_auto_select}")
    logger.info(f"Release matching: {settings.subtitles_use_release_matching}")
    logger.info(f"Webhook endpoint: {settings.server_webhook_path}")
    logger.info("=" * 60)

    # Initialize components
    plex_client = PlexClient.from_settings(settings)

    subtitle_manager = SubtitleManager(settings)
    webhook_handler = WebhookHandler(settings, plex_client, subtitle_manager)

    # Store in app state
    app.state.plex_client = plex_client
    app.state.subtitle_manager = subtitle_manager
    app.state.webhook_handler = webhook_handler

    # Run startup validation if configured
    if settings.discovery_enabled and settings.discovery_validate_on_startup:
        _run_startup_validation(plex_client, settings)

    yield

    # Shutdown (if needed)
    pass


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()

    # Create FastAPI app
    app = FastAPI(
        title="plexsubs - Plex Subtitle Webhook Server",
        version=__version__,
        debug=settings.server_debug,
        lifespan=lifespan,
    )

    # Register exception handlers for consistent error responses
    register_exception_handlers(app)

    # Register discovery router if enabled
    if settings.discovery_enabled:
        app.include_router(discovery_router, prefix="/discover")
        logger.info("Discovery endpoints enabled at /discover/*")

    # Routes
    @app.post(settings.server_webhook_path)
    async def handle_webhook(payload: str = Form(...)) -> JSONResponse:
        """Handle Plex webhook events."""
        if not payload:
            logger.error("No payload in webhook request")
            return JSONResponse(
                content=WebhookIgnoredResponse(
                    status="error", event="missing_payload"
                ).model_dump(),
                status_code=400,
            )

        webhook_handler = app.state.webhook_handler
        response_data, status_code = await webhook_handler.handle_event(payload)
        return JSONResponse(content=response_data, status_code=status_code)

    @app.get("/health", response_model=HealthResponse)
    async def health_check() -> HealthResponse:
        """Health check endpoint."""
        return HealthResponse(status="healthy", version=__version__)

    @app.get("/config", response_model=ConfigResponse)
    async def get_config() -> ConfigResponse:
        """Get current configuration (without secrets)."""
        return ConfigResponse(
            plex_url=settings.plex_url,
            languages=settings.languages_list,
            auto_select=settings.subtitles_auto_select,
            use_release_matching=settings.subtitles_use_release_matching,
        )

    return app


def _run_startup_validation(plex_client: PlexClient, settings) -> None:
    """Run path validation on startup and log results."""
    try:
        logger.info("Running startup path validation...")
        discovery = PathDiscovery(plex_client, settings.path_mappings)

        test_paths = None
        if settings.discovery_test_file:
            test_paths = [settings.discovery_test_file]

        report = discovery.validate_path_mappings(test_paths)

        if report.valid:
            logger.info("Path validation PASSED: All mappings are working correctly")
        else:
            logger.warning("Path validation FAILED: Issues detected with path mappings")
            for suggestion in report.suggestions:
                logger.warning(f"  - {suggestion}")

        # Log summary
        logger.info(
            f"Validation summary: {report.summary.get('passed', 0)}/"
            f"{report.summary.get('total', 0)} tests passed"
        )

    except Exception as e:
        logger.error(f"Startup validation failed: {e}")


def main():
    """Run the FastAPI application."""
    import uvicorn

    settings = get_settings()

    # Setup logging early
    setup_logging(
        level=settings.log_level,
        use_colors=settings.log_use_colors,
        json_format=settings.log_json_format,
        log_file=settings.log_file,
    )

    uvicorn.run(
        "plexsubs.main:create_app",
        host=settings.server_host,
        port=settings.server_port,
        reload=settings.server_debug,
        factory=True,
    )


if __name__ == "__main__":
    main()
