"""Subtitle manager - orchestrates downloading from multiple providers."""

import os
from typing import Optional

from plexsubs.config.settings import Settings
from plexsubs.core.language_detector import verify_language
from plexsubs.core.release_matcher import extract_release_info
from plexsubs.providers import BaseProvider, OpenSubtitlesProvider
from plexsubs.providers.base import SubtitleResult
from plexsubs.utils.constants import SUBTITLE_EXTENSIONS
from plexsubs.utils.exceptions import ProviderError
from plexsubs.utils.language_codes import to_plex_language_code
from plexsubs.utils.logging_config import get_logger
from plexsubs.utils.retry import retry_with_backoff

logger = get_logger(__name__)


class SubtitleManager:
    """Manages subtitle downloading from multiple providers."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.providers: list[BaseProvider] = []
        self._init_providers()

    def _should_skip_first_language(self, existing: dict[str, str], first_lang: str) -> dict | None:
        """Check if we should skip downloading first language subtitle.

        Args:
            existing: Dictionary mapping language codes to file paths
            first_lang: The first language code to check

        Returns:
            Skip result dict if should skip, None otherwise
        """
        if first_lang in existing:
            logger.info(
                f"Subtitle for first language ({first_lang}) already exists: {existing[first_lang]}"
            )
            # Check if we should try to upgrade with a perfect match
            if not self.settings.subtitles_use_release_matching:
                logger.info("Release matching disabled, keeping existing subtitle")
                return {"success": False, "existing": existing[first_lang]}
        return None

    def _should_skip_language_check(
        self,
        is_first: bool,
        first_lang: str,
        existing: dict[str, str],
        current_lang: str,
    ) -> dict | None:
        """Check if we should skip downloading for current language.

        Args:
            is_first: Whether this is the first language
            first_lang: The first language code
            existing: Dictionary mapping language codes to file paths
            current_lang: The current language being processed

        Returns:
            Skip result dict if should skip, None otherwise
        """
        # Only skip first language if release matching is disabled or upgrade is disabled
        # Otherwise, let _try_download check for perfect match upgrades
        if is_first and first_lang in existing:
            if not self.settings.subtitles_use_release_matching:
                logger.info(
                    f"Release matching disabled, keeping existing subtitle for {first_lang}"
                )
                return {"success": False, "existing": existing[first_lang]}
            if not self.settings.subtitles_upgrade_on_perfect_match:
                logger.info(
                    f"Upgrade on perfect match disabled, keeping existing subtitle for {first_lang}"
                )
                return {"success": False, "existing": existing[first_lang]}
            # Continue to _try_download to check for perfect match upgrades
            return None
        return None

    def _init_providers(self) -> None:
        """Initialize subtitle provider."""
        # OpenSubtitles API - always enabled
        self.providers.append(
            OpenSubtitlesProvider(
                username=self.settings.opensubtitles_username,
                password=self.settings.opensubtitles_password,
                api_key=self.settings.opensubtitles_api_key,
                enabled=True,
            )
        )

        logger.info(f"Initialized {len(self.providers)} subtitle provider(s)")

    def _get_existing_subtitles(self, media_dir: str, media_name: str) -> dict[str, str]:
        """Check for existing subtitle files.

        Returns:
            Dict mapping language codes to file paths
        """
        existing = {}
        languages = self.settings.languages_list

        # Check all configured languages
        for lang in languages:
            for ext in SUBTITLE_EXTENSIONS:
                path = os.path.join(media_dir, f"{media_name}.{lang}{ext}")
                if os.path.exists(path):
                    existing[lang] = path
                    break

        return existing

    def download_subtitles(
        self,
        media_path: str,
        title: str,
        year: Optional[int] = None,
        imdb_id: Optional[str] = None,
        rating_key: Optional[str] = None,
    ) -> dict:
        """Download subtitles for a media file.

        Returns:
            Dict with download result information
        """
        media_dir = os.path.dirname(media_path)
        media_name = os.path.splitext(os.path.basename(media_path))[0]

        logger.info(f"Processing: {media_name}")

        # Get configured languages
        languages = self.settings.languages_list
        if not languages:
            logger.warning("No languages configured")
            return {"success": False}

        # Check for existing subtitles
        existing = self._get_existing_subtitles(media_dir, media_name)

        # Check if first language already exists and whether to skip
        first_lang = languages[0]
        skip_result = self._should_skip_first_language(existing, first_lang)
        if skip_result:
            return skip_result

        # Extract release info for matching
        release_groups = None
        if self.settings.subtitles_use_release_matching:
            release_groups = extract_release_info(media_name)
            if release_groups:
                logger.info(f"Release groups detected: {release_groups}")

        # Try each language in order
        for i, lang in enumerate(languages):
            is_first = i == 0

            # Check if we should skip this language (already exists and not upgrading)
            skip_check = self._should_skip_language_check(is_first, first_lang, existing, lang)
            if skip_check:
                return skip_check

            # Try downloading this language
            if not is_first:
                logger.info(f"No subtitles found for previous languages, trying {lang}")

            result = self._try_download(
                media_dir=media_dir,
                media_name=media_name,
                title=title,
                year=year,
                imdb_id=imdb_id,
                language=lang,
                release_groups=release_groups,
                existing_path=existing.get(lang),
            )

            if result["success"]:
                return result

        # Nothing found for any language
        logger.warning("No subtitles found from any provider for any language")
        return {"success": False}

    def _try_download(
        self,
        media_dir: str,
        media_name: str,
        title: str,
        year: Optional[int],
        imdb_id: Optional[str],
        language: str,
        release_groups: Optional[list[str]],
        existing_path: Optional[str],
    ) -> dict:
        """Try to download subtitles for a specific language."""

        # Search all providers
        all_results: list[tuple] = []  # (provider, result, token)

        for provider in self.providers:
            try:
                logger.info(f"Searching {provider.name} for {language} subtitles...")
                results, token = provider.search(
                    title=title,
                    year=year,
                    imdb_id=imdb_id,
                    language=language,
                    release_groups=release_groups,
                    filename=media_name,
                )

                for result in results:
                    all_results.append((provider, result, token))

            except Exception as e:
                logger.error(f"Provider {provider.name} search failed: {e}")
                continue

        if not all_results:
            logger.info(f"No {language} subtitles found")
            return {"success": False}

        # Sort by perfect match first, then by download count (descending), then by score
        all_results.sort(
            key=lambda x: (not x[1].is_perfect_match, -x[1].download_count, -x[1].score)
        )

        # Check if we should upgrade existing subtitle
        has_perfect_match = any(r[1].is_perfect_match for r in all_results)
        best_result = all_results[0][1]

        if existing_path and not has_perfect_match:
            # No perfect match, but check if we should upgrade to a popular subtitle
            if self.settings.subtitles_upgrade_on_popular:
                if best_result.download_count >= self.settings.subtitles_popular_download_threshold:
                    logger.info(
                        f"No perfect match, but found popular subtitle with "
                        f"{best_result.download_count} downloads (threshold: "
                        f"{self.settings.subtitles_popular_download_threshold})"
                    )
                    # Continue to download the most popular subtitle
                else:
                    logger.info(
                        f"Existing subtitle found and no perfect match available. "
                        f"Best alternative has only {best_result.download_count} downloads "
                        f"(threshold: {self.settings.subtitles_popular_download_threshold}), "
                        f"skipping download"
                    )
                    return {"success": False, "existing": existing_path}
            else:
                logger.info(
                    "Existing subtitle found and no perfect match available, skipping download"
                )
                return {"success": False, "existing": existing_path}

        if (
            existing_path
            and has_perfect_match
            and not self.settings.subtitles_upgrade_on_perfect_match
        ):
            logger.info("Perfect match found but upgrade_on_perfect_match is disabled")
            return {"success": False, "existing": existing_path}

        # Try to download results in order with retry logic
        for provider, result, token in all_results:
            # Skip non-perfect matches if we have existing subtitle (unless upgrading to popular)
            if existing_path and not result.is_perfect_match:
                # Only skip if we're not in "upgrade on popular" mode or this isn't
                # the best popular result
                if not self.settings.subtitles_upgrade_on_popular:
                    logger.debug(f"Skipping non-perfect match from {provider.name}")
                    continue
                # In upgrade_on_popular mode, only try the first (most popular) result
                if result != best_result:
                    logger.debug(f"Skipping less popular match from {provider.name}")
                    continue

            output_path = os.path.join(media_dir, f"{media_name}.{language}.srt")

            logger.info(f"Attempting download from {provider.name}: {result.filename}")

            download_result = self._download_with_retry(
                provider=provider,
                subtitle=result,
                output_path=output_path,
                token=token,
                language=language,
                existing_path=existing_path,
            )

            if download_result.get("success"):
                return download_result

        logger.warning(f"All download attempts failed for {language}")
        return {"success": False}

    @retry_with_backoff(max_retries=3, exceptions=(Exception,), on_retry=None)
    def _download_and_verify(
        self,
        provider: BaseProvider,
        subtitle: SubtitleResult,
        output_path: str,
        token: Optional[str],
        language: str,
    ) -> bool:
        """Download and verify a subtitle file.

        Returns:
            True if download and verification succeeded
        """
        success = provider.download(subtitle, output_path, token)

        if not success:
            return False

        # Verify language if possible
        if not verify_language(output_path, language):
            logger.warning("Language verification failed, removing file")
            os.remove(output_path)
            raise Exception("Language verification failed")

        return True

    def _download_with_retry(
        self,
        provider: BaseProvider,
        subtitle: SubtitleResult,
        output_path: str,
        token: Optional[str],
        language: str,
        existing_path: Optional[str],
    ) -> dict:
        """Download subtitle with retry logic."""
        try:
            success = self._download_and_verify(provider, subtitle, output_path, token, language)

            if success:
                # Remove existing subtitle if upgrading
                if existing_path and existing_path != output_path and subtitle.is_perfect_match:
                    try:
                        os.remove(existing_path)
                        logger.info(f"Removed old subtitle: {existing_path}")
                    except Exception as e:
                        logger.warning(f"Could not remove old subtitle: {e}")

                logger.info(f"Successfully downloaded {language} subtitle from {provider.name}")

                return {
                    "success": True,
                    "path": output_path,
                    "language": language,
                    "language_code": to_plex_language_code(language),
                    "provider": provider.name,
                    "upgraded": existing_path is not None and subtitle.is_perfect_match,
                }

        except ProviderError as e:
            # Provider errors are not retryable
            logger.error(f"Provider error from {provider.name}: {e}")
        except Exception as e:
            logger.error(f"Download from {provider.name} failed: {e}")

        return {"success": False}
