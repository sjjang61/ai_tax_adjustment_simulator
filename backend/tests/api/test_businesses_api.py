from typing import Any

from fastapi.testclient import TestClient

from tests.factories import input_dict

API = "/api/v1/businesses"


def _record(partners: list[dict[str, Any]], **override: Any) -> dict[str, Any]:
    record: dict[str, Any] = {
        "name": "공동 스튜디오",
        "tax_year": 2025,
        "revenue": 100_000_000,
        "expense_method": "book",
        "expenses": 40_000_000,
        "partners": partners,
    }
    record.update(override)
    return record


def _year_end(client: TestClient, name: str, salary: int, **extra: Any) -> dict[str, Any]:
    res = client.post(
        "/api/v1/simulations",
        json={"name": name, "input": input_dict(income={"annual_earned_income": salary}, **extra)},
    )
    body: dict[str, Any] = res.json()
    return body


def test_allocate(client: TestClient) -> None:
    res = client.post(
        f"{API}/allocate",
        json=_record([{"name": "A", "share": 6}, {"name": "B", "share": 4}]),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["income_amount"] == 60_000_000
    assert [p["income_amount"] for p in body["partners"]] == [36_000_000, 24_000_000]
    assert body["withholding_tax"] == 3_000_000


def test_crud(client: TestClient) -> None:
    created = client.post(f"{API}", json={"record": _record([{"name": "단독", "share": 1}])})
    assert created.status_code == 201, created.text
    b = created.json()
    assert b["partner_count"] == 1 and b["income_amount"] == 60_000_000
    assert b["allocation"]["partners"][0]["ratio"] == "100%"
    assert [x["id"] for x in client.get(API).json()] == [b["id"]]
    assert client.get(API, params={"tax_year": 2026}).json() == []

    updated = client.put(
        f"{API}/{b['id']}",
        json={
            "record": _record(
                [{"name": "A", "share": 5}, {"name": "B", "share": 5}], name="이름 변경"
            )
        },
    ).json()
    assert updated["name"] == "이름 변경" and updated["partner_count"] == 2
    assert client.delete(f"{API}/{b['id']}").status_code == 204
    assert client.get(f"{API}/{b['id']}").status_code == 404


def test_partnership_uses_each_partners_year_end_result(client: TestClient) -> None:
    kim = _year_end(client, "김대표 연말정산", 60_000_000, prepaid_tax={"withholding": 3_000_000})
    lee = _year_end(client, "이대표 연말정산", 30_000_000)
    res = client.post(
        f"{API}/partnership",
        json=_record(
            [
                {"name": "김대표", "share": 6, "simulation_id": kim["id"]},
                {"name": "이대표", "share": 4, "simulation_id": lee["id"]},
                {"name": "박대표", "share": 0 + 2},  # 연말정산 미연결
            ]
        ),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    partners = body["partners"]
    assert [p["simulation_name"] for p in partners] == ["김대표 연말정산", "이대표 연말정산", None]
    # 각자의 근로소득
    assert partners[0]["result"]["earned_income_amount"] == kim["result"]["earned_income_amount"]
    assert partners[1]["result"]["earned_income_amount"] == lee["result"]["earned_income_amount"]
    assert partners[2]["result"]["earned_income_amount"] == 0
    assert "근로소득 없이" in partners[2]["notes"][0]
    # 지분만큼의 사업소득 (6:4:2), 합계는 사업장 소득금액
    incomes = [p["result"]["business_income_amount"] for p in partners]
    assert incomes == [30_000_000, 20_000_000, 10_000_000]
    assert sum(incomes) == body["allocation"]["income_amount"]
    # 근로소득 기납부 = 각자의 연말정산 결정세액
    assert partners[0]["result"]["prepaid"]["earned_settled"] == kim["result"]["determined_tax"]
    assert body["combined_total_balance_due"] == sum(
        p["result"]["total_balance_due"] for p in partners
    )


def test_partnership_with_deleted_link(client: TestClient) -> None:
    kim = _year_end(client, "김대표", 50_000_000)
    client.delete(f"/api/v1/simulations/{kim['id']}")
    body = client.post(
        f"{API}/partnership",
        json=_record([{"name": "김대표", "share": 1, "simulation_id": kim["id"]}]),
    ).json()
    assert "삭제" in body["partners"][0]["notes"][0]


def test_partnership_year_mismatch_note(client: TestClient) -> None:
    sim = _year_end(client, "2026 연말정산", 50_000_000, tax_year=2026)
    body = client.post(
        f"{API}/partnership",
        json=_record([{"name": "A", "share": 1, "simulation_id": sim["id"]}]),
    ).json()
    assert "2026년 귀속 연말정산 결과를 2025년" in body["partners"][0]["notes"][0]


def test_validation(client: TestClient) -> None:
    res = client.post(f"{API}/allocate", json=_record([]))
    assert res.status_code == 422
    assert (
        client.post(
            f"{API}/allocate", json=_record([{"name": "A", "share": 1}], tax_year=2019)
        ).json()["code"]
        == "unsupported_tax_year"
    )
