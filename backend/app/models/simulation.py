from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.types import UTCDateTime


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Simulation(Base):
    __tablename__ = "simulations"
    # MySQL: 한글 이름·JSON 저장을 위해 utf8mb4 사용 (다른 DB에서는 무시됨)
    __table_args__ = {  # noqa: RUF012 - SQLAlchemy 선언 규약상 클래스 속성 dict
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_unicode_ci",
    }

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    tax_year: Mapped[int] = mapped_column(Integer, index=True)
    schema_version: Mapped[int] = mapped_column(Integer)
    input: Mapped[dict[str, Any]] = mapped_column(JSON)
    result_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
    source_simulation_id: Mapped[int | None] = mapped_column(
        ForeignKey("simulations.id", ondelete="SET NULL"), nullable=True
    )
    # MySQL DATETIME은 시간대를 저장하지 않으므로 UTCDateTime으로 UTC 저장·반환을 보장한다.
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=_utcnow, onupdate=_utcnow)
