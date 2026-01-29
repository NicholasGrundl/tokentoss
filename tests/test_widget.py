"""Tests for tokentoss.widget module."""

from __future__ import annotations

import json
from unittest.mock import Mock, patch

import pytest

from tokentoss.widget import GoogleAuthWidget, CallbackServer
from tokentoss.auth_manager import ClientConfig, AuthManager
from tokentoss.storage import MemoryStorage, TokenData
from tokentoss.exceptions import TokenExchangeError


class TestCallbackServer:
    """Tests for CallbackServer."""

    def test_redirect_uri_without_port(self):
        """Test redirect_uri when no port is set."""
        server = CallbackServer()
        assert server.redirect_uri == "http://localhost"

    def test_redirect_uri_with_port(self):
        """Test redirect_uri when port is set."""
        server = CallbackServer()
        server.port = 12345
        assert server.redirect_uri == "http://127.0.0.1:12345"

    def test_reset(self):
        """Test reset clears state."""
        server = CallbackServer()
        server.auth_code = "test-code"
        server.state = "test-state"
        server.error = "test-error"
        server.callback_received = True

        server.reset()

        assert server.auth_code is None
        assert server.state is None
        assert server.error is None
        assert server.callback_received is False

    def test_check_callback_without_server(self):
        """Test check_callback when server not started."""
        server = CallbackServer()
        server.callback_received = True
        assert server.check_callback() is True

    def test_check_callback_copies_from_server(self):
        """Test check_callback copies state from server instance."""
        server = CallbackServer()
        # Mock the internal server
        mock_server = Mock()
        mock_server.auth_code = "test-code"
        mock_server.state = "test-state"
        mock_server.error = None
        mock_server.callback_received = True
        server._server = mock_server

        result = server.check_callback()

        assert result is True
        assert server.auth_code == "test-code"
        assert server.state == "test-state"


