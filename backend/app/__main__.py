"""개발 서버 실행.

호스트·포트는 실행 인자로 지정하고, 생략하면 루트 .env의 BACKEND_HOST / BACKEND_PORT를 사용한다.

사용: uv run python -m app                    (.env 값, --reload 기본 적용)
      uv run python -m app --port 8101
      uv run python -m app -p 8101 --host 0.0.0.0 --no-reload

포트를 바꾸면 프론트엔드가 호출하는 VITE_API_BASE_URL의 포트도 같게 맞춰야 한다.
"""

import argparse

import uvicorn

from app.core.config import BACKEND_DIR, get_settings


def _port(value: str) -> int:
    try:
        port = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"포트는 숫자여야 합니다: {value}") from None
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError(f"포트는 1~65535 사이여야 합니다: {port}")
    return port


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app", description="연말정산 시뮬레이터 백엔드 개발 서버"
    )
    parser.add_argument(
        "-p", "--port", type=_port, default=None, help="포트 (기본: .env의 BACKEND_PORT)"
    )
    parser.add_argument("--host", default=None, help="호스트 (기본: .env의 BACKEND_HOST)")
    parser.add_argument("--no-reload", action="store_true", help="코드 변경 시 자동 재시작 끄기")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    settings = get_settings()
    reload = not args.no_reload
    uvicorn.run(
        "app.main:app",
        host=args.host or settings.backend_host,
        port=args.port or settings.backend_port,
        reload=reload,
        reload_dirs=[str(BACKEND_DIR / "app")] if reload else None,
    )


if __name__ == "__main__":
    main()
