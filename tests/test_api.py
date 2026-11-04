"""가짜 푸두 클라이언트와 메모리 SQLite로 돌리는 서버 테스트. 네트워크를 쓰지 않는다."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.db import Base
from app.pudu import PuduAPIError


class FakePudu:
    def get_store_list(self):
        return {"code": 0, "message": "ok", "data": {"list": [{"shop_id": "42"}]}}

    def get_robot_list(self, shop_id):
        return {"message": "ok", "data": {"list": [{"sn": "SN1", "shop": shop_id}]}}

    def store_map_list(self, shop_id):
        return {"message": "ok", "data": {"list": []}}

    def get_current_map_points(self, sn):
        raise PuduAPIError("map not found", status_code=200, code=1001)

    def get_position(self, sn):
        return {"message": "ok", "data": {"sn": sn, "x": 1.5, "y": 2.0}}


def _session_factory():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def client():
    Session = _session_factory()

    def get_db():
        with Session() as db:
            yield db

    main.app.dependency_overrides[main.get_db] = get_db
    main.app.dependency_overrides[main.get_pudu] = lambda: FakePudu()
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()


def test_health(client):
    assert client.get("/health").json() == {"ok": True}


def test_stores_returns_payload_and_logs_the_call(client):
    r = client.get("/stores")
    assert r.status_code == 200
    assert r.json()["data"]["list"][0]["shop_id"] == "42"

    logs = client.get("/call-logs").json()
    assert len(logs) == 1
    assert logs[0]["command"] == "get_store_list"
    assert logs[0]["ok"] is True


def test_query_params_are_passed_and_logged(client):
    r = client.get("/robots", params={"shop_id": "7"})
    assert r.json()["data"]["list"][0]["shop"] == "7"
    assert client.get("/call-logs").json()[0]["params"] == {"shop_id": "7"}


def test_position_uses_sn(client):
    assert client.get("/position", params={"sn": "SN1"}).json()["data"]["x"] == 1.5


def test_platform_error_becomes_502_and_is_logged(client):
    r = client.get("/points", params={"sn": "SN1"})
    assert r.status_code == 502
    assert r.json()["detail"]["code"] == 1001

    log = client.get("/call-logs").json()[0]
    assert log["ok"] is False
    assert log["code"] == 1001
    assert "map not found" in log["message"]


def test_logs_are_newest_first_and_limit_applies(client):
    client.get("/stores")
    client.get("/maps", params={"shop_id": "1"})
    logs = client.get("/call-logs", params={"limit": 1}).json()
    assert [entry["command"] for entry in logs] == ["store_map_list"]


def test_missing_config_returns_503(monkeypatch, tmp_path):
    """자격 증명이 없으면 이유를 담아 503을 준다(실제 .env를 읽지 않도록 빈 폴더에서 실행)."""
    monkeypatch.chdir(tmp_path)
    for var in ("PLATFORM_URL", "API_APP_KEY", "API_APP_SECRET"):
        monkeypatch.delenv(var, raising=False)
    main._pudu.cache_clear()

    Session = _session_factory()

    def get_db():
        with Session() as db:
            yield db

    main.app.dependency_overrides[main.get_db] = get_db
    try:
        r = TestClient(main.app).get("/stores")
    finally:
        main.app.dependency_overrides.clear()
    assert r.status_code == 503
    assert "PLATFORM_URL" in r.json()["detail"]


def test_no_route_can_move_the_robot():
    """GET 외의 메서드가 하나도 없어야 한다."""
    write_routes = [
        r.path
        for r in main.app.routes
        if getattr(r, "methods", None) and not r.methods <= {"GET", "HEAD"}
    ]
    assert write_routes == []
