"""Token storage implementations for tokentoss."""

from __future__ import annotations

import json
import os
import stat
import warnings
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import platformdirs

from .exceptions import InsecureFilePermissionsWarning, StorageError

# Default application name for platformdirs
APP_NAME = "tokentoss"


@dataclass
class TokenData:
    """Container for OAuth token data."""

    access_token: str
    id_token: str
    refresh_token: str
    expiry: str  # ISO format datetime string
    scopes: list[str]
    user_email: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TokenData:
        """Create TokenData from dictionary."""
        return cls(
            access_token=data["access_token"],
            id_token=data["id_token"],
            refresh_token=data["refresh_token"],
            expiry=data["expiry"],
            scopes=data.get("scopes", []),
            user_email=data.get("user_email"),
        )

    @property
    def expiry_datetime(self) -> datetime:
        """Parse expiry string to datetime."""
        return datetime.fromisoformat(self.expiry.replace("Z", "+00:00"))

    @property
    def is_expired(self) -> bool:
        """Check if access token is expired."""
        from datetime import timezone

        return datetime.now(timezone.utc) >= self.expiry_datetime


class MemoryStorage:
    """In-memory token storage for testing and temporary use."""

    def __init__(self) -> None:
        self._tokens: TokenData | None = None

    def save(self, tokens: TokenData) -> None:
        """Save tokens to memory."""
        self._tokens = tokens

    def load(self) -> TokenData | None:
        """Load tokens from memory."""
        return self._tokens

    def clear(self) -> None:
        """Clear stored tokens."""
        self._tokens = None

    def exists(self) -> bool:
        """Check if tokens exist in storage."""
        return self._tokens is not None


class FileStorage:
    """File-based token storage with secure permissions."""

    # Secure file permissions: owner read/write only (0600)
    SECURE_PERMISSIONS = stat.S_IRUSR | stat.S_IWUSR

    def __init__(self, path: str | Path | None = None) -> None:
        """Initialize file storage.

        Args:
            path: Path to token file. If None, uses platformdirs default location.
        """
        if path is None:
            config_dir = platformdirs.user_config_dir(APP_NAME)
            self.path = Path(config_dir) / "tokens.json"
        else:
            self.path = Path(path)

    def save(self, tokens: TokenData) -> None:
        """Save tokens to file with secure permissions.

        Args:
            tokens: TokenData to save.

        Raises:
            StorageError: If file cannot be written.
        """
        try:
            # Ensure parent directory exists
            self.path.parent.mkdir(parents=True, exist_ok=True)

            # Write tokens to file
            with open(self.path, "w") as f:
                json.dump(tokens.to_dict(), f, indent=2)

            # Set secure permissions (owner read/write only)
            os.chmod(self.path, self.SECURE_PERMISSIONS)

        except OSError as e:
            raise StorageError(f"Failed to save tokens to {self.path}: {e}") from e

    def load(self) -> TokenData | None:
        """Load tokens from file.

        Returns:
            TokenData if file exists and is valid, None otherwise.

        Raises:
            StorageError: If file exists but cannot be read or parsed.

        Warns:
            InsecureFilePermissionsWarning: If file has insecure permissions.
        """
        if not self.path.exists():
            return None

        # Check file permissions
        self._check_permissions()

        try:
            with open(self.path) as f:
                data = json.load(f)
            return TokenData.from_dict(data)

        except json.JSONDecodeError as e:
            raise StorageError(f"Invalid JSON in token file {self.path}: {e}") from e
        except KeyError as e:
            raise StorageError(f"Missing required field in token file: {e}") from e
        except OSError as e:
            raise StorageError(f"Failed to read token file {self.path}: {e}") from e

    def clear(self) -> None:
        """Delete the token file."""
        if self.path.exists():
            try:
                self.path.unlink()
            except OSError as e:
                raise StorageError(f"Failed to delete token file {self.path}: {e}") from e

    def exists(self) -> bool:
        """Check if token file exists."""
        return self.path.exists()

    def _check_permissions(self) -> None:
        """Check if file has secure permissions, warn if not."""
        if not self.path.exists():
            return

        try:
            current_mode = self.path.stat().st_mode & 0o777
            if current_mode != (self.SECURE_PERMISSIONS & 0o777):
                warnings.warn(
                    f"Token file {self.path} has insecure permissions "
                    f"(mode {oct(current_mode)}). "
                    f"Recommended: {oct(self.SECURE_PERMISSIONS & 0o777)} (owner read/write only). "
                    f"Run: chmod 600 {self.path}",
                    InsecureFilePermissionsWarning,
                    stacklevel=3,
                )
        except OSError:
            # Can't check permissions, skip warning
            pass
