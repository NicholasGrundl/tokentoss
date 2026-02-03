# tokentoss - Development Progress Log

**Last Updated:** 2026-01-28
**Status:** Phase 1-4 Complete

---

## What We're Building

**tokentoss** - A Python package that lets users authenticate from Jupyter notebooks to access IAP-protected GCP services via a "Sign in with Google" widget.

### The Goal
```python
# One-time setup (run once per machine)
import tokentoss
tokentoss.configure(client_id="...", client_secret="...")

# Every session
from tokentoss import GoogleAuthWidget, IAPClient

widget = GoogleAuthWidget()  # auto-discovers client_secrets.json
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

**Key Classes:** TokenData, FileStorage, MemoryStorage, ClientConfig, AuthManager

### Phase 2: GoogleAuthWidget ✅

**Files Created:**
| File | Purpose |
|------|---------|
| `src/tokentoss/widget.py` | GoogleAuthWidget anywidget implementation |
| `tests/test_widget.py` | 38 tests |

**Key Classes:** CallbackServer, GoogleAuthWidget

### Phase 3: IAPClient ✅

**Files Created/Rewritten:**
| File | Purpose |
|------|---------|
| `src/tokentoss/client.py` | IAPClient HTTP client (rewritten for quality) |
| `tests/test_client.py` | 37 tests |

**Key Features:**
- Token discovery chain: AuthManager → module CREDENTIALS → FileStorage
- Auto-refresh on 401 with single retry
- Configurable timeout (default 30s)
- Context manager support (`with IAPClient(...) as client:`)
- `ValueError` on relative path without `base_url`
- Cached FileStorage for fallback discovery

### Phase 4: Client Secrets Setup ✅

**Files Created:**
| File | Purpose |
|------|---------|
| `src/tokentoss/setup.py` | `configure()` API for client secrets installation |
| `tests/test_setup.py` | 26 tests |

**Key Functions:**
- `configure(client_id=..., client_secret=...)` - from direct credentials
- `configure(path="./client_secrets.json")` - from existing file
- `configure_from_credentials()` - builds client_secrets.json with Google boilerplate
- `configure_from_file()` - validates and copies existing file
- `get_config_path()` - standard location (~/.config/tokentoss/client_secrets.json)

**Integration:**
- AuthManager auto-discovers client_secrets.json from standard location
- All writes go to platformdirs standard location with 0600 permissions

**Test Status:** 138 tests passing (total)

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

### Client Secrets Storage
- Location: `~/.config/tokentoss/client_secrets.json` (via platformdirs)
- Permissions: 0600
- Installed via `tokentoss.configure()`

### IAP Authentication
- IAP requires **ID token** (not access token) in Authorization header
- Desktop OAuth client must be added to IAP's "programmatic access allowlist"
- ID token audience = Desktop client ID (IAP accepts because allowlisted)

### IAPClient Token Discovery Chain
```
1. Explicit AuthManager (constructor arg)
2. Module-level tokentoss.CREDENTIALS (set by AuthManager on login)
3. Token file (TOKENTOSS_TOKEN_FILE env var or default path)
4. Raise NoCredentialsError
```

---

## Files Reference

```
/Users/nicholasgrundl/projects/tokentoss/
├── pyproject.toml              # Package config
├── README.md                   # User docs
├── src/tokentoss/
│   ├── __init__.py             # CREDENTIALS variable, exports
│   ├── auth_manager.py         # AuthManager, ClientConfig, PKCE
│   ├── storage.py              # FileStorage, MemoryStorage, TokenData
│   ├── exceptions.py           # Custom exceptions
│   ├── widget.py               # GoogleAuthWidget ✅
│   ├── client.py               # IAPClient ✅
│   └── setup.py                # configure() API ✅
├── tests/
│   ├── test_storage.py         # 17 tests ✅
│   ├── test_auth_manager.py    # 20 tests ✅
│   ├── test_widget.py          # 38 tests ✅
│   ├── test_client.py          # 37 tests ✅
│   └── test_setup.py           # 26 tests ✅
└── _blueprint/
    └── plan/
        ├── tokentoss_implementation.md
        ├── client_secrets_implementation.md
        ├── user_feedback.md
        └── progress.md          # THIS FILE
```

---

## Commands

```bash
# Install dependencies
uv sync

# Run all tests
uv run pytest -v

# Run specific test file
uv run pytest tests/test_client.py -v

# Verify package imports
uv run python -c "import tokentoss; print(tokentoss.__version__)"

# Start Jupyter for testing widget
uv run jupyter lab
```

---

## GCP Setup (User Must Do Once)

1. Create Desktop OAuth client in GCP Console
2. Configure tokentoss:
   ```python
   import tokentoss
   tokentoss.configure(client_id="...", client_secret="...")
   ```
   OR download `client_secrets.json` and:
   ```python
   tokentoss.configure(path="./client_secrets.json")
   ```
3. Add Desktop client ID to IAP's programmatic access allowlist
4. Grant user "IAP-secured Web App User" role

---

## When You Return

1. Read this file
2. All core phases (1-4) are complete with 138 tests passing
3. For next steps consider:
   - End-to-end manual testing in JupyterLab
   - README updates for the new `configure()` API
   - PyPI publishing preparation
4. Full design details in `_blueprint/plan/tokentoss_implementation.md`
