# Plan: Phase 3+ Implementation

## Summary

1. **Rewrite `client.py`** - clean IAPClient fixing all 7 quality issues
2. **Write `test_client.py`** - comprehensive tests for the new client
3. **Create `setup.py`** - `configure()` API for client secrets installation
4. **Write `test_setup.py`** - tests for setup module
5. **Wire up exports and auto-discovery** - update `__init__.py` and `auth_manager.py`
6. **Update `progress.md`** - reflect actual state

---

## Phase 3A: Rewrite `src/tokentoss/client.py`

Fixes all 7 issues from review. Clean implementation.

**Key changes from current code:**

| Issue | Fix |
|-------|-----|
| No timeout | Add `default_timeout=30` constructor param, pass to all requests |
| Convoluted refresh logic | Simplify: try token → if expired, refresh → if fail, raise |
| Expired stored tokens dead-ended | Accept that storage-only can't refresh (no client config). Document clearly. |
| FileStorage created every call | Cache `_fallback_storage` on first use |
| Silent broad exception catch on 401 | Only catch `NoCredentialsError`, log others |
| Invalid URL with no base_url | Raise `ValueError` if no base_url and relative path |
| No session cleanup | Add `close()` method and `__enter__`/`__exit__` |

**Constructor:**
```python
class IAPClient:
    def __init__(
        self,
        base_url: str | None = None,
        auth_manager: AuthManager | None = None,
        timeout: int = 30,
    ) -> None:
```

**Token discovery chain** (simplified):
```
1. self._auth_manager.id_token (if provided)
   - If expired: call auth_manager.refresh_tokens()
2. tokentoss.CREDENTIALS.id_token
   - If expired: call creds.refresh(Request())
3. FileStorage (cached, checks env var then default path)
   - Return id_token if not expired
   - Cannot refresh from storage alone → raise
4. Raise NoCredentialsError
```

**401 retry** (simplified):
```
response = request(...)
if response.status_code == 401:
    try:
        refreshed_token = self._get_id_token(force_refresh=True)
        response = retry_request(...)
    except NoCredentialsError:
        pass  # return original 401
return response
```

**Public API:**
- `get(path, **kwargs) -> Response`
- `post(path, **kwargs) -> Response`
- `put(path, **kwargs) -> Response`
- `delete(path, **kwargs) -> Response`
- `patch(path, **kwargs) -> Response`
- `get_json(path, **kwargs) -> Any`
- `post_json(path, json=None, **kwargs) -> Any`
- `close() -> None`
- `__enter__` / `__exit__` context manager

---

## Phase 3B: Create `tests/test_client.py`

~25-30 tests across 5 test classes:

- **TestIAPClientInit** (3): base_url stripping, auth_manager storage, timeout param
- **TestGetIdToken** (8): each discovery chain step, force_refresh paths, error cases
- **TestBuildUrl** (4): absolute URL passthrough, base_url joining, no base_url + relative raises ValueError
- **TestRequest** (8): bearer token injection, 401 retry flow, timeout passed, kwargs forwarded
- **TestHTTPMethods** (7): get/post/put/delete/patch, get_json, post_json

**Mocking strategy:**
- Mock `requests.Session` for all HTTP tests
- Mock `tokentoss.CREDENTIALS` via `mocker.patch.object`
- Mock `FileStorage` via `mocker.patch("tokentoss.client.FileStorage")`
- Create real `AuthManager` with `MemoryStorage` for integration-style tests

---

## Phase 4A: Create `src/tokentoss/setup.py`

**Three public functions:**

