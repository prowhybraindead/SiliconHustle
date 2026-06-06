from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models.entities import Brand, BrandCategory, HardwareProduct, InventoryUnit, PlayerProfile, SaveGame
from app.models.enums import BrandCategoryName, BrandType, MarketTier, ConditionType, Grade, HardwareCategory, InventoryStatus
from app.seed.initial_data import seed_database
from scripts.brand_data import normalize_category, parse_categories_field
from scripts.product_data import validate_products


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


def seed_test_brand_master(db: Session) -> None:
    specs = [
        ("Intel", "intel", "US", BrandType.CHIP_VENDOR, MarketTier.PREMIUM, 90, -8, [BrandCategoryName.CPU]),
        ("NVIDIA", "nvidia", "US", BrandType.CHIP_VENDOR, MarketTier.PREMIUM, 88, -2, [BrandCategoryName.GPU]),
        ("Corsair", "corsair", "US", BrandType.MEMORY_STORAGE, MarketTier.MAINSTREAM, 80, 0, [BrandCategoryName.RAM, BrandCategoryName.PSU]),
        ("Samsung", "samsung", "KR", BrandType.MEMORY_STORAGE, MarketTier.PREMIUM, 86, -4, [BrandCategoryName.STORAGE, BrandCategoryName.RAM]),
    ]
    brands: dict[str, Brand] = {}
    for name, slug, origin, brand_type, tier, trust, risk, categories in specs:
        brand = Brand(
            name=name,
            slug=slug,
            origin_name_vi=None,
            origin_code=origin,
            logo_url=f"/assets/brands/{slug}.svg",
            brand_type=brand_type,
            market_tier=tier,
            base_trust_score=trust,
            used_market_risk_modifier=risk,
        )
        db.add(brand)
        db.flush()
        for category in categories:
            db.add(BrandCategory(brand_id=brand.id, category=category))
        brands[slug] = brand
    for product in db.scalars(select(HardwareProduct)):
        slug = product.brand.lower().replace(" ", "-")
        if slug in brands:
            product.brand_id = brands[slug].id
        if slug in {"intel", "nvidia"}:
            product.chip_vendor_brand_id = brands[slug].id
    db.commit()


def create_save(client: TestClient) -> dict:
    response = client.post("/api/save-games", json={"name": "Test Bench Save"})
    assert response.status_code == 200
    return response.json()


def generate_build_request(client: TestClient, save_id: int) -> dict:
    for _ in range(12):
        response = client.post(f"/api/save-games/{save_id}/customers/generate-sample")
        assert response.status_code == 200
        request = response.json()["request"]
        if request["request_type"] == "BUILD_PC":
            return request
    raise AssertionError("Sample generator did not produce a BUILD_PC request")


def product_by_category(client: TestClient) -> dict[str, dict]:
    products = client.get("/api/hardware-products").json()
    selected: dict[str, dict] = {}
    for product in products:
        selected.setdefault(product["category"], product)
    return selected


def create_inventory_for_build(client: TestClient, save_id: int, condition_type: str = "NEW", source: str = "SUPPLIER") -> list[dict]:
    selected = product_by_category(client)
    units = []
    for category in ["CPU", "GPU", "RAM", "SSD", "PSU", "MOTHERBOARD", "CASE"]:
        product = selected[category]
        response = client.post(
            f"/api/save-games/{save_id}/inventory",
            json={
                "product_id": product["id"],
                "condition_type": condition_type,
                "source": source,
                "purchase_price_vnd": max(100_000, int(product["msrp_vnd"] * 0.65)),
                "listed_price_vnd": int(product["msrp_vnd"] * 0.9),
            },
        )
        assert response.status_code == 200
        units.append(response.json())
    return units


def test_seed_catalog_exists(client: TestClient) -> None:
    response = client.get("/api/hardware-products")
    assert response.status_code == 200
    assert len(response.json()) >= 15


def test_brand_category_normalization_helpers() -> None:
    warnings: list[str] = []
    errors: list[str] = []
    categories = parse_categories_field("SSD;water cooling|mother board", "test categories", warnings, errors)
    assert categories == ["STORAGE", "WATER_COOLING", "MOTHERBOARD"]
    assert normalize_category("mainboard") == "MOTHERBOARD"
    assert errors == []


