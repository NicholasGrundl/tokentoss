"""IAP-authenticated HTTP client.

This module provides the IAPClient which automatically handles Google ID token
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
    """HTTP client that automatically adds IAP authentication tokens.

    The client handles ID token discovery, injection, and auto-refresh.
    It provides a requests-like API (get, post, etc.) and JSON helpers.
    """

    def __init__(
        self,
        base_url: str | None = None,
        auth_manager: AuthManager | None = None,
    ) -> None:
        """Initialize IAPClient.

        Args:
            base_url: Optional base URL for relative paths.
            auth_manager: Optional AuthManager instance to use for credentials.
                If not provided, the client will attempt to discover credentials.
        """
        self.base_url = base_url.rstrip("/") if base_url else ""
        self._auth_manager = auth_manager
        self._session = requests.Session()

    def _get_id_token(self, force_refresh: bool = False) -> str:
        """Find and return a valid ID token.

        Discovery chain:
        1. Explicit auth_manager passed in constructor
        2. Module-level tokentoss.CREDENTIALS variable
        3. Token file at TOKENTOSS_TOKEN_FILE environment variable
        4. Token file at default location (~/.config/tokentoss/tokens.json)

        Args:
            force_refresh: Whether to force a token refresh if possible.

        Returns:
            A valid ID token string.

        Raises:
            NoCredentialsError: If no valid credentials found or refresh fails.
        """
        # 1. Check explicit auth_manager
        if self._auth_manager:
            if force_refresh:
                try:
                    self._auth_manager.refresh_tokens()
                except Exception as e:
                    raise NoCredentialsError(f"Failed to refresh explicit AuthManager: {e}") from e
            
            token = self._auth_manager.id_token
            if token:
                return token

        # 2. Check module-level credentials
        import tokentoss
        if tokentoss.CREDENTIALS:
            creds = tokentoss.CREDENTIALS
            if force_refresh or creds.expired:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    # If it has no refresh token or other issue
                    if not force_refresh and creds.id_token:
                        # Maybe it's not actually expired according to IAP even if creds.expired is true
                        # (clock skew, etc.), but usually we want to refresh.
                        pass
                    else:
                        raise NoCredentialsError(f"Failed to refresh module-level credentials: {e}") from e
            
            if creds.id_token:
                return creds.id_token

        # 3 & 4. Check storage (default or env var)
        token_path = os.environ.get("TOKENTOSS_TOKEN_FILE")
        storage = FileStorage(path=token_path)
        try:
            token_data = storage.load()
            if token_data and token_data.id_token:
                if not token_data.is_expired:
                    return token_data.id_token
                
                # If expired and we don't have an AuthManager/Credentials with refresh info,
                # we are out of luck for auto-refresh.
                if force_refresh:
                    raise NoCredentialsError(
                        "Stored ID token is expired and no refresh credentials available."
                    )
                
                # We could try to return it anyway if not force_refresh, 
                # but it will likely fail with 401 anyway.
                # Let's be strict.
        except Exception as e:
            # Storage error or invalid format
            if force_refresh:
                raise NoCredentialsError(f"Error loading stored tokens: {e}") from e

        raise NoCredentialsError(
            "No valid credentials found. Use GoogleAuthWidget to authenticate."
        )

    def _build_url(self, path: str) -> str:
        """Construct full URL from base_url and path."""
        if path.startswith(("http://", "https://")):
            return path
        
        path = path.lstrip("/")
        if self.base_url:
            return f"{self.base_url}/{path}"
        return path

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        """Internal request handler with auth injection and auto-refresh."""
        url = self._build_url(path)
        
        # Get token (may refresh internally if using AuthManager or Credentials)
        id_token = self._get_id_token()

        # Add auth header
        headers = kwargs.get("headers", {}).copy()
        headers["Authorization"] = f"Bearer {id_token}"
        kwargs["headers"] = headers

        response = self._session.request(method, url, **kwargs)

        # Retry once on 401 if we can refresh
        if response.status_code == 401:
            try:
                id_token = self._get_id_token(force_refresh=True)
                headers["Authorization"] = f"Bearer {id_token}"
                kwargs["headers"] = headers
                response = self._session.request(method, url, **kwargs)
            except NoCredentialsError:
                # Can't refresh, return the original 401
                pass
            except Exception:
                # Other errors during refresh, return the original 401
                pass

        return response

    def get(self, path: str, **kwargs) -> requests.Response:
        """Perform a GET request with IAP authentication."""
        return self._request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> requests.Response:
        """Perform a POST request with IAP authentication."""
        return self._request("POST", path, **kwargs)

    def put(self, path: str, **kwargs) -> requests.Response:
        """Perform a PUT request with IAP authentication."""
        return self._request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs) -> requests.Response:
        """Perform a DELETE request with IAP authentication."""
        return self._request("DELETE", path, **kwargs)

    def patch(self, path: str, **kwargs) -> requests.Response:
        """Perform a PATCH request with IAP authentication."""
        return self._request("PATCH", path, **kwargs)

    def get_json(self, path: str, **kwargs) -> Any:
        """Perform a GET request and return the JSON response.

        Raises:
            requests.HTTPError: If the response status is not successful.
        """
        response = self.get(path, **kwargs)
        response.raise_for_status()
        return response.json()

    def post_json(self, path: str, json: Any = None, **kwargs) -> Any:
        """Perform a POST request with JSON body and return the JSON response.

        Raises:
            requests.HTTPError: If the response status is not successful.
        """
        response = self.post(path, json=json, **kwargs)
        response.raise_for_status()
        return response.json()