"""Tests for tokentoss.widget module."""

from __future__ import annotations

import json
import threading
import time
import urllib.request
from datetime import datetime, timedelta, timezone

import pytest

from tokentoss.auth_manager import AuthManager, ClientConfig
from tokentoss.exceptions import TokenExchangeError
from tokentoss.storage import MemoryStorage, TokenData
from tokentoss.widget import CallbackServer, GoogleAuthWidget

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_token_data(**overrides):
    """Create a TokenData with sensible defaults."""
    defaults = {
        "access_token": "access-token",
        "id_token": "id-token",
        "refresh_token": "refresh-token",
        "expiry": "2099-01-01T00:00:00+00:00",
        "scopes": ["openid"],
        "user_email": "user@example.com",
    }
    defaults.update(overrides)
    return TokenData(**defaults)


def _mock_exchange(auth_manager, mocker, **token_overrides):
    """Mock exchange_code so it also updates the auth manager's internal state.

    When exchange_code is mocked, the auth manager's _token_data doesn't get
    set. This helper creates a side_effect that simulates the real behavior.
    """
    token_data = _make_token_data(**token_overrides)

    def side_effect(auth_code, code_verifier, redirect_uri="http://localhost"):
        auth_manager._token_data = token_data
        return token_data

    return mocker.patch.object(auth_manager, "exchange_code", side_effect=side_effect)


# ---------------------------------------------------------------------------
# CallbackServer unit tests
# ---------------------------------------------------------------------------


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

    def test_check_callback_copies_from_server(self, mocker):
        """Test check_callback copies state from server instance."""
        server = CallbackServer()
        mock_server = mocker.Mock()
        mock_server.auth_code = "test-code"
        mock_server.state = "test-state"
        mock_server.error = None
        mock_server.callback_received = True
        server._server = mock_server

        result = server.check_callback()

        assert result is True
        assert server.auth_code == "test-code"
        assert server.state == "test-state"

    def test_stop_copies_results_from_server(self, mocker):
        """Test stop copies final state from server."""
        server = CallbackServer()
        mock_server = mocker.Mock()
        mock_server.auth_code = "final-code"
        mock_server.state = "final-state"
        mock_server.error = None
        mock_server.callback_received = True
        server._server = mock_server

        server.stop()

        assert server.auth_code == "final-code"
        assert server.state == "final-state"
        assert server._server is None


