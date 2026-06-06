import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from typing import Generator

from app.core.database import Base, get_db
from app.core.config import get_settings
from app.main import app
from app.models.entities import ExchangeRate
from app.services import fx_service


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    settings = get_settings()
    original_enabled = settings.fx_external_calls_enabled
    settings.fx_external_calls_enabled = False
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
        settings.fx_external_calls_enabled = original_enabled


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    settings = get_settings()
    original_enabled = settings.fx_external_calls_enabled
    settings.fx_external_calls_enabled = False
    
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        settings.fx_external_calls_enabled = original_enabled


def test_supported_currencies():
    currencies = fx_service.get_supported_currencies()
    assert len(currencies) == 10
    codes = {c["code"] for c in currencies}
    assert "VND" in codes
    assert "USD" in codes
    assert "EUR" in codes


def test_vnd_to_vnd_is_one(db_session: Session):
    rate, provider, _, _, is_fallback = fx_service.get_latest_rate(db_session, "VND", "VND")
    assert rate == 1.0
    assert provider == "identity"
    assert not is_fallback


def test_static_fallback_when_external_disabled(db_session: Session):
    settings = get_settings()
    original_enabled = settings.fx_external_calls_enabled
    settings.fx_external_calls_enabled = False
    try:
        # USD -> VND static fallback is 25400
        rate, provider, source, fetched_at, is_fallback = fx_service.get_latest_rate(db_session, "USD", "VND")
        assert rate == 25400.0
        assert provider == "static_fallback"
        assert is_fallback
    finally:
        settings.fx_external_calls_enabled = original_enabled


def test_conversion_with_spread(db_session: Session):
    settings = get_settings()
    original_enabled = settings.fx_external_calls_enabled
    settings.fx_external_calls_enabled = False
    try:
        # USD base rate is 25400. With 1.5% spread, it should be 25400 * 1.015 = 2578100
        amount = 100.0
        _, rate, _, _, _, _, final_vnd = fx_service.convert_to_vnd(db_session, amount, "USD", spread_percent=1.5)
        assert rate == 25400.0
        assert final_vnd == round(100.0 * 25400.0 * 1.015)
        assert final_vnd == 2578100
    finally:
        settings.fx_external_calls_enabled = original_enabled


def test_cache_mechanism(db_session: Session):
    settings = get_settings()
    original_enabled = settings.fx_external_calls_enabled
    settings.fx_external_calls_enabled = False
    try:
        # Set a cached rate manually
        fetched = datetime.now(timezone.utc) - timedelta(minutes=5)
        db_session.add(ExchangeRate(
            base_currency="USD",
            quote_currency="VND",
            rate=25000.0,
            provider="test_provider",
            source="Test Suite Cache",
            is_fallback=False,
            fetched_at=fetched
        ))
        db_session.commit()

        # Query USD -> VND, should get cached 25000 instead of static 25400
        rate, provider, source, fetched_at, is_fallback = fx_service.get_latest_rate(db_session, "USD", "VND")
        assert rate == 25000.0
        assert provider == "test_provider"
        assert source == "Test Suite Cache"
        assert not is_fallback

        # If we force refresh, even if external calls are disabled, it should fall back to cached rate but mark as fallback, or update from static fallback
        rate, provider, source, fetched_at, is_fallback = fx_service.get_latest_rate(db_session, "USD", "VND", force_refresh=True)
        # Since force_refresh is True and external calls are disabled, get_rate_to_vnd will query external, fail,
        # fallback to the cached DB rate (which is 25000.0) but mark is_fallback = True.
        assert rate == 25000.0
        assert is_fallback
    finally:
        settings.fx_external_calls_enabled = original_enabled


def test_api_supported_currencies(client: TestClient):
    response = client.get("/api/fx/supported-currencies")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 10
    codes = {item["code"] for item in data}
    assert "USD" in codes


def test_api_convert(client: TestClient):
    # Mock settings for testing
    settings = get_settings()
    original_enabled = settings.fx_external_calls_enabled
    settings.fx_external_calls_enabled = False
    try:
        response = client.get("/api/fx/convert", params={"amount": 100, "from_currency": "USD", "to_currency": "VND", "spread_percent": 1.5})
        assert response.status_code == 200
        data = response.json()
        assert data["from_currency"] == "USD"
        assert data["to_currency"] == "VND"
        assert data["final_amount_vnd"] == 2578100
        assert data["rate"] == 25400.0
        assert data["is_fallback"] is True
    finally:
        settings.fx_external_calls_enabled = original_enabled


def test_api_rates(client: TestClient):
    settings = get_settings()
    original_enabled = settings.fx_external_calls_enabled
    settings.fx_external_calls_enabled = False
    try:
        response = client.get("/api/fx/rates", params={"base": "USD", "quote": "VND"})
        assert response.status_code == 200
        data = response.json()
        assert data["base_currency"] == "USD"
        assert data["quote_currency"] == "VND"
        assert data["rate"] == 25400.0
    finally:
        settings.fx_external_calls_enabled = original_enabled


