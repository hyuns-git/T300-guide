"""로봇을 움직이는 명령. 조회 모듈(app/pudu.py)과 일부러 분리했다.

기본은 연습 실행이다. 무엇을 보낼지 화면에 보여 주기만 하고 아무것도 보내지 않는다.
실제로 보내려면 --send를 붙이고, 이어서 나오는 질문에 MOVE라고 입력해야 한다.
보낸 명령은 t300.db의 call_log 테이블에 남는다.

사용 예 (저장소 루트에서):
    python -m app.move call --sn ABCDEFG0123456 --point 3F-A
    python -m app.move call --sn ABCDEFG0123456 --point 3F-A --send
    python -m app.move recharge --sn ABCDEFG0123456 --send
    python -m app.move cancel --sn ABCDEFG0123456
"""

import argparse
import base64
import hashlib
import json
import sys
from typing import Any, Callable, Dict, Optional
from urllib.parse import urlparse

import requests

from app.db import Base, CallLog, SessionLocal, engine
from app.pudu import PuduAPI, PuduError, _error_dict, make_headers

CONFIRM_WORD = "MOVE"


class MoveError(Exception):
    """보내기 전 점검에서 막혔을 때."""


def content_md5(body_json: str) -> str:
    """푸두 방식 Content-MD5: MD5의 16진 문자열을 다시 base64로 인코딩한다."""
    hex_digest = hashlib.md5(body_json.encode("utf-8")).hexdigest()
    return base64.b64encode(hex_digest.encode("ascii")).decode("ascii")


class Mover(PuduAPI):
    def post_json(self, path: str, body: Dict[str, Any]) -> Dict[str, Any]:
        url = self.base_url + path
        body_json = json.dumps(body, ensure_ascii=False)
        headers = make_headers(
            self.settings.api_app_key,
            self.settings.api_app_secret,
            urlparse(url).hostname or "",
            urlparse(url).path,
            method="POST",
            content_md5=content_md5(body_json),
        )
        try:
            resp = self._session.post(
                url, headers=headers, data=body_json.encode("utf-8"), timeout=self.timeout
            )
        except requests.RequestException as exc:
            raise PuduError("서버에 연결하지 못했습니다: %s" % exc) from exc
        return self._parse(resp)

    # --- 점검 -------------------------------------------------------------

    def plan_call(self, sn: str, point: str) -> Dict[str, Any]:
        """같은 맵 안의 지점으로 보내는 요청을 만든다. 조회만 하고 아무것도 보내지 않는다.

        맵 이름과 지점 종류는 로봇이 지금 올라가 있는 맵에서 읽어 온다.
        그래서 다른 층 지점이나 없는 지점 이름은 여기서 막힌다.
        """
        current = self.get_current_map(sn).get("data") or {}
        map_name = current.get("name")
        if not map_name:
            raise MoveError("로봇의 현재 맵 이름을 읽지 못했습니다.")
        points = (self.get_current_map_points(sn).get("data") or {}).get("list") or []
        by_name = {p.get("name"): p for p in points}
        if point not in by_name:
            raise MoveError(
                "현재 맵(%s)에 '%s' 지점이 없습니다. 있는 지점: %s"
                % (map_name, point, ", ".join(sorted(str(n) for n in by_name)) or "없음")
            )
        return {
            "path": "/open-platform-service/v1/custom_call",
            "body": {
                "sn": sn,
                "map_name": map_name,
                "point": point,
                "point_type": by_name[point].get("type"),
                # 바로 못 가면 큐에 쌓아 두지 말고 실패시킨다. 나중에 갑자기 움직이는 것을 막는다.
                "do_not_queue": True,
            },
        }


# --- 기록과 확인 ---------------------------------------------------------


def log_call(command: str, params: Dict[str, Any], ok: bool, code=None, message=None) -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        db.add(
            CallLog(
                command=command,
                params=json.dumps(params, ensure_ascii=False),
                ok=ok,
                code=code if isinstance(code, int) else None,
                message=str(message) if message is not None else None,
            )
        )
        db.commit()


def _print(obj: Any) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def confirm(ask: Callable[[str], str]) -> bool:
    answer = ask("로봇이 실제로 움직입니다. 계속하려면 %s 라고 입력하세요: " % CONFIRM_WORD)
    return answer.strip() == CONFIRM_WORD


def run(argv=None, mover: Optional[Mover] = None, ask: Callable[[str], str] = input) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        prog="python -m app.move", description="로봇을 움직이는 명령 (기본은 연습 실행)"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p_call = sub.add_parser("call", help="현재 맵의 지점으로 보낸다")
    p_call.add_argument("--sn", required=True)
    p_call.add_argument("--point", required=True)
    p_call.add_argument("--send", action="store_true", help="실제로 보낸다")
    p_rech = sub.add_parser("recharge", help="충전기로 복귀시킨다")
    p_rech.add_argument("--sn", required=True)
    p_rech.add_argument("--send", action="store_true", help="실제로 보낸다")
    p_cancel = sub.add_parser("cancel", help="이 키로 보낸 호출 작업을 취소한다 (바로 보낸다)")
    p_cancel.add_argument("--sn", required=True)
    ns = parser.parse_args(argv)

    attempt = None  # 실제로 보내는 단계에 들어가면 (명령, 내용)이 들어간다. 실패도 기록하려는 것.
    try:
        mover = mover or Mover()
        if ns.command == "cancel":
            body = {"sn": ns.sn}
            attempt = ("cancel", body)
            result = mover.post_json("/open-platform-service/v1/custom_call/cancel", body)
            log_call("cancel", body, True, message=result.get("message"))
            _print(result)
            return 0

        if ns.command == "call":
            plan = mover.plan_call(ns.sn, ns.point)
            request = {"method": "POST", **plan}
        else:
            request = {
                "method": "GET",
                "path": "/open-platform-service/v2/recharge",
                "query": {"sn": ns.sn},
            }

        if not ns.send:
            _print({"연습 실행": "아무것도 보내지 않았습니다. 보낼 내용은 아래와 같습니다.", "request": request})
            print("실제로 보내려면 같은 명령 끝에 --send를 붙이세요.")
            return 0

        if not confirm(ask):
            print("취소했습니다. 아무것도 보내지 않았습니다.")
            return 1

        params = request["body"] if ns.command == "call" else request["query"]
        attempt = (ns.command, params)
        if ns.command == "call":
            result = mover.post_json(request["path"], request["body"])
        else:
            result = mover.get(request["path"], request["query"])
        log_call(ns.command, params, True, message=result.get("message"))
        _print(result)
        return 0
    except MoveError as exc:
        _print({"ok": False, "막힘": str(exc)})
        return 2
    except PuduError as exc:
        if attempt:
            log_call(attempt[0], attempt[1], False, code=getattr(exc, "code", None), message=exc)
        _print({"ok": False, "error": _error_dict(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
