from typing import Any

from fastapi.testclient import TestClient

from tests.factories import input_dict

API = "/api/v1/global-income"


def _body(**override: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "tax_year": 2025,
        "base": input_dict(income={"annual_earned_income": 50_000_000}),
        "business_incomes": [
            {"name": "부업", "revenue": 10_000_000, "expense_method": "rate", "expense_rate": "60"}
        ],
        "other_incomes": [{"name": "원고료", "kind": "deemed_expense", "revenue": 1_000_000}],
    }
    body.update(override)
    return body


def test_calculate(client: TestClient) -> None:
    res = client.post(f"{API}/calculate", json=_body())
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["business_income_amount"] == 4_000_000
    assert [line["kind"] for line in body["income_lines"]] == ["earned", "business", "other"]
    assert body["tax_result"]["tax_base"] > 0
    assert "종합소득세" in body["disclaimer"]


def test_calculate_validation(client: TestClient) -> None:
    res = client.post(f"{API}/calculate", json=_body(tax_year=2026))
    assert res.status_code == 422
    assert res.json()["code"] == "validation_error"


def test_crud_and_source_link(client: TestClient) -> None:
    year_end = client.post(
        "/api/v1/simulations", json={"name": "연말정산", "input": input_dict()}
    ).json()
    created = client.post(
        f"{API}/simulations",
        json={"name": "2025 종소세", "input": _body(), "source_simulation_id": year_end["id"]},
    )
    assert created.status_code == 201, created.text
    sim = created.json()
    assert sim["source_simulation_id"] == year_end["id"]
    assert sim["result"]["total_balance_due"] == sim["total_balance_due"]

    assert [s["id"] for s in client.get(f"{API}/simulations").json()] == [sim["id"]]
    assert client.get(f"{API}/simulations", params={"tax_year": 2026}).json() == []

    updated = client.put(
        f"{API}/simulations/{sim['id']}",
        json={"name": "수정", "input": _body(other_incomes=[])},
    ).json()
    assert updated["name"] == "수정"
    assert updated["result"]["other_income_taxation"] == "none"

    # 원본 연말정산 삭제 → 연결만 해제
    client.delete(f"/api/v1/simulations/{year_end['id']}")
    assert client.get(f"{API}/simulations/{sim['id']}").json()["source_simulation_id"] is None

    assert client.delete(f"{API}/simulations/{sim['id']}").status_code == 204
    assert client.get(f"{API}/simulations/{sim['id']}").status_code == 404


def test_unknown_source_is_not_linked(client: TestClient) -> None:
    sim = client.post(
        f"{API}/simulations", json={"name": "x", "input": _body(), "source_simulation_id": 999}
    ).json()
    assert sim["source_simulation_id"] is None


def test_not_found(client: TestClient) -> None:
    assert (
        client.put(f"{API}/simulations/1", json={"name": "x", "input": _body()}).status_code == 404
    )
    assert client.delete(f"{API}/simulations/1").status_code == 404
