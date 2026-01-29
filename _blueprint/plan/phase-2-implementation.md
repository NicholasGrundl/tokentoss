# Phase 2: GoogleAuthWidget Implementation Plan

## Overview

Implement `GoogleAuthWidget` - an anywidget-based component that handles Google OAuth in Jupyter notebooks.

## Key Design Decision: Redirect URI Strategy

**Challenge:** Desktop OAuth clients require `http://localhost` as redirect URI, but we can't reliably run a local HTTP server in all notebook environments (Colab, JupyterHub, etc.).

**Solution:** Both approaches with auto-detection

### Primary: Local HTTP Server (when available)
1. Start temporary HTTP server on `http://localhost:{random_port}`
2. Use `http://localhost:{port}` as redirect URI
3. Open popup with Google OAuth URL
4. Server receives callback, extracts code, serves success page
5. Server shuts down, widget proceeds with token exchange

### Fallback: Manual URL Paste (for remote environments)
1. If server fails to start (Colab, JupyterHub, etc.), use `http://localhost` redirect
2. User completes OAuth, Google redirects to localhost (page fails to load)
3. Widget shows input field: "Paste the URL from the popup's address bar"
4. User pastes URL, widget extracts auth code

### Implementation
- Create `CallbackServer` helper class in widget.py
- Try to start server on init, set `_server_available` flag
- `prepare_auth()` uses appropriate redirect URI based on server availability
- JS shows manual input only when server is not available

---

## Implementation Steps

### Step 1: Create CallbackServer Helper

**File:** `src/tokentoss/widget.py`

```python
class CallbackServer:
    """Temporary HTTP server to capture OAuth callback."""

    def __init__(self):
        self.port: int | None = None
        self.auth_code: str | None = None
        self.state: str | None = None
        self._server: HTTPServer | None = None
        self._thread: Thread | None = None

    def start(self) -> bool:
        """Start server on random port. Returns True if successful."""

    def stop(self) -> None:
        """Stop the server."""

    @property
    def redirect_uri(self) -> str:
        """Return redirect URI (http://localhost:{port})."""
```

### Step 2: Define Widget Class Structure

**File:** `src/tokentoss/widget.py`

```python
class GoogleAuthWidget(anywidget.AnyWidget):
    # Synced traitlets
    auth_url = Unicode("").tag(sync=True)        # OAuth URL (Python → JS)
    auth_code = Unicode("").tag(sync=True)       # Auth code (JS → Python)
    state = Unicode("").tag(sync=True)           # CSRF token
    status = Unicode("Click to sign in").tag(sync=True)
    error = Unicode("").tag(sync=True)
    user_email = Unicode("").tag(sync=True)
    is_authenticated = Bool(False).tag(sync=True)
    show_manual_input = Bool(False).tag(sync=True)  # Show paste field

    # Python-only
    _code_verifier: str | None  # PKCE verifier (never sent to JS)
    _auth_manager: AuthManager
    _callback_server: CallbackServer | None
```

### Step 2: Implement Python Methods

1. **`__init__`** - Accept `client_secrets_path`, `client_config`, `auth_manager`, `storage`, `scopes`
2. **`prepare_auth()`** - Generate PKCE pair, state token, and auth URL
3. **`_on_auth_code_change()`** - Observer that triggers `auth_manager.exchange_code()`
4. **`sign_out()`** - Clear credentials and reset widget state
5. **`_handle_message()`** - Handle `prepare_auth` and `sign_out` messages from JS

### Step 3: Implement JavaScript ESM

```javascript
function render({ model, el }) {
    // Create UI: button, status, manual input field, sign-out link, error display
    // Handle button click → send 'prepare_auth' message to Python
    // Watch auth_url changes → open popup
    // Handle manual URL paste → extract code, set auth_code traitlet
    // Handle postMessage (for future Web OAuth support)
    // Update UI based on status/error/is_authenticated
}
```

### Step 4: Add CSS Styles

- Clean, minimal design matching Google's style guide
- Status display, button, manual input field, error box
- Responsive sizing for notebook cells

### Step 5: Update Exports

**File:** `src/tokentoss/__init__.py`
- Already has lazy import for `GoogleAuthWidget` - just needs widget.py to export the class

---

## Traitlet Sync Direction

| Traitlet | Direction | Purpose |
|----------|-----------|---------|
| `auth_url` | Python → JS | OAuth URL to open in popup |
| `auth_code` | JS → Python | Authorization code from callback |
| `state` | Python → JS | CSRF protection token |
| `status` | Both | Current status message |
| `error` | Both | Error message if any |
| `user_email` | Python → JS | Email after successful auth |
| `is_authenticated` | Python → JS | Whether authenticated |

---

## Files to Modify/Create

1. **`src/tokentoss/widget.py`** - Replace placeholder with full implementation
2. **`tests/test_widget.py`** - Unit tests for widget

---

## Verification Plan

1. **Unit tests** - Test Python logic (prepare_auth, exchange flow, state validation)
2. **Manual notebook test** - Display widget in JupyterLab, complete OAuth flow
3. **Verify credentials** - Check `widget.credentials` and `tokentoss.CREDENTIALS` are set
4. **Verify token storage** - Check `~/.config/tokentoss/tokens.json` exists with 0600 permissions
5. **Test sign-out** - Verify widget resets and tokens are cleared
6. **Test re-auth** - Verify can sign in again after sign out

---

## Implementation Order

1. Create `CallbackServer` helper class
2. Create widget class with traitlets and `__init__`
3. Implement `prepare_auth()` method (with server/fallback logic)
4. Implement `_on_auth_code_change()` observer
5. Implement `_poll_callback_server()` to check for server-received code
6. Implement `sign_out()` method
7. Add message handler for JS→Python communication
8. Write JavaScript ESM (UI, popup, manual input, polling)
9. Add CSS styles
10. Write unit tests
11. Manual integration test in notebook
