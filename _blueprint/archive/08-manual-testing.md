# Manual Testing Checklist

## Purpose

Before any release, verify the full user-facing flow in a real JupyterLab environment. Automated tests cover unit logic and mocked flows, but the widget rendering, popup OAuth, and end-to-end token usage need a human in the loop.

## Prerequisites

- A GCP project with IAP enabled on a Cloud Run (or App Engine) service
- A Desktop OAuth client created in GCP Console
- The Desktop client ID added to IAP's programmatic access allowlist
- Your Google account granted the "IAP-secured Web App User" role
- JupyterLab running locally: `uv run jupyter lab`

## Checklist

### ConfigureWidget

- [ ] `ConfigureWidget()` renders in a notebook cell with two input fields
- [ ] Both fields are password-masked (no plaintext secrets visible)
- [ ] Entering valid `client_id` and `client_secret` and clicking "Configure" shows success
- [ ] Credentials are written to `~/.config/tokentoss/client_secrets.json`
- [ ] File permissions are `0600` (owner read/write only)
- [ ] Submitting with empty fields shows a validation error
- [ ] Re-running `ConfigureWidget()` and submitting overwrites the previous config

### GoogleAuthWidget — Fresh Auth

- [ ] `GoogleAuthWidget()` (no args) picks up credentials from `~/.config/tokentoss/client_secrets.json`
- [ ] Widget renders with a "Sign in with Google" button
- [ ] Clicking the button opens a popup for Google OAuth
- [ ] After completing OAuth in the popup, widget updates to "Signed in as user@example.com"
- [ ] `tokentoss.CREDENTIALS` is set (not `None`)

### GoogleAuthWidget — Manual URL Fallback

- [ ] If the popup is blocked, the widget shows a manual URL input option
- [ ] Pasting the redirect URL into the manual input completes authentication

### IAPClient

- [ ] `IAPClient(base_url="https://your-iap-service.run.app")` creates a client
- [ ] `client.get_json("/some-endpoint")` returns data successfully (200)
- [ ] The request includes a valid `Authorization: Bearer <id_token>` header

### Token Refresh

- [ ] Wait for the access token to expire (or manually clear it)
- [ ] A subsequent `IAPClient` request automatically refreshes the token
- [ ] No re-authentication prompt needed

### Sign Out + Re-Auth

- [ ] Calling `widget.sign_out()` clears credentials
- [ ] `tokentoss.CREDENTIALS` is `None` after sign out
- [ ] Re-displaying the widget shows the "Sign in" button again
- [ ] Completing OAuth again works cleanly

### Edge Cases

- [ ] Delete `~/.config/tokentoss/client_secrets.json` and run `GoogleAuthWidget()` — should get a clear error about missing credentials
- [ ] Provide an invalid `client_secret` and attempt auth — should get a clear error during token exchange
- [ ] Run in a fresh virtual environment with only `tokentoss` installed (no extra dev deps)

## When to Run

- Before tagging any release (`v0.x.0`)
- After any changes to widget JS/CSS
- After any changes to the OAuth flow or token handling
- After the widgets subpackage refactor
