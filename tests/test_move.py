"""움직이는 명령의 안전장치 테스트. 네트워크와 실제 로봇 없이 돈다."""

import base64
import hashlib
import hmac

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import app.move as move
from app.db import Base, CallLog
from app.pudu import Settings

BASE = "https://example.test/pudu-entry"
SN = "ABCDEFG0123456"


class FakeResponse:
    status_code = 200
    headers = {}
    text = ""

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self):
        self.posts = []
        self.gets = []

    def post(self, url, headers=None, data=None, timeout=None):
        self.posts.append((url, headers, data))
        return FakeResponse({"message": "SUCCESS", "data": {"task_id": "T1"}})

    def get(self, url, headers=None, timeout=None):
        self.gets.append(url)
        if "/map-service/v1/open/current" in url:
            return FakeResponse({"data": {"name": "3F#3#예시맵", "floor": "3F"}})
        if "/map-service/v1/open/point" in url:
            return FakeResponse(
                {"data": {"list": [
                    {"name": "lift_wait", "type": "parking"},
                    {"name": "3F-A", "type": "table"},
                ]}}
            )
        return FakeResponse({"message": "SUCCESS", "data": {"task_id": "R1"}})


@pytest.fixture
def mover():
    settings = Settings(platform_url=BASE, api_app_key="k", api_app_secret="s")
    return move.Mover(settings=settings, session=FakeSession())


@pytest.fixture(autouse=True)
def memory_db(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    monkeypatch.setattr(move, "engine", engine)
    monkeypatch.setattr(move, "SessionLocal", sessionmaker(bind=engine, expire_on_commit=False))
    return engine


def logs(engine):
    with sessionmaker(bind=engine)() as db:
        return list(db.scalars(select(CallLog)))


def never_ask(_):
    raise AssertionError("확인 질문이 나오면 안 되는 경로입니다")


def test_dry_run_sends_nothing(mover, memory_db):
    assert move.run(["call", "--sn", SN, "--point", "3F-A"], mover=mover, ask=never_ask) == 0
    assert mover._session.posts == []
    assert logs(memory_db) == []


def test_send_needs_the_confirm_word(mover, memory_db):
    code = move.run(["call", "--sn", SN, "--point", "3F-A", "--send"], mover=mover, ask=lambda _: "yes")
    assert code == 1
    assert mover._session.posts == []
    assert logs(memory_db) == []


def test_send_with_confirm_posts_the_expected_body_and_logs(mover, memory_db):
    code = move.run(["call", "--sn", SN, "--point", "3F-A", "--send"], mover=mover, ask=lambda _: "MOVE")
    assert code == 0
    (url, _headers, data), = mover._session.posts
    assert url == BASE + "/open-platform-service/v1/custom_call"
    import json
    body = json.loads(data.decode("utf-8"))
    assert body == {
        "sn": SN,
        "map_name": "3F#3#예시맵",
        "point": "3F-A",
        "point_type": "table",
        "do_not_queue": True,
    }
    (row,) = logs(memory_db)
    assert row.command == "call" and row.ok is True


def test_unknown_point_is_refused_before_anything_is_sent(mover, memory_db):
    code = move.run(["call", "--sn", SN, "--point", "5F-X", "--send"], mover=mover, ask=never_ask)
    assert code == 2
    assert mover._session.posts == []


def test_post_signature_includes_method_and_body_hash(mover):
    body = {"sn": SN}
    mover.post_json("/p", body)
    _url, headers, data = mover._session.posts[0]
    md5 = base64.b64encode(hashlib.md5(data).hexdigest().encode()).decode()
    signing = "\n".join(["x-date: " + headers["x-date"], "POST", "application/json",
                         "application/json", md5, "/pudu-entry/p"])
    expected = base64.b64encode(hmac.new(b"s", signing.encode(), hashlib.sha1).digest()).decode()
    assert 'signature="%s"' % expected in headers["Authorization"]


def test_recharge_is_dry_run_by_default(mover):
    assert move.run(["recharge", "--sn", SN], mover=mover, ask=never_ask) == 0
    assert mover._session.gets == []


def test_recharge_send_uses_v2_get(mover):
    assert move.run(["recharge", "--sn", SN, "--send"], mover=mover, ask=lambda _: "MOVE") == 0
    assert mover._session.gets[-1].endswith("/open-platform-service/v2/recharge?sn=" + SN)


def test_cancel_posts_immediately(mover):
    assert move.run(["cancel", "--sn", SN], mover=mover, ask=never_ask) == 0
    assert mover._session.posts[0][0].endswith("/custom_call/cancel")
