# Plan: Widget Testing Feedback — All Open Items

## Summary

Address all 4 open items from `_blueprint/plan/widget-testing-feedback.md`, sequenced by dependency and risk.

---

## Implementation Order

### 1. Fix flaky test `test_init_requires_config` (Item 5)

**File:** `tests/test_auth_manager.py` (~line 151)

- Add `mocker` param to test method
- Mock `tokentoss.setup.get_config_path` to return a non-existent path
- This isolates the test from the host filesystem

### 2. Style "Sign out" as red button (Item 2)

**File:** `src/tokentoss/widget.py`

- Change `<a>` element to `<button>` in JS ESM (~line 254)
- Remove `e.preventDefault()` from click handler (no longer a link)
- Update all JS references from `signOutLink` to `signOutButton`
- Replace CSS `.tokentoss-signout` styles: red background (`#dc2626`), white text, border, border-radius, hover/active states
- Update `display` values from `'inline'` to `'inline-block'`

### 3. Add `created_at` to TokenData (Item 3a)

**File:** `src/tokentoss/storage.py`

- Add `created_at: str | None = None` field to `TokenData` dataclass
- Add `created_at_datetime` property (parse ISO string, return `datetime | None`)
- Update `from_dict()` to load `created_at` via `.get()` (backward compatible)
- `to_dict()` should include `created_at` when present

**File:** `src/tokentoss/auth_manager.py`

- `exchange_code()`: set `created_at=datetime.now(UTC).isoformat()` on new TokenData
- `refresh_tokens()`: preserve original `created_at` from existing token data

**Tests:** `tests/test_storage.py` — created_at round-trip, optional/None case

### 4. Add max session lifetime + expiry check (Item 3b + 3c)

**File:** `src/tokentoss/auth_manager.py`

- Add `DEFAULT_MAX_SESSION_LIFETIME_HOURS = 24` constant
- Add `max_session_lifetime_hours` param to `__init__` (default 24)
- Add `_is_session_stale(token_data)` helper — checks `created_at` age vs max lifetime; returns `False` if `created_at` is None (backward compat)
- Update `_load_from_storage()`:
  - If session stale: `storage.clear()`, set `last_error`, return early
  - If token expired: attempt `refresh_tokens()`. On failure: clear credentials + storage, set `last_error`
- Update `is_authenticated` property: return `False` if credentials are None (already handles the above since we clear `_credentials`)

**File:** `src/tokentoss/widget.py`

- After `is_authenticated` check in `__init__`, if not authenticated and `last_error` exists, set `self.status = "Session expired — sign in again"`
- GoogleAuthWidget needs to accept and pass through `max_session_lifetime_hours` to AuthManager (only when it creates its own AuthManager)

**Tests:** `tests/test_auth_manager.py` — stale session cleared, expired token refresh succeeds, expired token refresh fails clears creds, backward compat (no created_at)
**Tests:** `tests/test_widget.py` — widget shows "Session expired" message for stale/failed-refresh cases

### 5. ConfigureWidget: Add "Advanced" section with project_id (Item 1)

**File:** `src/tokentoss/setup.py`

- Add `project_id: str | None = None` param to `configure()` wrapper
- Pass through to `configure_from_credentials(..., project_id=project_id)`

**File:** `src/tokentoss/configure_widget.py`

- Add `project_id` traitlet (`Unicode("")`)
- Add collapsible "Advanced (optional)" section in JS ESM:
  - `▶`/`▼` toggle header, hidden content div with Project ID text input
  - On submit: `model.set('project_id', projectInput.value)`
- Update `_on_submit` to pass `project_id` to `configure()`
- Add CSS for advanced header (gray text, pointer cursor, toggle arrow)

**Tests:** `tests/test_setup.py` — `configure()` with/without project_id
**Tests:** `tests/test_configure_widget.py` — widget passes project_id through, works without it

---

## Verification

```bash
# Run full test suite after each item
uv run pytest tests/ -x -q

# Targeted test runs
uv run pytest tests/test_auth_manager.py -x -q
uv run pytest tests/test_storage.py -x -q
uv run pytest tests/test_widget.py -x -q
uv run pytest tests/test_configure_widget.py -x -q
uv run pytest tests/test_setup.py -x -q
```

Manual testing in Jupyter notebook:
- Sign out button is visually red
- Expired token shows "Session expired — sign in again" on widget load
- ConfigureWidget advanced section toggles open/closed
- Project ID saves correctly to client_secrets.json

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Max session lifetime default | 24 hours | User preference |
| HMAC signing for created_at | Skip | Low incremental value per threat model |
| Old tokens without created_at | Treat as fresh | Backward compat, avoids breaking existing sessions |
| configure() wrapper | Update to accept project_id | Keep API consistent |
| Sign-out element | `<button>` not `<a>` | Semantic HTML, simpler event handling |

## Critical Files

- `src/tokentoss/storage.py` — TokenData model
- `src/tokentoss/auth_manager.py` — session lifetime + expiry logic
- `src/tokentoss/widget.py` — GoogleAuthWidget UI
- `src/tokentoss/configure_widget.py` — ConfigureWidget UI
- `src/tokentoss/setup.py` — configure() wrapper
- `tests/test_auth_manager.py`, `test_storage.py`, `test_widget.py`, `test_configure_widget.py`, `test_setup.py`
