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

---

## IAPClient

*(to be filled as testing continues)*
