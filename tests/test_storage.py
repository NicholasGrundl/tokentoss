"""Tests for tokentoss.storage module."""

import json
import os
import stat
import tempfile
import warnings
from datetime import datetime, timezone
from pathlib import Path

import pytest

from tokentoss.storage import (
    TokenData,
    MemoryStorage,
    FileStorage,
)
from tokentoss.exceptions import StorageError, InsecureFilePermissionsWarning


class TestTokenData:
    """Tests for TokenData dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        token = TokenData(
            access_token="access123",
            id_token="id123",
            refresh_token="refresh123",
            expiry="2024-01-15T10:30:00+00:00",
            scopes=["openid", "email"],
            user_email="test@example.com",
        )

        data = token.to_dict()

        assert data["access_token"] == "access123"
        assert data["id_token"] == "id123"
        assert data["refresh_token"] == "refresh123"
        assert data["scopes"] == ["openid", "email"]
        assert data["user_email"] == "test@example.com"

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "access_token": "access123",
            "id_token": "id123",
            "refresh_token": "refresh123",
            "expiry": "2024-01-15T10:30:00+00:00",
            "scopes": ["openid", "email"],
            "user_email": "test@example.com",
        }

        token = TokenData.from_dict(data)

        assert token.access_token == "access123"
        assert token.id_token == "id123"
        assert token.user_email == "test@example.com"

    def test_expiry_datetime(self):
        """Test expiry datetime parsing."""
        token = TokenData(
            access_token="a",
            id_token="i",
            refresh_token="r",
            expiry="2024-01-15T10:30:00+00:00",
            scopes=[],
        )

        expiry = token.expiry_datetime
        assert expiry.year == 2024
        assert expiry.month == 1
        assert expiry.day == 15

    def test_is_expired_future(self):
        """Test is_expired returns False for future expiry."""
        future = datetime.now(timezone.utc).replace(year=2099)
        token = TokenData(
            access_token="a",
            id_token="i",
            refresh_token="r",
            expiry=future.isoformat(),
            scopes=[],
        )

        assert token.is_expired is False

    def test_is_expired_past(self):
        """Test is_expired returns True for past expiry."""
        past = datetime.now(timezone.utc).replace(year=2020)
        token = TokenData(
            access_token="a",
            id_token="i",
            refresh_token="r",
            expiry=past.isoformat(),
            scopes=[],
        )

        assert token.is_expired is True


class TestMemoryStorage:
    """Tests for MemoryStorage."""

    def test_save_and_load(self):
        """Test saving and loading tokens."""
        storage = MemoryStorage()
        token = TokenData(
            access_token="access123",
            id_token="id123",
            refresh_token="refresh123",
            expiry="2024-01-15T10:30:00+00:00",
            scopes=["openid"],
        )

        storage.save(token)
        loaded = storage.load()

        assert loaded is not None
        assert loaded.access_token == "access123"

    def test_load_empty(self):
        """Test loading when nothing stored."""
        storage = MemoryStorage()
        assert storage.load() is None

    def test_clear(self):
        """Test clearing storage."""
        storage = MemoryStorage()
        token = TokenData(
            access_token="a",
            id_token="i",
            refresh_token="r",
            expiry="2024-01-15T10:30:00+00:00",
            scopes=[],
        )

        storage.save(token)
        storage.clear()

        assert storage.load() is None

    def test_exists(self):
        """Test exists check."""
        storage = MemoryStorage()
        assert storage.exists() is False

        storage.save(TokenData(
            access_token="a",
            id_token="i",
            refresh_token="r",
            expiry="2024-01-15T10:30:00+00:00",
            scopes=[],
        ))
        assert storage.exists() is True


class TestFileStorage:
    """Tests for FileStorage."""

    def test_save_and_load(self, tmp_path):
        """Test saving and loading tokens."""
        token_file = tmp_path / "tokens.json"
        storage = FileStorage(path=token_file)

        token = TokenData(
            access_token="access123",
            id_token="id123",
            refresh_token="refresh123",
            expiry="2024-01-15T10:30:00+00:00",
            scopes=["openid", "email"],
            user_email="test@example.com",
        )

        storage.save(token)
        loaded = storage.load()

        assert loaded is not None
        assert loaded.access_token == "access123"
        assert loaded.user_email == "test@example.com"

    def test_creates_parent_directory(self, tmp_path):
        """Test that parent directories are created."""
        token_file = tmp_path / "subdir" / "tokens.json"
        storage = FileStorage(path=token_file)

        storage.save(TokenData(
            access_token="a",
            id_token="i",
            refresh_token="r",
            expiry="2024-01-15T10:30:00+00:00",
            scopes=[],
        ))

        assert token_file.exists()

    def test_secure_permissions(self, tmp_path):
        """Test that file is created with secure permissions."""
        token_file = tmp_path / "tokens.json"
        storage = FileStorage(path=token_file)

        storage.save(TokenData(
            access_token="a",
            id_token="i",
            refresh_token="r",
            expiry="2024-01-15T10:30:00+00:00",
            scopes=[],
        ))

        mode = token_file.stat().st_mode & 0o777
        assert mode == 0o600  # Owner read/write only

    def test_warns_on_insecure_permissions(self, tmp_path):
        """Test warning on insecure file permissions."""
        token_file = tmp_path / "tokens.json"

        # Create file with insecure permissions
        token_file.write_text(json.dumps({
            "access_token": "a",
            "id_token": "i",
            "refresh_token": "r",
            "expiry": "2024-01-15T10:30:00+00:00",
            "scopes": [],
        }))
        os.chmod(token_file, 0o644)  # World readable

        storage = FileStorage(path=token_file)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            storage.load()

            assert len(w) == 1
            assert issubclass(w[0].category, InsecureFilePermissionsWarning)
            assert "insecure permissions" in str(w[0].message)

    def test_load_nonexistent(self, tmp_path):
        """Test loading from nonexistent file."""
        token_file = tmp_path / "nonexistent.json"
        storage = FileStorage(path=token_file)

        assert storage.load() is None

    def test_clear(self, tmp_path):
        """Test clearing storage."""
        token_file = tmp_path / "tokens.json"
        storage = FileStorage(path=token_file)

        storage.save(TokenData(
            access_token="a",
            id_token="i",
            refresh_token="r",
            expiry="2024-01-15T10:30:00+00:00",
            scopes=[],
        ))

        assert token_file.exists()
        storage.clear()
        assert not token_file.exists()

    def test_exists(self, tmp_path):
        """Test exists check."""
        token_file = tmp_path / "tokens.json"
        storage = FileStorage(path=token_file)

        assert storage.exists() is False

        storage.save(TokenData(
            access_token="a",
            id_token="i",
            refresh_token="r",
            expiry="2024-01-15T10:30:00+00:00",
            scopes=[],
        ))
        assert storage.exists() is True

    def test_invalid_json_raises_error(self, tmp_path):
        """Test that invalid JSON raises StorageError."""
        token_file = tmp_path / "tokens.json"
        token_file.write_text("not valid json")
        os.chmod(token_file, 0o600)

        storage = FileStorage(path=token_file)

        with pytest.raises(StorageError, match="Invalid JSON"):
            storage.load()
