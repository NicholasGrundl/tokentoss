"""Tests for tokentoss.auth_manager module."""

import json
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from tokentoss.auth_manager import (
    AuthManager,
    ClientConfig,
    generate_pkce_pair,
    GOOGLE_AUTH_URI,
    GOOGLE_TOKEN_URI,
)
from tokentoss.storage import MemoryStorage, TokenData
from tokentoss.exceptions import TokenExchangeError, TokenRefreshError


class TestClientConfig:
    """Tests for ClientConfig."""

    def test_from_file_installed(self, tmp_path):
        """Test loading from installed (desktop) app format."""
        secrets_file = tmp_path / "client_secrets.json"
        secrets_file.write_text(json.dumps({
            "installed": {
                "client_id": "test-client-id.apps.googleusercontent.com",
                "client_secret": "test-secret",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"],
            }
        }))

        config = ClientConfig.from_file(secrets_file)

        assert config.client_id == "test-client-id.apps.googleusercontent.com"
        assert config.client_secret == "test-secret"
        assert config.auth_uri == "https://accounts.google.com/o/oauth2/auth"

    def test_from_file_web(self, tmp_path):
        """Test loading from web app format."""
        secrets_file = tmp_path / "client_secrets.json"
        secrets_file.write_text(json.dumps({
            "web": {
                "client_id": "web-client-id.apps.googleusercontent.com",
                "client_secret": "web-secret",
            }
        }))

        config = ClientConfig.from_file(secrets_file)

        assert config.client_id == "web-client-id.apps.googleusercontent.com"

    def test_from_file_not_found(self, tmp_path):
        """Test FileNotFoundError on missing file."""
        with pytest.raises(FileNotFoundError):
            ClientConfig.from_file(tmp_path / "nonexistent.json")

    def test_from_file_invalid_format(self, tmp_path):
        """Test ValueError on invalid format."""
        secrets_file = tmp_path / "client_secrets.json"
        secrets_file.write_text(json.dumps({"invalid": {}}))

        with pytest.raises(ValueError, match="Invalid client_secrets.json"):
            ClientConfig.from_file(secrets_file)


class TestGeneratePKCE:
    """Tests for PKCE generation."""

    def test_generates_verifier_and_challenge(self):
        """Test PKCE pair generation."""
        verifier, challenge = generate_pkce_pair()

        # Verifier should be a URL-safe base64 string
        assert len(verifier) > 0
        assert all(c.isalnum() or c in "-_" for c in verifier)

        # Challenge should be different from verifier
        assert challenge != verifier

        # Challenge should be URL-safe base64 encoded
        assert all(c.isalnum() or c in "-_" for c in challenge)

    def test_generates_unique_pairs(self):
        """Test that each call generates unique pair."""
        pair1 = generate_pkce_pair()
        pair2 = generate_pkce_pair()

        assert pair1[0] != pair2[0]
        assert pair1[1] != pair2[1]


