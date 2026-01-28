"""Authentication manager for OAuth token handling."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, TYPE_CHECKING

import requests
from google.oauth2.credentials import Credentials

from .exceptions import TokenExchangeError, TokenRefreshError
from .storage import FileStorage, MemoryStorage, TokenData

if TYPE_CHECKING:
    from .storage import FileStorage, MemoryStorage


# Google OAuth endpoints
GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"

# Default scopes for IAP access
DEFAULT_SCOPES = [
    "openid",
    "email",
    "profile",
]


@dataclass
class ClientConfig:
    """OAuth client configuration loaded from client_secrets.json."""

    client_id: str
    client_secret: str
    auth_uri: str = GOOGLE_AUTH_URI
    token_uri: str = GOOGLE_TOKEN_URI
    redirect_uris: list[str] | None = None

    @classmethod
    def from_file(cls, path: str | Path) -> ClientConfig:
        """Load client config from client_secrets.json file.

        Args:
            path: Path to the client_secrets.json file.

        Returns:
            ClientConfig instance.

        Raises:
            FileNotFoundError: If file doesn't exist.
            ValueError: If file format is invalid.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Client secrets file not found: {path}")

        with open(path) as f:
            data = json.load(f)

        # Handle both "installed" (desktop app) and "web" formats
        if "installed" in data:
            config = data["installed"]
        elif "web" in data:
            config = data["web"]
        else:
            raise ValueError(
                "Invalid client_secrets.json format. "
                "Expected 'installed' or 'web' key."
            )

        return cls(
            client_id=config["client_id"],
            client_secret=config["client_secret"],
            auth_uri=config.get("auth_uri", GOOGLE_AUTH_URI),
            token_uri=config.get("token_uri", GOOGLE_TOKEN_URI),
            redirect_uris=config.get("redirect_uris"),
        )


def generate_pkce_pair() -> tuple[str, str]:
    """Generate PKCE code verifier and challenge.

    Returns:
        Tuple of (code_verifier, code_challenge).
    """
    # Generate random 32-byte code verifier
    code_verifier = secrets.token_urlsafe(32)

    # Create SHA256 hash of verifier
    digest = hashlib.sha256(code_verifier.encode()).digest()

    # Base64url encode the hash (no padding)
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()

    return code_verifier, code_challenge


