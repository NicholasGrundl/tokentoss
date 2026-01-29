# tokentoss - Implementation Plan

## Overview

**tokentoss** is a Python package providing OAuth authentication from Jupyter notebooks to access IAP-protected GCP services.

**Key Features:**
- anywidget with "Sign in with Google" button
- Authorization Code flow with PKCE (gets refresh tokens)
- Python kernel handles token exchange (secure)
- Tokens persisted to file for reuse across sessions
- IAPClient manages auth headers, refresh, and HTTP requests

**MVP Requirements:**
- Allow access to IAP service using credentials from login button flow
- IAP service sees authenticated user's email
- Single initial setup (download client_secrets.json, add to IAP allowlist)
- Seamless credential refresh using refresh tokens

---

## Part 1: anywidget Sign-in Button & OAuth Flow

### Decisions

1. **Callback method:** postMessage API
   - Popup completes OAuth, redirects to callback page
   - Callback page extracts auth code from URL, sends via `window.opener.postMessage()`
   - Parent window (widget JS) receives message, extracts code
   - Well-proven pattern used by Google Sign-In, Auth0, etc.

2. **Callback page location:** Bundled in widget
   - Embed callback HTML as string in JavaScript
   - Serve as `blob:` URL or data URI
   - Self-contained in Python package, no external hosting needed

3. **Security:** Use PKCE (Proof Key for Code Exchange)
   - Generate `code_verifier` and `code_challenge` in Python
   - Pass challenge to auth URL, verifier used in token exchange
   - More secure for public clients

4. **Code handoff to Python:** Traitlet sync with `observe()`
   - JS sets `auth_code` traitlet when received
   - Python watches via `widget.observe(callback, names='auth_code')`
   - Future: optional callback arg for custom event handling

5. **Widget UX:** Status updates displayed in widget
   - States: "Click to sign in" → "Waiting for auth..." → "Signed in as user@email.com" or "Error: ..."
   - Visual feedback within the widget itself

### Flow Diagram

```
User clicks button
       │
       ▼
Widget JS opens popup ──────────────────────────┐
       │                                         │
       ▼                                         ▼
Widget shows "Waiting..."              Google OAuth screen
       │                                         │
       │                                         ▼
       │                               User authenticates
       │                                         │
       │                                         ▼
       │                               Redirect to blob: callback
       │                                         │
       │◀──── postMessage(auth_code) ───────────┘
       │
       ▼
JS sets auth_code traitlet
       │
       ▼
Python observe() fires
       │
       ▼
Token exchange begins (Part 2)
```

---

## Part 2: Python Kernel Token Exchange

### Decisions

1. **Exchange trigger:** Automatic in `observe()` callback
   - When `auth_code` traitlet changes, observer automatically initiates exchange
   - No manual user action required after popup completes

2. **Architecture:** Widget + separate AuthManager class
   - **Widget:** Handles UI, popup, OAuth flow initiation, status display
   - **AuthManager:** Handles token exchange, storage, refresh, credentials management
   - Better separation of concerns, more testable

3. **AuthManager lifecycle:** Created by widget internally
   - Widget instantiates AuthManager on init
   - User accesses via `widget.auth_manager`
   - Keeps API simple for users

4. **Error handling:** Widget status + inspectable properties
   - Widget displays error in UI (e.g., "Error: invalid_grant")
   - Error details available via `widget.error` or `widget.auth_manager.last_error`
   - Does not raise exceptions that interrupt notebook flow

5. **Success indication:** Widget status + credentials property
   - Widget shows "Signed in as user@email.com"
   - Credentials available via `widget.credentials` (convenience) or `widget.auth_manager.credentials`

### Flow Diagram

```
auth_code traitlet changes
       │
       ▼
observe() callback fires
       │
       ▼
widget.auth_manager.exchange_code(auth_code, code_verifier)
       │
       ├──── Success ────┐
       │                 ▼
       │         Store tokens (Part 3)
       │                 │
       │                 ▼
       │         Update widget.credentials
       │                 │
       │                 ▼
       │         Widget shows "Signed in as X"
       │
       └──── Failure ────┐
                         ▼
                 Store error in widget.error
                         │
                         ▼
                 Widget shows "Error: ..."
```

