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

from .auth_manager import DEFAULT_SCOPES, AuthManager, ClientConfig, generate_pkce_pair
from .exceptions import (
    InsecureFilePermissionsWarning,
    NoCredentialsError,
    StorageError,
    TokenExchangeError,
    TokenRefreshError,
    TokenTossError,
)
from .setup import configure, configure_from_credentials, configure_from_file, get_config_path
from .storage import FileStorage, MemoryStorage, TokenData

if TYPE_CHECKING:
    from google.oauth2.credentials import Credentials

__version__ = "0.1.0"

# Module-level credentials set by AuthManager on successful authentication.
# Used by IAPClient for automatic credential discovery.
CREDENTIALS: Credentials | None = None

__all__ = [
    "AuthManager",
    "ClientConfig",
    "CREDENTIALS",
    "DEFAULT_SCOPES",
    "FileStorage",
    "InsecureFilePermissionsWarning",
    "MemoryStorage",
    "NoCredentialsError",
    "StorageError",
    "TokenData",
    "TokenExchangeError",
    "TokenRefreshError",
    "TokenTossError",
    "__version__",
    "configure",
    "configure_from_credentials",
    "configure_from_file",
    "generate_pkce_pair",
    "get_config_path",
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
