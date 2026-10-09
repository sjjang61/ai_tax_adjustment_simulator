"""DB 공통 컬럼 타입."""

from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator[datetime]):
    """항상 UTC로 저장·반환하는 datetime 컬럼.

    MySQL DATETIME은 시간대 정보를 저장하지 않으므로, 저장 시 UTC로 변환한 naive 값을 쓰고
    읽을 때 UTC 시간대를 붙여 API 응답이 항상 ``+00:00``을 포함하도록 한다.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("UTCDateTime에는 시간대가 있는 datetime만 저장할 수 있습니다.")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