def test_brand_api_returns_categories_and_filters(client: TestClient) -> None:
    response = client.get("/api/brands")
    assert response.status_code == 200
    brands = response.json()
    intel = next(brand for brand in brands if brand["slug"] == "intel")
    assert intel["categories"] == ["CPU"]
    assert intel["origin_code"] == "US"

    gpu_response = client.get("/api/brands", params={"category": "GPU"})
    assert gpu_response.status_code == 200
    gpu_slugs = {brand["slug"] for brand in gpu_response.json()}
    assert "nvidia" in gpu_slugs
    assert "intel" not in gpu_slugs


def test_hardware_product_response_includes_brand_reference(client: TestClient) -> None:
    response = client.get("/api/hardware-products")
    assert response.status_code == 200
    products = response.json()
    intel_cpu = next(product for product in products if product["brand"] == "Intel")
    assert intel_cpu["brand_id"] is not None
    assert intel_cpu["brand_ref"]["slug"] == "intel"
    assert intel_cpu["chip_vendor_brand"]["slug"] == "intel"
    assert intel_cpu["effective_logo_url"] == "/assets/brands/intel.svg"


def test_product_json_validation_accepts_storage_and_water_cooling() -> None:
    path = Path(__file__).with_name("_hardware_products.normalized.accept.json")
    result = validate_products({"samsung", "corsair"}, path=path)
    assert result.errors == []
    assert result.categories["STORAGE"] == 1
    assert result.categories["WATER_COOLING"] == 1


def test_product_json_validation_rejects_unknown_brands_and_duplicates() -> None:
    path = Path(__file__).with_name("_hardware_products.normalized.reject.json")
    result = validate_products({"intel"}, path=path)
    assert any("unknown brand_slug" in error for error in result.errors)
    assert any("unknown chip_vendor_slug" in error for error in result.errors)
    assert any("Duplicate product slug" in error for error in result.errors)


def product_json_row(slug: str, name: str, brand_slug: str, category: str, chip_vendor_slug: str | None = None) -> dict:
    return {
        "slug": slug,
        "name": name,
        "brand_slug": brand_slug,
        "chip_vendor_slug": chip_vendor_slug,
        "category": category,
        "release_year": None,
        "origin_code": "US",
        "source_name": "Manual curated sheet",
        "source_url": None,
        "data_confidence": "MANUAL",
        "real_specs": {"raw_key_specs": "Test specs", "power_watts": 10},
        "pricing": {"msrp_vnd": None, "base_local_price_vnd": None, "base_used_price_vnd": None, "supplier_cost_vnd": None},
        "game_balance": {
            "base_performance_score": 50,
            "base_power_watts": 10,
            "base_heat_score": 20,
            "base_reliability_score": 80,
            "used_demand_score": 30,
            "mining_popularity_score": 0,
            "depreciation_rate": 10,
        },
        "image_url": None,
        "notes": None,
    }


def test_create_save_game(client: TestClient) -> None:
    save = create_save(client)
    assert save["cash"] == 150_000_000
    assert save["game_day"] == 1


def test_used_untested_item_has_unknown_metrics_then_reveals(client: TestClient) -> None:
    save = create_save(client)
    product_id = client.get("/api/hardware-products").json()[0]["id"]
    response = client.post(
        f"/api/save-games/{save['id']}/inventory",
        json={"product_id": product_id, "condition_type": "USED", "source": "USED_MARKET", "purchase_price_vnd": 1_000_000},
    )
    assert response.status_code == 200
    unit = response.json()
    assert unit["health_score"] is None
    assert unit["performance_score"] is None

    test_response = client.post(f"/api/save-games/{save['id']}/inventory/{unit['id']}/tests/benchmark")
    assert test_response.status_code == 200
    tested = test_response.json()["unit"]
    assert tested["inspection_confidence"] >= 45
    assert tested["performance_score"] is not None


def test_receive_purchase_order_creates_inventory_units(client: TestClient) -> None:
    save = create_save(client)
    offer = client.get("/api/supplier-offers").json()[0]
    response = client.post(
        f"/api/save-games/{save['id']}/purchase-orders",
        json={
            "supplier_id": offer["supplier_id"],
            "items": [
                {
                    "product_id": offer["product_id"],
                    "quantity": 2,
                    "unit_price_vnd": offer["unit_price_vnd"],
                    "warranty_months": offer["warranty_months"],
                }
            ],
        },
    )
    assert response.status_code == 200
    purchase_order = response.json()

    receive = client.post(f"/api/save-games/{save['id']}/purchase-orders/{purchase_order['id']}/receive")
    assert receive.status_code == 200
    assert receive.json()["status"] == "RECEIVED"

    inventory = client.get(f"/api/save-games/{save['id']}/inventory").json()
    assert len(inventory) == 2
    assert inventory[0]["status"] == "READY_FOR_SALE"


