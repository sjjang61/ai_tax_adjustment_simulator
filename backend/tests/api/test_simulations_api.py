from typing import Any

from fastapi.testclient import TestClient

from tests.factories import input_dict

API = "/api/v1"


def _create(client: TestClient, name: str = "2025 기본", **override: Any) -> dict[str, Any]:
    res = client.post(f"{API}/simulations", json={"name": name, "input": input_dict(**override)})
    assert res.status_code == 201, res.text
    body: dict[str, Any] = res.json()
    return body


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_calculate_without_saving(client: TestClient) -> None:
    res = client.post(f"{API}/simulations/calculate", json=input_dict())
    assert res.status_code == 200
    body = res.json()
    assert body["gross_salary"] == 50_000_000
    assert body["disclaimer"].endswith("회사 정산 결과를 확인하세요.")
    assert client.get(f"{API}/simulations").json() == []


def test_calculate_validation_error_format(client: TestClient) -> None:
    res = client.post(
        f"{API}/simulations/calculate", json=input_dict(income={"annual_earned_income": -1})
    )
    assert res.status_code == 422
    body = res.json()
    assert body["code"] == "validation_error"
    assert set(body) == {"code", "message", "details"}
    assert body["details"]["errors"]


def test_unknown_field_rejected(client: TestClient) -> None:
    res = client.post(f"{API}/simulations/calculate", json=input_dict(unknown_field=1))
    assert res.status_code == 422


def test_unsupported_year(client: TestClient) -> None:
    res = client.post(f"{API}/simulations/calculate", json=input_dict(tax_year=2019))
    assert res.status_code == 400
    assert res.json()["code"] == "unsupported_tax_year"
    assert res.json()["details"]["supported_years"] == [2025, 2026]


def test_crud_flow(client: TestClient) -> None:
    created = _create(client)
    sim_id = created["id"]
    assert created["tax_year"] == 2025
    assert created["schema_version"] == 1
    assert created["created_at"].endswith(("+00:00", "Z"))  # 항상 UTC
    assert created["result"]["determined_tax"] == created["determined_tax"]

    listed = client.get(f"{API}/simulations").json()
    assert [s["id"] for s in listed] == [sim_id]
    assert client.get(f"{API}/simulations", params={"tax_year": 2026}).json() == []

    got = client.get(f"{API}/simulations/{sim_id}").json()
    assert got["input"]["income"]["annual_earned_income"] == 50_000_000

    updated = client.put(
        f"{API}/simulations/{sim_id}",
        json={"name": "수정", "input": input_dict(income={"annual_earned_income": 60_000_000})},
    ).json()
    assert updated["name"] == "수정"
    assert updated["result"]["gross_salary"] == 60_000_000
    assert updated["determined_tax"] > created["determined_tax"]

    assert client.delete(f"{API}/simulations/{sim_id}").status_code == 204
    res = client.get(f"{API}/simulations/{sim_id}")
    assert res.status_code == 404
    assert res.json()["code"] == "not_found"


def test_not_found_on_update_delete(client: TestClient) -> None:
    assert (
        client.put(f"{API}/simulations/999", json={"name": "x", "input": input_dict()}).status_code
        == 404
    )
    assert client.delete(f"{API}/simulations/999").status_code == 404