class TestGoogleAuthWidget:
    """Tests for GoogleAuthWidget."""

    @pytest.fixture
    def client_config(self):
        """Create a test client config."""
        return ClientConfig(
            client_id="test-client-id.apps.googleusercontent.com",
            client_secret="test-secret",
        )

    @pytest.fixture
    def widget(self, client_config):
        """Create a widget with memory storage."""
        with patch.object(CallbackServer, "start", return_value=True):
            return GoogleAuthWidget(
                client_config=client_config,
                storage=MemoryStorage(),
            )

    def test_init_with_client_secrets_path(self, tmp_path):
        """Test initialization with client_secrets_path."""
        secrets_file = tmp_path / "client_secrets.json"
        secrets_file.write_text(
            json.dumps(
                {
                    "installed": {
                        "client_id": "test-id",
                        "client_secret": "test-secret",
                    }
                }
            )
        )

        with patch.object(CallbackServer, "start", return_value=True):
            widget = GoogleAuthWidget(
                client_secrets_path=str(secrets_file),
                storage=MemoryStorage(),
            )

        assert widget._auth_manager.client_config.client_id == "test-id"
        assert widget.is_authenticated is False

    def test_init_with_existing_auth_manager(self, client_config):
        """Test initialization with existing AuthManager."""
        auth_manager = AuthManager(
            client_config=client_config,
            storage=MemoryStorage(),
        )

        with patch.object(CallbackServer, "start", return_value=True):
            widget = GoogleAuthWidget(auth_manager=auth_manager)

        assert widget.auth_manager is auth_manager

    def test_init_loads_existing_credentials(self, client_config):
        """Test that existing credentials are loaded on init."""
        storage = MemoryStorage()
        storage.save(
            TokenData(
                access_token="existing-token",
                id_token="existing-id",
                refresh_token="existing-refresh",
                expiry="2099-01-01T00:00:00+00:00",
                scopes=["openid"],
                user_email="existing@example.com",
            )
        )

        with patch.object(CallbackServer, "start", return_value=True):
            widget = GoogleAuthWidget(
                client_config=client_config,
                storage=storage,
            )

        assert widget.is_authenticated is True
        assert widget.user_email == "existing@example.com"
        assert "Signed in as" in widget.status

    def test_prepare_auth_generates_pkce(self, widget):
        """Test that prepare_auth generates PKCE pair."""
        widget.prepare_auth()

        assert widget._code_verifier is not None
        assert len(widget._code_verifier) > 0
        assert widget.auth_url != ""
        assert "code_challenge" in widget.auth_url
        assert widget.state != ""

    def test_prepare_auth_generates_unique_state(self, widget):
        """Test that each prepare_auth call generates unique state."""
        widget.prepare_auth()
        state1 = widget.state

        widget.prepare_auth()
        state2 = widget.state

        assert state1 != state2

    def test_prepare_auth_uses_server_redirect_uri(self, client_config):
        """Test that prepare_auth uses server redirect URI when available."""
        with patch.object(CallbackServer, "start", return_value=True):
            widget = GoogleAuthWidget(
                client_config=client_config,
                storage=MemoryStorage(),
            )
            widget._callback_server.port = 12345

        widget.prepare_auth()

        assert "127.0.0.1:12345" in widget.auth_url
        assert widget.show_manual_input is False

    def test_prepare_auth_fallback_to_localhost(self, client_config):
        """Test that prepare_auth falls back to localhost when server unavailable."""
        with patch.object(CallbackServer, "start", return_value=False):
            widget = GoogleAuthWidget(
                client_config=client_config,
                storage=MemoryStorage(),
            )

        widget.prepare_auth()

        assert "localhost" in widget.auth_url
        assert widget.show_manual_input is True

    @patch.object(AuthManager, "exchange_code")
    def test_auth_code_triggers_exchange(self, mock_exchange, widget):
        """Test that setting auth_code triggers token exchange."""
        widget.prepare_auth()
        mock_exchange.return_value = TokenData(
            access_token="new-access",
            id_token="new-id",
            refresh_token="new-refresh",
            expiry="2099-01-01T00:00:00+00:00",
            scopes=["openid"],
            user_email="user@example.com",
        )

        widget.auth_code = "test-auth-code"

        mock_exchange.assert_called_once()
        assert widget.is_authenticated is True

    @patch.object(AuthManager, "exchange_code")
    def test_exchange_error_sets_error_status(self, mock_exchange, widget):
        """Test that exchange errors are handled gracefully."""
        widget.prepare_auth()
        mock_exchange.side_effect = TokenExchangeError("invalid_grant")

        widget.auth_code = "bad-code"

        assert widget.is_authenticated is False
        assert "invalid_grant" in widget.error
        assert "failed" in widget.status.lower()

    def test_state_validation_rejects_mismatch(self, widget):
        """Test that mismatched state is rejected."""
        widget.prepare_auth()
        widget.received_state = "wrong-state"
        widget.auth_code = "some-code"

        assert "Invalid state" in widget.error
        assert widget.is_authenticated is False

    def test_sign_out_clears_state(self, client_config):
        """Test that sign_out clears all auth state."""
        storage = MemoryStorage()
        storage.save(
            TokenData(
                access_token="token",
                id_token="id",
                refresh_token="refresh",
                expiry="2099-01-01T00:00:00+00:00",
                scopes=[],
                user_email="user@example.com",
            )
        )

        with patch.object(CallbackServer, "start", return_value=True):
            widget = GoogleAuthWidget(
                client_config=client_config,
                storage=storage,
            )

        assert widget.is_authenticated is True

        widget.sign_out()

        assert widget.is_authenticated is False
        assert widget.user_email == ""
        assert widget.status == "Click to sign in"
        assert storage.load() is None

    def test_credentials_property(self, widget):
        """Test credentials property accessor."""
        assert widget.credentials is None

    def test_auth_manager_property(self, widget):
        """Test auth_manager property accessor."""
        assert widget.auth_manager is widget._auth_manager

    def test_handle_message_prepare_auth(self, widget):
        """Test message handler for prepare_auth."""
        with patch.object(widget, "prepare_auth") as mock_prepare:
            widget._handle_message(widget, {"type": "prepare_auth"}, [])
            mock_prepare.assert_called_once()

    def test_handle_message_sign_out(self, widget):
        """Test message handler for sign_out."""
        with patch.object(widget, "sign_out") as mock_sign_out:
            widget._handle_message(widget, {"type": "sign_out"}, [])
            mock_sign_out.assert_called_once()

    def test_handle_message_check_callback(self, widget):
        """Test message handler for check_callback."""
        with patch.object(widget, "_check_callback") as mock_check:
            widget._handle_message(widget, {"type": "check_callback"}, [])
            mock_check.assert_called_once()

    def test_exchange_without_code_verifier(self, widget):
        """Test that exchange fails gracefully without code_verifier."""
        widget._code_verifier = None
        widget._exchange_code("some-code", "http://localhost")

        assert "No code verifier" in widget.error
        assert widget.is_authenticated is False


@pytest.mark.integration
class TestCallbackServerIntegration:
    """Integration tests for CallbackServer with HTTP requests.

    These tests require real HTTP connections and may be slow.
    Run with: pytest -m integration
    """

    def test_server_receives_callback(self):
        """Test that server can receive an OAuth callback."""
        import urllib.request
        import time

        server = CallbackServer()
        try:
            server.start()
            assert server.port is not None

            # Simulate OAuth callback in a thread to avoid blocking
            import threading
            def make_request():
                url = f"http://127.0.0.1:{server.port}/?code=test-code&state=test-state"
                try:
                    urllib.request.urlopen(url, timeout=1)
                except Exception:
                    pass

            thread = threading.Thread(target=make_request)
            thread.start()
            thread.join(timeout=2)

            # Give server time to process
            time.sleep(0.2)

            assert server.check_callback() is True
            assert server.auth_code == "test-code"
            assert server.state == "test-state"
        finally:
            server.stop()

    def test_server_receives_error(self):
        """Test that server handles error callback."""
        import urllib.request
        import time
        import threading

        server = CallbackServer()
        try:
            server.start()

            def make_request():
                url = f"http://127.0.0.1:{server.port}/?error=access_denied"
                try:
                    urllib.request.urlopen(url, timeout=1)
                except Exception:
                    pass

            thread = threading.Thread(target=make_request)
            thread.start()
            thread.join(timeout=2)

            time.sleep(0.2)

            assert server.check_callback() is True
            assert server.error == "access_denied"
        finally:
            server.stop()