def test_api_refresh(client: TestClient):
    settings = get_settings()
    original_enabled = settings.fx_external_calls_enabled
    settings.fx_external_calls_enabled = False
    try:
        response = client.post("/api/fx/rates/refresh", params={"force": True})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        usd_rate = next(r for r in data if r["base_currency"] == "USD")
        assert usd_rate["rate"] == 25400.0
        assert usd_rate["is_fallback"] is True
    finally:
        settings.fx_external_calls_enabled = original_enabled


def test_customer_generation_with_foreign_currency(db_session: Session):
    from app.services import customer_service
    from app.models.entities import SaveGame
    
    save_game = SaveGame(name="FX Save")
    db_session.add(save_game)
    db_session.commit()
    db_session.refresh(save_game)
    
    found_foreign = False
    for i in range(50):
        customer, request = customer_service.generate_sample_customer(db_session, save_game.id)
        if customer.preferred_currency != "VND":
            found_foreign = True
            assert customer.country_code != "VN"
            assert request.budget_currency == customer.preferred_currency
            assert request.foreign_budget_amount > 0
            assert request.budget_fx_rate_to_vnd > 1.0
            break
    assert found_foreign


def test_quote_generation_stores_fx_snapshot(db_session: Session):
    from app.services import customer_service, quote_service
    from app.models.entities import SaveGame, HardwareProduct
    
    save_game = SaveGame(name="FX Save")
    db_session.add(save_game)
    product = HardwareProduct(
        name="Test GPU",
        brand="Test",
        category="GPU",
        base_performance_score=80,
        base_power_watts=150,
        base_heat_score=60,
        base_reliability_score=85,
        msrp_vnd=10000000,
        used_demand_score=80,
        mining_popularity_score=0,
        depreciation_rate=10
    )
    db_session.add(product)
    db_session.commit()
    
    customer, request = customer_service.generate_sample_customer(db_session, save_game.id)
    customer.preferred_currency = "USD"
    customer.country_code = "US"
    request.budget_currency = "USD"
    request.request_type = "BUY_COMPONENT"
    request.use_case = "gaming"
    db_session.commit()
    
    quote = quote_service.generate_quote_from_customer_request(db_session, save_game.id, request.id)
    assert quote.quote_currency == "USD"
    assert quote.foreign_quoted_price is not None
    assert quote.foreign_quoted_price > 0
    assert quote.fx_rate_to_vnd == 25400.0
    assert quote.fx_provider == "static_fallback"
    
    order = quote_service.accept_quote_to_order(db_session, save_game.id, quote.id)
    assert order.order_currency == "USD"
    assert order.foreign_order_amount == quote.foreign_quoted_price
    assert order.fx_rate_to_vnd == quote.fx_rate_to_vnd
    assert order.fx_provider == quote.fx_provider


def test_purchase_order_foreign_conversion(db_session: Session):
    from app.services import supplier_service
    from app.models.entities import SaveGame, Supplier, HardwareProduct
    from app.schemas.game import PurchaseOrderCreate, PurchaseOrderItemCreate
    
    save_game = SaveGame(name="FX Save", cash=100000000)
    supplier = Supplier(
        name="Foreign Supplier",
        type="WHOLESALE",
        trust_score=80,
        relationship_score=50,
        delivery_days=5,
        invoice_currency="USD",
        fx_spread_percent=2.0,
        import_fee_percent=5.0,
        payment_fee_flat_vnd=100000
    )
    product = HardwareProduct(
        name="Test CPU",
        brand="Test",
        category="CPU",
        base_performance_score=80,
        base_power_watts=150,
        base_heat_score=60,
        base_reliability_score=85,
        msrp_vnd=10000000,
        used_demand_score=80,
        mining_popularity_score=0,
        depreciation_rate=10
    )
    db_session.add(save_game)
    db_session.add(supplier)
    db_session.add(product)
    db_session.commit()
    
    payload = PurchaseOrderCreate(
        supplier_id=supplier.id,
        items=[
            PurchaseOrderItemCreate(
                product_id=product.id,
                quantity=10,
                unit_price_vnd=200,
                warranty_months=12
            )
        ]
    )
    
    po = supplier_service.create_purchase_order(db_session, save_game.id, payload)
    assert po.invoice_currency == "USD"
    assert po.foreign_subtotal == 2000.0
    assert po.fx_rate_to_vnd == 25400.0
    assert po.fx_spread_percent == 2.0
    assert po.fx_fee_vnd == 2690800
    assert po.final_total_vnd == 54506800
    assert po.subtotal_vnd == 51816000