def test_carry_over(client: TestClient) -> None:
    created = _create(
        client,
        taxpayer={"is_married": True, "marriage_registered_this_year": True},
        dependents=[
            {"name": "아버지", "relation": "lineal_ascendant", "birth_year": 1956},  # 69 → 70
            {"name": "첫째", "relation": "lineal_descendant", "birth_year": 2018},  # 7 → 8
            {
                "name": "막내",
                "relation": "lineal_descendant",
                "birth_year": 2025,
                "born_or_adopted_this_year": True,
                "child_order": 2,
            },
        ],
        prepaid_tax={"withholding": 3_000_000},
    )
    res = client.post(
        f"{API}/simulations/{created['id']}/carry-over",
        params={"target_year": 2026, "salary_increase_rate": "5"},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    draft = body["simulation"]
    assert draft["tax_year"] == 2026
    assert draft["source_simulation_id"] == created["id"]
    assert draft["input"]["income"]["annual_earned_income"] == 52_500_000
    assert draft["input"]["taxpayer"]["marriage_registered_this_year"] is False
    assert draft["input"]["dependents"][2]["born_or_adopted_this_year"] is False
    codes = {w["code"] for w in body["warnings"]}
    assert {
        "carry_over_elderly",
        "carry_over_child_credit",
        "carry_over_reset_birth",
        "carry_over_reset_marriage",
        "carry_over_salary_adjusted",
        "carry_over_prepaid_tax",
        "carry_over_new_item",
    } <= codes
    # 원본은 변경되지 않는다
    original = client.get(f"{API}/simulations/{created['id']}").json()
    assert original["input"]["taxpayer"]["marriage_registered_this_year"] is True
    assert original["tax_year"] == 2025


def test_carry_over_invalid_target(client: TestClient) -> None:
    created = _create(client)
    res = client.post(f"{API}/simulations/{created['id']}/carry-over", params={"target_year": 2025})
    assert res.status_code == 400
    assert res.json()["code"] == "invalid_carry_over"
    res = client.post(f"{API}/simulations/{created['id']}/carry-over", params={"target_year": 2030})
    assert res.json()["code"] == "unsupported_tax_year"


def test_export_import_roundtrip(client: TestClient) -> None:
    created = _create(client, credits={"monthly_rent": 1_000_000})
    res = client.get(f"{API}/simulations/{created['id']}/export")
    assert res.status_code == 200
    assert "attachment" in res.headers["content-disposition"]
    doc = res.json()
    assert doc["schema_version"] == 1
    assert doc["tax_year"] == 2025

    imported = client.post(f"{API}/simulations/import", json=doc)
    assert imported.status_code == 201, imported.text
    sim = imported.json()["simulation"]
    assert sim["input"] == created["input"]
    assert sim["id"] != created["id"]

    carried = client.post(f"{API}/simulations/import", params={"target_year": 2026}, json=doc)
    assert carried.status_code == 201
    assert carried.json()["simulation"]["tax_year"] == 2026


def test_import_rejects_unknown_fields_and_versions(client: TestClient) -> None:
    doc = {"schema_version": 1, "tax_year": 2025, "name": "x", "input": input_dict()}
    assert client.post(f"{API}/simulations/import", json={**doc, "extra": 1}).status_code == 422

    bad_input = {**doc, "input": input_dict(hacked=True)}
    res = client.post(f"{API}/simulations/import", json=bad_input)
    assert res.status_code == 422
    assert res.json()["code"] == "invalid_import"

    res = client.post(f"{API}/simulations/import", json={**doc, "schema_version": 99})
    assert res.status_code == 400
    assert res.json()["code"] == "unsupported_schema_version"

    res = client.post(f"{API}/simulations/import", json={**doc, "tax_year": 2026})
    assert res.json()["code"] == "invalid_import"

    unsupported = {**doc, "tax_year": 2019, "input": input_dict(tax_year=2019)}
    assert client.post(f"{API}/simulations/import", json=unsupported).json()["code"] == (
        "unsupported_tax_year"
    )

    res = client.post(f"{API}/simulations/import", params={"target_year": 2024}, json=doc)
    assert res.json()["code"] == "invalid_carry_over"


def test_rules_endpoints(client: TestClient) -> None:
    years = client.get(f"{API}/rules").json()
    assert years == {"supported_years": [2025, 2026], "default_tax_year": 2025}
    rules = client.get(f"{API}/rules/2025").json()
    assert rules["tax_year"] == 2025
    assert rules["verified"] is True
    assert rules["card"]["credit_rate"] == "0.15"
    assert client.get(f"{API}/rules/2026").json()["verified"] is False
    res = client.get(f"{API}/rules/1999")
    assert res.status_code == 400


def test_default_year_falls_back_when_unsupported() -> None:
    from app.core.config import Settings
    from app.main import create_app

    app = create_app(Settings(app_env="test", default_tax_year=1999))
    with TestClient(app) as c:
        assert c.get(f"{API}/rules").json()["default_tax_year"] == 2026


def test_unknown_route_error_format(client: TestClient) -> None:
    res = client.get(f"{API}/nope")
    assert res.status_code == 404
    assert res.json()["code"] == "not_found"
    res = client.patch(f"{API}/simulations/1")
    assert res.json()["code"] == "http_error"
