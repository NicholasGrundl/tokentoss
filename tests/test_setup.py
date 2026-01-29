"""Tests for tokentoss.setup (client secrets configuration)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tokentoss.setup import (
    DEFAULT_REDIRECT_URIS,
    GOOGLE_AUTH_URI,
    GOOGLE_CERT_URL,
    GOOGLE_TOKEN_URI,
    configure,
    configure_from_credentials,
    configure_from_file,
    get_config_path,
)

# -- Helpers --


def _make_client_secrets_file(tmp_path: Path, **overrides) -> Path:
    """Write a valid client_secrets.json to tmp_path and return its path."""
    data = {
        "installed": {
            "client_id": "test-id.apps.googleusercontent.com",
            "client_secret": "GOCSPX-test-secret",
            "auth_uri": GOOGLE_AUTH_URI,
            "token_uri": GOOGLE_TOKEN_URI,
            "redirect_uris": ["http://localhost"],
        }
    }
    if overrides:
        data["installed"].update(overrides)
    filepath = tmp_path / "client_secrets.json"
    filepath.write_text(json.dumps(data, indent=2))
    return filepath


# -- TestGetConfigPath --


class TestGetConfigPath:
    def test_returns_path_object(self):
        result = get_config_path()
        assert isinstance(result, Path)

    def test_ends_with_client_secrets_json(self):
        result = get_config_path()
        assert result.name == "client_secrets.json"
        assert "tokentoss" in str(result)

    def test_consistent_across_calls(self):
        assert get_config_path() == get_config_path()


# -- TestConfigureFromCredentials --


class TestConfigureFromCredentials:
    def test_creates_file(self, mocker, tmp_path):
        dest = tmp_path / "client_secrets.json"
        mocker.patch("tokentoss.setup.get_config_path", return_value=dest)

        result = configure_from_credentials("my-client-id", "my-secret")

        assert result == dest
        assert dest.exists()

    def test_correct_structure(self, mocker, tmp_path):
        dest = tmp_path / "client_secrets.json"
        mocker.patch("tokentoss.setup.get_config_path", return_value=dest)

        configure_from_credentials("my-client-id", "my-secret")

        data = json.loads(dest.read_text())
        assert "installed" in data
        installed = data["installed"]
        assert installed["client_id"] == "my-client-id"
        assert installed["client_secret"] == "my-secret"
        assert installed["auth_uri"] == GOOGLE_AUTH_URI
        assert installed["token_uri"] == GOOGLE_TOKEN_URI
        assert installed["auth_provider_x509_cert_url"] == GOOGLE_CERT_URL
        assert installed["redirect_uris"] == DEFAULT_REDIRECT_URIS

    def test_with_project_id(self, mocker, tmp_path):
        dest = tmp_path / "client_secrets.json"
        mocker.patch("tokentoss.setup.get_config_path", return_value=dest)

        configure_from_credentials("id", "secret", project_id="my-project")

        data = json.loads(dest.read_text())
        assert data["installed"]["project_id"] == "my-project"

    def test_without_project_id(self, mocker, tmp_path):
        dest = tmp_path / "client_secrets.json"
        mocker.patch("tokentoss.setup.get_config_path", return_value=dest)

        configure_from_credentials("id", "secret")

        data = json.loads(dest.read_text())
        assert "project_id" not in data["installed"]

    def test_secure_permissions(self, mocker, tmp_path):
        dest = tmp_path / "client_secrets.json"
        mocker.patch("tokentoss.setup.get_config_path", return_value=dest)

        configure_from_credentials("id", "secret")

        mode = dest.stat().st_mode & 0o777
        assert mode == 0o600

    def test_strips_whitespace(self, mocker, tmp_path):
        dest = tmp_path / "client_secrets.json"
        mocker.patch("tokentoss.setup.get_config_path", return_value=dest)

        configure_from_credentials("  my-id  ", "  my-secret  ")

        data = json.loads(dest.read_text())
        assert data["installed"]["client_id"] == "my-id"
        assert data["installed"]["client_secret"] == "my-secret"

    def test_empty_client_id_raises(self):
        with pytest.raises(ValueError, match="client_id cannot be empty"):
            configure_from_credentials("", "secret")

    def test_whitespace_only_client_id_raises(self):
        with pytest.raises(ValueError, match="client_id cannot be empty"):
            configure_from_credentials("   ", "secret")

    def test_empty_client_secret_raises(self):
        with pytest.raises(ValueError, match="client_secret cannot be empty"):
            configure_from_credentials("id", "")

    def test_creates_parent_directory(self, mocker, tmp_path):
        dest = tmp_path / "nested" / "dir" / "client_secrets.json"
        mocker.patch("tokentoss.setup.get_config_path", return_value=dest)

        configure_from_credentials("id", "secret")

        assert dest.exists()


# -- TestConfigureFromFile --


class TestConfigureFromFile:
    def test_copies_valid_file(self, mocker, tmp_path):
        source = _make_client_secrets_file(tmp_path)
        dest = tmp_path / "installed" / "client_secrets.json"
        mocker.patch("tokentoss.setup.get_config_path", return_value=dest)

        result = configure_from_file(source)

        assert result == dest
        assert dest.exists()
        source_data = json.loads(source.read_text())
        dest_data = json.loads(dest.read_text())
        assert source_data == dest_data

    def test_sets_secure_permissions(self, mocker, tmp_path):
        source = _make_client_secrets_file(tmp_path)
        dest = tmp_path / "installed" / "client_secrets.json"
        mocker.patch("tokentoss.setup.get_config_path", return_value=dest)

        configure_from_file(source)

        mode = dest.stat().st_mode & 0o777
        assert mode == 0o600

    def test_missing_source_raises(self):
        with pytest.raises(FileNotFoundError, match="not found"):
            configure_from_file("/nonexistent/client_secrets.json")

    def test_invalid_json_raises(self, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not json {{{")
        with pytest.raises(ValueError, match="Invalid JSON"):
            configure_from_file(bad_file)

    def test_missing_installed_key_raises(self, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps({"other": {}}))
        with pytest.raises(ValueError, match="Expected 'installed' or 'web' key"):
            configure_from_file(bad_file)

    def test_missing_client_id_raises(self, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps({"installed": {"client_secret": "s"}}))
        with pytest.raises(ValueError, match="Missing client_id"):
            configure_from_file(bad_file)

    def test_web_format_accepted(self, mocker, tmp_path):
        source = tmp_path / "web_secrets.json"
        source.write_text(
            json.dumps(
                {
                    "web": {
                        "client_id": "web-id",
                        "client_secret": "web-secret",
                    }
                }
            )
        )
        dest = tmp_path / "installed" / "client_secrets.json"
        mocker.patch("tokentoss.setup.get_config_path", return_value=dest)

        configure_from_file(source)

        data = json.loads(dest.read_text())
        assert data["web"]["client_id"] == "web-id"


# -- TestConfigure (master function) --


class TestConfigure:
    def test_routes_to_credentials(self, mocker, tmp_path):
        dest = tmp_path / "client_secrets.json"
        mocker.patch("tokentoss.setup.get_config_path", return_value=dest)

        result = configure(client_id="id", client_secret="secret")
        assert result == dest

    def test_routes_to_file(self, mocker, tmp_path):
        source = _make_client_secrets_file(tmp_path)
        dest = tmp_path / "installed" / "client_secrets.json"
        mocker.patch("tokentoss.setup.get_config_path", return_value=dest)

        result = configure(path=source)
        assert result == dest

    def test_path_takes_precedence(self, mocker, tmp_path):
        """If both path and credentials provided, path wins."""
        source = _make_client_secrets_file(tmp_path)
        dest = tmp_path / "installed" / "client_secrets.json"
        mocker.patch("tokentoss.setup.get_config_path", return_value=dest)

        configure(client_id="id", client_secret="secret", path=source)
        # Should use file path, not credentials
        data = json.loads(dest.read_text())
        assert data["installed"]["client_id"] == "test-id.apps.googleusercontent.com"

    def test_no_args_raises(self):
        with pytest.raises(ValueError, match="Provide either"):
            configure()

    def test_only_client_id_raises(self):
        with pytest.raises(ValueError, match="Provide either"):
            configure(client_id="id")

    def test_only_client_secret_raises(self):
        with pytest.raises(ValueError, match="Provide either"):
            configure(client_secret="secret")