```python
def configure(
    client_id: str | None = None,
    client_secret: str | None = None,
    path: str | Path | None = None,
) -> Path:
    """Master configure function. Always writes to standard platformdirs location.

    Usage from JupyterLab:
        import tokentoss

        # From direct credentials (e.g. copy-paste from GCP console)
        tokentoss.configure(client_id="...", client_secret="...")

        # From downloaded client_secrets.json file
        tokentoss.configure(path="./client_secrets.json")

    Returns:
        Path where client_secrets.json was installed.
    """
    if path is not None:
        return configure_from_file(path)
    elif client_id is not None and client_secret is not None:
        return configure_from_credentials(client_id, client_secret)
    else:
        raise ValueError(
            "Provide either (client_id, client_secret) or path"
        )


def configure_from_credentials(
    client_id: str,
    client_secret: str,
    project_id: str | None = None,
) -> Path:
    """Build client_secrets.json from credentials and install to standard location.

    Merges with hardcoded Google OAuth boilerplate (auth_uri, token_uri, etc.)
    so the user only needs to provide client_id and client_secret.
    """


def configure_from_file(source_path: str | Path) -> Path:
    """Copy an existing client_secrets.json to standard location.

    Validates the file format, then copies to ~/.config/tokentoss/client_secrets.json.
    """


def get_config_path() -> Path:
    """Get the standard client_secrets.json location."""
    return Path(platformdirs.user_config_dir(APP_NAME)) / "client_secrets.json"
```

**Hardcoded Google defaults** (same constants already in `auth_manager.py`):
```python
GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"
GOOGLE_CERT_URL = "https://www.googleapis.com/oauth2/v1/certs"
DEFAULT_REDIRECT_URIS = ["http://localhost"]
```

**All writes go to:** `~/.config/tokentoss/client_secrets.json` with `0o600` permissions.

---

## Phase 4B: Create `tests/test_setup.py`

~12 tests:

- **TestConfigureFromCredentials** (4): creates file, correct structure, 0600 perms, validates empty inputs
- **TestConfigureFromFile** (4): copies valid file, validates format, rejects invalid, handles missing source
- **TestConfigure** (2): routes to correct sub-function, raises on bad args
- **TestGetConfigPath** (2): returns correct platform path, consistent across calls

---

## Phase 4C: Wire up exports and auto-discovery

**`src/tokentoss/__init__.py`** - add to exports:
```python
from .setup import configure, configure_from_credentials, configure_from_file, get_config_path
```

**`src/tokentoss/auth_manager.py`** - update `__init__` to auto-discover:
```python
# After existing client_config / client_secrets_path checks:
else:
    # Auto-discover from standard location
    from .setup import get_config_path
    default_path = get_config_path()
    if default_path.exists():
        self.client_config = ClientConfig.from_file(default_path)
    else:
        raise ValueError(
            "No client config provided. Run tokentoss.configure() first, "
            f"or pass client_secrets_path. Expected: {default_path}"
        )
```

This enables the simplified notebook flow:
```python
# One-time setup (run once)
import tokentoss
tokentoss.configure(client_id="...", client_secret="...")

# Every session after
from tokentoss import GoogleAuthWidget
widget = GoogleAuthWidget()  # auto-discovers client_secrets.json
display(widget)
```

---

## Phase 5: Update progress.md

Update to reflect:
- Phase 3 complete (IAPClient rewritten + tested)
- Phase 4 complete (setup module)
- Accurate test counts
- Updated file tree
- New "When You Return" section pointing to setup flow

---

## Files to modify/create

| File | Action |
|------|--------|
| `src/tokentoss/client.py` | **Rewrite** |
| `tests/test_client.py` | **Create** |
| `src/tokentoss/setup.py` | **Create** |
| `tests/test_setup.py` | **Create** |
| `src/tokentoss/__init__.py` | **Edit** - add setup exports |
| `src/tokentoss/auth_manager.py` | **Edit** - add auto-discovery fallback |
| `_blueprint/plan/progress.md` | **Edit** - update status |

---

## Verification

```bash
# Run all tests
uv run pytest -v

# Verify setup flow
uv run python -c "
from tokentoss.setup import get_config_path
print(f'Config path: {get_config_path()}')
"

# Verify IAPClient imports
uv run python -c "
from tokentoss import IAPClient
client = IAPClient(base_url='https://example.com', timeout=10)
print('IAPClient created OK')
client.close()
"
```