def test_generate_sample_customer_request(client: TestClient) -> None:
    save = create_save(client)
    response = client.post(f"/api/save-games/{save['id']}/customers/generate-sample")
    assert response.status_code == 200
    payload = response.json()
    assert payload["customer"]["save_game_id"] == save["id"]
    assert payload["request"]["status"] == "NEW"


def test_generate_build_quote_with_placeholders_when_inventory_missing(client: TestClient) -> None:
    save = create_save(client)
    request = generate_build_request(client, save["id"])
    response = client.post(f"/api/save-games/{save['id']}/customer-requests/{request['id']}/generate-quote", json={})
    assert response.status_code == 200
    quote_detail = response.json()
    quote = quote_detail["quote"]
    items = quote_detail["quote_items"]
    assert quote["quoted_price_vnd"] > 0
    assert quote["estimated_cost_vnd"] > 0
    assert quote["estimated_profit_vnd"] == quote["quoted_price_vnd"] - quote["estimated_cost_vnd"]
    assert len(items) >= 7
    assert any(item["source"] in {"SUPPLIER_NEEDED", "CATALOG_PLACEHOLDER"} for item in items)


def test_quote_reservation_and_release(client: TestClient) -> None:
    save = create_save(client)
    create_inventory_for_build(client, save["id"])
    request = generate_build_request(client, save["id"])
    quote_detail = client.post(f"/api/save-games/{save['id']}/customer-requests/{request['id']}/generate-quote", json={}).json()
    quote_id = quote_detail["quote"]["id"]

    reserve = client.post(f"/api/save-games/{save['id']}/quotes/{quote_id}/reserve")
    assert reserve.status_code == 200
    reserved_items = [item for item in reserve.json()["quote_items"] if item["inventory_unit_id"]]
    assert reserved_items
    assert all(item["is_reserved"] for item in reserved_items)
    inventory = client.get(f"/api/save-games/{save['id']}/inventory").json()
    assert any(unit["status"] == "RESERVED" for unit in inventory)

    release = client.post(f"/api/save-games/{save['id']}/quotes/{quote_id}/release")
    assert release.status_code == 200
    assert all(not item["is_reserved"] for item in release.json()["quote_items"])
    inventory = client.get(f"/api/save-games/{save['id']}/inventory").json()
    assert all(unit["status"] == "READY_FOR_SALE" for unit in inventory)


def test_accept_quote_creates_order_and_blocks_double_accept(client: TestClient) -> None:
    save = create_save(client)
    create_inventory_for_build(client, save["id"])
    request = generate_build_request(client, save["id"])
    quote_detail = client.post(f"/api/save-games/{save['id']}/customer-requests/{request['id']}/generate-quote", json={}).json()
    quote_id = quote_detail["quote"]["id"]

    accept = client.post(f"/api/save-games/{save['id']}/quotes/{quote_id}/accept", json={})
    assert accept.status_code == 200
    order = accept.json()
    assert order["status"] == "ACCEPTED"
    assert len(order["items"]) == len(quote_detail["quote_items"])

    quote_after = client.get(f"/api/save-games/{save['id']}/quotes/{quote_id}").json()["quote"]
    assert quote_after["status"] == "CONVERTED_TO_ORDER"
    inventory = client.get(f"/api/save-games/{save['id']}/inventory").json()
    assert any(unit["status"] == "INSTALLED_IN_BUILD" for unit in inventory)

    double_accept = client.post(f"/api/save-games/{save['id']}/quotes/{quote_id}/accept", json={})
    assert double_accept.status_code == 400


def test_untested_used_inventory_increases_quote_warranty_risk(client: TestClient) -> None:
    save = create_save(client)
    create_inventory_for_build(client, save["id"], condition_type="USED", source="USED_MARKET")
    request = generate_build_request(client, save["id"])
    response = client.post(f"/api/save-games/{save['id']}/customer-requests/{request['id']}/generate-quote", json={})
    assert response.status_code == 200
    quote = response.json()["quote"]
    assert quote["warranty_risk"] == "HIGH" or quote["reliability_score"] < 70


