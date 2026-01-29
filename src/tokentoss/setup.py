"""Client secrets configuration for tokentoss.

Provides functions to install OAuth client credentials to a standard
platform-specific location so AuthManager can auto-discover them.

Usage from JupyterLab:
    import tokentoss

    # From direct credentials (copy-paste from GCP console)
    tokentoss.configure(client_id="...", client_secret="...")

    # From a downloaded client_secrets.json file
    tokentoss.configure(path="./client_secrets.json")
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import platformdirs

from .exceptions import StorageError

# Application name for platformdirs paths
APP_NAME = "tokentoss"

# Hardcoded Google OAuth boilerplate - same for all Google OAuth apps
GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"
GOOGLE_CERT_URL = "https://www.googleapis.com/oauth2/v1/certs"
DEFAULT_REDIRECT_URIS = ["http://localhost"]


def get_config_path() -> Path:
    """Get the standard client_secrets.json location.

    Returns:
        Path to ~/.config/tokentoss/client_secrets.json (or platform equivalent).
    """
    config_dir = platformdirs.user_config_dir(APP_NAME)
    return Path(config_dir) / "client_secrets.json"


def configure(
    client_id: str | None = None,
    client_secret: str | None = None,
    path: str | Path | None = None,
    project_id: str | None = None,
) -> Path:
    """Install client secrets to the standard tokentoss config location.

    Supports two input modes:
    - Direct credentials: provide client_id and client_secret
    - Existing file: provide path to a client_secrets.json

    Always writes to the standard platformdirs location
    (~/.config/tokentoss/client_secrets.json on macOS/Linux).

    Args:
        client_id: Google OAuth client ID.
        client_secret: Google OAuth client secret.
        path: Path to an existing client_secrets.json file.

    Returns:
        Path where client_secrets.json was installed.

    Raises:
        ValueError: If arguments are invalid or missing.
        StorageError: If the file cannot be written.

    Examples:
        >>> import tokentoss
        >>> # From GCP console copy-paste
        >>> tokentoss.configure(client_id="123.apps.googleusercontent.com", client_secret="GOCSPX-...")
        >>> # From downloaded file
        >>> tokentoss.configure(path="./client_secrets.json")
    """
    if path is not None:
        return configure_from_file(path)
    elif client_id is not None and client_secret is not None:
        return configure_from_credentials(client_id, client_secret, project_id=project_id)
    else:
        raise ValueError(
            "Provide either (client_id, client_secret) or path to an existing "
            "client_secrets.json file."
        )


def configure_from_credentials(
    client_id: str,
    client_secret: str,
    project_id: str | None = None,
) -> Path:
    """Build client_secrets.json from credentials and install to standard location.

    Merges the provided credentials with hardcoded Google OAuth boilerplate
    (auth_uri, token_uri, etc.) so the user only needs client_id and client_secret.

    Args:
        client_id: Google OAuth client ID.
        client_secret: Google OAuth client secret.
        project_id: Optional GCP project ID.

    Returns:
        Path where client_secrets.json was written.

    Raises:
        ValueError: If client_id or client_secret is empty.
        StorageError: If file cannot be written.
    """
    if not client_id or not client_id.strip():
        raise ValueError("client_id cannot be empty")
    if not client_secret or not client_secret.strip():
        raise ValueError("client_secret cannot be empty")

    config_data: dict = {
        "installed": {
            "client_id": client_id.strip(),
            "client_secret": client_secret.strip(),
            "auth_uri": GOOGLE_AUTH_URI,
            "token_uri": GOOGLE_TOKEN_URI,
            "auth_provider_x509_cert_url": GOOGLE_CERT_URL,
            "redirect_uris": DEFAULT_REDIRECT_URIS.copy(),
        }
    }

    if project_id:
        config_data["installed"]["project_id"] = project_id.strip()

    return _write_config(config_data)


def configure_from_file(source_path: str | Path) -> Path:
    """Copy an existing client_secrets.json to the standard location.

    Validates the file format before copying. Supports both "installed"
    (desktop app) and "web" format client_secrets.json files.

    Args:
        source_path: Path to the source client_secrets.json file.

    Returns:
        Path where client_secrets.json was installed.

    Raises:
        FileNotFoundError: If source file doesn't exist.
        ValueError: If file format is invalid.
        StorageError: If file cannot be written.
    """
    source_path = Path(source_path)
    if not source_path.exists():
        raise FileNotFoundError(f"Client secrets file not found: {source_path}")

    try:
        with open(source_path) as f:
            config_data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {source_path}: {e}") from e

    # Validate structure
    if "installed" not in config_data and "web" not in config_data:
        raise ValueError(
            f"Invalid client_secrets.json format in {source_path}. "
            "Expected 'installed' or 'web' key."
        )

    section = config_data.get("installed") or config_data.get("web")
    if "client_id" not in section or "client_secret" not in section:
        raise ValueError(f"Missing client_id or client_secret in {source_path}.")

    return _write_config(config_data)


def _write_config(config_data: dict) -> Path:
    """Write config data to the standard location with secure permissions.

    Args:
        config_data: The client_secrets.json structure to write.

    Returns:
        Path where the file was written.

    Raises:
        StorageError: If file cannot be written.
    """
    dest = get_config_path()
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(config_data, indent=2))
        os.chmod(dest, 0o600)
    except OSError as e:
        raise StorageError(f"Failed to write config to {dest}: {e}") from e

    return dest
