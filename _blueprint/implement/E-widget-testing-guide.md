# Widget Testing Guide — Cell-by-Cell Walkthrough

Open a fresh notebook in JupyterLab (`uv run jupyter lab`) and work through each cell below.

---

## Cell 1: Verify Installation

```python
import tokentoss
print(f"tokentoss version: {tokentoss.__version__}")
print(f"Config path: {tokentoss.get_config_path()}")
```

**Expected:** Prints `0.1.0` and a path like `~/.config/tokentoss/client_secrets.json`.

---

## Cell 2: Check for Existing Config

```python
from pathlib import Path

config_path = tokentoss.get_config_path()
if config_path.exists():
    print(f"Config exists at: {config_path}")
    perms = oct(config_path.stat().st_mode & 0o777)
    print(f"Permissions: {perms}")
else:
    print("No config found — will use ConfigureWidget next")
```

**Expected:** Either shows existing config with `0o600` permissions, or says none found.

---

## Cell 3: ConfigureWidget

```python
from tokentoss import ConfigureWidget

cw = ConfigureWidget()
display(cw)
```

**Action:**
1. Enter your real GCP Desktop OAuth **Client ID** and **Client Secret**
2. Click **Configure**
3. Should show "Configured! Saved to ..."

**Check:** Status text turns green on success, red on error (try submitting empty fields first to test validation).

---

## Cell 4: Verify Config Was Saved

```python
import json, os

config_path = tokentoss.get_config_path()
assert config_path.exists(), "Config file not created!"

perms = oct(config_path.stat().st_mode & 0o777)
print(f"File: {config_path}")
print(f"Permissions: {perms}")
assert perms == "0o600", f"Expected 0o600, got {perms}"

with open(config_path) as f:
    data = json.load(f)

print(f"Has 'installed' key: {'installed' in data}")
print(f"Client ID ends with: ...{data['installed']['client_id'][-20:]}")
print("Config saved correctly!")
```

**Expected:** File exists, permissions are `0o600`, has `installed` key with your client ID.

---

## Cell 5: GoogleAuthWidget — Fresh Auth

```python
from tokentoss import GoogleAuthWidget

widget = GoogleAuthWidget()
display(widget)
```

**Action:**
1. Widget should auto-discover credentials from config path
2. Click **"Sign in with Google"**
3. A popup opens → complete Google OAuth consent
4. Popup closes → widget should update to **"Signed in as you@gmail.com"**

**If popup is blocked:** The widget should show a manual URL input field. Copy the redirect URL from the popup's address bar and paste it in.

---

## Cell 6: Verify Authentication State

```python
print(f"is_authenticated: {widget.is_authenticated}")
print(f"user_email: {widget.user_email}")
print(f"status: {widget.status}")

# Check module-level credentials
print(f"\ntokentoss.CREDENTIALS is set: {tokentoss.CREDENTIALS is not None}")
if tokentoss.CREDENTIALS:
    print(f"Credential type: {type(tokentoss.CREDENTIALS).__name__}")
    print(f"Token valid: {tokentoss.CREDENTIALS.valid}")
    print(f"Expired: {tokentoss.CREDENTIALS.expired}")
```

**Expected:** `is_authenticated: True`, email matches yours, CREDENTIALS is set and valid.

---

## Cell 7: Inspect AuthManager & Tokens

```python
am = widget.auth_manager

print(f"AuthManager.is_authenticated: {am.is_authenticated}")
print(f"AuthManager.user_email: {am.user_email}")
print(f"Has refresh token: {am.credentials.refresh_token is not None}")

# Check token data in storage
token_data = am.storage.load()
if token_data:
    print(f"\nStored token data:")
    print(f"  user_email: {token_data.user_email}")
    print(f"  scopes: {token_data.scopes}")
    print(f"  expiry: {token_data.expiry}")
    print(f"  is_expired: {token_data.is_expired}")
    print(f"  has id_token: {bool(token_data.id_token)}")
    print(f"  has refresh_token: {bool(token_data.refresh_token)}")
```

**Expected:** All fields populated. `is_expired` should be `False`. Both `id_token` and `refresh_token` should be present.

---

## Cell 8: Check Token File on Disk

```python
from tokentoss.storage import FileStorage

fs = FileStorage()
print(f"Token file: {fs.path}")
print(f"Exists: {fs.path.exists()}")
if fs.path.exists():
    perms = oct(fs.path.stat().st_mode & 0o777)
    print(f"Permissions: {perms}")
```

**Expected:** Token file exists at `~/.config/tokentoss/tokens.json` with `0o600` permissions.

---

## Cell 9: Sign Out

```python
widget.sign_out()

print(f"is_authenticated: {widget.is_authenticated}")
print(f"user_email: '{widget.user_email}'")
print(f"status: {widget.status}")
print(f"tokentoss.CREDENTIALS: {tokentoss.CREDENTIALS}")
```

**Expected:** `is_authenticated: False`, empty email, status is "Click to sign in", CREDENTIALS is `None`.

---

## Cell 10: Re-display Widget After Sign Out

```python
display(widget)
```

**Action:** Widget should show the "Sign in with Google" button again (not the signed-in state). Click it to re-authenticate and verify the full flow works a second time.

---

## Cell 11: Verify Re-Auth Worked

```python
print(f"is_authenticated: {widget.is_authenticated}")
print(f"user_email: {widget.user_email}")
print(f"tokentoss.CREDENTIALS is set: {tokentoss.CREDENTIALS is not None}")
```

**Expected:** Back to authenticated state after the second sign-in.

---

## Cell 12: IAPClient (Requires IAP Service)

> **Skip this cell** until we have a test service deployed. Come back here after Part 2.

```python
from tokentoss import IAPClient

# Replace with your actual IAP-protected service URL
client = IAPClient(base_url="https://YOUR-IAP-SERVICE.run.app")

# Test authenticated request
whoami = client.get_json("/whoami")
print(whoami)
```

---

## Troubleshooting

**Widget doesn't render:** Ensure you're running in JupyterLab (not plain Jupyter Notebook). Check that `anywidget` is installed: `uv run pip list | grep anywidget`.

**Popup blocked:** Browser popup blockers can prevent the OAuth window from opening. Allow popups for `localhost`. The widget provides a manual URL fallback if the popup fails.

**"Config not found" error:** Run Cell 3 (ConfigureWidget) first. Check that the file exists at the path shown by `tokentoss.get_config_path()`.

**Token expired after waiting:** Tokens expire after ~1 hour. Re-run Cell 5 to re-authenticate. The widget should handle refresh automatically if a refresh token is present.

**Sign-out doesn't clear state:** Restart the kernel and re-run from Cell 1. Module-level `CREDENTIALS` persists in the Python process.

---

## Summary Checklist

| # | Test | Pass? |
|---|------|-------|
| 1 | Package imports, version correct | |
| 2 | Config path accessible | |
| 3 | ConfigureWidget renders, saves credentials | |
| 4 | Config file has 0o600 permissions | |
| 5 | GoogleAuthWidget renders, OAuth popup works | |
| 6 | Widget state reflects authenticated user | |
| 7 | AuthManager has tokens, refresh token present | |
| 8 | Token file on disk with secure permissions | |
| 9 | Sign out clears all state | |
| 10 | Re-auth works cleanly after sign out | |
| 11 | Second auth state is correct | |
| 12 | IAPClient makes authenticated request (deferred) | |
