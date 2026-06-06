from collections.abc import Generator
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.seed.initial_data import seed_database
from app.tests.test_foundation import generate_build_request, seed_test_brand_master


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    with TestingSessionLocal() as db:
        seed_database(db)
        seed_test_brand_master(db)

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_compatibility_api_scores_matching_and_mismatching_parts(client: TestClient) -> None:
    products = product_map(client)

    matching = client.post(
        "/api/compatibility/evaluate",
        json={
            "product_ids": [
                products["AMD Ryzen 5 5600"]["id"],
                products["AMD B550 Motherboard"]["id"],
                products["16GB DDR4 RAM"]["id"],
                products["750W 80+ Gold PSU"]["id"],
                products["NVIDIA GeForce RTX 4060 8GB"]["id"],
            ]
        },
    )
    assert matching.status_code == 200
    matching_payload = matching.json()
    assert matching_payload["compatibility_score"] >= 75
    assert not any(item["code"] == "CPU_BOARD_SOCKET_MISMATCH" for item in matching_payload["blocking_issues"])

    mismatch = client.post(
        "/api/compatibility/evaluate",
        json={
            "product_ids": [
                products["AMD Ryzen 5 5600"]["id"],
                products["Intel B660 Motherboard"]["id"],
                products["32GB DDR5 RAM"]["id"],
            ]
        },
    )
    assert mismatch.status_code == 200
    mismatch_payload = mismatch.json()
    assert mismatch_payload["compatibility_score"] < 70
    assert any(item["code"] == "CPU_BOARD_SOCKET_MISMATCH" for item in mismatch_payload["blocking_issues"])


def test_compatibility_api_handles_memory_power_thermal_and_bottleneck_rules(client: TestClient) -> None:
    products = product_map(client)

    ram_mismatch = client.post(
        "/api/compatibility/evaluate",
        json={
            "product_ids": [
                products["AMD Ryzen 5 5600"]["id"],
                products["AMD B550 Motherboard"]["id"],
                products["32GB DDR5 RAM"]["id"],
            ]
        },
    )
    assert ram_mismatch.status_code == 200
    ram_payload = ram_mismatch.json()
    assert any(item["code"] == "RAM_BOARD_MEMORY_MISMATCH" for item in ram_payload["blocking_issues"])

    weak_psu = client.post(
        "/api/compatibility/evaluate",
        json={
            "product_ids": [
                products["Intel Core i5-14400"]["id"],
                products["Intel B660 Motherboard"]["id"],
                products["32GB DDR5 RAM"]["id"],
                products["NVIDIA GeForce RTX 3070 8GB"]["id"],
                products["NVIDIA GeForce RTX 3070 8GB"]["id"],
                products["NVIDIA GeForce RTX 3070 8GB"]["id"],
                products["650W 80+ Bronze PSU"]["id"],
            ]
        },
    )
    assert weak_psu.status_code == 200
    weak_payload = weak_psu.json()
    assert weak_payload["power_headroom_score"] < 60
    assert weak_payload["thermal_score"] < 80
    assert any(item["code"] in {"PSU_INSUFFICIENT", "PSU_HEADROOM_LOW"} for item in weak_payload["warnings"])
    assert any(item["code"] in {"COOLING_MISSING", "THERMAL_INSUFFICIENT"} for item in weak_payload["warnings"])

    balanced = client.post(
        "/api/compatibility/evaluate",
        json={
            "product_ids": [
                products["AMD Ryzen 5 5600"]["id"],
                products["NVIDIA GeForce RTX 4060 8GB"]["id"],
            ]
        },
    )
    assert balanced.status_code == 200
    balanced_payload = balanced.json()
    assert balanced_payload["bottleneck_score"] >= 90