def accepted_order_from_quote(client: TestClient, save_id: int, condition_type: str = "NEW", source: str = "SUPPLIER") -> dict:
    create_inventory_for_build(client, save_id, condition_type=condition_type, source=source)
    request = generate_build_request(client, save_id)
    quote_detail = client.post(f"/api/save-games/{save_id}/customer-requests/{request['id']}/generate-quote", json={}).json()
    accept = client.post(f"/api/save-games/{save_id}/quotes/{quote_detail['quote']['id']}/accept", json={})
    assert accept.status_code == 200
    return {"order": accept.json(), "request": request}


def delivered_order_from_quote(client: TestClient, save_id: int, condition_type: str = "NEW", source: str = "SUPPLIER") -> dict:
    payload = accepted_order_from_quote(client, save_id, condition_type=condition_type, source=source)
    order_id = payload["order"]["id"]
    client.post(f"/api/save-games/{save_id}/orders/{order_id}/start-build")
    client.post(f"/api/save-games/{save_id}/orders/{order_id}/run-build-test")
    deliver = client.post(f"/api/save-games/{save_id}/orders/{order_id}/deliver", json={"force": condition_type != "NEW"})
    assert deliver.status_code == 200
    payload["order"] = deliver.json()["order_detail"]["order"]
    return payload


def open_claim(client: TestClient, save_id: int, order_id: int, reason: str = "CRASHING") -> dict:
    response = client.post(
        f"/api/save-games/{save_id}/orders/{order_id}/warranty-claims",
        json={"claim_reason": reason, "complaint_summary": "Customer reports repeat instability after delivery."},
    )
    assert response.status_code == 200
    return response.json()


def diagnose_and_approve_claim(client: TestClient, save_id: int, claim_id: int) -> dict:
    start = client.post(f"/api/save-games/{save_id}/warranty-claims/{claim_id}/start-diagnosis")
    assert start.status_code == 200
    complete = client.post(f"/api/save-games/{save_id}/warranty-claims/{claim_id}/complete-diagnosis", json={})
    assert complete.status_code == 200
    approve = client.post(f"/api/save-games/{save_id}/warranty-claims/{claim_id}/approve")
    assert approve.status_code == 200
    return approve.json()


def test_accepted_order_can_start_build_and_creates_event(client: TestClient) -> None:
    save = create_save(client)
    payload = accepted_order_from_quote(client, save["id"])
    order = payload["order"]

    response = client.post(f"/api/save-games/{save['id']}/orders/{order['id']}/start-build")
    assert response.status_code == 200
    detail = response.json()
    assert detail["order"]["status"] == "IN_PROGRESS"
    assert detail["order"]["started_at"] is not None
    assert detail["fulfillment_events"][0]["event_type"] == "BUILD_STARTED"


