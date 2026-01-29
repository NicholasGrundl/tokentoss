"""IAP-authenticated HTTP client.

Provides IAPClient which automatically handles Google ID token
injection for requests to IAP-protected services.
"""

from __future__ import annotations

import os
from typing import Any, TYPE_CHECKING

import requests
from google.auth.transport.requests import Request

from .exceptions import NoCredentialsError
from .storage import FileStorage

if TYPE_CHECKING:
    from .auth_manager import AuthManager


class IAPClient:
    """HTTP client that adds IAP authentication tokens automatically.

    Discovers credentials via a fallback chain:
    1. Explicit AuthManager (passed to constructor)
    2. Module-level tokentoss.CREDENTIALS (set by AuthManager on login)
    3. Token file (TOKENTOSS_TOKEN_FILE env var or default platformdirs path)

    Automatically retries once on 401 by refreshing the token.

    Usage:
        client = IAPClient(base_url="https://my-iap-service.run.app")
        data = client.get_json("/api/data")

    Or as a context manager:
        with IAPClient(base_url="https://my-service.run.app") as client:
            data = client.get_json("/api/data")
    """

    def __init__(
        self,
        base_url: str | None = None,
        auth_manager: AuthManager | None = None,
        timeout: int = 30,
    ) -> None:
        """Initialize IAPClient.

        Args:
            base_url: Optional base URL for relative paths (e.g. "https://my-service.run.app").
            auth_manager: Optional AuthManager for credential discovery.
                If not provided, falls back to module-level CREDENTIALS or token file.
            timeout: Request timeout in seconds. Default 30.
        """
        self.base_url = base_url.rstrip("/") if base_url else None
        self.timeout = timeout
        self._auth_manager = auth_manager
        self._session = requests.Session()
        self._fallback_storage: FileStorage | None = None

    def _get_fallback_storage(self) -> FileStorage:
        """Get or create cached FileStorage for token discovery."""
        if self._fallback_storage is None:
            token_path = os.environ.get("TOKENTOSS_TOKEN_FILE")
            self._fallback_storage = FileStorage(path=token_path)
        return self._fallback_storage

    def _get_id_token(self, force_refresh: bool = False) -> str:
        """Find and return a valid ID token.

        Discovery chain:
        1. Explicit auth_manager passed in constructor
        2. Module-level tokentoss.CREDENTIALS variable
        3. Token file (TOKENTOSS_TOKEN_FILE env var or default location)

        Args:
            force_refresh: Force a token refresh before returning.

        Returns:
            A valid ID token string.

        Raises:
            NoCredentialsError: If no valid credentials found anywhere.
        """
        # 1. Explicit AuthManager
        token = self._try_auth_manager(force_refresh)
        if token:
            return token

        # 2. Module-level credentials
        token = self._try_module_credentials(force_refresh)
        if token:
            return token

        # 3. Token file (env var or default path)
        token = self._try_storage()
        if token:
            return token

        raise NoCredentialsError(
            "No valid credentials found. Use GoogleAuthWidget to authenticate."
        )

    def _try_auth_manager(self, force_refresh: bool) -> str | None:
        """Try to get ID token from explicit AuthManager."""
        if self._auth_manager is None:
            return None

        if force_refresh:
            self._auth_manager.refresh_tokens()

        return self._auth_manager.id_token

    def _try_module_credentials(self, force_refresh: bool) -> str | None:
        """Try to get ID token from module-level CREDENTIALS."""
        import tokentoss

        creds = tokentoss.CREDENTIALS
        if creds is None:
            return None

        if force_refresh or (hasattr(creds, "expired") and creds.expired):
            creds.refresh(Request())

        return getattr(creds, "id_token", None)

    def _try_storage(self) -> str | None:
        """Try to get a non-expired ID token from file storage.

        Note: Storage alone cannot refresh tokens (no client config available).
        If the stored token is expired, returns None to let the caller raise.
        """
        storage = self._get_fallback_storage()
        try:
            token_data = storage.load()
        except Exception:
            return None

        if token_data is None:
            return None

        if token_data.is_expired:
            return None

        return token_data.id_token or None

    def _build_url(self, path: str) -> str:
        """Construct full URL from base_url and path.

        Args:
            path: Absolute URL or relative path.

        Returns:
            Full URL string.

        Raises:
            ValueError: If path is relative and no base_url is set.
        """
        if path.startswith(("http://", "https://")):
            return path

        if self.base_url is None:
            raise ValueError(
                f"Relative path {path!r} requires a base_url. "
                "Pass base_url to IAPClient() or use an absolute URL."
            )

        return f"{self.base_url}/{path.lstrip('/')}"

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        """Make an authenticated request with auto-retry on 401.

        Args:
            method: HTTP method (GET, POST, etc.).
            path: URL path or absolute URL.
            **kwargs: Passed to requests.Session.request().

        Returns:
            requests.Response object.
        """
        url = self._build_url(path)

        # Set timeout if not explicitly provided
        kwargs.setdefault("timeout", self.timeout)

        # Get token and make request
        id_token = self._get_id_token()
        headers = kwargs.pop("headers", None) or {}
        headers["Authorization"] = f"Bearer {id_token}"
        kwargs["headers"] = headers

        response = self._session.request(method, url, **kwargs)

        # Retry once on 401 with forced refresh
        if response.status_code == 401:
            try:
                refreshed_token = self._get_id_token(force_refresh=True)
                headers["Authorization"] = f"Bearer {refreshed_token}"
                kwargs["headers"] = headers
                response = self._session.request(method, url, **kwargs)
            except (NoCredentialsError, Exception):
                pass  # Return original 401 response

        return response

    # -- Public HTTP methods --

    def get(self, path: str, **kwargs: Any) -> requests.Response:
        """GET request with IAP authentication."""
        return self._request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> requests.Response:
        """POST request with IAP authentication."""
        return self._request("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> requests.Response:
        """PUT request with IAP authentication."""
        return self._request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> requests.Response:
        """DELETE request with IAP authentication."""
        return self._request("DELETE", path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> requests.Response:
        """PATCH request with IAP authentication."""
        return self._request("PATCH", path, **kwargs)

    def get_json(self, path: str, **kwargs: Any) -> Any:
        """GET request, return parsed JSON. Raises on non-2xx status."""
        response = self.get(path, **kwargs)
        response.raise_for_status()
        return response.json()

    def post_json(self, path: str, json: Any = None, **kwargs: Any) -> Any:
        """POST with JSON body, return parsed JSON. Raises on non-2xx status."""
        response = self.post(path, json=json, **kwargs)
        response.raise_for_status()
        return response.json()

    # -- Lifecycle --

    def close(self) -> None:
        """Close the underlying requests session."""
        self._session.close()

    def __enter__(self) -> IAPClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
