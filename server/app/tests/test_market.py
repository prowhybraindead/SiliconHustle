import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from typing import Generator

from app.core.database import Base, get_db
from app.core.config import get_settings
from app.main import app
from app.models.entities import SaveGame, HardwareProduct, Supplier, SupplierOffer
from app.services import market_service, supplier_service, hardware_service
from app.schemas.game import PurchaseOrderCreate, PurchaseOrderItemCreate
from app.models.enums import MarketEventType, MarketEventGenerationSource


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    try:
        with TestingSessionLocal() as db:
            yield db
    finally:
        pass


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def test_data(db_session: Session):
    save_game = SaveGame(name="Market Test Save", cash=500000000)
    db_session.add(save_game)
    
    gpu_prod = HardwareProduct(
        name="GeForce RTX 4070 Super",
        brand="NVIDIA",
        category="GPU",
        base_performance_score=90,
        base_power_watts=220,
        base_heat_score=70,
        base_reliability_score=90,
        msrp_vnd=15000000,
        used_demand_score=85,
        mining_popularity_score=80,
        depreciation_rate=12,
        latest_local_retail_vnd=17000000,
        latest_used_market_vnd=13000000,
        latest_supplier_cost_vnd=14500000,
        latest_msrp_vnd=15000000
    )
    ram_prod = HardwareProduct(
        name="Corsair Vengeance 32GB DDR5",
        brand="Corsair",
        category="RAM",
        base_performance_score=85,
        base_power_watts=15,
        base_heat_score=35,
        base_reliability_score=95,
        msrp_vnd=3000000,
        used_demand_score=60,
        mining_popularity_score=0,
        depreciation_rate=15,
        latest_local_retail_vnd=3200000,
        latest_used_market_vnd=2200000,
        latest_supplier_cost_vnd=2800000,
        latest_msrp_vnd=3000000
    )
    db_session.add(gpu_prod)
    db_session.add(ram_prod)
    db_session.commit()
    
    supplier = Supplier(
        name="Official HW Distributor",
        type="OFFICIAL_DISTRIBUTOR",
        trust_score=95,
        relationship_score=60,
        delivery_days=2,
        invoice_currency="VND"
    )
    db_session.add(supplier)
    db_session.commit()
    
    offer = SupplierOffer(
        supplier_id=supplier.id,
        product_id=gpu_prod.id,
        unit_price_vnd=14000000,
        min_order_quantity=2,
        available_quantity=10,
        warranty_months=36
    )
    db_session.add(offer)
    db_session.commit()
    
    return {
        "save_game": save_game,
        "gpu": gpu_prod,
        "ram": ram_prod,
        "supplier": supplier,
        "offer": offer
    }


def test_rule_based_generation(db_session: Session, test_data):
    save_game = test_data["save_game"]
    event = market_service.generate_random_market_event(db_session, save_game.id)
    assert event.id is not None
    assert event.save_game_id == save_game.id
    assert event.is_active is True
    assert event.price_multiplier > 0.0
    assert event.generation_source == MarketEventGenerationSource.RULE


def test_manual_event_creation(db_session: Session, test_data):
    save_game = test_data["save_game"]
    payload = {
        "event_type": "MINING_BOOM",
        "title": "Manual Mining Surge",
        "summary": "Mining rises manually.",
        "severity": 4,
        "affected_category": "GPU",
        "price_multiplier": 2.5,
        "starts_on_day": 1,
        "ends_on_day": 10
    }
    event = market_service.create_market_event(db_session, save_game.id, payload)
    assert event.title == "Manual Mining Surge"
    assert event.price_multiplier == 2.5
    assert event.generation_source == MarketEventGenerationSource.MANUAL


def test_validation_and_clamping(db_session: Session):
    # Unsafe proposal price multiplier > 3.5 should clamp to 3.5
    proposal_unsafe = {
        "event_type": "MINING_BOOM",
        "title": "Crypto Rush Extreme",
        "summary": "Mining is back.",
        "severity": 5,
        "price_multiplier": 5.2,
        "duration_days": 15
    }
    validated = market_service.validate_market_event_proposal(db_session, proposal_unsafe)
    assert validated["price_multiplier"] == 3.5
    assert validated["severity"] == 5

    # Invalid event_type should fallback
    proposal_invalid = {
        "event_type": "DUMMY_UNKNOWN_TYPE",
        "title": "Strange Glitch",
        "summary": "Not a real event type.",
        "severity": 2,
        "price_multiplier": 1.2,
        "duration_days": 40  # Should clamp to 30
    }
    validated_invalid = market_service.validate_market_event_proposal(db_session, proposal_invalid)
    assert validated_invalid["event_type"] == MarketEventType.RANDOM_DEMAND_SPIKE.value
    assert validated_invalid["duration_days"] == 30