def test_build_test_sets_testing_scores_and_risk(client: TestClient) -> None:
    save = create_save(client)
    payload = accepted_order_from_quote(client, save["id"])
    order_id = payload["order"]["id"]
    client.post(f"/api/save-games/{save['id']}/orders/{order_id}/start-build")

    response = client.post(f"/api/save-games/{save['id']}/orders/{order_id}/run-build-test")
    assert response.status_code == 200
    order = response.json()["order"]
    assert order["status"] == "TESTING"
    assert order["build_quality_score"] is not None
    assert order["final_test_score"] is not None
    assert order["final_warranty_risk"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


def test_untested_used_build_has_higher_warranty_risk_or_lower_score(client: TestClient) -> None:
    save = create_save(client)
    payload = accepted_order_from_quote(client, save["id"], condition_type="USED", source="USED_MARKET")
    order_id = payload["order"]["id"]
    client.post(f"/api/save-games/{save['id']}/orders/{order_id}/start-build")
    response = client.post(f"/api/save-games/{save['id']}/orders/{order_id}/run-build-test")
    assert response.status_code == 200
    order = response.json()["order"]
    assert order["final_warranty_risk"] in {"HIGH", "CRITICAL"} or order["final_test_score"] < 70


def test_deliver_order_updates_cash_reputation_inventory_and_request(client: TestClient) -> None:
    save = create_save(client)
    payload = accepted_order_from_quote(client, save["id"])
    order_id = payload["order"]["id"]
    request_id = payload["request"]["id"]
    before_state = client.get(f"/api/save-games/{save['id']}").json()
    client.post(f"/api/save-games/{save['id']}/orders/{order_id}/start-build")
    client.post(f"/api/save-games/{save['id']}/orders/{order_id}/run-build-test")

    response = client.post(f"/api/save-games/{save['id']}/orders/{order_id}/deliver", json={})
    assert response.status_code == 200
    payload = response.json()
    order = payload["order_detail"]["order"]
    assert order["status"] == "DELIVERED"
    assert payload["cash_delta"] == order["quoted_price_vnd"]
    after_state = client.get(f"/api/save-games/{save['id']}").json()
    assert after_state["cash"] == before_state["cash"] + order["quoted_price_vnd"]
    assert after_state["reputation"] == max(0, min(100, before_state["reputation"] + payload["reputation_delta"]))

    inventory = client.get(f"/api/save-games/{save['id']}/inventory").json()
    assert any(unit["status"] == "SOLD" for unit in inventory)
    requests = client.get(f"/api/save-games/{save['id']}/customer-requests").json()
    completed = next(request for request in requests if request["id"] == request_id)
    assert completed["status"] == "COMPLETED"


def test_cannot_deliver_twice_or_before_build_test(client: TestClient) -> None:
    save = create_save(client)
    payload = accepted_order_from_quote(client, save["id"])
    order_id = payload["order"]["id"]
    early = client.post(f"/api/save-games/{save['id']}/orders/{order_id}/deliver", json={})
    assert early.status_code == 400

    client.post(f"/api/save-games/{save['id']}/orders/{order_id}/start-build")
    client.post(f"/api/save-games/{save['id']}/orders/{order_id}/run-build-test")
    delivered = client.post(f"/api/save-games/{save['id']}/orders/{order_id}/deliver", json={})
    assert delivered.status_code == 200
    again = client.post(f"/api/save-games/{save['id']}/orders/{order_id}/deliver", json={})
    assert again.status_code == 400


def test_delivered_order_can_open_warranty_claim_and_event(client: TestClient) -> None:
    save = create_save(client)
    payload = delivered_order_from_quote(client, save["id"])
    claim_detail = open_claim(client, save["id"], payload["order"]["id"])
    assert claim_detail["claim"]["status"] == "OPEN"
    assert claim_detail["claim"]["order_id"] == payload["order"]["id"]
    assert claim_detail["events"][0]["event_type"] == "CLAIM_OPENED"
    order_detail = client.get(f"/api/save-games/{save['id']}/orders/{payload['order']['id']}").json()
    assert order_detail["order"]["warranty_claim_count"] == 1


def test_cannot_open_warranty_claim_on_non_delivered_order(client: TestClient) -> None:
    save = create_save(client)
    payload = accepted_order_from_quote(client, save["id"])
    response = client.post(
        f"/api/save-games/{save['id']}/orders/{payload['order']['id']}/warranty-claims",
        json={"claim_reason": "NO_DISPLAY", "complaint_summary": "Too early."},
    )
    assert response.status_code == 400


def test_warranty_diagnosis_and_approval_flow(client: TestClient) -> None:
    save = create_save(client)
    payload = delivered_order_from_quote(client, save["id"], condition_type="USED", source="USED_MARKET")
    claim = open_claim(client, save["id"], payload["order"]["id"], reason="OVERHEATING")["claim"]
    start = client.post(f"/api/save-games/{save['id']}/warranty-claims/{claim['id']}/start-diagnosis")
    assert start.status_code == 200
    assert start.json()["claim"]["status"] == "DIAGNOSING"
    complete = client.post(f"/api/save-games/{save['id']}/warranty-claims/{claim['id']}/complete-diagnosis", json={})
    assert complete.status_code == 200
    assert complete.json()["claim"]["status"] == "AWAITING_DECISION"
    assert complete.json()["claim"]["diagnostic_summary"] is not None
    approve = client.post(f"/api/save-games/{save['id']}/warranty-claims/{claim['id']}/approve")
    assert approve.status_code == 200
    assert approve.json()["claim"]["status"] == "APPROVED"


def test_warranty_reject_updates_reputation_and_status(client: TestClient) -> None:
    save = create_save(client)
    payload = delivered_order_from_quote(client, save["id"])
    claim = open_claim(client, save["id"], payload["order"]["id"])["claim"]
    diagnose_and_approve_claim(client, save["id"], claim["id"])
    repair = client.post(f"/api/save-games/{save['id']}/warranty-claims/{claim['id']}/resolve/repair", json={})
    assert repair.status_code == 200
    closed_again = client.post(f"/api/save-games/{save['id']}/warranty-claims/{claim['id']}/resolve/refund", json={})
    assert closed_again.status_code == 400

    second = open_claim(client, save["id"], payload["order"]["id"], reason="OTHER")["claim"]
    reject = client.post(f"/api/save-games/{save['id']}/warranty-claims/{second['id']}/reject", json={"reason": "No reproducible fault."})
    assert reject.status_code == 200
    assert reject.json()["claim"]["status"] == "REJECTED"
    assert reject.json()["claim"]["reputation_delta"] is not None


def test_warranty_repair_refund_and_rma_affect_cash_or_status(client: TestClient) -> None:
    save = create_save(client)
    payload = delivered_order_from_quote(client, save["id"])
    base_cash = client.get(f"/api/save-games/{save['id']}").json()["cash"]

    repair_claim = open_claim(client, save["id"], payload["order"]["id"], reason="NOISY_FAN")["claim"]
    diagnose_and_approve_claim(client, save["id"], repair_claim["id"])
    repair = client.post(f"/api/save-games/{save['id']}/warranty-claims/{repair_claim['id']}/resolve/repair", json={})
    assert repair.status_code == 200
    assert repair.json()["claim"]["status"] == "CLOSED"
    after_repair_cash = client.get(f"/api/save-games/{save['id']}").json()["cash"]
    assert after_repair_cash < base_cash

    refund_claim = open_claim(client, save["id"], payload["order"]["id"], reason="DOA")["claim"]
    diagnose_and_approve_claim(client, save["id"], refund_claim["id"])
    refund = client.post(f"/api/save-games/{save['id']}/warranty-claims/{refund_claim['id']}/resolve/refund", json={})
    assert refund.status_code == 200
    assert refund.json()["claim"]["status"] == "REFUNDED"
    assert refund.json()["claim"]["reimbursement_vnd"] > 0

    rma_claim = open_claim(client, save["id"], payload["order"]["id"], reason="ARTIFACTING")["claim"]
    diagnose_and_approve_claim(client, save["id"], rma_claim["id"])
    rma = client.post(f"/api/save-games/{save['id']}/warranty-claims/{rma_claim['id']}/resolve/rma", json={})
    assert rma.status_code == 200
    assert rma.json()["claim"]["status"] == "RMA_SUBMITTED"
    close = client.post(f"/api/save-games/{save['id']}/warranty-claims/{rma_claim['id']}/close")
    assert close.status_code == 200
    assert close.json()["claim"]["status"] == "CLOSED"


def test_warranty_replace_consumes_replacement_inventory(client: TestClient) -> None:
    save = create_save(client)
    payload = delivered_order_from_quote(client, save["id"])
    product_id = payload["order"]["items"][0]["product_id"]
    replacement = client.post(
        f"/api/save-games/{save['id']}/inventory",
        json={"product_id": product_id, "condition_type": "NEW", "source": "SUPPLIER", "purchase_price_vnd": 900_000},
    )
    assert replacement.status_code == 200
    replacement_id = replacement.json()["id"]

    claim = open_claim(client, save["id"], payload["order"]["id"], reason="NO_DISPLAY")["claim"]
    diagnose_and_approve_claim(client, save["id"], claim["id"])
    response = client.post(f"/api/save-games/{save['id']}/warranty-claims/{claim['id']}/resolve/replace", json={})
    assert response.status_code == 200
    assert response.json()["claim"]["status"] == "REPLACED"
    inventory = client.get(f"/api/save-games/{save['id']}/inventory").json()
    consumed = next(unit for unit in inventory if unit["id"] == replacement_id)
    assert consumed["status"] == "SOLD"


def test_warranty_generate_review_resolve_inventory_only_and_privacy(client: TestClient) -> None:
    save = create_save(client)
    db = next(app.dependency_overrides[get_db]())
    gpu_prod = db.scalar(select(HardwareProduct).where(HardwareProduct.category == HardwareCategory.GPU))
    assert gpu_prod is not None

    unit = InventoryUnit(
        save_game_id=save["id"],
        product_id=gpu_prod.id,
        condition_type=ConditionType.USED,
        status=InventoryStatus.UNTESTED,
        grade=Grade.D,
        inspection_confidence=12,
        purchase_price_vnd=2_000_000,
        hidden_condition_json={
            "vram_instability": True,
            "random_crash": True,
            "true_health": 41,
        },
    )
    db.add(unit)
    db.commit()
    db.refresh(unit)

    before_cash = client.get(f"/api/save-games/{save['id']}").json()["cash"]

    res_generate = client.post(
        f"/api/save-games/{save['id']}/warranty/claims/generate",
        json={"inventory_unit_id": unit.id},
    )
    assert res_generate.status_code == 200
    detail = res_generate.json()
    claim = detail["claim"]
    assert claim["order_id"] is None
    assert claim["resale_listing_id"] is None
    assert claim["customer_id"] is None
    assert claim["customer"] is None
    assert detail["order"] is None
    assert detail["resale_listing"] is None
    assert "hidden_condition_json" not in claim
    if claim.get("inventory_unit"):
        assert "hidden_condition_json" not in claim["inventory_unit"]

    res_summary = client.get(f"/api/save-games/{save['id']}/warranty/summary")
    assert res_summary.status_code == 200
    summary = res_summary.json()
    assert summary["open_claims_count"] >= 1
    assert len(summary["recent_claims"]) >= 1

    res_review = client.post(
        f"/api/save-games/{save['id']}/warranty/claims/{claim['id']}/review",
        json={"notes": "QA review"},
    )
    assert res_review.status_code == 200
    reviewed = res_review.json()["claim"]
    assert reviewed["status"] in {"IN_REVIEW", "APPROVED"}

    res_resolve = client.post(
        f"/api/save-games/{save['id']}/warranty/claims/{claim['id']}/resolve",
        json={"resolution_type": "REPAIR", "notes": "Resolved in QA"},
    )
    assert res_resolve.status_code == 200
    resolved = res_resolve.json()
    assert resolved["claim"]["status"] == "RESOLVED"
    assert resolved["cash_delta"] < 0
    after_cash = client.get(f"/api/save-games/{save['id']}").json()["cash"]
    assert after_cash == before_cash + resolved["cash_delta"]

    res_resolve_again = client.post(
        f"/api/save-games/{save['id']}/warranty/claims/{claim['id']}/resolve",
        json={"resolution_type": "REPAIR"},
    )
    assert res_resolve_again.status_code == 400


def test_warranty_profile_lock_token_protects_generate_and_unassigned_save_remains_usable(client: TestClient) -> None:
    res_profile = client.post("/api/player-profiles", json={"display_name": "Warranty QA", "pin": "1234"})
    assert res_profile.status_code == 200
    profile_id = res_profile.json()["id"]

    locked_save = create_save(client)
    db = next(app.dependency_overrides[get_db]())
    save_game = db.get(SaveGame, locked_save["id"])
    save_game.player_profile_id = profile_id
    save_game.pin_required = True

    gpu_prod = db.scalar(select(HardwareProduct).where(HardwareProduct.category == HardwareCategory.GPU))
    assert gpu_prod is not None
    locked_unit = InventoryUnit(
        save_game_id=locked_save["id"],
        product_id=gpu_prod.id,
        condition_type=ConditionType.USED,
        status=InventoryStatus.UNTESTED,
        grade=Grade.C,
        inspection_confidence=35,
        purchase_price_vnd=1_500_000,
    )
    db.add(locked_unit)
    db.commit()

    res_blocked = client.post(
        f"/api/save-games/{locked_save['id']}/warranty/claims/generate",
        json={"inventory_unit_id": locked_unit.id},
    )
    assert res_blocked.status_code == 403

    res_unlock = client.post(f"/api/player-profiles/{profile_id}/unlock", json={"pin": "1234"})
    assert res_unlock.status_code == 200
    token = res_unlock.json()["token"]

    res_allowed = client.post(
        f"/api/save-games/{locked_save['id']}/warranty/claims/generate",
        json={"inventory_unit_id": locked_unit.id},
        headers={"X-Profile-Unlock-Token": token},
    )
    assert res_allowed.status_code == 200

    open_save = create_save(client)
    open_unit = InventoryUnit(
        save_game_id=open_save["id"],
        product_id=gpu_prod.id,
        condition_type=ConditionType.USED,
        status=InventoryStatus.UNTESTED,
        grade=Grade.C,
        inspection_confidence=35,
        purchase_price_vnd=1_500_000,
    )
    db.add(open_unit)
    db.commit()

    res_open = client.post(
        f"/api/save-games/{open_save['id']}/warranty/claims/generate",
        json={"inventory_unit_id": open_unit.id},
    )
    assert res_open.status_code == 200