def test_used_inventory_increases_warranty_risk_without_exposing_hidden_condition(client: TestClient) -> None:
    save = create_save(client)
    save_id = save["id"]
    products = product_map(client)

    inventory_response = client.post(
        f"/api/save-games/{save_id}/inventory",
        json={
            "product_id": products["AMD Ryzen 5 5600"]["id"],
            "condition_type": "USED",
            "source": "USED_MARKET",
            "purchase_price_vnd": 1_500_000,
            "listed_price_vnd": 1_900_000,
        },
    )
    assert inventory_response.status_code == 200
    inventory = inventory_response.json()
    assert "hidden_condition_json" not in inventory

    response = client.post(
        "/api/compatibility/evaluate",
        json={
            "save_game_id": save_id,
            "inventory_unit_ids": [inventory["id"]],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["warranty_risk_delta"] > 0
    assert any(item["code"] == "USED_PART_RISK" for item in payload["warnings"])
    assert "hidden_condition_json" not in json.dumps(payload)


def test_quote_generation_returns_compatibility_snapshot(client: TestClient) -> None:
    save = create_save(client)
    save_id = save["id"]
    request = generate_build_request(client, save_id)

    response = client.post(f"/api/save-games/{save_id}/customer-requests/{request['id']}/generate-quote", json={})
    assert response.status_code == 200
    detail = response.json()
    quote = detail["quote"]

    assert quote["compatibility_score"] is not None
    assert quote["power_headroom_score"] is not None
    assert quote["thermal_score"] is not None
    assert quote["bottleneck_score"] is not None
    assert quote["build_quality_score_estimate"] is not None
    assert quote["compatibility_result"] is not None
    assert detail["compatibility_result"] is None or isinstance(detail["compatibility_result"], dict)

    accepted = client.post(f"/api/save-games/{save_id}/quotes/{quote['id']}/accept", json={})
    assert accepted.status_code == 200
    order = accepted.json()
    assert order["compatibility_score"] is not None
    assert order["compatibility_result"] is not None


def test_order_build_test_uses_compatibility_to_shift_results(client: TestClient) -> None:
    save = create_save(client)
    save_id = save["id"]
    request = generate_build_request(client, save_id)
    products = product_map(client)

    balanced = create_order(
        client,
        save_id,
        request["customer_id"],
        request["id"],
        [
            "AMD Ryzen 5 5600",
            "AMD B550 Motherboard",
            "16GB DDR4 RAM",
            "NVIDIA GeForce RTX 4060 8GB",
            "750W 80+ Gold PSU",
            "240mm AIO Cooler",
        ],
        products,
    )
    weak = create_order(
        client,
        save_id,
        request["customer_id"],
        request["id"],
        [
            "Intel Core i5-14400",
            "Intel B660 Motherboard",
            "32GB DDR5 RAM",
            "NVIDIA GeForce RTX 3070 8GB",
            "NVIDIA GeForce RTX 3070 8GB",
            "NVIDIA GeForce RTX 3070 8GB",
            "650W 80+ Bronze PSU",
        ],
        products,
    )

    for order in (balanced, weak):
        start = client.post(f"/api/save-games/{save_id}/orders/{order['id']}/start-build")
        assert start.status_code == 200
        tested = client.post(f"/api/save-games/{save_id}/orders/{order['id']}/run-build-test")
        assert tested.status_code == 200
        payload = tested.json()["order"]
        assert payload["compatibility_score"] is not None
        assert payload["final_test_score"] is not None
        assert payload["final_warranty_risk"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        if order["id"] == balanced["id"]:
            balanced_result = payload
        else:
            weak_result = payload

    assert balanced_result["final_test_score"] > weak_result["final_test_score"]
    assert balanced_result["build_quality_score"] >= weak_result["build_quality_score"]


def create_save(client: TestClient) -> dict:
    response = client.post("/api/save-games", json={"name": "Compatibility Save"})
    assert response.status_code == 200
    return response.json()


def product_map(client: TestClient) -> dict[str, dict]:
    response = client.get("/api/hardware-products")
    assert response.status_code == 200
    return {product["name"]: product for product in response.json()}


def create_order(
    client: TestClient,
    save_id: int,
    customer_id: int,
    request_id: int,
    product_names: list[str],
    products: dict[str, dict],
) -> dict:
    items = []
    quoted_price_vnd = 0
    cost_vnd = 0
    for name in product_names:
        product = products[name]
        unit_price_vnd = product["latest_local_retail_vnd"] or product["msrp_vnd"] or 1_000_000
        unit_cost_vnd = max(0, int(unit_price_vnd * 0.75))
        quoted_price_vnd += unit_price_vnd
        cost_vnd += unit_cost_vnd
        items.append(
            {
                "product_id": product["id"],
                "inventory_unit_id": None,
                "quantity": 1,
                "unit_price_vnd": unit_price_vnd,
                "unit_cost_vnd": unit_cost_vnd,
            }
        )

    quote_response = client.post(
        f"/api/save-games/{save_id}/quotes",
        json={
            "customer_request_id": request_id,
            "title": "Compatibility Test Quote",
            "summary": "Generated for compatibility build test.",
            "quoted_price_vnd": quoted_price_vnd,
            "estimated_cost_vnd": cost_vnd,
            "items": items,
        },
    )
    assert quote_response.status_code == 200
    quote = quote_response.json()["quote"]

    accept_response = client.post(f"/api/save-games/{save_id}/quotes/{quote['id']}/accept", json={})
    assert accept_response.status_code == 200
    return accept_response.json()
