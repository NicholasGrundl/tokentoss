"""tokentoss - OAuth authentication from Jupyter notebooks for IAP-protected GCP services.

Example usage:
    from tokentoss import GoogleAuthWidget, IAPClient

    # Create and display authentication widget
    widget = GoogleAuthWidget(client_secrets_path="./client_secrets.json")
    display(widget)

    # After authentication, create client
    client = IAPClient(base_url="https://my-iap-service.run.app")
    data = client.get_json("/api/data")
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .auth_manager import AuthManager, ClientConfig, generate_pkce_pair, DEFAULT_SCOPES
from .exceptions import (
    TokenTossError,
    NoCredentialsError,
    TokenRefreshError,
    TokenExchangeError,
    StorageError,
    InsecureFilePermissionsWarning,
)
from .storage import FileStorage, MemoryStorage, TokenData
from .setup import configure, configure_from_credentials, configure_from_file, get_config_path

if TYPE_CHECKING:
    from google.oauth2.credentials import Credentials

__version__ = "0.1.0"

# Module-level credentials set by AuthManager on successful authentication.
# Used by IAPClient for automatic credential discovery.
CREDENTIALS: Credentials | None = None

__all__ = [
    # Version
    "__version__",
    # Module-level state
    "CREDENTIALS",
    # Auth
    "AuthManager",
    "ClientConfig",
    "generate_pkce_pair",
    "DEFAULT_SCOPES",
    # Storage
    "FileStorage",
    "MemoryStorage",
    "TokenData",
    # Setup
    "configure",
    "configure_from_credentials",
    "configure_from_file",
    "get_config_path",
    # Exceptions
    "TokenTossError",
    "NoCredentialsError",
    "TokenRefreshError",
    "TokenExchangeError",
    "StorageError",
    "InsecureFilePermissionsWarning",
    # Widget (imported lazily to avoid anywidget dependency if not needed)
    # "GoogleAuthWidget",
    # Client (imported lazily)
    # "IAPClient",
]


def __getattr__(name: str):
    """Lazy import for optional components."""
    if name == "GoogleAuthWidget":
        from .widget import GoogleAuthWidget
        return GoogleAuthWidget
    if name == "IAPClient":
        from .client import IAPClient
        return IAPClient
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