class AuthManager:
    """Manages OAuth authentication, token exchange, and refresh."""

    def __init__(
        self,
        client_config: ClientConfig | None = None,
        client_secrets_path: str | Path | None = None,
        storage: FileStorage | MemoryStorage | None = None,
        scopes: list[str] | None = None,
    ) -> None:
        """Initialize AuthManager.

        Args:
            client_config: Pre-loaded client configuration.
            client_secrets_path: Path to client_secrets.json (alternative to client_config).
            storage: Token storage backend. Defaults to FileStorage.
            scopes: OAuth scopes. Defaults to DEFAULT_SCOPES.

        Raises:
            ValueError: If neither client_config nor client_secrets_path provided.
        """
        # Load client config
        if client_config is not None:
            self.client_config = client_config
        elif client_secrets_path is not None:
            self.client_config = ClientConfig.from_file(client_secrets_path)
        else:
            raise ValueError(
                "Either client_config or client_secrets_path must be provided"
            )

        # Set up storage
        self.storage = storage if storage is not None else FileStorage()

        # Set scopes
        self.scopes = scopes if scopes is not None else DEFAULT_SCOPES.copy()

        # State
        self._credentials: Credentials | None = None
        self._token_data: TokenData | None = None
        self.last_error: Exception | None = None

        # Try to load existing tokens
        self._load_from_storage()

    def _load_from_storage(self) -> None:
        """Load tokens from storage if available."""
        try:
            token_data = self.storage.load()
            if token_data is not None:
                self._token_data = token_data
                self._credentials = self._create_credentials(token_data)

                # Update module-level variable
                self._set_module_credentials()

        except Exception as e:
            self.last_error = e
            # Don't raise - just means we need to authenticate

    def _create_credentials(self, token_data: TokenData) -> Credentials:
        """Create google.oauth2.credentials.Credentials from TokenData."""
        return Credentials(
            token=token_data.access_token,
            refresh_token=token_data.refresh_token,
            id_token=token_data.id_token,
            token_uri=self.client_config.token_uri,
            client_id=self.client_config.client_id,
            client_secret=self.client_config.client_secret,
            scopes=token_data.scopes,
        )

    def _set_module_credentials(self) -> None:
        """Set the module-level CREDENTIALS variable."""
        import tokentoss

        tokentoss.CREDENTIALS = self._credentials

    @property
    def credentials(self) -> Credentials | None:
        """Get current credentials, refreshing if needed."""
        if self._credentials is None:
            return None

        # Check if expired and refresh if needed
        if self._token_data and self._token_data.is_expired:
            try:
                self.refresh_tokens()
            except TokenRefreshError:
                # Refresh failed, credentials are stale
                pass

        return self._credentials

    @property
    def token_data(self) -> TokenData | None:
        """Get current token data."""
        return self._token_data

    @property
    def user_email(self) -> str | None:
        """Get authenticated user's email."""
        if self._token_data:
            return self._token_data.user_email
        return None

    @property
    def is_authenticated(self) -> bool:
        """Check if we have valid credentials."""
        return self._credentials is not None

    @property
    def id_token(self) -> str | None:
        """Get the current ID token for IAP authentication."""
        if self._token_data:
            return self._token_data.id_token
        return None

    def get_authorization_url(
        self,
        code_challenge: str,
        redirect_uri: str = "http://localhost",
        state: str | None = None,
    ) -> str:
        """Generate OAuth authorization URL.

        Args:
            code_challenge: PKCE code challenge.
            redirect_uri: OAuth redirect URI.
            state: Optional state parameter for CSRF protection.

        Returns:
            Authorization URL to open in browser.
        """
        params = {
            "client_id": self.client_config.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "access_type": "offline",  # Get refresh token
            "prompt": "consent",  # Force consent to ensure refresh token
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }

        if state:
            params["state"] = state

        query = "&".join(f"{k}={requests.utils.quote(str(v))}" for k, v in params.items())
        return f"{self.client_config.auth_uri}?{query}"

    def exchange_code(
        self,
        auth_code: str,
        code_verifier: str,
        redirect_uri: str = "http://localhost",
    ) -> TokenData:
        """Exchange authorization code for tokens.

        Args:
            auth_code: Authorization code from OAuth callback.
            code_verifier: PKCE code verifier.
            redirect_uri: Redirect URI used in authorization request.

        Returns:
            TokenData with all tokens.

        Raises:
            TokenExchangeError: If exchange fails.
        """
        try:
            response = requests.post(
                self.client_config.token_uri,
                data={
                    "client_id": self.client_config.client_id,
                    "client_secret": self.client_config.client_secret,
                    "code": auth_code,
                    "code_verifier": code_verifier,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
                timeout=30,
            )

            if response.status_code != 200:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get("error_description", error_data.get("error", "Unknown error"))
                raise TokenExchangeError(f"Token exchange failed: {error_msg}")

            data = response.json()

            # Calculate expiry time
            expires_in = data.get("expires_in", 3600)
            expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            expiry = expiry.replace(microsecond=0)

            # Extract user email from ID token if present
            user_email = self._extract_email_from_id_token(data.get("id_token"))

            # Create token data
            token_data = TokenData(
                access_token=data["access_token"],
                id_token=data.get("id_token", ""),
                refresh_token=data.get("refresh_token", ""),
                expiry=expiry.isoformat(),
                scopes=data.get("scope", " ".join(self.scopes)).split(),
                user_email=user_email,
            )

            # Save tokens
            self._token_data = token_data
            self._credentials = self._create_credentials(token_data)
            self.storage.save(token_data)
            self._set_module_credentials()

            self.last_error = None
            return token_data

        except requests.RequestException as e:
            self.last_error = e
            raise TokenExchangeError(f"Network error during token exchange: {e}") from e
        except Exception as e:
            self.last_error = e
            if isinstance(e, TokenExchangeError):
                raise
            raise TokenExchangeError(f"Token exchange failed: {e}") from e

    def refresh_tokens(self) -> TokenData:
        """Refresh access and ID tokens using refresh token.

        Returns:
            Updated TokenData.

        Raises:
            TokenRefreshError: If refresh fails or no refresh token available.
        """
        if not self._token_data or not self._token_data.refresh_token:
            raise TokenRefreshError("No refresh token available")

        try:
            response = requests.post(
                self.client_config.token_uri,
                data={
                    "client_id": self.client_config.client_id,
                    "client_secret": self.client_config.client_secret,
                    "refresh_token": self._token_data.refresh_token,
                    "grant_type": "refresh_token",
                },
                timeout=30,
            )

            if response.status_code != 200:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get("error_description", error_data.get("error", "Unknown error"))
                raise TokenRefreshError(f"Token refresh failed: {error_msg}")

            data = response.json()

            # Calculate new expiry
            expires_in = data.get("expires_in", 3600)
            expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            expiry = expiry.replace(microsecond=0)

            # Extract user email from new ID token
            user_email = self._extract_email_from_id_token(data.get("id_token"))
            if not user_email:
                user_email = self._token_data.user_email

            # Update token data (refresh token may or may not be returned)
            self._token_data = TokenData(
                access_token=data["access_token"],
                id_token=data.get("id_token", self._token_data.id_token),
                refresh_token=data.get("refresh_token", self._token_data.refresh_token),
                expiry=expiry.isoformat(),
                scopes=data.get("scope", " ".join(self._token_data.scopes)).split() if isinstance(self._token_data.scopes, list) else self._token_data.scopes,
                user_email=user_email,
            )

            # Update credentials and save
            self._credentials = self._create_credentials(self._token_data)
            self.storage.save(self._token_data)
            self._set_module_credentials()

            self.last_error = None
            return self._token_data

        except requests.RequestException as e:
            self.last_error = e
            raise TokenRefreshError(f"Network error during token refresh: {e}") from e
        except Exception as e:
            self.last_error = e
            if isinstance(e, TokenRefreshError):
                raise
            raise TokenRefreshError(f"Token refresh failed: {e}") from e

    def _extract_email_from_id_token(self, id_token: str | None) -> str | None:
        """Extract email from ID token payload without validation.

        Note: This is for display purposes only. IAP validates the token.
        """
        if not id_token:
            return None

        try:
            # ID token is JWT: header.payload.signature
            parts = id_token.split(".")
            if len(parts) != 3:
                return None

            # Decode payload (add padding if needed)
            payload = parts[1]
            payload += "=" * (4 - len(payload) % 4)
            decoded = base64.urlsafe_b64decode(payload)
            claims = json.loads(decoded)

            return claims.get("email")

        except Exception:
            return None

    def clear(self) -> None:
        """Clear all stored credentials."""
        self._credentials = None
        self._token_data = None
        self.storage.clear()

        # Clear module-level variable
        import tokentoss
        tokentoss.CREDENTIALS = None
