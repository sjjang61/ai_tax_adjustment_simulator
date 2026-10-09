from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.types import UTCDateTime


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Business(Base):
    """사업자 소득관리 (사업장 단위 수입·경비와 공동사업자 지분)."""

    __tablename__ = "businesses"
    __table_args__ = {  # noqa: RUF012 - SQLAlchemy 선언 규약상 클래스 속성 dict
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_unicode_ci",
    }

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50))
    tax_year: Mapped[int] = mapped_column(Integer, index=True)
    record: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=_utcnow, onupdate=_utcnow)
