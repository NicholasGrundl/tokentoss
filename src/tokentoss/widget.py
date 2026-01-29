"""Google OAuth authentication widget for Jupyter notebooks."""

from __future__ import annotations

import logging
import secrets
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlparse

import anywidget
import traitlets

from .auth_manager import AuthManager, ClientConfig, generate_pkce_pair
from .exceptions import TokenExchangeError

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .storage import FileStorage, MemoryStorage


# HTML page served by the callback server after successful auth
CALLBACK_SUCCESS_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>Authentication Complete</title>
    <style>
        body {
            font-family: system-ui, -apple-system, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            background: #f8f9fa;
        }
        .container {
            text-align: center;
            padding: 40px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .success { color: #059669; }
        h1 { margin: 0 0 16px; font-size: 24px; }
        p { color: #6b7280; margin: 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="success">Authentication Successful</h1>
        <p>You can close this window.</p>
    </div>
    <script>
        // Close the window after a short delay
        setTimeout(function() { window.close(); }, 1500);
    </script>
</body>
</html>"""


class _CallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler for OAuth callback."""

    def log_message(self, format, *args):
        """Suppress logging."""
        pass

    def do_GET(self):
        """Handle GET request from OAuth callback."""
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        # Extract auth code and state
        auth_code = params.get("code", [None])[0]
        state = params.get("state", [None])[0]
        error = params.get("error", [None])[0]

        logger.debug(
            "Callback received: code=%s, state=%s, error=%s",
            bool(auth_code),
            bool(state),
            error,
        )

        # Store in server instance
        self.server.auth_code = auth_code
        self.server.state = state
        self.server.error = error
        self.server.callback_received = True

        # Send response
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        if error:
            error_html = f"""<!DOCTYPE html>
<html><head><title>Authentication Error</title></head>
<body style="font-family: sans-serif; text-align: center; padding: 40px;">
<h1 style="color: #dc2626;">Authentication Failed</h1>
<p>Error: {error}</p>
</body></html>"""
            self.wfile.write(error_html.encode())
        else:
            self.wfile.write(CALLBACK_SUCCESS_HTML.encode())


class CallbackServer:
    """Temporary HTTP server to capture OAuth callback.

    Starts a local HTTP server on a random available port to receive
    the OAuth authorization code callback.
    """

    def __init__(self):
        self.port: int | None = None
        self.auth_code: str | None = None
        self.state: str | None = None
        self.error: str | None = None
        self.callback_received: bool = False
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> bool:
        """Start the callback server on a random available port.

        Returns:
            True if server started successfully, False otherwise.
        """
        try:
            # Find an available port
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", 0))
                self.port = s.getsockname()[1]

            # Create server
            self._server = HTTPServer(("127.0.0.1", self.port), _CallbackHandler)
            self._server.auth_code = None
            self._server.state = None
            self._server.error = None
            self._server.callback_received = False

            # Start in background thread
            self._thread = threading.Thread(target=self._serve, daemon=True)
            self._thread.start()

            logger.debug("Callback server started on port %s", self.port)
            return True

        except Exception:
            logger.warning("Failed to start callback server", exc_info=True)
            self.port = None
            return False

    def _serve(self):
        """Serve requests using serve_forever (stoppable via shutdown)."""
        if self._server:
            self._server.serve_forever(poll_interval=0.5)

    def stop(self):
        """Stop the callback server."""
        server = self._server
        if server:
            logger.debug("Stopping callback server on port %s", self.port)
            # Copy results from server
            self.auth_code = server.auth_code
            self.state = server.state
            self.error = server.error
            self.callback_received = server.callback_received

            # shutdown() signals serve_forever() to exit
            server.shutdown()
            self._server = None

        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

    def check_callback(self) -> bool:
        """Check if callback has been received.

        Returns:
            True if callback received, False otherwise.
        """
        if self._server:
            self.auth_code = self._server.auth_code
            self.state = self._server.state
            self.error = self._server.error
            self.callback_received = self._server.callback_received
        return self.callback_received

    @property
    def redirect_uri(self) -> str:
        """Get the redirect URI for this server."""
        if self.port:
            return f"http://127.0.0.1:{self.port}"
        return "http://localhost"

    def reset(self):
        """Reset the server state for a new auth flow."""
        self.auth_code = None
        self.state = None
        self.error = None
        self.callback_received = False
        if self._server:
            self._server.auth_code = None
            self._server.state = None
            self._server.error = None
            self._server.callback_received = False


# JavaScript ESM for the widget
_ESM = """
function render({ model, el }) {
    // Create widget container
    const container = document.createElement('div');
    container.className = 'tokentoss-widget';

    // Status display
    const statusEl = document.createElement('div');
    statusEl.className = 'tokentoss-status';

    // Sign-in button
    const button = document.createElement('button');
    button.className = 'tokentoss-button';
    button.innerHTML = `
        <svg viewBox="0 0 24 24" width="18" height="18" style="margin-right: 8px;">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
        </svg>
        Sign in with Google`;

    // Manual input section (hidden by default)
    const manualSection = document.createElement('div');
    manualSection.className = 'tokentoss-manual';
    manualSection.innerHTML = `
        <p>After signing in, copy the URL from the popup's address bar and paste it here:</p>
        <input type="text" class="tokentoss-manual-input" placeholder="http://localhost?code=...">
        <button class="tokentoss-manual-submit">Submit</button>
    `;

    // Sign-out link
    const signOutLink = document.createElement('a');
    signOutLink.href = '#';
    signOutLink.className = 'tokentoss-signout';
    signOutLink.textContent = 'Sign out';

    // Error display
    const errorEl = document.createElement('div');
    errorEl.className = 'tokentoss-error';

    // Assemble DOM
    container.appendChild(statusEl);
    container.appendChild(button);
    container.appendChild(manualSection);
    container.appendChild(signOutLink);
    container.appendChild(errorEl);
    el.appendChild(container);

    // State
    let popup = null;
    let pollInterval = null;

    // Update UI based on model state
    function updateUI() {
        const isAuthenticated = model.get('is_authenticated');
        const status = model.get('status');
        const error = model.get('error');
        const showManual = model.get('show_manual_input');

        statusEl.textContent = status;
        errorEl.textContent = error;
        errorEl.style.display = error ? 'block' : 'none';

        if (isAuthenticated) {
            button.style.display = 'none';
            manualSection.style.display = 'none';
            signOutLink.style.display = 'inline';
        } else {
            button.style.display = 'inline-flex';
            signOutLink.style.display = 'none';
            manualSection.style.display = showManual ? 'block' : 'none';
        }
    }

    // Handle sign-in button click
    button.addEventListener('click', () => {
        model.send({ type: 'prepare_auth' });
    });

    // Handle sign-out click
    signOutLink.addEventListener('click', (e) => {
        e.preventDefault();
        model.send({ type: 'sign_out' });
    });

    // Handle manual URL submission
    const manualInput = manualSection.querySelector('.tokentoss-manual-input');
    const manualSubmit = manualSection.querySelector('.tokentoss-manual-submit');

    manualSubmit.addEventListener('click', () => {
        const input = manualInput.value.trim();
        if (!input) return;

        try {
            const url = new URL(input);
            const code = url.searchParams.get('code');
            const state = url.searchParams.get('state');

            if (code) {
                model.set('received_state', state || '');
                model.set('auth_code', code);
                model.save_changes();
                manualInput.value = '';
            }
        } catch (e) {
            // Not a valid URL, treat as raw auth code
            model.set('auth_code', input);
            model.save_changes();
            manualInput.value = '';
        }
    });

    // Open popup when auth_url changes
    function onAuthUrlChange() {
        const authUrl = model.get('auth_url');
        if (!authUrl) return;

        // Open popup
        const width = 500;
        const height = 600;
        const left = (screen.width - width) / 2;
        const top = (screen.height - height) / 2;

        popup = window.open(
            authUrl,
            'tokentoss-oauth',
            `width=${width},height=${height},left=${left},top=${top},popup=yes`
        );

        // Poll for popup close
        startPolling();
    }

    function startPolling() {
        stopPolling();
        pollInterval = setInterval(() => {
            // Check if popup closed
            if (popup && popup.closed) {
                stopPolling();
                popup = null;
                // Tell Python to check for callback
                model.send({ type: 'check_callback' });
            }
        }, 500);
    }

    function stopPolling() {
        if (pollInterval) {
            clearInterval(pollInterval);
            pollInterval = null;
        }
    }

    // Model change observers
    model.on('change:auth_url', onAuthUrlChange);
    model.on('change:status', updateUI);
    model.on('change:error', updateUI);
    model.on('change:is_authenticated', updateUI);
    model.on('change:show_manual_input', updateUI);

    // Initial render
    updateUI();

    // Cleanup on destroy
    return () => {
        stopPolling();
        if (popup && !popup.closed) {
            popup.close();
        }
    };
}

export default { render };
"""

# CSS styles for the widget
_CSS = """
.tokentoss-widget {
    font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    padding: 16px;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    background: #ffffff;
    max-width: 400px;
}

.tokentoss-status {
    margin-bottom: 12px;
    font-size: 14px;
    color: #374151;
}

.tokentoss-button {
    display: inline-flex;
    align-items: center;
    padding: 10px 20px;
    font-size: 14px;
    font-weight: 500;
    color: #374151;
    background: #ffffff;
    border: 1px solid #dadce0;
    border-radius: 4px;
    cursor: pointer;
    transition: background 0.2s, box-shadow 0.2s;
}

.tokentoss-button:hover {
    background: #f8f9fa;
    box-shadow: 0 1px 2px rgba(0,0,0,0.1);
}

.tokentoss-button:active {
    background: #f1f3f4;
}

.tokentoss-manual {
    display: none;
    margin-top: 16px;
    padding-top: 16px;
    border-top: 1px solid #e5e7eb;
}

.tokentoss-manual p {
    margin: 0 0 8px;
    font-size: 13px;
    color: #6b7280;
}

.tokentoss-manual-input {
    width: 100%;
    padding: 8px 12px;
    font-size: 13px;
    border: 1px solid #d1d5db;
    border-radius: 4px;
    box-sizing: border-box;
}

.tokentoss-manual-input:focus {
    outline: none;
    border-color: #4285f4;
    box-shadow: 0 0 0 2px rgba(66, 133, 244, 0.2);
}

.tokentoss-manual-submit {
    margin-top: 8px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 500;
    color: #ffffff;
    background: #4285f4;
    border: none;
    border-radius: 4px;
    cursor: pointer;
}

.tokentoss-manual-submit:hover {
    background: #3574e2;
}

.tokentoss-signout {
    font-size: 13px;
    color: #6b7280;
    text-decoration: none;
}

.tokentoss-signout:hover {
    text-decoration: underline;
    color: #374151;
}

.tokentoss-error {
    display: none;
    margin-top: 12px;
    padding: 10px 12px;
    font-size: 13px;
    color: #dc2626;
    background: #fef2f2;
    border: 1px solid #fecaca;
    border-radius: 4px;
}
"""


class GoogleAuthWidget(anywidget.AnyWidget):
    """Interactive Google OAuth widget for Jupyter notebooks.

    Displays a "Sign in with Google" button that initiates the OAuth flow
    in a popup window. After authentication, tokens are automatically
    exchanged and stored.

    Example:
        widget = GoogleAuthWidget(client_secrets_path="./client_secrets.json")
        display(widget)
        # Click button, complete OAuth
        # widget.credentials now contains the tokens
    """

    # --- Synced Traitlets ---

    # OAuth flow
    auth_url = traitlets.Unicode("").tag(sync=True)
    auth_code = traitlets.Unicode("").tag(sync=True)
    received_state = traitlets.Unicode("").tag(sync=True)
    state = traitlets.Unicode("").tag(sync=True)

    # Status display
    status = traitlets.Unicode("Click to sign in").tag(sync=True)
    error = traitlets.Unicode("").tag(sync=True)
    user_email = traitlets.Unicode("").tag(sync=True)
    is_authenticated = traitlets.Bool(False).tag(sync=True)
    show_manual_input = traitlets.Bool(False).tag(sync=True)

    # --- JavaScript and CSS ---
    _esm = _ESM
    _css = _CSS

    def __init__(
        self,
        client_secrets_path: str | None = None,
        client_config: ClientConfig | None = None,
        auth_manager: AuthManager | None = None,
        storage: FileStorage | MemoryStorage | None = None,
        scopes: list[str] | None = None,
        **kwargs,
    ):
        """Initialize the authentication widget.

        Args:
            client_secrets_path: Path to client_secrets.json file.
            client_config: Pre-loaded ClientConfig (alternative to path).
            auth_manager: Existing AuthManager instance (alternative to above).
            storage: Token storage backend (default: FileStorage).
            scopes: OAuth scopes (default: openid, email, profile).
        """
        super().__init__(**kwargs)

        # Set up AuthManager
        if auth_manager is not None:
            self._auth_manager = auth_manager
        else:
            self._auth_manager = AuthManager(
                client_secrets_path=client_secrets_path,
                client_config=client_config,
                storage=storage,
                scopes=scopes,
            )

        # PKCE state
        self._code_verifier: str | None = None

        # Callback server
        self._callback_server: CallbackServer | None = None
        self._server_available = False

        # Try to start callback server
        self._try_start_server()

        # Check if already authenticated
        if self._auth_manager.is_authenticated:
            self._set_authenticated_state()

        # Set up observers
        self.observe(self._on_auth_code_change, names=["auth_code"])

        # Set up message handler
        self.on_msg(self._handle_message)

    def _try_start_server(self) -> None:
        """Try to start the callback server."""
        if self._callback_server:
            self._callback_server.stop()
            logger.debug("Stopped old callback server on port %s", self._callback_server.port)
        self._callback_server = CallbackServer()
        self._server_available = self._callback_server.start()
        if self._server_available:
            logger.debug("Started callback server on port %s", self._callback_server.port)
        else:
            logger.warning("Failed to start callback server")

    @property
    def auth_manager(self) -> AuthManager:
        """Get the underlying AuthManager instance."""
        return self._auth_manager

    @property
    def credentials(self):
        """Get current credentials (convenience accessor)."""
        return self._auth_manager.credentials

    def prepare_auth(self) -> None:
        """Prepare for OAuth flow by generating PKCE pair and auth URL.

        Called automatically when user clicks the sign-in button.
        """
        # Reset server state if reusing
        if self._callback_server:
            self._callback_server.reset()

        # Generate PKCE pair
        self._code_verifier, code_challenge = generate_pkce_pair()

        # Generate state for CSRF protection
        self.state = secrets.token_urlsafe(16)

        # Determine redirect URI
        if self._server_available and self._callback_server:
            redirect_uri = self._callback_server.redirect_uri
            self.show_manual_input = False
        else:
            redirect_uri = "http://localhost"
            self.show_manual_input = True

        # Generate authorization URL
        self.auth_url = self._auth_manager.get_authorization_url(
            code_challenge=code_challenge,
            redirect_uri=redirect_uri,
            state=self.state,
        )

        self.status = "Waiting for authentication..."
        self.error = ""

    def _check_callback(self) -> None:
        """Check if the callback server received the auth code."""
        if not self._callback_server:
            return

        if self._callback_server.check_callback():
            if self._callback_server.error:
                self.error = f"Authentication error: {self._callback_server.error}"
                self.status = "Authentication failed"
                self._code_verifier = None
            elif self._callback_server.auth_code:
                # Validate state
                if self._callback_server.state and self._callback_server.state != self.state:
                    self.error = "Invalid state - possible CSRF attack"
                    self.status = "Authentication failed"
                    self._code_verifier = None
                    return

                # Exchange code
                self._exchange_code(
                    self._callback_server.auth_code,
                    self._callback_server.redirect_uri,
                )
            else:
                # No code received - user may have closed popup
                self.status = "Click to sign in"
                self._code_verifier = None

            # Stop and reset server
            self._callback_server.stop()
            self._try_start_server()
        else:
            # Callback not received - show manual input
            self.show_manual_input = True
            self.status = "Paste the redirect URL below"

    def _on_auth_code_change(self, change) -> None:
        """Handle auth_code traitlet change from manual input."""
        auth_code = change["new"]
        if not auth_code:
            return

        # Validate state (if provided)
        if self.received_state and self.received_state != self.state:
            self.error = "Invalid state - possible CSRF attack"
            self.status = "Authentication failed"
            self._code_verifier = None
            self.auth_code = ""
            return

        # Determine redirect URI
        if self._server_available and self._callback_server:
            redirect_uri = self._callback_server.redirect_uri
        else:
            redirect_uri = "http://localhost"

        self._exchange_code(auth_code, redirect_uri)
        self.auth_code = ""  # Clear for security

    def _exchange_code(self, auth_code: str, redirect_uri: str) -> None:
        """Exchange authorization code for tokens."""
        if not self._code_verifier:
            self.error = "No code verifier - please try signing in again"
            self.status = "Authentication failed"
            return

        try:
            self.status = "Exchanging authorization code..."
            self._auth_manager.exchange_code(
                auth_code=auth_code,
                code_verifier=self._code_verifier,
                redirect_uri=redirect_uri,
            )
            self._set_authenticated_state()

        except TokenExchangeError as e:
            self.error = str(e)
            self.status = "Authentication failed"
            self._code_verifier = None

    def _set_authenticated_state(self) -> None:
        """Update widget state after successful authentication."""
        self.is_authenticated = True
        self.user_email = self._auth_manager.user_email or ""
        self.status = f"Signed in as {self.user_email}" if self.user_email else "Signed in"
        self.error = ""
        self.show_manual_input = False
        self._code_verifier = None

    def sign_out(self) -> None:
        """Sign out and clear stored credentials."""
        self._auth_manager.clear()
        self.is_authenticated = False
        self.user_email = ""
        self.status = "Click to sign in"
        self.error = ""
        self.auth_code = ""
        self.auth_url = ""
        self.show_manual_input = False
        self._code_verifier = None

    def _handle_message(self, widget, content, buffers):
        """Handle custom messages from JavaScript."""
        msg_type = content.get("type")

        if msg_type == "prepare_auth":
            self.prepare_auth()
        elif msg_type == "sign_out":
            self.sign_out()
        elif msg_type == "check_callback":
            self._check_callback()
