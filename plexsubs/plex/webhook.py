"""Webhook handler logic."""

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

from plexsubs.config.settings import Settings
from plexsubs.core.subtitle_manager import SubtitleManager
from plexsubs.plex.client import PlexClient
from plexsubs.utils.constants import (
    BASE_RETRY_WAIT_SECONDS,
    MAX_SESSION_RETRIES,
    PROCESSABLE_EVENTS,
)
from plexsubs.utils.exceptions import PlexSubtitleError
from plexsubs.utils.logging_config import get_logger
from plexsubs.utils.retry import retry_with_backoff

logger = get_logger(__name__)


class WebhookHandler:
    """Handle Plex webhook events."""

    def __init__(
        self,
        settings: Settings,
        plex_client: PlexClient,
        subtitle_manager: SubtitleManager,
    ):
        self.settings = settings
        self.plex = plex_client
        self.subtitle_manager = subtitle_manager
        self._executor = ThreadPoolExecutor(max_workers=2)

    @retry_with_backoff(
        max_retries=MAX_SESSION_RETRIES,
        base_delay=BASE_RETRY_WAIT_SECONDS,
        exceptions=(Exception,),
    )
    async def _try_set_session_subtitle(self, rating_key: str, language_code: str) -> bool:
        """Try to set subtitle on active session.

        This method is designed to be used with retry logic.

        Args:
            rating_key: The Plex rating key
            language_code: The language code to set

        Returns:
            True if successful

        Raises:
            Exception: If subtitle setting failed (triggers retry)
        """
        success = await self._run_in_executor(
            self.plex.set_active_session_subtitle,
            rating_key,
            language_code,
        )
        if not success:
            raise Exception(f"Failed to set subtitle {language_code} for {rating_key}")
        return True

    async def _try_set_session_subtitle_with_retry(
        self, rating_key: str, language_code: str
    ) -> bool:
        """Try to set subtitle with retry logic and proper logging.

        Args:
            rating_key: The Plex rating key
            language_code: The language code to set

        Returns:
            True if successful, False otherwise
        """
        try:
            success = await self._try_set_session_subtitle(rating_key, language_code)
            if success:
                logger.info(f"Successfully set subtitle to {language_code} on active session")
            return success
        except Exception:
            # All retries exhausted, return False
            return False

    async def _run_in_executor(self, func: Callable, *args: Any) -> Any:
        """Run a synchronous function in the thread pool.

        Args:
            func: Function to run
            *args: Arguments to pass to the function

        Returns:
            Result from the function
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, func, *args)

    async def handle_event(self, payload_str: str) -> tuple:
        """Handle a Plex webhook event.

        Returns:
            Tuple of (response_dict, status_code)
        """
        try:
            payload = json.loads(payload_str)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON payload: {e}")
            return {"status": "error", "message": "Invalid JSON"}, 400

        event = payload.get("event")
        logger.info(f"Received webhook event: {event}")

        # Only process play and resume events
        if event not in PROCESSABLE_EVENTS:
            logger.debug(f"Ignoring event: {event}")
            return {"status": "ignored", "event": event}, 200

        # Get metadata
        metadata = payload.get("Metadata", {})
        rating_key = metadata.get("ratingKey")

        if not rating_key:
            logger.error("No rating key in payload")
            return {"status": "error", "message": "No rating key"}, 400

        logger.info(f"Processing media with rating key: {rating_key}")

        # Get media info from Plex (run in thread pool to avoid blocking)
        try:
            media_info = await self._run_in_executor(self.plex.get_media_info, rating_key)
        except PlexSubtitleError as e:
            logger.error(f"Failed to get media info: {e}")
            return {"status": "error", "message": str(e)}, 500

        if not media_info:
            return {"status": "error", "message": "Could not get media info"}, 500

        if not media_info.file_path:
            return {"status": "error", "message": "Could not get file path"}, 500

        logger.info(f"Media file: {media_info.file_path}")

        # Try to download subtitles (run in thread pool)
        try:
            result = await self._run_in_executor(
                self.subtitle_manager.download_subtitles,
                media_info.file_path,
                media_info.title,
                media_info.year,
                media_info.imdb_id,
                rating_key,
            )

            if result["success"]:
                # Refresh Plex metadata (run in thread pool)
                await self._run_in_executor(self.plex.refresh_metadata, rating_key)

                # Auto-select subtitle if enabled
                if self.settings.subtitles_auto_select:
                    # Try to set subtitle on active session with retry logic
                    session_success = await self._try_set_session_subtitle_with_retry(
                        rating_key, result["language_code"]
                    )

                    if not session_success:
                        # Fallback to setting default subtitle for future plays
                        logger.debug(
                            "Could not set subtitle on active session, "
                            "setting default for future plays..."
                        )
                        default_success = await self._run_in_executor(
                            self.plex.set_subtitle_stream,
                            rating_key,
                            result["language_code"],
                        )

                        if default_success:
                            logger.info(
                                f"Set default subtitle to {result['language_code']} "
                                "for future plays"
                            )
                        else:
                            logger.warning(
                                "Failed to set subtitle stream, will be available on next play"
                            )

                return {
                    "status": "success",
                    "subtitle": result["path"],
                    "language": result["language"],
                    "provider": result["provider"],
                    "upgraded": result.get("upgraded", False),
                }, 200
            else:
                return {
                    "status": "not_found",
                    "message": "No suitable subtitle found",
                }, 404

        except PlexSubtitleError as e:
            logger.error(f"Subtitle download failed: {e}")
            return {"status": "error", "message": str(e)}, 500
