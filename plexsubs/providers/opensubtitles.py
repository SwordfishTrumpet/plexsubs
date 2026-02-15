"""OpenSubtitles API provider implementation."""

import os
import threading
import time
from typing import Optional

import requests

from plexsubs.providers.base import BaseProvider, SubtitleResult
from plexsubs.utils.constants import (
    DEFAULT_REQUEST_TIMEOUT,
    DOWNLOAD_TIMEOUT,
    TOKEN_EXPIRY_SECONDS,
)
from plexsubs.utils.exceptions import OpenSubtitlesError
from plexsubs.utils.http_client import AuthenticatedHTTPClient
from plexsubs.utils.language_codes import get_allowed_languages
from plexsubs.utils.logging_config import get_logger
from plexsubs.utils.retry import retry_with_backoff

logger = get_logger(__name__)


class OpenSubtitlesProvider(BaseProvider, AuthenticatedHTTPClient):
    """OpenSubtitles.com API provider.

    Provides subtitle search and download functionality for OpenSubtitles.com.
    Implements automatic authentication with JWT token management.

    Attributes:
        username: OpenSubtitles username
        password: OpenSubtitles password
        api_key: OpenSubtitles API key
    """

    def __init__(
        self,
        username: str,
        password: str,
        api_key: Optional[str] = None,
        enabled: bool = True,
    ):
        """Initialize OpenSubtitles provider.

        Args:
            username: OpenSubtitles username
            password: OpenSubtitles password
            api_key: OpenSubtitles API key (optional but recommended)
            enabled: Whether this provider is enabled
        """
        BaseProvider.__init__(self, enabled)
        AuthenticatedHTTPClient.__init__(
            self,
            base_url="https://api.opensubtitles.com/api/v1",
            auth_header_name="Authorization",
            auth_header_prefix="Bearer ",
            verify_ssl=True,
        )
        self.username = username
        self.password = password
        self.api_key = api_key
        self._token_expiry: float = 0
        self._token_lock = threading.Lock()

    def _get_headers(self) -> dict[str, str]:
        """Build request headers with API key and authentication."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "PlexSubtitleWebhook/2.0",
        }
        if self.api_key:
            headers["Api-Key"] = self.api_key

        # Add authentication header from parent class
        auth_headers = super()._get_headers()
        headers.update(auth_headers)

        return headers

    def _authenticate(self) -> str:
        """Authenticate and get JWT token (thread-safe)."""
        # Fast path: check if token is valid without lock
        if self.token and time.time() < self._token_expiry:
            return self.token

        # Slow path: acquire lock and authenticate
        with self._token_lock:
            # Double-check after acquiring lock
            if self.token and time.time() < self._token_expiry:
                return self.token

            logger.info("Authenticating with OpenSubtitles API")

            try:
                # Use parent class POST method but without authentication
                url = f"{self.base_url}/login"
                payload = {"username": self.username, "password": self.password}

                # Make unauthenticated request for login
                headers = {
                    "Content-Type": "application/json",
                    "User-Agent": "PlexSubtitleWebhook/2.0",
                }
                if self.api_key:
                    headers["Api-Key"] = self.api_key

                response = requests.post(
                    url, json=payload, headers=headers, timeout=DEFAULT_REQUEST_TIMEOUT
                )
                response.raise_for_status()
                data = response.json()

                self.token = data.get("token")
                # Token typically valid for 24 hours
                self._token_expiry = time.time() + TOKEN_EXPIRY_SECONDS

                logger.info("Successfully authenticated with OpenSubtitles")
                return self.token

            except requests.exceptions.RequestException as e:
                raise OpenSubtitlesError(f"Authentication failed: {e}")

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        json_data: Optional[dict] = None,
        timeout: Optional[int] = None,
        retry_on_auth_error: bool = True,
    ) -> dict:
        """Make an authenticated request to the OpenSubtitles API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Optional query parameters
            json_data: Optional JSON body
            timeout: Request timeout in seconds
            retry_on_auth_error: Whether to retry on 401 errors after re-authenticating

        Returns:
            JSON response data

        Raises:
            OpenSubtitlesError: If the request fails
        """
        # Ensure we have a valid token
        self._authenticate()

        try:
            response = super()._make_request(
                method=method,
                endpoint=endpoint,
                params=params,
                json_data=json_data,
                timeout=timeout,
            )
            return response.json()

        except Exception as e:
            # Check if this is an authentication error
            if hasattr(e, "response") and e.response is not None:
                if e.response.status_code == 401 and retry_on_auth_error:
                    logger.warning("Token expired, re-authenticating...")
                    self.clear_token()
                    self._authenticate()
                    # Retry once without allowing further retries
                    return self._make_request(
                        method=method,
                        endpoint=endpoint,
                        params=params,
                        json_data=json_data,
                        timeout=timeout,
                        retry_on_auth_error=False,
                    )

            raise OpenSubtitlesError(f"Request failed: {e}")

    def search(
        self,
        title: str,
        year: Optional[int] = None,
        imdb_id: Optional[str] = None,
        language: str = "nl",
        release_groups: Optional[list[str]] = None,
        filename: Optional[str] = None,
    ) -> tuple[list[SubtitleResult], Optional[str]]:
        """Search for subtitles on OpenSubtitles."""
        if not self.enabled:
            return [], None

        # Ensure authenticated
        self._authenticate()

        params = {"languages": language}

        if imdb_id:
            params["imdb_id"] = imdb_id
            logger.info(f"Searching by IMDB ID: {imdb_id} (language: {language})")
        else:
            params["query"] = title
            if year:
                params["year"] = year
            logger.info(f"Searching by title: {title} (language: {language})")

        try:
            data = self._make_request("GET", "/subtitles", params=params)
            subtitles = data.get("data", [])

            logger.info(f"Found {len(subtitles)} subtitles from API")

            if not subtitles:
                return [], self.token

            # Filter by language
            allowed_langs = get_allowed_languages(language)

            results = []
            for sub in subtitles:
                attrs = sub.get("attributes", {})
                sub_lang = attrs.get("language", "").lower()

                if sub_lang not in allowed_langs:
                    continue

                files = attrs.get("files", [])
                if not files:
                    continue

                file_info = files[0]

                result = SubtitleResult(
                    id=str(file_info.get("file_id")),
                    language=language,
                    release=attrs.get("release", ""),
                    filename=file_info.get("file_name", ""),
                    download_params={"file_id": file_info.get("file_id")},
                    provider=self.name,
                    download_count=attrs.get("download_count", 0),
                )
                results.append(result)

            logger.info(f"Filtered to {len(results)} subtitles in language '{language}'")
            return results, self.token

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise OpenSubtitlesError(f"Search failed: {e}")

    def _download_with_retry(
        self,
        subtitle: SubtitleResult,
        output_path: str,
        token: Optional[str],
    ) -> bool:
        """Internal download method to be wrapped by retry decorator."""
        if not token:
            token = self._authenticate()

        payload = subtitle.download_params or {"file_id": subtitle.id}

        # Get download link
        data = self._make_request("POST", "/download", json_data=payload, timeout=DOWNLOAD_TIMEOUT)

        download_link = data.get("link")
        if not download_link:
            logger.error("No download link in response")
            return False

        # Download the file
        logger.info(f"Downloading subtitle from: {download_link[:50]}...")
        sub_response = requests.get(download_link, timeout=DOWNLOAD_TIMEOUT)
        sub_response.raise_for_status()

        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        # Save file
        with open(output_path, "wb") as f:
            f.write(sub_response.content)

        logger.info(f"Downloaded subtitle to: {output_path}")
        return True

    def download(
        self, subtitle: SubtitleResult, output_path: str, token: Optional[str] = None
    ) -> bool:
        """Download subtitle from OpenSubtitles with retry on server errors."""

        def on_retry(attempt: int, delay: float, exception: Exception) -> None:
            """Log retry attempts."""
            if isinstance(exception, requests.exceptions.HTTPError):
                status_code = exception.response.status_code if exception.response else "unknown"
                logger.warning(
                    f"Server error {status_code} on attempt {attempt + 1}, retrying in {delay}s..."
                )
            else:
                logger.warning(f"Download failed on attempt {attempt + 1}, retrying in {delay}s...")

        try:
            # Use retry decorator with server error exceptions
            return retry_with_backoff(
                max_retries=3,
                base_delay=2.0,
                exceptions=(requests.exceptions.HTTPError, requests.exceptions.RequestException),
                on_retry=on_retry,
            )(self._download_with_retry)(subtitle, output_path, token)
        except Exception as e:
            logger.error(f"Download failed after all retries: {e}")
            return False
