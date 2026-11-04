"""서명과 응답 처리 테스트. 네트워크와 실제 키 없이 돈다."""

import base64
import hashlib
import hmac

import pytest
import requests

from app.pudu import (
    PuduAPI,
    PuduAPIError,
    PuduConfigError,
    PuduError,
    Settings,
    load_settings,
    sign_path,
)

BASE = "https://example.test/pudu-entry"


@pytest.fixture
def settings():
    return Settings(
        platform_url=BASE, api_app_key="test-key", api_app_secret="test-secret"
    )


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text="", headers=None):
        self.status_code = status_code
        self._payload = payload
        self.text = text
        self.headers = headers or {}

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


class FakeSession:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def get(self, url, headers=None, timeout=None):
        self.calls.append((url, headers))
        if self.error:
            raise self.error
        return self.response


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        (None, "/p"),
        ({}, "/p"),
        ({"offset": 0, "limit": 100}, "/p?limit=100&offset=0"),
        ({"a": ""}, "/p?a"),
        ({"d": ["d2", "d1", "d3"]}, "/p?d=d1,d2,d3"),
    ],
)
def test_sign_path(params, expected):
    assert sign_path("/p", params) == expected


def test_signature_matches_the_documented_recipe(settings):
    api = PuduAPI(settings)
    x_date = "Thu, 05 Nov 2026 00:00:00 GMT"
    url, headers = api.build_request(
        "/data-open-platform-service/v1/api/shop", {"offset": 0, "limit": 100}, x_date=x_date
    )

    assert url == BASE + "/data-open-platform-service/v1/api/shop?offset=0&limit=100"
    signing_str = "\n".join(
        [
            "x-date: " + x_date,
            "GET",
            "application/json",
            "application/json",
            "",
            "/pudu-entry/data-open-platform-service/v1/api/shop?limit=100&offset=0",
        ]
    )
    expected = base64.b64encode(
        hmac.new(b"test-secret", signing_str.encode(), hashlib.sha1).digest()
    ).decode()
    assert headers["Authorization"] == (
        'hmac id="test-key", algorithm="hmac-sha1", headers="x-date", signature="%s"' % expected
    )
    assert headers["x-date"] == x_date


def test_get_returns_the_json_body(settings):
    session = FakeSession(FakeResponse(payload={"message": "success", "data": {"list": []}}))
    result = PuduAPI(settings, session=session).get_store_list()
    assert result["data"] == {"list": []}
    assert session.calls[0][0].startswith(BASE + "/data-open-platform-service/v1/api/shop?")


def test_http_error_keeps_status_text_and_headers(settings):
    resp = FakeResponse(401, text="denied", headers={"X-Demo": "1"})
    with pytest.raises(PuduAPIError) as excinfo:
        PuduAPI(settings, session=FakeSession(resp)).health_check()
    assert excinfo.value.status_code == 401
    assert excinfo.value.response_text == "denied"
    assert excinfo.value.response_headers == {"X-Demo": "1"}


def test_error_code_in_body_raises(settings):
    resp = FakeResponse(payload={"code": 1001, "msg": "nope"})
    with pytest.raises(PuduAPIError) as excinfo:
        PuduAPI(settings, session=FakeSession(resp)).health_check()
    assert excinfo.value.code == 1001
    assert "nope" in str(excinfo.value)


def test_code_zero_and_200_are_success(settings):
    for code in (0, 200):
        resp = FakeResponse(payload={"code": code, "data": 1})
        assert PuduAPI(settings, session=FakeSession(resp)).health_check()["data"] == 1


def test_non_json_body_raises(settings):
    with pytest.raises(PuduAPIError):
        PuduAPI(settings, session=FakeSession(FakeResponse(text="<html>"))).health_check()


def test_connection_failure_becomes_pudu_error(settings):
    session = FakeSession(error=requests.ConnectionError("boom"))
    with pytest.raises(PuduError) as excinfo:
        PuduAPI(settings, session=session).health_check()
    assert "연결" in str(excinfo.value)


def test_missing_config_lists_the_names(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    for var in ("PLATFORM_URL", "API_APP_KEY", "API_APP_SECRET"):
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(PuduConfigError) as excinfo:
        load_settings()
    assert "PLATFORM_URL" in str(excinfo.value)


def test_env_file_with_bom_is_read(monkeypatch, tmp_path):
    """윈도우 메모장이 BOM을 붙여 저장해도 첫 줄이 읽혀야 한다."""
    for var in ("PLATFORM_URL", "API_APP_KEY", "API_APP_SECRET"):
        monkeypatch.delenv(var, raising=False)
    env = tmp_path / ".env"
    env.write_bytes(
        b"\xef\xbb\xbfPLATFORM_URL=https://example.test/pudu-entry\r\n"
        b"API_APP_KEY=k\r\nAPI_APP_SECRET=s\r\n"
    )
    loaded = Settings(_env_file=str(env))
    assert loaded.platform_url == "https://example.test/pudu-entry"
    assert (loaded.api_app_key, loaded.api_app_secret) == ("k", "s")
