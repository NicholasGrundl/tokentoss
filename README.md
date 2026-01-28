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

### 2. Authenticate in Jupyter

```python
from tokentoss import GoogleAuthWidget, IAPClient

# Create and display authentication widget
widget = GoogleAuthWidget(client_secrets_path="./client_secrets.json")
display(widget)

# Click "Sign in with Google" and complete the flow
# Widget shows "Signed in as user@example.com"
```

### 3. Make Authenticated Requests

```python
# Create client (auto-discovers credentials)
client = IAPClient(base_url="https://my-iap-service.run.app")

# Make requests - ID token added automatically
data = client.get_json("/api/data")
response = client.post("/api/items", json={"name": "test"})
```

## How It Works

1. **Widget** opens a popup for Google OAuth
2. User authenticates and grants consent
3. **AuthManager** exchanges auth code for tokens (with PKCE)
4. Tokens are stored securely (file permissions 0600)
5. **IAPClient** uses ID token for IAP authentication
6. Tokens refresh automatically when expired

## Development

```bash
# Clone and install
git clone https://github.com/yourusername/tokentoss.git
cd tokentoss
uv sync --group dev

# Run tests
uv run pytest

# Start Jupyter for testing
uv run jupyter lab
```

## License

MIT
