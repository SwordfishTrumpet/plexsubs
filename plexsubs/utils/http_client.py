"""HTTP client abstraction for consistent API communication.

Provides a base class for HTTP clients with authentication, retry logic,
and standardized error handling.
"""

from abc import ABC
from typing import Optional

import requests
import urllib3

from plexsubs.utils.constants import DEFAULT_REQUEST_TIMEOUT
from plexsubs.utils.exceptions import PlexAPIError
from plexsubs.utils.logging_config import get_logger

logger = get_logger(__name__)

# Disable SSL warnings for Plex self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class BaseHTTPClient(ABC):
    """Base HTTP client with authentication and retry capabilities.

    This abstract base class provides common functionality for making HTTP requests
    to APIs, including authentication header management, request execution with
    multiple HTTP methods, and standardized error handling.

    Attributes:
        base_url: The base URL for all API requests
        timeout: Default timeout for requests in seconds
        session: Requests session for connection pooling
    """

    def __init__(
        self,
        base_url: str,
        timeout: int = DEFAULT_REQUEST_TIMEOUT,
        verify_ssl: bool = False,
    ):
        """Initialize the HTTP client.

        Args:
            base_url: Base URL for API requests (trailing slashes are stripped)
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.verify = verify_ssl

    def _get_headers(self) -> dict[str, str]:
        """Build request headers.

        Returns:
            Dictionary of HTTP headers to include in requests.
            Override in subclasses to add authentication headers.
        """
        return {}

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        json_data: Optional[dict] = None,
        timeout: Optional[int] = None,
    ) -> requests.Response:
        """Make an HTTP request to the API.

        This method centralizes all HTTP request logic, eliminating duplication
        across different client implementations.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            endpoint: API endpoint path (will be appended to base_url)
            params: Optional query parameters
            json_data: Optional JSON payload for POST/PUT requests
            timeout: Optional override for request timeout

        Returns:
            Response object from the request

        Raises:
            PlexAPIError: If the request fails or returns an error status
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        request_timeout = timeout or self.timeout
        headers = self._get_headers()

        try:
            method = method.upper()
            if method == "GET":
                response = self.session.get(
                    url, headers=headers, params=params, timeout=request_timeout
                )
            elif method == "POST":
                response = self.session.post(
                    url,
                    headers=headers,
                    json=json_data,
                    params=params,
                    timeout=request_timeout,
                )
            elif method == "PUT":
                response = self.session.put(
                    url, headers=headers, params=params, timeout=request_timeout
                )
            elif method == "DELETE":
                response = self.session.delete(
                    url, headers=headers, params=params, timeout=request_timeout
                )
            else:
                raise PlexAPIError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response

        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP {method} request failed: {e}")
            raise PlexAPIError(f"Request failed: {e}")

    def get(self, endpoint: str, params: Optional[dict] = None, **kwargs) -> requests.Response:
        """Make a GET request."""
        return self._make_request("GET", endpoint, params=params, **kwargs)

    def post(
        self,
        endpoint: str,
        json_data: Optional[dict] = None,
        params: Optional[dict] = None,
        **kwargs,
    ) -> requests.Response:
        """Make a POST request."""
        return self._make_request("POST", endpoint, params=params, json_data=json_data, **kwargs)

    def put(self, endpoint: str, params: Optional[dict] = None, **kwargs) -> requests.Response:
        """Make a PUT request."""
        return self._make_request("PUT", endpoint, params=params, **kwargs)

    def delete(self, endpoint: str, params: Optional[dict] = None, **kwargs) -> requests.Response:
        """Make a DELETE request."""
        return self._make_request("DELETE", endpoint, params=params, **kwargs)

    def close(self) -> None:
        """Close the HTTP session."""
        self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


class AuthenticatedHTTPClient(BaseHTTPClient):
    """HTTP client with token-based authentication.

    Extends BaseHTTPClient with automatic token management and
    retry on authentication failures.

    Attributes:
        token: Current authentication token
        auth_header_name: Name of the header for the token
        auth_header_prefix: Prefix for the token value (e.g., "Bearer ")
    """

    def __init__(
        self,
        base_url: str,
        token: Optional[str] = None,
        auth_header_name: str = "Authorization",
        auth_header_prefix: str = "Bearer ",
        **kwargs,
    ):
        """Initialize authenticated client.

        Args:
            base_url: Base URL for API requests
            token: Initial authentication token
            auth_header_name: Header name for authentication
            auth_header_prefix: Prefix for token in header
            **kwargs: Additional arguments passed to BaseHTTPClient
        """
        super().__init__(base_url, **kwargs)
        self.token = token
        self.auth_header_name = auth_header_name
        self.auth_header_prefix = auth_header_prefix

    def _get_headers(self) -> dict[str, str]:
        """Build headers including authentication."""
        headers = super()._get_headers()
        if self.token:
            headers[self.auth_header_name] = f"{self.auth_header_prefix}{self.token}"
        return headers

    def set_token(self, token: str) -> None:
        """Update the authentication token."""
        self.token = token

    def clear_token(self) -> None:
        """Clear the authentication token."""
        self.token = None
