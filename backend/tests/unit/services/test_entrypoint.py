from typing import Any

import pytest

import app.__main__ as entry
from app.core.config import Settings


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    recorded: list[dict[str, Any]] = []
    monkeypatch.setattr(
        entry,
        "get_settings",
        lambda: Settings(_env_file=None, backend_host="127.0.0.1", backend_port=8123),  # type: ignore[call-arg]
    )
    monkeypatch.setattr(entry.uvicorn, "run", lambda app, **kw: recorded.append({"app": app, **kw}))
    return recorded


def test_defaults_come_from_env(calls: list[dict[str, Any]]) -> None:
    entry.main([])
    assert calls[0]["app"] == "app.main:app"
    assert (calls[0]["host"], calls[0]["port"], calls[0]["reload"]) == ("127.0.0.1", 8123, True)


def test_cli_port_and_host_override_env(calls: list[dict[str, Any]]) -> None:
    entry.main(["--port", "8001", "--host", "0.0.0.0"])
    assert (calls[0]["host"], calls[0]["port"]) == ("0.0.0.0", 8001)
    entry.main(["-p", "8002"])
    assert (calls[1]["host"], calls[1]["port"]) == ("127.0.0.1", 8002)


def test_no_reload(calls: list[dict[str, Any]]) -> None:
    entry.main(["--no-reload"])
    assert calls[0]["reload"] is False
    assert calls[0]["reload_dirs"] is None


@pytest.mark.parametrize("bad", [["--port", "0"], ["--port", "70000"], ["--port", "abc"]])
def test_invalid_port_rejected(calls: list[dict[str, Any]], bad: list[str]) -> None:
    with pytest.raises(SystemExit):
        entry.main(bad)
    assert calls == []
