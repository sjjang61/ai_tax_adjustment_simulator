"""가져오기 JSON의 schema_version 마이그레이션 체인.

``MIGRATIONS[n]``은 버전 n의 ``input`` 문서를 버전 n+1로 변환하는 순수 함수다.
입력 스키마를 하위 호환되지 않게 바꿀 때 ``CURRENT_SCHEMA_VERSION``을 올리고 변환 함수를 등록한다.
"""

from collections.abc import Callable, Mapping
from typing import Any

from app.schemas.simulation import CURRENT_SCHEMA_VERSION

Migration = Callable[[dict[str, Any]], dict[str, Any]]

# 현재 스키마는 버전 1이 최초 버전이므로 등록된 변환이 없다.
MIGRATIONS: dict[int, Migration] = {}


class SchemaVersionError(ValueError):
    def __init__(self, message: str, version: int) -> None:
        super().__init__(message)
        self.version = version


def migrate_input(
    data: dict[str, Any],
    from_version: int,
    *,
    target_version: int = CURRENT_SCHEMA_VERSION,
    migrations: Mapping[int, Migration] = MIGRATIONS,
) -> dict[str, Any]:
    if from_version > target_version:
        raise SchemaVersionError(
            f"지원하지 않는 최신 스키마 버전입니다: {from_version} (지원: {target_version} 이하)",
            from_version,
        )
    version = from_version
    current = dict(data)
    while version < target_version:
        step = migrations.get(version)
        if step is None:
            raise SchemaVersionError(
                f"스키마 버전 {version} → {version + 1} 변환 함수가 없습니다.", version
            )
        current = step(current)
        version += 1
    return current
