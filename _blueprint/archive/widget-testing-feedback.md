# Widget Testing Feedback

Collected during manual testing walkthrough. Items here are candidates for the widgets subpackage refactor (blueprint `03-widgets-subpackage.md`).

---

## ConfigureWidget

### 1. Add optional "Advanced" section with project_id field
- `configure_from_credentials()` already accepts `project_id` but it's not exposed in the widget UI
- Project ID isn't required for the OAuth flow — it's just metadata carried in `client_secrets.json`
- **Proposal:** Add a collapsible/accordion "Advanced" section below the main fields with an optional `Project ID` text input
- **Priority:** Low — nice-to-have for v0.2.0, bundle with widgets refactor

---

## GoogleAuthWidget

### 2. Style "Sign out" as a red button instead of a text link
- Currently rendered as an `<a>` tag styled as subtle text — easy to miss
- **Proposal:** Render as a button with red background/border to make it visually distinct from the sign-in button
- **Priority:** Low — cosmetic, bundle with widgets refactor

### 3. `is_authenticated` should check token expiry, not just existence
- `AuthManager.is_authenticated` only checks `self._credentials is not None` (`auth_manager.py:220-222`)
- `_load_from_storage()` loads tokens from disk without checking `is_expired` (`auth_manager.py:158-171`)
- Result: widget shows "Signed in as ..." even when access token has been expired for hours/days
- The refresh happens lazily when `credentials` property is accessed (e.g. by `IAPClient`), but the widget state is misleading
- **Proposal:** On widget init, if tokens are loaded from storage and expired, attempt a silent refresh. If refresh fails, show "Sign in" button instead of stale "Signed in" state. Consider:
  - `is_authenticated` could return `False` when both access token is expired AND refresh fails
  - Widget could show "Session expired — sign in again" instead of "Signed in as ..."
  - Add max session lifetime (e.g. 7 days default, configurable) after which stored tokens are discarded regardless of refresh token validity
  - Store `created_at` timestamp in `tokens.json`; on load, discard if older than max age
  - Primary security control is file permissions (`0600`); `created_at` is enforceable against casual tampering but not a motivated attacker with local filesystem access (this is out of scope for threat model — if they have file access they already have the refresh token)
  - **Advanced (future):** HMAC-sign `created_at` with a machine-local secret key to resist casual tampering. Stdlib-only (`hmac` + `hashlib`), auto-generated key in `~/.config/tokentoss/.session_key`. Doesn't protect against attacker with full filesystem access, so low incremental value.
- **Priority:** Medium — security/UX concern, should address before v0.1.0 or at latest v0.2.0

### 4. BUG (RESOLVED): OAuth callback flow broken — favicon request overwrites auth code
- **Severity:** High — blocked authentication entirely (both fresh and re-auth)
- **Status:** Fixed in `widget.py`
- **Root cause:** Browser `/favicon.ico` request

#### Root Cause

`_CallbackHandler.do_GET()` handled **all** GET requests identically, unconditionally storing parsed query params on the server. After the real OAuth callback (`/?code=AUTH_CODE&state=NONCE`), the browser automatically requested `/favicon.ico` (standard browser behavior when loading any HTML page). This second request had no query params, so `do_GET()` overwrote:
- `server.auth_code = None` (was the real auth code)
- `server.state = None` (was the CSRF nonce)
- `server.callback_received = True` (unchanged)

When `_check_callback()` then ran, it found `callback_received=True` but `auth_code=None`, hitting the "no code received" branch and resetting the widget to "Click to sign in".

#### Diagnostic trace that confirmed the bug

Using `enable_debug()` logging added to `do_GET`, two requests were visible:
```
[tokentoss.widget DEBUG] Callback received: code=True, state=True, error=None    ← real OAuth callback
[tokentoss.widget DEBUG] Callback received: code=False, state=False, error=None   ← /favicon.ico
```

The polling loop then read `auth_code=None` because the favicon request had already overwritten it.

#### Fix applied

In `do_GET()`, only store callback data when the request is an actual OAuth callback (has `code` or `error` param):

```python
is_callback = auth_code is not None or error is not None
if is_callback:
    self.server.auth_code = auth_code
    self.server.state = state
    self.server.error = error
    self.server.callback_received = True
```

Non-callback requests (`/favicon.ico`, `/robots.txt`, etc.) still receive a 200 response but do not modify stored auth data.

#### Additional hardening applied (from original analysis)

The earlier hypotheses (A–D) identified real secondary issues that were also fixed:
1. **`_try_start_server()` now stops old server first** — prevents orphaned servers holding old ports
2. **`_check_callback()` uses `reset()` instead of `stop()` + `_try_start_server()`** — server stays alive on the same port between auth flows
3. **JS popup polling debounced** — requires 2 consecutive `popup.closed` checks (1s total) before firing `check_callback`, preventing premature detection during cross-origin redirects
4. **Logging added** — `_logging.py` module with `enable_debug()`/`disable_debug()`, debug calls in `do_GET`, `start()`, `stop()`, `prepare_auth()`, `_check_callback()`, `_handle_message()`

#### Test updated

`test_server_handles_no_query_params` renamed to `test_server_ignores_no_query_params` — now asserts that requests without `code`/`error` params do NOT set `callback_received=True`.

### 5. BUG: `test_init_requires_config` fails when config file exists on disk
- **Severity:** Low — test-only, does not affect runtime
- **Status:** Open
- **Root cause:** `AuthManager.__init__` auto-discovers config from the platform default path (`~/.config/tokentoss/client_secrets.json` or equivalent). The test `test_init_requires_config` expects `AuthManager(storage=MemoryStorage())` to raise `ValueError`, but when a config file exists on the developer's machine, auto-discovery succeeds and no error is raised.
- **Fix:** Mock `get_config_path` to return a non-existent path, isolating the test from the host filesystem.
- **Priority:** Low — only fails on machines with existing config, does not affect CI (if CI has no config file)

---

## IAPClient

*(to be filled as testing continues)*
