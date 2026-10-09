from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy.dialects import mysql

from app.models.types import UTCDateTime

DIALECT = mysql.dialect()
KST = timezone(timedelta(hours=9))


def test_bind_converts_to_naive_utc() -> None:
    value = datetime(2026, 1, 10, 9, 0, tzinfo=KST)
    assert UTCDateTime().process_bind_param(value, DIALECT) == datetime(2026, 1, 10, 0, 0)


def test_bind_rejects_naive_and_passes_none() -> None:
    with pytest.raises(ValueError):
        UTCDateTime().process_bind_param(datetime(2026, 1, 10), DIALECT)
    assert UTCDateTime().process_bind_param(None, DIALECT) is None


def test_result_attaches_utc() -> None:
    t = UTCDateTime()
    assert t.process_result_value(datetime(2026, 1, 10), DIALECT) == datetime(
        2026, 1, 10, tzinfo=UTC
    )
    aware = datetime(2026, 1, 10, 9, tzinfo=KST)
    assert t.process_result_value(aware, DIALECT) == datetime(2026, 1, 10, tzinfo=UTC)
    assert t.process_result_value(None, DIALECT) is None
