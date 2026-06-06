from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.seed.initial_data import seed_database
from app.tests.test_foundation import generate_build_request
from app.tests.test_profile_and_used_market import seed_test_brand_master


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


def test_persona_registry_routes_and_generated_customer_fields(client: TestClient) -> None:
    list_response = client.get("/api/customer-personas")
    assert list_response.status_code == 200
    personas = list_response.json()
    assert any(persona["persona_type"] == "BUDGET_GAMER" for persona in personas)

    detail_response = client.get("/api/customer-personas/RGB_ENTHUSIAST")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["label"] == "RGB Enthusiast"
    assert detail["sample_use_case"]

    save = create_save(client)
    generated = client.post(f"/api/save-games/{save['id']}/customers/generate-sample")
    assert generated.status_code == 200
    payload = generated.json()
    customer = payload["customer"]
    request = payload["request"]

    assert customer["persona_type"] is not None
    assert customer["preference_json"] is not None
    assert request["persona_type"] == customer["persona_type"]
    assert request["priority_tags_json"]
    assert request["accepts_used_parts"] is not None
    assert request["min_compatibility_score"] is not None
    assert request["min_build_quality_score"] is not None
    assert request["warranty_expectation_days"] is not None


def test_manual_persona_assignment_and_over_budget_quote_penalty(client: TestClient) -> None:
    save = create_save(client)
    generated = client.post(f"/api/save-games/{save['id']}/customers/generate-sample").json()
    customer_id = generated["customer"]["id"]
    request_id = generated["request"]["id"]

    assign = client.post(
        f"/api/save-games/{save['id']}/customers/{customer_id}/persona",
        json={"persona_type": "BARGAIN_HUNTER"},
    )
    assert assign.status_code == 200
    assert assign.json()["persona_type"] == "BARGAIN_HUNTER"

    products = product_map(client)
    request = generated["request"]
    detail = create_quote(
        client,
        save["id"],
        request_id,
        "Budget Breaker",
        [
            {
                "product_id": products["NVIDIA GeForce RTX 4060 8GB"]["id"],
                "inventory_unit_id": None,
                "quantity": 1,
                "unit_price_vnd": request["budget_vnd"] + 12_000_000,
                "unit_cost_vnd": request["budget_vnd"] // 2,
                "source": "CATALOG_PLACEHOLDER",
                "notes": "Intentionally pricey for the test.",
            }
        ],
        quoted_price_vnd=request["budget_vnd"] + 12_000_000,
        estimated_cost_vnd=request["budget_vnd"] // 2,
    )
    quote = detail["quote"]

    assert quote["customer_fit_score"] is not None
    assert quote["price_fit_score"] is not None
    assert quote["quote_acceptance_chance"] is not None
    assert quote["price_fit_score"] < 60
    assert quote["quote_acceptance_chance"] < 60
    assert quote["persona_warnings_json"]
    assert any(warning["code"] == "OVER_BUDGET" for warning in quote["persona_warnings_json"])

    evaluations = client.post(f"/api/save-games/{save['id']}/customer-requests/{request_id}/evaluate-quotes")
    assert evaluations.status_code == 200
    evaluation_rows = evaluations.json()
    assert any(row["quote_id"] == quote["id"] for row in evaluation_rows)