---

## Part 3: Token Storage

### Decisions

1. **Primary storage location:** Use `platformdirs` package
   - Cross-platform user config directory (e.g., `~/.config/your-package/` on Linux)
   - Standard, portable approach

2. **Storage modes:** Support both file and memory
   - **FileStorage:** Default, persists across sessions
   - **MemoryStorage:** For testing, demos, or when persistence isn't wanted
   - No abstract base class (keep simple), add later if extensibility needed

3. **File security:** 0600 permissions + warning
   - Set file permissions to owner read/write only
   - On load, warn if file has insecure permissions (e.g., world-readable)

4. **Token file contents:** Tokens + metadata only
   - `access_token`, `id_token`, `refresh_token`, `expiry`, `scopes`, `user_email`
   - Client config (client_id, client_secret) loaded separately from `client_secrets.json`
   - Keeps token file simple, user controls client secrets location

### File Structure

```
~/.config/jupyter-iap/           # platformdirs.user_config_dir()
├── tokens.json                  # Stored by AuthManager
│   {
│     "access_token": "ya29...",
│     "id_token": "eyJ...",
│     "refresh_token": "1//...",
│     "expiry": "2024-01-15T10:30:00Z",
│     "scopes": ["openid", "email", ...],
│     "user_email": "user@example.com"
│   }
│
~/path/to/project/
└── client_secrets.json          # User downloads from GCP Console
    {
      "installed": {
        "client_id": "...",
        "client_secret": "...",
        ...
      }
    }
```

---

## Part 4: IAP Client

### Decisions

1. **Credential discovery:** Fallback chain
   ```
   1. AuthManager reference (passed as optional arg)
   2. Module-level variable (my_package.CREDENTIALS, set by AuthManager on success)
   3. Default token file location (platformdirs)
   4. Environment variable (e.g., JUPYTER_IAP_TOKEN_FILE)
   ```

2. **API style:** requests-like methods
   - `client.get(url, **kwargs)`
   - `client.post(url, json=data, **kwargs)`
   - `client.put(url, json=data, **kwargs)`
   - `client.delete(url, **kwargs)`
   - Plus `client.get_json()`, `client.post_json()` etc. for convenience

3. **Base URL:** Optional
   - `IAPClient(base_url='https://my-service.run.app')` - requests relative
   - Or pass full URLs to each method
   - Flexible for single-service or multi-service use

4. **Token refresh:** Auto-refresh on 401
   - If request returns 401, attempt token refresh
   - Retry the request once with new token
   - If still fails, raise exception
   - Transparent to user

5. **No credentials behavior:** Raise clear exception
   - `NoCredentialsError` with helpful message
   - Explains how to authenticate (use widget, or check token file)
   - MVP simplicity; can relax to allow credential-less creation later

6. **Response handling:** Return Response, helper for JSON
   - `client.get()` returns `requests.Response`
   - `client.get_json()` returns parsed JSON directly
   - Standard pattern, flexible for different response types

### Usage Examples

```python
# After authentication via widget
from my_package import IAPClient

# Option 1: Auto-discover (uses module-level CREDENTIALS set by widget)
client = IAPClient()

# Option 2: Explicit base URL
client = IAPClient(base_url="https://my-service.run.app")

# Option 3: Explicit AuthManager
client = IAPClient(auth_manager=widget.auth_manager)

# Making requests
response = client.get("/api/data")
data = client.get_json("/api/data")  # Convenience

response = client.post("/api/items", json={"name": "test"})
```

---

## Final Implementation Plan

### Package Info

- **Name:** `tokentoss`
- **Package manager:** UV with src layout
- **Location:** Convert current `gcptest` directory

### Package Structure

