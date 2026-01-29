"""Tests for tokentoss.client (IAPClient)."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, PropertyMock

import pytest
import requests

from tokentoss.client import IAPClient
from tokentoss.exceptions import NoCredentialsError
from tokentoss.storage import TokenData


# -- Helpers --

def _make_token_data(**kwargs) -> TokenData:
    """Create TokenData with sensible defaults."""
    defaults = {
        "access_token": "access-123",
        "id_token": "id-token-123",
        "refresh_token": "refresh-123",
        "expiry": "2099-01-01T00:00:00+00:00",
        "scopes": ["openid"],
        "user_email": "test@example.com",
    }
    defaults.update(kwargs)
    return TokenData(**defaults)


def _make_expired_token_data(**kwargs) -> TokenData:
    """Create expired TokenData."""
    return _make_token_data(expiry="2020-01-01T00:00:00+00:00", **kwargs)


def _mock_response(status_code: int = 200, json_data: dict | None = None) -> MagicMock:
    """Create a mock requests.Response."""
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = requests.HTTPError(response=resp)
    return resp


# -- TestIAPClientInit --

class TestIAPClientInit:
    def test_base_url_trailing_slash_stripped(self):
        client = IAPClient(base_url="https://example.com/")
        assert client.base_url == "https://example.com"

    def test_base_url_none_when_not_provided(self):
        client = IAPClient()
        assert client.base_url is None

    def test_auth_manager_stored(self):
        mock_am = MagicMock()
        client = IAPClient(auth_manager=mock_am)
        assert client._auth_manager is mock_am

    def test_timeout_default(self):
        client = IAPClient()
        assert client.timeout == 30

    def test_timeout_custom(self):
        client = IAPClient(timeout=60)
        assert client.timeout == 60

    def test_session_created(self):
        client = IAPClient()
        assert isinstance(client._session, requests.Session)


# -- TestBuildUrl --

class TestBuildUrl:
    def test_absolute_url_passes_through(self):
        client = IAPClient(base_url="https://example.com")
        assert client._build_url("https://other.com/api") == "https://other.com/api"

    def test_http_url_passes_through(self):
        client = IAPClient(base_url="https://example.com")
        assert client._build_url("http://other.com/api") == "http://other.com/api"

    def test_relative_path_with_base_url(self):
        client = IAPClient(base_url="https://example.com")
        assert client._build_url("api/data") == "https://example.com/api/data"

    def test_relative_path_leading_slash_stripped(self):
        client = IAPClient(base_url="https://example.com")
        assert client._build_url("/api/data") == "https://example.com/api/data"

    def test_relative_path_without_base_url_raises(self):
        client = IAPClient()
        with pytest.raises(ValueError, match="requires a base_url"):
            client._build_url("api/data")


# -- TestGetIdToken --

class TestGetIdToken:
    def test_from_auth_manager(self):
        mock_am = MagicMock()
        mock_am.id_token = "am-id-token"
        client = IAPClient(auth_manager=mock_am)

        token = client._get_id_token()
        assert token == "am-id-token"

    def test_from_auth_manager_force_refresh(self):
        mock_am = MagicMock()
        mock_am.id_token = "refreshed-token"
        client = IAPClient(auth_manager=mock_am)

        token = client._get_id_token(force_refresh=True)
        mock_am.refresh_tokens.assert_called_once()
        assert token == "refreshed-token"

    def test_from_module_credentials(self, mocker):
        import tokentoss
        mock_creds = MagicMock()
        mock_creds.id_token = "module-id-token"
        mock_creds.expired = False
        mocker.patch.object(tokentoss, "CREDENTIALS", mock_creds)

        client = IAPClient()
        token = client._get_id_token()
        assert token == "module-id-token"

    def test_from_module_credentials_refreshes_when_expired(self, mocker):
        import tokentoss
        mock_creds = MagicMock()
        mock_creds.id_token = "refreshed-module-token"
        mock_creds.expired = True
        mocker.patch.object(tokentoss, "CREDENTIALS", mock_creds)

        client = IAPClient()
        token = client._get_id_token()
        mock_creds.refresh.assert_called_once()
        assert token == "refreshed-module-token"

    def test_from_storage(self, mocker):
        token_data = _make_token_data(id_token="stored-id-token")
        mock_storage = MagicMock()
        mock_storage.load.return_value = token_data
        mocker.patch("tokentoss.client.FileStorage", return_value=mock_storage)
        mocker.patch.object(__import__("tokentoss"), "CREDENTIALS", None)

        client = IAPClient()
        token = client._get_id_token()
        assert token == "stored-id-token"

    def test_from_storage_env_var(self, mocker):
        token_data = _make_token_data(id_token="env-id-token")
        mock_storage_cls = mocker.patch("tokentoss.client.FileStorage")
        mock_storage_cls.return_value.load.return_value = token_data
        mocker.patch.object(__import__("tokentoss"), "CREDENTIALS", None)
        mocker.patch.dict(os.environ, {"TOKENTOSS_TOKEN_FILE": "/custom/tokens.json"})

        client = IAPClient()
        client._get_id_token()
        mock_storage_cls.assert_called_with(path="/custom/tokens.json")

    def test_expired_storage_token_returns_none(self, mocker):
        token_data = _make_expired_token_data()
        mock_storage = MagicMock()
        mock_storage.load.return_value = token_data
        mocker.patch("tokentoss.client.FileStorage", return_value=mock_storage)
        mocker.patch.object(__import__("tokentoss"), "CREDENTIALS", None)

        client = IAPClient()
        with pytest.raises(NoCredentialsError):
            client._get_id_token()

    def test_no_credentials_raises(self, mocker):
        mock_storage = MagicMock()
        mock_storage.load.return_value = None
        mocker.patch("tokentoss.client.FileStorage", return_value=mock_storage)
        mocker.patch.object(__import__("tokentoss"), "CREDENTIALS", None)

        client = IAPClient()
        with pytest.raises(NoCredentialsError, match="No valid credentials"):
            client._get_id_token()

    def test_storage_error_falls_through(self, mocker):
        mock_storage = MagicMock()
        mock_storage.load.side_effect = Exception("corrupt file")
        mocker.patch("tokentoss.client.FileStorage", return_value=mock_storage)
        mocker.patch.object(__import__("tokentoss"), "CREDENTIALS", None)

        client = IAPClient()
        with pytest.raises(NoCredentialsError):
            client._get_id_token()


# -- TestRequest --

class TestRequest:
    def _make_client_with_token(self, mocker, token="test-token"):
        """Create an IAPClient with mocked token discovery."""
        mocker.patch.object(IAPClient, "_get_id_token", return_value=token)
        mock_session = MagicMock()
        client = IAPClient(base_url="https://example.com")
        client._session = mock_session
        return client, mock_session

    def test_adds_bearer_token(self, mocker):
        client, session = self._make_client_with_token(mocker, "my-token")
        session.request.return_value = _mock_response(200)

        client.get("/api")
        call_kwargs = session.request.call_args
        assert call_kwargs.kwargs["headers"]["Authorization"] == "Bearer my-token"

    def test_passes_timeout(self, mocker):
        client, session = self._make_client_with_token(mocker)
        client.timeout = 45
        session.request.return_value = _mock_response(200)

        client.get("/api")
        call_kwargs = session.request.call_args
        assert call_kwargs.kwargs["timeout"] == 45

    def test_custom_timeout_not_overridden(self, mocker):
        client, session = self._make_client_with_token(mocker)
        session.request.return_value = _mock_response(200)

        client.get("/api", timeout=99)
        call_kwargs = session.request.call_args
        assert call_kwargs.kwargs["timeout"] == 99

    def test_custom_headers_merged(self, mocker):
        client, session = self._make_client_with_token(mocker, "tk")
        session.request.return_value = _mock_response(200)

        client.get("/api", headers={"X-Custom": "value"})
        call_kwargs = session.request.call_args
        headers = call_kwargs.kwargs["headers"]
        assert headers["Authorization"] == "Bearer tk"
        assert headers["X-Custom"] == "value"

    def test_401_retries_with_refresh(self, mocker):
        """On 401, should call _get_id_token(force_refresh=True) and retry."""
        mock_get_token = mocker.patch.object(
            IAPClient, "_get_id_token", side_effect=["old-token", "new-token"]
        )
        mock_session = MagicMock()
        mock_session.request.side_effect = [
            _mock_response(401),
            _mock_response(200, {"data": "ok"}),
        ]
        client = IAPClient(base_url="https://example.com")
        client._session = mock_session

        response = client.get("/api")
        assert response.status_code == 200
        assert mock_session.request.call_count == 2
        # Second call to _get_id_token should be force_refresh=True
        assert mock_get_token.call_args_list[1].kwargs.get("force_refresh") is True or \
               mock_get_token.call_args_list[1].args == (True,)

    def test_401_refresh_fails_returns_original(self, mocker):
        """If refresh fails on 401, return the original 401 response."""
        mocker.patch.object(
            IAPClient, "_get_id_token",
            side_effect=["old-token", NoCredentialsError("no creds")],
        )
        mock_session = MagicMock()
        original_401 = _mock_response(401)
        mock_session.request.return_value = original_401
        client = IAPClient(base_url="https://example.com")
        client._session = mock_session

        response = client.get("/api")
        assert response.status_code == 401
        assert mock_session.request.call_count == 1

    def test_non_401_no_retry(self, mocker):
        client, session = self._make_client_with_token(mocker)
        session.request.return_value = _mock_response(500)

        response = client.get("/api")
        assert response.status_code == 500
        assert session.request.call_count == 1


# -- TestHTTPMethods --

class TestHTTPMethods:
    @pytest.fixture(autouse=True)
    def setup_client(self, mocker):
        mocker.patch.object(IAPClient, "_get_id_token", return_value="token")
        self.mock_session = MagicMock()
        self.mock_session.request.return_value = _mock_response(200, {"key": "val"})
        self.client = IAPClient(base_url="https://example.com")
        self.client._session = self.mock_session

    def test_get(self):
        self.client.get("/path")
        assert self.mock_session.request.call_args.args == ("GET", "https://example.com/path")

    def test_post(self):
        self.client.post("/path", json={"a": 1})
        assert self.mock_session.request.call_args.args == ("POST", "https://example.com/path")

    def test_put(self):
        self.client.put("/path")
        assert self.mock_session.request.call_args.args == ("PUT", "https://example.com/path")

    def test_delete(self):
        self.client.delete("/path")
        assert self.mock_session.request.call_args.args == ("DELETE", "https://example.com/path")

    def test_patch(self):
        self.client.patch("/path")
        assert self.mock_session.request.call_args.args == ("PATCH", "https://example.com/path")

    def test_get_json(self):
        result = self.client.get_json("/path")
        assert result == {"key": "val"}

    def test_get_json_raises_on_error(self, mocker):
        self.mock_session.request.return_value = _mock_response(500)
        with pytest.raises(requests.HTTPError):
            self.client.get_json("/path")

    def test_post_json(self):
        result = self.client.post_json("/path", json={"input": "data"})
        assert result == {"key": "val"}


# -- TestLifecycle --

class TestLifecycle:
    def test_close(self):
        client = IAPClient()
        mock_session = MagicMock()
        client._session = mock_session
        client.close()
        mock_session.close.assert_called_once()

    def test_context_manager(self):
        mock_session = MagicMock()
        with IAPClient() as client:
            client._session = mock_session
        mock_session.close.assert_called_once()