# ---------------------------------------------------------------------------
# GoogleAuthWidget unit tests
# ---------------------------------------------------------------------------


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
    def widget(self, client_config, mocker):
        """Create a widget with memory storage and mocked server."""
        mocker.patch.object(CallbackServer, "start", return_value=True)
        return GoogleAuthWidget(
            client_config=client_config,
            storage=MemoryStorage(),
        )

    def test_init_with_client_secrets_path(self, tmp_path, mocker):
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

        mocker.patch.object(CallbackServer, "start", return_value=True)
        widget = GoogleAuthWidget(
            client_secrets_path=str(secrets_file),
            storage=MemoryStorage(),
        )

        assert widget._auth_manager.client_config.client_id == "test-id"
        assert widget.is_authenticated is False

    def test_init_with_existing_auth_manager(self, client_config, mocker):
        """Test initialization with existing AuthManager."""
        auth_manager = AuthManager(
            client_config=client_config,
            storage=MemoryStorage(),
        )

        mocker.patch.object(CallbackServer, "start", return_value=True)
        widget = GoogleAuthWidget(auth_manager=auth_manager)

        assert widget.auth_manager is auth_manager

    def test_init_loads_existing_credentials(self, client_config, mocker):
        """Test that existing credentials are loaded on init."""
        storage = MemoryStorage()
        storage.save(_make_token_data(user_email="existing@example.com"))

        mocker.patch.object(CallbackServer, "start", return_value=True)
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

    def test_prepare_auth_uses_server_redirect_uri(self, client_config, mocker):
        """Test that prepare_auth uses server redirect URI when available."""
        mocker.patch.object(CallbackServer, "start", return_value=True)
        widget = GoogleAuthWidget(
            client_config=client_config,
            storage=MemoryStorage(),
        )
        widget._callback_server.port = 12345

        widget.prepare_auth()

        # URL-encoded: colon becomes %3A
        assert "127.0.0.1%3A12345" in widget.auth_url
        assert widget.show_manual_input is False

    def test_prepare_auth_fallback_to_localhost(self, client_config, mocker):
        """Test that prepare_auth falls back to localhost when server unavailable."""
        mocker.patch.object(CallbackServer, "start", return_value=False)
        widget = GoogleAuthWidget(
            client_config=client_config,
            storage=MemoryStorage(),
        )

        widget.prepare_auth()

        assert "localhost" in widget.auth_url
        assert widget.show_manual_input is True

    def test_auth_code_triggers_exchange(self, widget, mocker):
        """Test that setting auth_code triggers token exchange."""
        widget.prepare_auth()
        mocker.patch.object(
            widget._auth_manager,
            "exchange_code",
            return_value=_make_token_data(),
        )

        widget.auth_code = "test-auth-code"

        widget._auth_manager.exchange_code.assert_called_once()
        assert widget.is_authenticated is True

    def test_exchange_error_sets_error_status(self, widget, mocker):
        """Test that exchange errors are handled gracefully."""
        widget.prepare_auth()
        mocker.patch.object(
            widget._auth_manager,
            "exchange_code",
            side_effect=TokenExchangeError("invalid_grant"),
        )

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

    def test_sign_out_clears_state(self, client_config, mocker):
        """Test that sign_out clears all auth state."""
        storage = MemoryStorage()
        storage.save(_make_token_data())

        mocker.patch.object(CallbackServer, "start", return_value=True)
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

    def test_handle_message_prepare_auth(self, widget, mocker):
        """Test message handler for prepare_auth."""
        spy = mocker.spy(widget, "prepare_auth")
        widget._handle_message(widget, {"type": "prepare_auth"}, [])
        spy.assert_called_once()

    def test_handle_message_sign_out(self, widget, mocker):
        """Test message handler for sign_out."""
        spy = mocker.spy(widget, "sign_out")
        widget._handle_message(widget, {"type": "sign_out"}, [])
        spy.assert_called_once()

    def test_handle_message_check_callback(self, widget, mocker):
        """Test message handler for check_callback."""
        spy = mocker.spy(widget, "_check_callback")
        widget._handle_message(widget, {"type": "check_callback"}, [])
        spy.assert_called_once()

    def test_exchange_without_code_verifier(self, widget):
        """Test that exchange fails gracefully without code_verifier."""
        widget._code_verifier = None
        widget._exchange_code("some-code", "http://localhost")

        assert "No code verifier" in widget.error
        assert widget.is_authenticated is False


# ---------------------------------------------------------------------------
# Flow simulation tests (Layer 2)
# ---------------------------------------------------------------------------


