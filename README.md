# tokentoss

OAuth authentication from Jupyter notebooks for IAP-protected GCP services.

## Features

- **anywidget** with "Sign in with Google" button
- **Authorization Code flow with PKCE** for security and refresh tokens
- **Token persistence** across sessions
- **IAPClient** for authenticated HTTP requests with auto-refresh

## Installation

```bash
pip install tokentoss
```

Or with uv:

```bash
uv add tokentoss
```

## Quick Start

### 1. One-Time GCP Setup

1. Create a Desktop OAuth client in [GCP Console](https://console.cloud.google.com/apis/credentials)
2. Download `client_secrets.json`
3. Add the Desktop client ID to your IAP's programmatic access allowlist
4. Grant yourself the "IAP-secured Web App User" role

### 2. Configure Credentials

Use the `ConfigureWidget` for a password-safe setup (credentials never appear in notebook source):

```python
from tokentoss import ConfigureWidget

display(ConfigureWidget())
# Enter Client ID and Client Secret, click "Configure"
```

Or configure programmatically:

```python
import tokentoss

tokentoss.configure(client_id="YOUR_CLIENT_ID", client_secret="YOUR_SECRET")
```

Credentials are stored to `~/.config/tokentoss/client_secrets.json` so they stay out of version control.

### 3. Authenticate in Jupyter

```python
from tokentoss import GoogleAuthWidget

# Widget auto-discovers credentials from the standard config location
widget = GoogleAuthWidget()
display(widget)

# Click "Sign in with Google" and complete the flow
# Widget shows "Signed in as user@example.com"
```

### 4. Make Authenticated Requests

```python
from tokentoss import IAPClient

# Create client (auto-discovers credentials)
client = IAPClient(base_url="https://my-iap-service.run.app")

# Make requests - ID token added automatically
data = client.get_json("/api/data")
response = client.post("/api/items", json={"name": "test"})
```

## How It Works

1. **`configure()`** stores OAuth client credentials to a standard platform location
2. **Widget** opens a popup for Google OAuth
3. User authenticates and grants consent
4. **AuthManager** exchanges auth code for tokens (with PKCE)
5. Tokens are stored securely (file permissions 0600)
6. **IAPClient** uses ID token for IAP authentication
7. Tokens refresh automatically when expired

## Development

```bash
# Clone and install
git clone https://github.com/yourusername/tokentoss.git
cd tokentoss
uv sync --group dev

# Run tests
uv run pytest

# Lint and format
uv run ruff format src/ tests/
uv run ruff check src/ tests/

# Type check (advisory)
uv run ty check src/

# Start Jupyter for testing
uv run jupyter lab
```

## License

MIT
