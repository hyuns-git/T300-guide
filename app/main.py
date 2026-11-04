"""T300 서버: 푸두 클라우드 조회용 FastAPI.

지금은 조회 전용이라서 GET 엔드포인트만 있다. 로봇을 움직이는 호출은 일부러 만들지 않았다.
동작 엔드포인트는 현장 담당자 입회와 승인 절차를 정한 뒤에 추가한다.
"""

import json
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Any, Callable, Dict, Iterator

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import Base, CallLog, SessionLocal, engine
from .pudu import PuduAPI, PuduAPIError, PuduConfigError, PuduError


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="T300 server", version="0.1.0", lifespan=lifespan)


def get_db() -> Iterator[Session]:
    with SessionLocal() as db:
        yield db


@lru_cache(maxsize=1)
def _pudu() -> PuduAPI:
    return PuduAPI()


def get_pudu() -> PuduAPI:
    """푸두 클라이언트. 설정이 비어 있으면 503으로 이유를 알려 준다."""
    try:
        return _pudu()
    except PuduConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


def call_pudu(
    db: Session, command: str, params: dict, fn: Callable[[], Dict[str, Any]]
) -> Dict[str, Any]:
    """푸두 호출을 실행하고 결과와 상관없이 call_log에 한 줄 남긴다."""
    log = CallLog(command=command, params=json.dumps(params, ensure_ascii=False))
    try:
        payload = fn()
    except PuduError as exc:
        log.ok = False
        log.code = getattr(exc, "code", None)
        log.message = str(exc)
        db.add(log)
        db.commit()
        detail = {"message": str(exc), "code": log.code}
        if isinstance(exc, PuduAPIError):
            detail["status_code"] = exc.status_code
        raise HTTPException(status_code=502, detail=detail)

    log.ok = True
    log.code = payload.get("code")
    log.message = payload.get("message") or payload.get("msg")
    db.add(log)
    db.commit()
    return payload


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"ok": True}


@app.get("/stores")
def stores(db: Session = Depends(get_db), pudu: PuduAPI = Depends(get_pudu)):
    return call_pudu(db, "get_store_list", {}, pudu.get_store_list)


@app.get("/robots")
def robots(
    shop_id: str, db: Session = Depends(get_db), pudu: PuduAPI = Depends(get_pudu)
):
    return call_pudu(
        db, "get_robot_list", {"shop_id": shop_id},
        lambda: pudu.get_robot_list(shop_id=shop_id),
    )


@app.get("/maps")
def maps(shop_id: str, db: Session = Depends(get_db), pudu: PuduAPI = Depends(get_pudu)):
    return call_pudu(
        db, "store_map_list", {"shop_id": shop_id},
        lambda: pudu.store_map_list(shop_id=shop_id),
    )


@app.get("/points")
def points(sn: str, db: Session = Depends(get_db), pudu: PuduAPI = Depends(get_pudu)):
    return call_pudu(
        db, "get_current_map_points", {"sn": sn},
        lambda: pudu.get_current_map_points(sn=sn),
    )


@app.get("/position")
def position(sn: str, db: Session = Depends(get_db), pudu: PuduAPI = Depends(get_pudu)):
    return call_pudu(db, "get_position", {"sn": sn}, lambda: pudu.get_position(sn=sn))


@app.get("/call-logs")
def call_logs(limit: int = Query(50, ge=1, le=500), db: Session = Depends(get_db)):
    rows = db.scalars(select(CallLog).order_by(CallLog.id.desc()).limit(limit)).all()
    return [
        {
            "id": r.id,
            "created_at": r.created_at.isoformat(),
            "command": r.command,
            "params": json.loads(r.params),
            "ok": r.ok,
            "code": r.code,
            "message": r.message,
        }
        for r in rows
    ]
