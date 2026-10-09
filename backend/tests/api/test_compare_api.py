from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import update

from app.models.simulation import Simulation
from tests.factories import input_dict

API = "/api/v1/simulations"


def _create(client: TestClient, **override: Any) -> dict[str, Any]:
    res = client.post(API, json={"name": "기준", "input": input_dict(**override)})
    assert res.status_code == 201, res.text
    body: dict[str, Any] = res.json()
    return body


def test_compare_with_changed_input(client: TestClient) -> None:
    base = _create(client, income={"annual_earned_income": 60_000_000})
    changed = input_dict(income={"annual_earned_income": 60_000_000}, credits={"irp": 3_000_000})
    res = client.post(f"{API}/{base['id']}/compare", json=changed)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["base"]["id"] == base["id"]
    assert body["snapshot_differs"] is False
    cmp = body["comparison"]
    assert cmp["saving"] == 396_000
    assert cmp["input_diffs"] == [{"path": "credits.irp", "before": 0, "after": 3_000_000}]
    # 저장하지 않는다
    assert client.get(f"{API}/{base['id']}").json()["input"]["credits"]["irp"] == 0
    assert len(client.get(API).json()) == 1


def test_compare_two_saved_simulations(client: TestClient) -> None:
    a = _create(client)
    b = _create(client, tax_year=2026)
    res = client.post(f"{API}/{a['id']}/compare", json=b["input"])
    assert res.json()["comparison"]["tax_year_changed"] is True


def test_snapshot_differs_when_stored_result_is_stale(client: TestClient) -> None:
    base = _create(client)
    factory = client.app.state.session_factory  # type: ignore[attr-defined]
    with factory() as session:
        sim = session.get(Simulation, base["id"])
        snapshot = {
            **sim.result_snapshot,
            "determined_tax": sim.result_snapshot["determined_tax"] + 1,
        }
        session.execute(
            update(Simulation).where(Simulation.id == base["id"]).values(result_snapshot=snapshot)
        )
        session.commit()
    res = client.post(f"{API}/{base['id']}/compare", json=base["input"])
    assert res.json()["snapshot_differs"] is True


def test_compare_not_found_and_validation(client: TestClient) -> None:
    assert client.post(f"{API}/999/compare", json=input_dict()).status_code == 404
    base = _create(client)
    res = client.post(f"{API}/{base['id']}/compare", json=input_dict(unknown=1))
    assert res.status_code == 422
