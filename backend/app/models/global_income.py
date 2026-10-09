from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.types import UTCDateTime


def _utcnow() -> datetime:
    return datetime.now(UTC)


class GlobalIncomeSimulation(Base):
    """종합소득세 시뮬레이션 (연말정산 시뮬레이션과 별도 테이블)."""

    __tablename__ = "global_income_simulations"
    __table_args__ = {  # noqa: RUF012 - SQLAlchemy 선언 규약상 클래스 속성 dict
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_unicode_ci",
    }

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    tax_year: Mapped[int] = mapped_column(Integer, index=True)
    input: Mapped[dict[str, Any]] = mapped_column(JSON)
    result_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
    # 불러온 연말정산 시뮬레이션 (원본 삭제 시 NULL)
    source_simulation_id: Mapped[int | None] = mapped_column(
        ForeignKey("simulations.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=_utcnow, onupdate=_utcnow)