def test_used_parts_and_compatibility_influence_persona_scores(client: TestClient) -> None:
    save = create_save(client)
    generated = client.post(f"/api/save-games/{save['id']}/customers/generate-sample").json()
    customer_id = generated["customer"]["id"]
    request_id = generated["request"]["id"]

    client.post(
        f"/api/save-games/{save['id']}/customers/{customer_id}/persona",
        json={"persona_type": "WARRANTY_SENSITIVE"},
    )

    products = product_map(client)
    used_product = products["NVIDIA GeForce RTX 3060 12GB"]
    inventory_response = client.post(
        f"/api/save-games/{save['id']}/inventory",
        json={
            "product_id": used_product["id"],
            "condition_type": "USED",
            "source": "USED_MARKET",
            "purchase_price_vnd": 3_800_000,
            "listed_price_vnd": 4_500_000,
        },
    )
    assert inventory_response.status_code == 200
    inventory_unit = inventory_response.json()

    detail = create_quote(
        client,
        save["id"],
        request_id,
        "Used Risk Quote",
        [
            {
                "product_id": used_product["id"],
                "inventory_unit_id": inventory_unit["id"],
                "quantity": 1,
                "unit_price_vnd": 5_200_000,
                "unit_cost_vnd": 3_800_000,
                "source": "INVENTORY",
                "notes": "Used GPU for a warranty-sensitive customer.",
            }
        ],
        quoted_price_vnd=5_200_000,
        estimated_cost_vnd=3_800_000,
    )
    quote = detail["quote"]
    assert quote["used_part_fit_score"] is not None
    assert quote["quote_acceptance_chance"] is not None
    assert quote["used_part_fit_score"] < 55
    assert quote["quote_acceptance_chance"] < 55
    assert any(warning["code"] in {"USED_PART_RISK", "WARRANTY_RISK"} for warning in quote["persona_warnings_json"] or [])

    request = generate_build_request(client, save["id"])
    balanced_products = product_map(client)
    balanced_detail = create_quote(
        client,
        save["id"],
        request["id"],
        "Balanced Build",
        [
            {
                "product_id": balanced_products["AMD Ryzen 5 5600"]["id"],
                "inventory_unit_id": None,
                "quantity": 1,
                "unit_price_vnd": 3_100_000,
                "unit_cost_vnd": 2_200_000,
                "source": "CATALOG_PLACEHOLDER",
            },
            {
                "product_id": balanced_products["AMD B550 Motherboard"]["id"],
                "inventory_unit_id": None,
                "quantity": 1,
                "unit_price_vnd": 2_250_000,
                "unit_cost_vnd": 1_600_000,
                "source": "CATALOG_PLACEHOLDER",
            },
            {
                "product_id": balanced_products["16GB DDR4 RAM"]["id"],
                "inventory_unit_id": None,
                "quantity": 1,
                "unit_price_vnd": 950_000,
                "unit_cost_vnd": 650_000,
                "source": "CATALOG_PLACEHOLDER",
            },
            {
                "product_id": balanced_products["750W 80+ Gold PSU"]["id"],
                "inventory_unit_id": None,
                "quantity": 1,
                "unit_price_vnd": 2_450_000,
                "unit_cost_vnd": 1_800_000,
                "source": "CATALOG_PLACEHOLDER",
            },
        ],
        quoted_price_vnd=8_750_000,
        estimated_cost_vnd=6_250_000,
    )
    weak_detail = create_quote(
        client,
        save["id"],
        request["id"],
        "Mismatch Build",
        [
            {
                "product_id": balanced_products["Intel Core i5-14400"]["id"],
                "inventory_unit_id": None,
                "quantity": 1,
                "unit_price_vnd": 5_200_000,
                "unit_cost_vnd": 3_600_000,
                "source": "CATALOG_PLACEHOLDER",
            },
            {
                "product_id": balanced_products["AMD B550 Motherboard"]["id"],
                "inventory_unit_id": None,
                "quantity": 1,
                "unit_price_vnd": 2_250_000,
                "unit_cost_vnd": 1_600_000,
                "source": "CATALOG_PLACEHOLDER",
            },
            {
                "product_id": balanced_products["32GB DDR5 RAM"]["id"],
                "inventory_unit_id": None,
                "quantity": 1,
                "unit_price_vnd": 2_400_000,
                "unit_cost_vnd": 1_750_000,
                "source": "CATALOG_PLACEHOLDER",
            },
        ],
        quoted_price_vnd=9_850_000,
        estimated_cost_vnd=6_950_000,
    )
    balanced = balanced_detail["quote"]
    weak = weak_detail["quote"]
    assert balanced["quote_acceptance_chance"] is not None
    assert weak["quote_acceptance_chance"] is not None
    assert balanced["quote_acceptance_chance"] > weak["quote_acceptance_chance"]


def create_save(client: TestClient) -> dict[str, Any]:
    response = client.post("/api/save-games", json={"name": "Persona Save"})
    assert response.status_code == 200
    return response.json()


def product_map(client: TestClient) -> dict[str, dict[str, Any]]:
    response = client.get("/api/hardware-products")
    assert response.status_code == 200
    return {product["name"]: product for product in response.json()}


def create_quote(
    client: TestClient,
    save_id: int,
    request_id: int,
    title: str,
    items: list[dict[str, Any]],
    *,
    quoted_price_vnd: int,
    estimated_cost_vnd: int,
) -> dict[str, Any]:
    response = client.post(
        f"/api/save-games/{save_id}/quotes",
        json={
            "customer_request_id": request_id,
            "title": title,
            "summary": f"{title} summary",
            "quoted_price_vnd": quoted_price_vnd,
            "estimated_cost_vnd": estimated_cost_vnd,
            "items": items,
        },
    )
    assert response.status_code == 200
    return response.json()
