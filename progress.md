# tokentoss - Development Progress Log

**Last Updated:** 2026-01-28
**Status:** Phase 1 Complete, Phases 2 & 3 Pending

---

## What We're Building

**tokentoss** - A Python package that lets users authenticate from Jupyter notebooks to access IAP-protected GCP services via a "Sign in with Google" widget.

### The Goal
```python
from tokentoss import GoogleAuthWidget, IAPClient

# User clicks button, completes OAuth in popup
widget = GoogleAuthWidget(client_secrets_path="./client_secrets.json")
display(widget)

# After auth, make requests to IAP-protected services
client = IAPClient(base_url="https://my-iap-service.run.app")
data = client.get_json("/api/data")  # ID token added automatically
```

---

## Completed Work

### Phase 1: Package Setup + Storage + AuthManager ✅

**Files Created:**
| File | Purpose |
|------|---------|
| `pyproject.toml` | UV package config, dependencies |
| `README.md` | Package documentation |
| `src/tokentoss/__init__.py` | Exports, module-level `CREDENTIALS` variable |
| `src/tokentoss/exceptions.py` | `NoCredentialsError`, `TokenExchangeError`, etc. |
| `src/tokentoss/storage.py` | `FileStorage`, `MemoryStorage`, `TokenData` |
| `src/tokentoss/auth_manager.py` | `AuthManager`, `ClientConfig`, PKCE generation |
| `tests/test_storage.py` | 17 tests |
| `tests/test_auth_manager.py` | 20 tests |

**Test Status:** 37 tests passing

**Key Classes Implemented:**

1. **TokenData** - Dataclass holding: access_token, id_token, refresh_token, expiry, scopes, user_email
2. **FileStorage** - Saves tokens to `~/.config/tokentoss/tokens.json` with 0600 permissions
3. **MemoryStorage** - In-memory storage for testing
4. **ClientConfig** - Loads OAuth client config from `client_secrets.json`
5. **AuthManager** - Core auth logic:
   - `get_authorization_url()` - generates OAuth URL with PKCE
   - `exchange_code()` - exchanges auth code for tokens
   - `refresh_tokens()` - refreshes expired tokens
   - Auto-sets `tokentoss.CREDENTIALS` on success

---

## Next Steps (Not Started)

### Phase 2: GoogleAuthWidget

**File:** `src/tokentoss/widget.py` (currently placeholder)

**What to build:**
- anywidget-based widget with "Sign in with Google" button
- Opens popup for OAuth flow
- Bundled callback HTML page (blob URL) that uses postMessage to return auth code
- Traitlets for state sync: `auth_code`, `status`, `error`, `user_email`
- PKCE code_verifier generated in Python, code_challenge passed to auth URL
- Auto-calls `auth_manager.exchange_code()` when auth_code arrives via `observe()`
- Status display: "Click to sign in" → "Waiting..." → "Signed in as X" / "Error: ..."

**Key Design Decisions:**
- Callback method: postMessage API (popup → parent window)
- Callback page: Embedded in widget JS as blob URL (self-contained)
- Security: PKCE (code_verifier + code_challenge)
- Code handoff: Traitlet sync with `observe()` callback

### Phase 3: IAPClient

**File:** `src/tokentoss/client.py` (currently placeholder)

**What to build:**
- HTTP client that auto-adds ID token to Authorization header
- Credential discovery chain:
  1. AuthManager passed as arg
  2. Module-level `tokentoss.CREDENTIALS`
  3. Token file at default location
  4. `TOKENTOSS_TOKEN_FILE` env var
- requests-like API: `get()`, `post()`, `put()`, `delete()`
- JSON helpers: `get_json()`, `post_json()`
- Auto-refresh on 401, retry once
- Optional `base_url` for relative paths
- Raises `NoCredentialsError` if no credentials found

---

## Key Architecture Decisions

### OAuth Flow
```
User clicks button
       │
       ▼
Widget JS opens popup → Google OAuth screen
       │                        │
       ▼                        ▼
Widget shows "Waiting..."    User authenticates
       │                        │
       │◀── postMessage ────────┘ (auth code)
       │
       ▼
JS sets auth_code traitlet
       │
       ▼
Python observe() fires → auth_manager.exchange_code()
       │
       ▼
Tokens stored, CREDENTIALS set, widget shows "Signed in as X"
```

### Token Storage
- Location: `~/.config/tokentoss/tokens.json` (via platformdirs)
- Permissions: 0600 (owner read/write only)
- Contents: tokens + metadata (NOT client secrets)
- Client secrets: Loaded separately from user's `client_secrets.json`

### IAP Authentication
- IAP requires **ID token** (not access token) in Authorization header
- Desktop OAuth client must be added to IAP's "programmatic access allowlist"
- ID token audience = Desktop client ID (IAP accepts because allowlisted)

---

## Files Reference

```
/Users/nicholasgrundl/projects/gcptest/
├── pyproject.toml              # Package config
├── README.md                   # User docs
├── progress.md                 # THIS FILE
├── src/tokentoss/
│   ├── __init__.py             # CREDENTIALS variable, exports
│   ├── auth_manager.py         # AuthManager, ClientConfig, PKCE
│   ├── storage.py              # FileStorage, MemoryStorage, TokenData
│   ├── exceptions.py           # Custom exceptions
│   ├── widget.py               # PLACEHOLDER - Phase 2
│   └── client.py               # PLACEHOLDER - Phase 3
├── tests/
│   ├── test_storage.py         # 17 tests ✅
│   └── test_auth_manager.py    # 20 tests ✅
└── _blueprint/
    └── plan/
        └── tokentoss_implementation.md  # Full design decisions
```

---

## Commands to Remember

```bash
# Install dependencies
uv sync

# Run all tests
uv run pytest -v

# Run specific test file
uv run pytest tests/test_storage.py -v

# Verify package imports
uv run python -c "import tokentoss; print(tokentoss.__version__)"

# Start Jupyter for testing widget
uv run jupyter lab
```

---

## GCP Setup (User Must Do Once)

1. Create Desktop OAuth client in GCP Console
2. Download `client_secrets.json`
3. Add Desktop client ID to IAP's programmatic access allowlist
4. Grant user "IAP-secured Web App User" role

---

## When You Return

1. Read this file
2. Check task status: Phases 2 and 3 are independent, can do either
3. For Phase 2: Look at `widget.py`, implement anywidget with OAuth popup
4. For Phase 3: Look at `client.py`, implement IAPClient with credential chain
5. Full design details in `_blueprint/plan/tokentoss_implementation.md`

**Recommendation:** Start with Phase 2 (widget) since it's the user-facing component and more complex. Phase 3 (client) is straightforward HTTP wrapper.