```
tokentoss/
├── pyproject.toml
├── uv.lock
├── README.md
├── src/
│   └── tokentoss/
│       ├── __init__.py          # Exports + module-level CREDENTIALS
│       ├── auth_manager.py      # AuthManager class
│       ├── storage.py           # FileStorage, MemoryStorage
│       ├── widget.py            # GoogleAuthWidget (anywidget)
│       ├── client.py            # IAPClient
│       └── exceptions.py        # NoCredentialsError, etc.
├── tests/
│   ├── test_auth_manager.py
│   ├── test_storage.py
│   ├── test_client.py
│   └── test_widget.py
└── examples/
    └── basic_usage.ipynb
```

### Dependencies

```toml
[project]
dependencies = [
    "anywidget>=0.9.0",
    "google-auth>=2.23.0",
    "google-auth-oauthlib>=1.2.0",
    "requests>=2.31.0",
    "platformdirs>=4.0.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "jupyter>=1.0.0",
]
```

### Implementation Phases

#### Phase 1: Storage + AuthManager (Foundation)

**Files:** `storage.py`, `auth_manager.py`, `exceptions.py`, `__init__.py`

**storage.py:**
- `FileStorage` class: save/load/clear tokens from platformdirs location
- `MemoryStorage` class: in-memory only (for testing)
- Handle 0600 permissions, warn on insecure files

**auth_manager.py:**
- `AuthManager` class
- Load client config from `client_secrets.json` path
- `exchange_code(auth_code, code_verifier)` → tokens
- `refresh_tokens()` → new access/ID tokens
- `credentials` property → current credentials
- On success: set `tokentoss.CREDENTIALS` module variable

**Verify:** Unit tests for storage and token exchange (mock Google endpoints)

#### Phase 2: Widget (OAuth Flow)

**Files:** `widget.py`

**widget.py:**
- `GoogleAuthWidget(anywidget.AnyWidget)`
- Traitlets: `client_id`, `auth_code`, `status`, `error`, `user_email`
- JavaScript: "Sign in with Google" button, popup handling, postMessage listener
- Embedded callback HTML (blob URL)
- PKCE: generate code_verifier/code_challenge
- On auth_code change: call `auth_manager.exchange_code()`
- Update status: "Click to sign in" → "Waiting..." → "Signed in as X" / "Error: ..."

**Verify:** Manual test in Jupyter notebook with real OAuth flow

#### Phase 3: IAPClient (HTTP Requests)

**Files:** `client.py`

**client.py:**
- `IAPClient` class
- Credential discovery chain: arg → module var → file → env var
- Methods: `get()`, `post()`, `put()`, `delete()`, `get_json()`, `post_json()`
- Auto-add Authorization header with ID token
- Auto-refresh on 401, retry once
- Optional `base_url`

**Verify:** Integration test against real IAP-protected service

### One-Time GCP Setup (User Does This)

1. Create Desktop OAuth client in GCP Console
2. Download `client_secrets.json`
3. Add Desktop client ID to IAP's programmatic access allowlist
4. Grant user IAP-secured Web App User role

### End-to-End Usage

```python
# In Jupyter notebook
from tokentoss import GoogleAuthWidget, IAPClient

# Create widget (points to client secrets)
widget = GoogleAuthWidget(client_secrets_path="./client_secrets.json")
display(widget)

# User clicks button, completes OAuth flow
# Widget shows "Signed in as user@example.com"

# Create client (auto-discovers credentials from module variable)
client = IAPClient(base_url="https://my-iap-service.run.app")

# Make authenticated requests
data = client.get_json("/api/data")
```

### Verification Checklist

- [ ] `uv sync` installs all dependencies
- [ ] Unit tests pass for storage, auth_manager
- [ ] Widget renders in JupyterLab
- [ ] OAuth popup opens, completes, returns auth code
- [ ] Token exchange succeeds, tokens stored to file
- [ ] File has 0600 permissions
- [ ] IAPClient auto-discovers credentials
- [ ] Request to IAP service succeeds with 200
- [ ] IAP service sees authenticated user email in headers
- [ ] Token refresh works (force expiry, make request)
- [ ] Second session loads tokens from file without re-auth