class TestAuthManager:
    """Tests for AuthManager."""

    @pytest.fixture
    def client_config(self):
        """Create a test client config."""
        return ClientConfig(
            client_id="test-client-id.apps.googleusercontent.com",
            client_secret="test-secret",
        )

    @pytest.fixture
    def auth_manager(self, client_config):
        """Create an AuthManager with memory storage."""
        return AuthManager(
            client_config=client_config,
            storage=MemoryStorage(),
        )

    def test_init_with_config(self, client_config):
        """Test initialization with ClientConfig."""
        manager = AuthManager(
            client_config=client_config,
            storage=MemoryStorage(),
        )

        assert manager.client_config == client_config
        assert manager.is_authenticated is False

    def test_init_with_secrets_path(self, tmp_path):
        """Test initialization with client_secrets_path."""
        secrets_file = tmp_path / "client_secrets.json"
        secrets_file.write_text(json.dumps({
            "installed": {
                "client_id": "test-id",
                "client_secret": "test-secret",
            }
        }))

        manager = AuthManager(
            client_secrets_path=secrets_file,
            storage=MemoryStorage(),
        )

        assert manager.client_config.client_id == "test-id"

    def test_init_requires_config(self):
        """Test that either config or path is required."""
        with pytest.raises(ValueError, match="Either client_config or client_secrets_path"):
            AuthManager(storage=MemoryStorage())

    def test_get_authorization_url(self, auth_manager):
        """Test authorization URL generation."""
        url = auth_manager.get_authorization_url(
            code_challenge="test-challenge",
            redirect_uri="http://localhost:8080",
        )

        assert "accounts.google.com" in url
        assert "client_id=test-client-id" in url
        assert "code_challenge=test-challenge" in url
        assert "code_challenge_method=S256" in url
        assert "access_type=offline" in url

    def test_get_authorization_url_with_state(self, auth_manager):
        """Test authorization URL with state parameter."""
        url = auth_manager.get_authorization_url(
            code_challenge="test-challenge",
            state="csrf-token-123",
        )

        assert "state=csrf-token-123" in url

    @patch("tokentoss.auth_manager.requests.post")
    def test_exchange_code_success(self, mock_post, auth_manager):
        """Test successful code exchange."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "access-token-123",
            "id_token": "eyJhbGciOiJSUzI1NiJ9.eyJlbWFpbCI6InRlc3RAZXhhbXBsZS5jb20ifQ.sig",
            "refresh_token": "refresh-token-123",
            "expires_in": 3600,
            "scope": "openid email",
        }
        mock_post.return_value = mock_response

        token_data = auth_manager.exchange_code(
            auth_code="auth-code-123",
            code_verifier="verifier-123",
        )

        assert token_data.access_token == "access-token-123"
        assert token_data.refresh_token == "refresh-token-123"
        assert auth_manager.is_authenticated is True

    @patch("tokentoss.auth_manager.requests.post")
    def test_exchange_code_extracts_email(self, mock_post, auth_manager):
        """Test that email is extracted from ID token."""
        # ID token with email claim (header.payload.signature format)
        import base64
        payload = base64.urlsafe_b64encode(
            json.dumps({"email": "user@example.com"}).encode()
        ).rstrip(b"=").decode()
        id_token = f"eyJhbGciOiJSUzI1NiJ9.{payload}.signature"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "access-token",
            "id_token": id_token,
            "refresh_token": "refresh-token",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response

        token_data = auth_manager.exchange_code("code", "verifier")

        assert token_data.user_email == "user@example.com"
        assert auth_manager.user_email == "user@example.com"

    @patch("tokentoss.auth_manager.requests.post")
    def test_exchange_code_failure(self, mock_post, auth_manager):
        """Test code exchange failure handling."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.content = b'{"error": "invalid_grant"}'
        mock_response.json.return_value = {"error": "invalid_grant"}
        mock_post.return_value = mock_response

        with pytest.raises(TokenExchangeError, match="invalid_grant"):
            auth_manager.exchange_code("bad-code", "verifier")

    @patch("tokentoss.auth_manager.requests.post")
    def test_refresh_tokens_success(self, mock_post, auth_manager):
        """Test successful token refresh."""
        # First, set up initial tokens
        auth_manager._token_data = TokenData(
            access_token="old-access",
            id_token="old-id",
            refresh_token="refresh-token-123",
            expiry="2020-01-01T00:00:00+00:00",  # Expired
            scopes=["openid"],
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new-access-token",
            "id_token": "new-id-token",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response

        token_data = auth_manager.refresh_tokens()

        assert token_data.access_token == "new-access-token"
        # Refresh token should be preserved if not returned
        assert token_data.refresh_token == "refresh-token-123"

    def test_refresh_tokens_no_refresh_token(self, auth_manager):
        """Test refresh fails without refresh token."""
        with pytest.raises(TokenRefreshError, match="No refresh token"):
            auth_manager.refresh_tokens()

    @patch("tokentoss.auth_manager.requests.post")
    def test_refresh_tokens_failure(self, mock_post, auth_manager):
        """Test token refresh failure."""
        auth_manager._token_data = TokenData(
            access_token="old",
            id_token="old",
            refresh_token="invalid-refresh",
            expiry="2020-01-01T00:00:00+00:00",
            scopes=[],
        )

        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.content = b'{"error": "invalid_grant"}'
        mock_response.json.return_value = {"error": "invalid_grant"}
        mock_post.return_value = mock_response

        with pytest.raises(TokenRefreshError):
            auth_manager.refresh_tokens()

    def test_clear(self, auth_manager):
        """Test clearing credentials."""
        auth_manager._token_data = TokenData(
            access_token="a",
            id_token="i",
            refresh_token="r",
            expiry="2099-01-01T00:00:00+00:00",
            scopes=[],
        )
        auth_manager._credentials = Mock()

        auth_manager.clear()

        assert auth_manager._token_data is None
        assert auth_manager._credentials is None
        assert auth_manager.storage.load() is None

    @patch("tokentoss.auth_manager.requests.post")
    def test_sets_module_credentials(self, mock_post, auth_manager):
        """Test that module-level CREDENTIALS is set on success."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "access-token",
            "id_token": "id-token",
            "refresh_token": "refresh-token",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response

        auth_manager.exchange_code("code", "verifier")

        import tokentoss
        assert tokentoss.CREDENTIALS is not None

    def test_loads_from_storage_on_init(self, client_config):
        """Test that tokens are loaded from storage on init."""
        storage = MemoryStorage()
        storage.save(TokenData(
            access_token="stored-access",
            id_token="stored-id",
            refresh_token="stored-refresh",
            expiry="2099-01-01T00:00:00+00:00",
            scopes=["openid"],
            user_email="stored@example.com",
        ))

        manager = AuthManager(
            client_config=client_config,
            storage=storage,
        )

        assert manager.is_authenticated is True
        assert manager.user_email == "stored@example.com"
