"""푸두 오픈플랫폼 조회용 최소 클라이언트.

서명 규칙은 푸두 개발자 문서의 "Authentication Access"를 따른다.
GET 조회만 지원한다. 로봇을 움직이는 호출은 일부러 넣지 않았다.

사용 예 (저장소 루트에서):
    python -m app.pudu health-check
    python -m app.pudu get-robot-list --shop-id 123456789
"""

import argparse
import base64
import hashlib
import hmac
import json
import sys
from email.utils import formatdate
from typing import Any, Dict, Mapping, Optional, Union
from urllib.parse import quote, urlencode, urlparse

import requests
from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

# 응답 본문의 code가 이 값이면 성공으로 본다(code 필드가 아예 없는 응답도 성공).
SUCCESS_CODES = (None, 0, 200)


class PuduError(Exception):
    """이 모듈이 내는 모든 오류의 부모."""


class PuduConfigError(PuduError):
    """PLATFORM_URL, API_APP_KEY, API_APP_SECRET이 비어 있을 때."""


class PuduAPIError(PuduError):
    """HTTP 오류, JSON이 아닌 응답, 본문의 오류 코드."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        code: Optional[int] = None,
        response_text: Optional[str] = None,
        response_headers: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.response_text = response_text
        self.response_headers = response_headers


class Settings(BaseSettings):
    """환경변수 또는 실행 폴더의 .env 파일에서 읽는다.

    .env는 UTF-8과 UTF-8(BOM 포함) 둘 다 읽는다. 메모장이 BOM을 붙여도 괜찮다.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8-sig",
        extra="ignore",
        populate_by_name=True,
    )

    platform_url: str = Field(validation_alias="PLATFORM_URL")
    api_app_key: str = Field(validation_alias="API_APP_KEY")
    api_app_secret: str = Field(validation_alias="API_APP_SECRET")


def load_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as exc:
        raise PuduConfigError(
            "설정이 없습니다. PLATFORM_URL, API_APP_KEY, API_APP_SECRET을 "
            "환경변수나 .env 파일에 넣어 주세요."
        ) from exc


def sign_path(path: str, params: Optional[Mapping[str, Any]]) -> str:
    """서명에 쓰는 경로+쿼리 문자열.

    키는 사전순, 값이 비면 키만 적고, 같은 키의 여러 값은 사전순으로 정렬해 쉼표로 잇는다.
    쿼리가 없으면 물음표 없이 경로만 쓴다.
    """
    if not params:
        return path
    parts = []
    for key in sorted(params):
        raw = params[key]
        values = [str(v) for v in raw] if isinstance(raw, (list, tuple)) else [str(raw)]
        values = sorted(v for v in values if v != "")
        parts.append(key + "=" + ",".join(values) if values else key)
    return path + "?" + "&".join(parts)


def make_headers(
    app_key: str,
    app_secret: str,
    hostname: str,
    path_and_params: str,
    x_date: Optional[str] = None,
    accept: str = "application/json",
    content_type: str = "application/json",
) -> Dict[str, str]:
    """GET 요청용 헤더. 서명 문자열은 줄바꿈으로 이은 6개 항목이다.

    x-date 줄, 메서드, Accept, Content-Type, Content-MD5(GET은 빈 값), 경로+쿼리.
    """
    x_date = x_date or formatdate(usegmt=True)
    signing_str = "\n".join(
        ["x-date: " + x_date, "GET", accept, content_type, "", path_and_params]
    )
    digest = hmac.new(
        app_secret.encode("utf-8"), signing_str.encode("utf-8"), hashlib.sha1
    ).digest()
    signature = base64.b64encode(digest).decode("ascii")
    return {
        "Host": hostname,
        "Accept": accept,
        "Content-Type": content_type,
        "x-date": x_date,
        "Authorization": (
            'hmac id="%s", algorithm="hmac-sha1", headers="x-date", signature="%s"'
            % (app_key, signature)
        ),
    }


