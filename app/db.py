"""SQLite 연결과 테이블 정의 (SQLAlchemy 2.x).

DB 파일 위치는 환경변수 T300_DB_URL로 바꿀 수 있다. 기본값은 실행 위치의 t300.db.
"""

import os
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DB_URL = os.getenv("T300_DB_URL", "sqlite:///./t300.db")

# FastAPI의 동기 엔드포인트는 스레드풀에서 돌기 때문에 SQLite 스레드 검사를 끈다.
# 요청마다 세션을 따로 열어 쓰므로 세션을 스레드끼리 공유하지는 않는다.
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


class CallLog(Base):
    """푸두 클라우드로 보낸 요청 기록. 키와 시크릿은 저장하지 않는다."""

    __tablename__ = "call_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    command: Mapped[str] = mapped_column(String(64))
    params: Mapped[str] = mapped_column(Text, default="{}")
    ok: Mapped[bool] = mapped_column(Boolean, default=False)
    code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
