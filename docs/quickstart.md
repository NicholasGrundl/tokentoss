# Quick Start

Get up and running with tokentoss in a Jupyter notebook.

## Prerequisites

- Python 3.10+
- A Google account (Gmail or Workspace)
- Access to an IAP-protected GCP service (your admin provides the credentials and service URL)

## Install

```bash
pip install tokentoss
```

Or with uv:

```bash
uv add tokentoss
```

## 1. Configure Credentials (One-Time)

Your GCP admin will provide you with a **Client ID** and **Client Secret**. Enter them using the ConfigureWidget:

```python
from tokentoss import ConfigureWidget

display(ConfigureWidget())
# Enter Client ID and Client Secret, click "Configure"
```

Or configure programmatically:

```python
import tokentoss

tokentoss.configure(
    client_id="YOUR_CLIENT_ID.apps.googleusercontent.com",
    client_secret="YOUR_SECRET",
)
```

Credentials are stored securely at `~/.config/tokentoss/client_secrets.json` (file permissions `0600`) so they stay out of your notebooks and version control.

You only need to do this once per machine.

## 2. Authenticate (Per Session)

```python
from tokentoss import GoogleAuthWidget

widget = GoogleAuthWidget()
display(widget)
```

Click **"Sign in with Google"** and complete the OAuth flow in the popup. The widget updates to show **"Signed in as user@example.com"** when done.

If the popup is blocked by your browser, the widget provides a manual URL fallback — copy the URL, complete sign-in in a new tab, and paste the redirect URL back.

## 3. Make Authenticated Requests

```python
from tokentoss import IAPClient

# Point at your IAP-protected service
client = IAPClient(base_url="https://my-iap-service.run.app")

# Make requests — ID token is added automatically
data = client.get_json("/api/data")
response = client.post("/api/items", json={"name": "test"})
```

Tokens refresh automatically when they expire. No re-authentication needed during a session (up to 24 hours).

## Working with Multiple Services

All IAP-protected services that share the same OAuth client work with a single authentication:

```python
service_a = IAPClient(base_url="https://service-a.run.app")
service_b = IAPClient(base_url="https://service-b.run.app")

data_a = service_a.get_json("/data")
data_b = service_b.get_json("/info")
```

## Sign Out

```python
widget.sign_out()
```

This clears stored credentials. You'll need to re-authenticate to make further requests.

## Troubleshooting

**"Popup blocked"** — Check your browser's popup settings for the Jupyter URL. Alternatively, use the manual URL fallback shown by the widget.

**"No valid credentials"** — Run `ConfigureWidget()` to enter your Client ID and Client Secret, or call `tokentoss.configure(...)`.

**"Permission denied" from the IAP service** — Contact your GCP admin to verify you've been granted the "IAP-secured Web App User" role.

**"Session expired"** — Sessions last up to 24 hours. Re-display `GoogleAuthWidget()` and sign in again.