def test_ai_fallback_when_disabled(db_session: Session, test_data):
    save_game = test_data["save_game"]
    settings = get_settings()
    settings.ai_market_events_enabled = False
    
    # Attempting to generate AI assisted event should fallback to rule-based event
    event = market_service.generate_market_event(db_session, save_game.id, mode="ai")
    assert event.generation_source == MarketEventGenerationSource.AI_FALLBACK


def test_day_advancement_and_expiration(db_session: Session, test_data):
    save_game = test_data["save_game"]
    payload = {
        "event_type": "MINING_BOOM",
        "title": "Quick Event",
        "summary": "Quick one.",
        "severity": 2,
        "affected_category": "GPU",
        "price_multiplier": 1.5,
        "starts_on_day": 1,
        "ends_on_day": 2
    }
    event = market_service.create_market_event(db_session, save_game.id, payload)
    assert event.is_active is True

    # Advance to day 2
    market_service.advance_market_day(db_session, save_game.id)
    db_session.refresh(save_game)
    assert save_game.game_day == 2
    # The event end day is 2. The code expires when ends_on_day < current_day.
    # So on day 2, it is still active.
    db_session.refresh(event)
    assert event.is_active is True

    # Advance to day 3
    market_service.advance_market_day(db_session, save_game.id)
    db_session.refresh(save_game)
    assert save_game.game_day == 3
    db_session.refresh(event)
    assert event.is_active is False  # Now expired because ends_on_day (2) < current_day (3)


def test_matching_multiplier_rules(db_session: Session, test_data):
    save_game = test_data["save_game"]
    gpu = test_data["gpu"]
    ram = test_data["ram"]

    # 1. GPU Mining boom
    payload1 = {
        "event_type": "MINING_BOOM",
        "title": "Crypto Boom",
        "summary": "GPU prices rise.",
        "severity": 3,
        "affected_category": "GPU",
        "price_multiplier": 1.5,
        "starts_on_day": 1,
        "ends_on_day": 10
    }
    market_service.create_market_event(db_session, save_game.id, payload1)

    mult_gpu = market_service.get_effective_product_multiplier(db_session, save_game.id, gpu)
    mult_ram = market_service.get_effective_product_multiplier(db_session, save_game.id, ram)

    assert mult_gpu == 1.5
    assert mult_ram == 1.0  # RAM not affected by GPU mining boom

    # 2. AI Datacenter demand matching RAM
    payload2 = {
        "event_type": "AI_DATACENTER_DEMAND",
        "title": "Memory Rush",
        "summary": "RAM prices rise.",
        "severity": 3,
        "affected_category": "RAM",
        "price_multiplier": 2.0,
        "starts_on_day": 1,
        "ends_on_day": 10
    }
    market_service.create_market_event(db_session, save_game.id, payload2)

    mult_gpu_new = market_service.get_effective_product_multiplier(db_session, save_game.id, gpu)
    mult_ram_new = market_service.get_effective_product_multiplier(db_session, save_game.id, ram)

    assert mult_gpu_new == 1.5
    assert mult_ram_new == 2.0

    # 3. Stacked multipliers. Let's add a general GPU price crash
    payload3 = {
        "event_type": "MINING_CRASH",
        "title": "Crash",
        "summary": "Crash GPU.",
        "severity": 1,
        "affected_category": "GPU",
        "price_multiplier": 0.5,
        "starts_on_day": 1,
        "ends_on_day": 10
    }
    market_service.create_market_event(db_session, save_game.id, payload3)

    mult_gpu_stacked = market_service.get_effective_product_multiplier(db_session, save_game.id, gpu)
    # 1.5 * 0.5 = 0.75
    assert mult_gpu_stacked == 0.75


def test_baseline_and_adjusted_pricing(db_session: Session, test_data):
    save_game = test_data["save_game"]
    gpu = test_data["gpu"]
    
    # Initially no event
    prod_original = hardware_service.get_product(db_session, gpu.id, save_game.id)
    assert prod_original.market_multiplier == 1.0
    assert prod_original.market_adjusted_local_retail_vnd == gpu.latest_local_retail_vnd
    assert prod_original.latest_msrp_vnd == gpu.latest_msrp_vnd

    # Create event
    payload = {
        "event_type": "MINING_BOOM",
        "title": "Boom",
        "summary": "GPU rises.",
        "severity": 3,
        "affected_category": "GPU",
        "price_multiplier": 2.0,
        "starts_on_day": 1,
        "ends_on_day": 10
    }
    market_service.create_market_event(db_session, save_game.id, payload)

    # Fetch product with save_game_id
    prod_adjusted = hardware_service.get_product(db_session, gpu.id, save_game_id=save_game.id)
    assert prod_adjusted.market_multiplier == 2.0
    assert prod_adjusted.market_adjusted_local_retail_vnd == gpu.latest_local_retail_vnd * 2
    
    # MSRP baseline remains unchanged
    assert prod_adjusted.latest_msrp_vnd == gpu.latest_msrp_vnd
    assert gpu.latest_msrp_vnd == 15000000

    # Fetch product without save_game_id (baseline returns multiplier 1.0)
    prod_no_save = hardware_service.get_product(db_session, gpu.id, save_game_id=None)
    assert prod_no_save.market_multiplier == 1.0
    assert prod_no_save.market_adjusted_local_retail_vnd == gpu.latest_local_retail_vnd