class TestAuthFlowSimulation:
    """Simulate the full auth flow as the JS frontend would drive it."""

    @pytest.fixture
    def client_config(self):
        return ClientConfig(
            client_id="test-client-id.apps.googleusercontent.com",
            client_secret="test-secret",
        )

    @pytest.fixture
    def widget(self, client_config, mocker):
        mocker.patch.object(CallbackServer, "start", return_value=True)
        return GoogleAuthWidget(
            client_config=client_config,
            storage=MemoryStorage(),
        )

    def test_full_flow_via_manual_paste(self, widget, mocker):
        """Simulate: button click → prepare → paste URL → exchange → authenticated."""
        _mock_exchange(widget._auth_manager, mocker, user_email="flow@example.com")

        # 1. JS sends prepare_auth message (button click)
        widget._handle_message(widget, {"type": "prepare_auth"}, [])
        assert widget.auth_url != ""
        assert widget.status == "Waiting for authentication..."
        assert widget._code_verifier is not None

        # 2. JS sets auth_code (simulating manual paste)
        widget.auth_code = "manual-auth-code"

        # 3. Verify authenticated
        assert widget.is_authenticated is True
        assert widget.user_email == "flow@example.com"
        assert "Signed in as flow@example.com" in widget.status
        assert widget.error == ""
        assert widget.show_manual_input is False

    def test_full_flow_via_callback_server(self, widget, mocker):
        """Simulate: button click → prepare → server receives code → authenticated."""
        _mock_exchange(widget._auth_manager, mocker, user_email="server@example.com")

        # 1. JS sends prepare_auth
        widget._handle_message(widget, {"type": "prepare_auth"}, [])
        assert widget.auth_url != ""

        # 2. Simulate server receiving the callback
        widget._callback_server.auth_code = "server-auth-code"
        widget._callback_server.state = widget.state
        widget._callback_server.callback_received = True
        if widget._callback_server._server:
            widget._callback_server._server.auth_code = "server-auth-code"
            widget._callback_server._server.state = widget.state
            widget._callback_server._server.callback_received = True

        # 3. JS detects popup closed, sends check_callback
        widget._handle_message(widget, {"type": "check_callback"}, [])

        # 4. Verify authenticated
        assert widget.is_authenticated is True
        assert widget.user_email == "server@example.com"

    def test_sign_out_and_reauthenticate(self, widget, mocker):
        """Test full sign-out → re-authenticate cycle."""
        _mock_exchange(widget._auth_manager, mocker, user_email="first@example.com")

        # First auth
        widget._handle_message(widget, {"type": "prepare_auth"}, [])
        widget.auth_code = "first-code"
        assert widget.is_authenticated is True
        assert widget.user_email == "first@example.com"

        # Sign out
        widget._handle_message(widget, {"type": "sign_out"}, [])
        assert widget.is_authenticated is False
        assert widget.user_email == ""
        assert widget.status == "Click to sign in"

        # Re-authenticate with different user
        _mock_exchange(widget._auth_manager, mocker, user_email="second@example.com")
        widget._handle_message(widget, {"type": "prepare_auth"}, [])
        widget.auth_code = "second-code"
        assert widget.is_authenticated is True
        assert widget.user_email == "second@example.com"

    def test_exchange_failure_then_retry(self, widget, mocker):
        """Test: first exchange fails, user retries and succeeds."""
        # First attempt fails
        mocker.patch.object(
            widget._auth_manager,
            "exchange_code",
            side_effect=TokenExchangeError("network_error"),
        )

        widget._handle_message(widget, {"type": "prepare_auth"}, [])
        widget.auth_code = "bad-code"

        assert widget.is_authenticated is False
        assert "network_error" in widget.error

        # Retry succeeds
        _mock_exchange(widget._auth_manager, mocker)

        widget._handle_message(widget, {"type": "prepare_auth"}, [])
        widget.auth_code = "good-code"

        assert widget.is_authenticated is True
        assert widget.error == ""

    def test_popup_closed_without_auth(self, widget):
        """Test: user closes popup without completing auth."""
        widget._handle_message(widget, {"type": "prepare_auth"}, [])
        assert widget.status == "Waiting for authentication..."

        # Popup closed, no callback received
        widget._handle_message(widget, {"type": "check_callback"}, [])

        # Should show manual input fallback
        assert widget.is_authenticated is False
        assert widget.show_manual_input is True

    def test_multiple_prepare_auth_regenerates_pkce(self, widget):
        """Test that each prepare_auth generates fresh PKCE pair."""
        widget.prepare_auth()
        verifier1 = widget._code_verifier
        state1 = widget.state

        widget.prepare_auth()
        verifier2 = widget._code_verifier
        state2 = widget.state

        assert verifier1 != verifier2
        assert state1 != state2

    def test_auth_code_without_prepare_fails(self, widget):
        """Test setting auth_code without calling prepare_auth first."""
        widget._code_verifier = None
        widget.auth_code = "orphan-code"

        assert widget.is_authenticated is False
        assert "No code verifier" in widget.error

    def test_callback_server_error_propagated(self, widget):
        """Test that OAuth error from callback is shown."""
        widget._handle_message(widget, {"type": "prepare_auth"}, [])

        # Simulate server receiving an error
        widget._callback_server.error = "access_denied"
        widget._callback_server.callback_received = True
        if widget._callback_server._server:
            widget._callback_server._server.error = "access_denied"
            widget._callback_server._server.callback_received = True

        widget._handle_message(widget, {"type": "check_callback"}, [])

        assert widget.is_authenticated is False
        assert "access_denied" in widget.error

    def test_callback_state_mismatch_rejected(self, widget):
        """Test that callback with wrong state is rejected."""
        widget._handle_message(widget, {"type": "prepare_auth"}, [])

        # Simulate server receiving code with wrong state
        widget._callback_server.auth_code = "some-code"
        widget._callback_server.state = "wrong-state"
        widget._callback_server.callback_received = True
        if widget._callback_server._server:
            widget._callback_server._server.auth_code = "some-code"
            widget._callback_server._server.state = "wrong-state"
            widget._callback_server._server.callback_received = True

        widget._handle_message(widget, {"type": "check_callback"}, [])

        assert widget.is_authenticated is False
        assert "Invalid state" in widget.error


