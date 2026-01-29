"""Tests for tokentoss.configure_widget (ConfigureWidget)."""

from __future__ import annotations

from pathlib import Path

from tokentoss.configure_widget import ConfigureWidget


class TestConfigureWidgetInit:
    def test_default_traitlets(self):
        widget = ConfigureWidget()
        assert widget.client_id == ""
        assert widget.client_secret == ""
        assert widget.status == "Enter credentials"
        assert widget.configured is False
        assert widget._submit == 0

    def test_has_esm_and_css(self):
        widget = ConfigureWidget()
        assert widget._esm
        assert widget._css


class TestConfigureWidgetSubmit:
    def test_successful_configure(self, mocker, tmp_path):
        dest = tmp_path / "client_secrets.json"
        mocker.patch(
            "tokentoss.configure_widget.configure",
            return_value=dest,
        )

        widget = ConfigureWidget()
        widget.client_id = "test-id.apps.googleusercontent.com"
        widget.client_secret = "GOCSPX-test-secret"
        widget._submit = 1

        assert widget.configured is True
        assert str(dest) in widget.status
        assert "Configured" in widget.status

    def test_configure_error(self, mocker):
        mocker.patch(
            "tokentoss.configure_widget.configure",
            side_effect=ValueError("client_id cannot be empty"),
        )

        widget = ConfigureWidget()
        widget.client_id = "some-id"
        widget.client_secret = "some-secret"
        widget._submit = 1

        assert widget.configured is False
        assert widget.status.startswith("Error:")
        assert "client_id cannot be empty" in widget.status

    def test_empty_client_id_rejected(self):
        widget = ConfigureWidget()
        widget.client_id = ""
        widget.client_secret = "some-secret"
        widget._submit = 1

        assert widget.configured is False
        assert "required" in widget.status

    def test_empty_client_secret_rejected(self):
        widget = ConfigureWidget()
        widget.client_id = "some-id"
        widget.client_secret = ""
        widget._submit = 1

        assert widget.configured is False
        assert "required" in widget.status

    def test_whitespace_only_rejected(self):
        widget = ConfigureWidget()
        widget.client_id = "   "
        widget.client_secret = "   "
        widget._submit = 1

        assert widget.configured is False
        assert "required" in widget.status

    def test_configured_resets_on_error(self, mocker):
        dest = Path("/fake/path")
        mocker.patch(
            "tokentoss.configure_widget.configure",
            return_value=dest,
        )

        widget = ConfigureWidget()
        widget.client_id = "id"
        widget.client_secret = "secret"
        widget._submit = 1
        assert widget.configured is True

        # Now trigger an error
        mocker.patch(
            "tokentoss.configure_widget.configure",
            side_effect=OSError("disk full"),
        )
        widget._submit = 2
        assert widget.configured is False
        assert "disk full" in widget.status

    def test_submit_zero_ignored(self):
        """Setting _submit to 0 should not trigger configure."""
        widget = ConfigureWidget()
        widget.client_id = ""
        widget.client_secret = ""
        widget._submit = 0

        assert widget.status == "Enter credentials"
        assert widget.configured is False


class TestConfigureWidgetImport:
    def test_lazy_import_from_package(self):
        import tokentoss

        assert tokentoss.ConfigureWidget is ConfigureWidget
