"""OpenAPI 스키마를 파일로 내보낸다 (프론트엔드 타입 생성용).

사용: uv run python -m app.scripts.export_openapi [출력경로]
기본 출력: backend/openapi.json
"""

import json
import sys
from pathlib import Path

from app.core.config import BACKEND_DIR, Settings
from app.main import create_app


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else BACKEND_DIR / "openapi.json"
    schema = create_app(Settings(app_env="test")).openapi()
    out.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