# ---------------------------------------------------------------------------
# Integration tests (Layer 3) - real HTTP to CallbackServer
# ---------------------------------------------------------------------------


def _http_get(url: str) -> None:
    """Make an HTTP GET request, ignoring errors."""
    try:
        urllib.request.urlopen(url, timeout=2)
    except Exception:
        pass


@pytest.mark.integration
class TestCallbackServerIntegration:
    """Integration tests for CallbackServer with real HTTP.

    Run with: pytest -m integration -v
    """

    def test_server_starts_on_available_port(self):
        """Test server starts and binds to a real port."""
        server = CallbackServer()
        try:
            assert server.start() is True
            assert server.port is not None
            assert server.port > 0
            assert server.redirect_uri.startswith("http://127.0.0.1:")
        finally:
            server.stop()

    def test_server_receives_callback_with_code(self):
        """Test server receives auth code from HTTP callback."""
        server = CallbackServer()
        try:
            server.start()
            url = f"http://127.0.0.1:{server.port}/?code=test-code&state=test-state"

            t = threading.Thread(target=_http_get, args=(url,))
            t.start()
            t.join(timeout=3)

            # Allow server to process
            time.sleep(0.2)

            assert server.check_callback() is True
            assert server.auth_code == "test-code"
            assert server.state == "test-state"
            assert server.error is None
        finally:
            server.stop()

    def test_server_receives_error_callback(self):
        """Test server handles OAuth error parameter."""
        server = CallbackServer()
        try:
            server.start()
            url = f"http://127.0.0.1:{server.port}/?error=access_denied"

            t = threading.Thread(target=_http_get, args=(url,))
            t.start()
            t.join(timeout=3)

            time.sleep(0.2)

            assert server.check_callback() is True
            assert server.error == "access_denied"
            assert server.auth_code is None
        finally:
            server.stop()

    def test_server_ignores_no_query_params(self):
        """Test server ignores requests with no query params (e.g. favicon)."""
        server = CallbackServer()
        try:
            server.start()
            url = f"http://127.0.0.1:{server.port}/"

            t = threading.Thread(target=_http_get, args=(url,))
            t.start()
            t.join(timeout=3)

            time.sleep(0.2)

            # Requests without code or error params (like /favicon.ico)
            # should not be treated as callbacks
            assert server.check_callback() is False
            assert server.auth_code is None
            assert server.error is None
        finally:
            server.stop()

    def test_server_reset_allows_reuse(self):
        """Test server can be reset and reused for a new auth flow."""
        server = CallbackServer()
        try:
            server.start()

            # First callback
            url1 = f"http://127.0.0.1:{server.port}/?code=first-code"
            t = threading.Thread(target=_http_get, args=(url1,))
            t.start()
            t.join(timeout=3)
            time.sleep(0.2)

            assert server.check_callback() is True
            assert server.auth_code == "first-code"

            # Stop and restart for second flow
            server.stop()
            server = CallbackServer()
            server.start()

            url2 = f"http://127.0.0.1:{server.port}/?code=second-code"
            t = threading.Thread(target=_http_get, args=(url2,))
            t.start()
            t.join(timeout=3)
            time.sleep(0.2)

            assert server.check_callback() is True
            assert server.auth_code == "second-code"
        finally:
            server.stop()

    def test_server_shuts_down_cleanly(self):
        """Test server shuts down without hanging."""
        server = CallbackServer()
        server.start()
        assert server.port is not None

        # Stop should return promptly
        server.stop()

        assert server._server is None
        assert server._thread is None