class PuduClient:
    def __init__(
        self,
        settings: Optional[Settings] = None,
        session: Optional[requests.Session] = None,
        timeout: float = 30.0,
    ) -> None:
        self.settings = settings or load_settings()
        self._session = session or requests.Session()
        self.timeout = timeout

    @property
    def base_url(self) -> str:
        return self.settings.platform_url.rstrip("/")

    def build_request(
        self,
        path: str,
        params: Optional[Mapping[str, Any]] = None,
        x_date: Optional[str] = None,
    ):
        """보내지 않고 (url, headers)만 만든다. 테스트와 디버깅용."""
        url = self.base_url + path
        if params:
            url += "?" + urlencode(params, doseq=True, quote_via=quote)
        parsed = urlparse(url)
        headers = make_headers(
            self.settings.api_app_key,
            self.settings.api_app_secret,
            parsed.hostname or "",
            sign_path(parsed.path, params),
            x_date=x_date,
        )
        return url, headers

    def get(self, path: str, params: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        url, headers = self.build_request(path, params)
        try:
            resp = self._session.get(url, headers=headers, timeout=self.timeout)
        except requests.RequestException as exc:
            raise PuduError("서버에 연결하지 못했습니다: %s" % exc) from exc
        return self._parse(resp)

    @staticmethod
    def _parse(resp: Any) -> Dict[str, Any]:
        headers = dict(getattr(resp, "headers", None) or {})
        if resp.status_code >= 400:
            raise PuduAPIError(
                "HTTP %s" % resp.status_code,
                status_code=resp.status_code,
                response_text=resp.text,
                response_headers=headers,
            )
        try:
            payload = resp.json()
        except ValueError as exc:
            raise PuduAPIError(
                "응답이 JSON이 아닙니다",
                status_code=resp.status_code,
                response_text=resp.text,
                response_headers=headers,
            ) from exc
        if not isinstance(payload, dict):
            return {"data": payload}
        code = payload.get("code")
        if code not in SUCCESS_CODES:
            raise PuduAPIError(
                payload.get("message") or payload.get("msg") or "API 오류 코드 %s" % code,
                status_code=resp.status_code,
                code=code,
                response_text=resp.text,
                response_headers=headers,
            )
        return payload


Id = Union[int, str]


class PuduAPI(PuduClient):
    """조회 전용 엔드포인트 모음. 전부 GET이다."""

    def health_check(self) -> Dict[str, Any]:
        return self.get("/data-open-platform-service/v1/api/healthCheck")

    def get_store_list(self) -> Dict[str, Any]:
        return self.get(
            "/data-open-platform-service/v1/api/shop", {"limit": 100, "offset": 0}
        )

    def get_robot_list(self, shop_id: Id) -> Dict[str, Any]:
        # limit은 로봇 대수보다 크게 잡는다. 20이 허용되는지 문서에서 확인하지 못했다.
        return self.get(
            "/data-open-platform-service/v1/api/robot",
            {"limit": 20, "offset": 0, "shop_id": shop_id},
        )

    def store_map_list(self, shop_id: Id) -> Dict[str, Any]:
        return self.get("/data-open-platform-service/v1/api/maps", {"shop_id": shop_id})

    def get_current_map(self, sn: str) -> Dict[str, Any]:
        return self.get(
            "/map-service/v1/open/current", {"sn": sn, "need_element": "true"}
        )

    def get_current_map_points(self, sn: str) -> Dict[str, Any]:
        return self.get(
            "/map-service/v1/open/point", {"sn": sn, "limit": 100, "offset": 0}
        )

    def get_robot_groups(self, shop_id: Id) -> Dict[str, Any]:
        return self.get(
            "/open-platform-service/v1/robot/group/list", {"shop_id": shop_id}
        )

    def get_position(self, sn: str) -> Dict[str, Any]:
        return self.get("/open-platform-service/v1/robot/get_position", {"sn": sn})


# 명령 이름 -> (메서드 이름, 필요한 인자 이름들)
COMMANDS = {
    "health-check": ("health_check", []),
    "get-store-list": ("get_store_list", []),
    "get-robot-list": ("get_robot_list", ["shop_id"]),
    "store-map-list": ("store_map_list", ["shop_id"]),
    "get-current-map": ("get_current_map", ["sn"]),
    "get-current-map-points": ("get_current_map_points", ["sn"]),
    "get-robot-groups": ("get_robot_groups", ["shop_id"]),
    "get-position": ("get_position", ["sn"]),
}


def _error_dict(exc: BaseException) -> Dict[str, Any]:
    error = {"type": type(exc).__name__, "message": str(exc)}
    if isinstance(exc, PuduAPIError):
        error.update(
            status_code=exc.status_code,
            code=exc.code,
            response_text=exc.response_text,
            response_headers=exc.response_headers,
        )
    return error


def main(argv=None) -> int:
    # 윈도우 콘솔의 기본 인코딩(cp949)에서도 JSON이 깨지지 않게 한다.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        prog="python -m app.pudu", description="푸두 오픈플랫폼 조회 (읽기 전용)"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    for name, (_, arg_names) in COMMANDS.items():
        p = sub.add_parser(name)
        for arg in arg_names:
            p.add_argument("--" + arg.replace("_", "-"), dest=arg, required=True)
    ns = parser.parse_args(argv)

    method, arg_names = COMMANDS[ns.command]
    try:
        result = getattr(PuduAPI(), method)(**{a: getattr(ns, a) for a in arg_names})
    except PuduError as exc:
        print(json.dumps({"ok": False, "error": _error_dict(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
