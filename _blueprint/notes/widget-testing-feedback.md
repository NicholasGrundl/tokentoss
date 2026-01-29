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

### 4. BUG: OAuth callback flow broken — callback server never receives auth code
- **Severity:** High — blocks authentication entirely (both fresh and re-auth)
- **Status:** Partially diagnosed, root cause not fully confirmed

#### Symptoms
1. User clicks "Sign in with Google", popup opens, OAuth flow completes, **success page is displayed** in popup
2. Popup auto-closes (via `setTimeout(window.close(), 1500)` in success HTML)
3. Widget does NOT update to "Signed in" — instead shows either:
   - "Click to sign in" (meaning `_check_callback()` ran, `check_callback()` returned `True`, but `auth_code` was `None`)
   - "Paste the redirect URL below" (meaning `check_callback()` returned `False` — callback not received)
4. Subsequent attempts also fail with port mismatch

#### Observed Evidence
- **Port mismatch confirmed multiple times:** Auth URL contains `redirect_uri=http://127.0.0.1:{port_A}` but `widget._callback_server.port` is `{port_B}` after flow completes
  - Example 1: auth URL port `56820`, server port `56834`
  - Example 2: auth URL port `57640`, server port `57643`
- **Server state after failure:** `callback_received: False`, `auth_code: None`, `error: None`, `_server` is not `None` (server alive but saw nothing)
- **Monkey-patching `_try_start_server`** on the widget instance did NOT fire — suggesting the server is being replaced via a different code path (e.g. `self._try_start_server()` resolved from the class, not the patched instance attribute, OR a new `CallbackServer` object is being created)
- **Monkey-patching `_CallbackHandler.do_GET`** at the class level also did NOT fire — the handler never processed any GET request, even though the browser displayed the success HTML. This is the most puzzling observation.
- **First-ever auth (previous day)** worked. Token was persisted to disk. All subsequent fresh-kernel attempts fail.
- **Widget auto-detects existing tokens** correctly — when `tokens.json` exists from a prior session, `__init__` → `_load_from_storage()` works and widget shows "Signed in"

#### Analysis & Hypotheses

**Hypothesis A: Port mismatch from server recycling**
- `_check_callback()` (`widget.py:648-650`) calls `stop()` then `_try_start_server()` unconditionally after any callback check that returns `True`
- This allocates a new random port, but the auth URL still references the old port
- However, this doesn't explain why the FIRST attempt on a fresh kernel also fails (no prior `_check_callback()` to recycle the server)

**Hypothesis B: `check_callback()` fires prematurely (race condition)**
- JS polls every 500ms for `popup.closed` (`widget.py:340-348`)
- The popup may briefly report as "closed" during the OAuth redirect (navigating between Google's consent page and the localhost callback)
- If JS detects `popup.closed` before the OAuth flow completes, it sends `check_callback` too early
- Python's `_check_callback()` finds no callback yet → takes the `else` branch (line 651-654) OR the `True` branch with no code (line 643-646)
- In the `True`-with-no-code path: server is stopped and restarted (lines 648-650), new port assigned
- The actual OAuth redirect then hits the OLD port (now dead) → success page was likely served by the old server just before it was stopped, but the code was lost in the stop/restart
- This would explain: success page visible, but code never captured by current server

**Hypothesis C: Multiple `_check_callback()` invocations**
- JS polling continues sending `check_callback` messages while the popup is open
- If `_handle_message` dispatches `check_callback` multiple times rapidly, the server could be cycled multiple times
- The +3 port gap (57640 → 57643) suggests ~3 server restarts occurred

**Hypothesis D: Browser behavior / popup detection**
- Some browsers may report `popup.closed` differently during redirects
- The `window.open()` popup may lose its reference during cross-origin navigation (Google → localhost)
- This could trigger the "popup closed" detection prematurely

#### Key Code Paths (for debugging)

1. **JS click handler** → `model.send({ type: 'prepare_auth' })` (`widget.py:281`)
2. **Python `prepare_auth()`** → resets server, generates PKCE, builds auth URL with current server port (`widget.py:587-618`)
3. **JS `onAuthUrlChange`** → opens popup, starts polling (`widget.py:318-336`)
4. **JS polling** → every 500ms checks `popup.closed`, sends `check_callback` when true (`widget.py:338-356`)
5. **Python `_check_callback()`** → reads server state, exchanges code or resets (`widget.py:620-654`)
6. **Callback handler** → `_CallbackHandler.do_GET()` stores code on `self.server` (`widget.py:69-99`)
7. **Server lifecycle** → `stop()` copies results then shuts down, `_try_start_server()` creates fresh server (`widget.py:118-145, 152-168`)

#### Proposed Fix Direction
1. **Do NOT restart the server in `_check_callback()`** — remove lines 649-650. Keep the same server alive.
2. **Only create/restart server in `prepare_auth()`** — tie the server lifecycle to auth flow initiation, not callback checking.
3. **Debounce or guard `check_callback`** — prevent multiple invocations from JS polling. Add a flag like `_auth_in_progress` that's set in `prepare_auth()` and cleared after exchange or timeout.
4. **Consider removing popup auto-close** — let the user close the popup manually, giving more time for the callback to be captured. Or increase the auto-close delay significantly (e.g. 5s).
5. **Add logging** — the callback server and handler are completely silent. Add `print()` or `logging` calls to `_CallbackHandler.do_GET()`, `CallbackServer.start()`, `CallbackServer.stop()`, and `_check_callback()` to make debugging possible.

#### Priority
**High — must fix before v0.1.0.** This blocks the core authentication flow. The widget's primary purpose is non-functional.

---

## IAPClient

*(to be filled as testing continues)*