def test_supplier_offers_and_po_snapshots(db_session: Session, test_data):
    save_game = test_data["save_game"]
    offer = test_data["offer"]
    supplier = test_data["supplier"]

    # Initial state
    offers_no_save = supplier_service.list_offers(db_session, save_game_id=None)
    assert offers_no_save[0].market_multiplier == 1.0
    assert offers_no_save[0].market_adjusted_unit_price_vnd == offers_no_save[0].effective_unit_price_vnd

    # Create event raising GPU price by 2.0x
    payload = {
        "event_type": "MINING_BOOM",
        "title": "Boom",
        "summary": "GPU rises.",
        "severity": 3,
        "affected_category": "GPU",
        "price_multiplier": 2.0,
        "starts_on_day": 1,
        "ends_on_day": 10
    }
    market_service.create_market_event(db_session, save_game.id, payload)

    offers_adjusted = supplier_service.list_offers(db_session, save_game_id=save_game.id)
    assert offers_adjusted[0].market_multiplier == 2.0
    assert offers_adjusted[0].market_adjusted_unit_price_vnd == offer.unit_price_vnd * 2

    # Create purchase order - should snapshot the market adjusted price
    po_payload = PurchaseOrderCreate(
        supplier_id=supplier.id,
        items=[
            PurchaseOrderItemCreate(
                product_id=offer.product_id,
                quantity=2,
                unit_price_vnd=offer.unit_price_vnd, # Frontend sends the base or adjusted, backend resolves with offer
                warranty_months=offer.warranty_months
            )
        ]
    )
    po = supplier_service.create_purchase_order(db_session, save_game.id, po_payload)
    # Unit price vnd in PO should be 14M * 2.0 = 28M
    assert po.items[0].unit_price_vnd == 28000000
    assert po.subtotal_vnd == 56000000
    assert po.market_multiplier_snapshot == 2.0
    assert "Boom" in po.market_event_titles_snapshot


def test_advance_day_max_limit(db_session: Session, test_data):
    save_game = test_data["save_game"]
    settings = get_settings()
    settings.market_random_event_chance = 1.0  # Force generation
    settings.market_max_active_events = 2

    # Advance day 1
    market_service.advance_market_day(db_session, save_game.id)
    events_d1 = market_service.get_active_market_events(db_session, save_game.id)
    assert len(events_d1) == 1

    # Advance day 2
    market_service.advance_market_day(db_session, save_game.id)
    events_d2 = market_service.get_active_market_events(db_session, save_game.id)
    assert len(events_d2) == 2

    # Advance day 3 - should NOT generate new event because count is at max (2)
    market_service.advance_market_day(db_session, save_game.id)
    events_d3 = market_service.get_active_market_events(db_session, save_game.id)
    assert len(events_d3) == 2


def test_api_endpoints(client: TestClient, test_data):
    save_game = test_data["save_game"]
    
    # 1. Get summary
    res_sum = client.get(f"/api/save-games/{save_game.id}/market/summary")
    assert res_sum.status_code == 200
    assert res_sum.json()["active_market_events_count"] == 0

    # 2. Generate event
    res_gen = client.post(f"/api/save-games/{save_game.id}/market/events/generate", params={"mode": "rule"})
    assert res_gen.status_code == 200
    assert res_gen.json()["is_active"] is True

    # 3. Get active list
    res_act = client.get(f"/api/save-games/{save_game.id}/market/events/active")
    assert res_act.status_code == 200
    assert len(res_act.json()) == 1

    # 4. Advance day
    res_adv = client.post(f"/api/save-games/{save_game.id}/advance-day")
    assert res_adv.status_code == 200
    assert res_adv.json()["active_market_events_count"] >= 1


def test_hardware_product_list_no_save_game(db_session: Session, test_data):
    products = hardware_service.list_products(db_session, save_game_id=None)
    assert len(products) > 0
    for p in products:
        assert p.market_multiplier == 1.0
        assert p.market_adjusted_local_retail_vnd == p.latest_local_retail_vnd
        assert p.market_adjusted_used_market_vnd == p.latest_used_market_vnd
        assert p.market_adjusted_supplier_cost_vnd == p.latest_supplier_cost_vnd
        assert p.active_market_event_titles == []

