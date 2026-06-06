import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.models.entities import Supplier, SupplierOffer, HardwareProduct, PurchaseOrder, Brand
from app.models.enums import SupplierType, SupplierTier, HardwareCategory
from app.services import fx_service, supplier_service

@pytest.fixture()
def db_session() -> Session:
    settings = get_settings()
    original_enabled = settings.fx_external_calls_enabled
    settings.fx_external_calls_enabled = False
    
    from app.core.database import Base
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    
    try:
        with TestingSessionLocal() as db:
            intel = Brand(name="Intel", slug="intel", base_trust_score=90)
            db.add(intel)
            db.flush()
            cpu = HardwareProduct(
                name="Intel Core i5-14400",
                slug="intel-core-i5-14400",
                brand="Intel",
                brand_id=intel.id,
                category=HardwareCategory.CPU,
                base_performance_score=78,
                base_power_watts=65,
                base_heat_score=55,
                base_reliability_score=88,
                used_demand_score=78,
                mining_popularity_score=0,
                depreciation_rate=20,
            )
            db.add(cpu)
            db.commit()
            yield db
    finally:
        settings.fx_external_calls_enabled = original_enabled


def test_supplier_tier_mapping():
    from scripts.import_suppliers import map_tier_to_type
    assert map_tier_to_type("OFFICIAL_DISTRIBUTOR") == SupplierType.OFFICIAL_DISTRIBUTOR
    assert map_tier_to_type("IMPORTER") == SupplierType.WHOLESALE
    assert map_tier_to_type("USED_MARKET") == SupplierType.USED_MARKET
    assert map_tier_to_type("UNKNOWN") == SupplierType.OTHER


def test_supplier_import_currency_validation(db_session: Session):
    supported_currencies = {curr["code"] for curr in fx_service.get_supported_currencies()}
    assert "USD" in supported_currencies
    assert "ABC" not in supported_currencies


def test_supplier_import_idempotency(db_session: Session):
    s_data = {
        "slug": "test-import-supplier",
        "name": "Test Import Supplier",
        "supplier_tier": "WHOLESALE",
        "trust_score": 85,
        "relationship_score": 50,
        "default_delivery_days": 3,
        "country_code": "US",
        "invoice_currency": "USD",
        "fx_spread_percent": 1.5,
        "import_fee_percent": 2.0,
        "payment_fee_flat_vnd": 50000,
        "supported_brand_slugs": ["intel"],
        "supported_categories": ["CPU"]
    }
    
    # 1st run: Create
    s = db_session.scalar(select(Supplier).where(Supplier.slug == s_data["slug"]))
    assert s is None
    
    s = Supplier(
        slug=s_data["slug"],
        name=s_data["name"],
        type=SupplierType.WHOLESALE,
        supplier_tier=SupplierTier.WHOLESALE,
        trust_score=s_data["trust_score"],
        relationship_score=s_data["relationship_score"],
        delivery_days=s_data["default_delivery_days"],
        default_delivery_days=s_data["default_delivery_days"],
        country_code=s_data["country_code"],
        invoice_currency=s_data["invoice_currency"],
        fx_spread_percent=s_data["fx_spread_percent"],
        import_fee_percent=s_data["import_fee_percent"],
        payment_fee_flat_vnd=s_data["payment_fee_flat_vnd"]
    )
    db_session.add(s)
    db_session.commit()
    
    # Assert counts
    count1 = db_session.scalar(select(Supplier).where(Supplier.slug == s_data["slug"]))
    assert count1 is not None
    assert count1.name == "Test Import Supplier"
    
    # 2nd run: Update (idempotency check)
    s_existing = db_session.scalar(select(Supplier).where(Supplier.slug == s_data["slug"]))
    assert s_existing is not None
    s_existing.name = "Test Import Supplier Updated"
    db_session.commit()
    
    # Check that there is only one
    all_suppliers = db_session.scalars(select(Supplier).where(Supplier.slug == s_data["slug"])).all()
    assert len(all_suppliers) == 1
    assert all_suppliers[0].name == "Test Import Supplier Updated"


def test_foreign_supplier_offer_converts_to_vnd(db_session: Session):
    supplier = Supplier(
        slug="global-tech-import",
        name="Global Tech Import",
        type=SupplierType.WHOLESALE,
        supplier_tier=SupplierTier.IMPORTER,
        trust_score=85,
        relationship_score=40,
        delivery_days=7,
        country_code="US",
        invoice_currency="USD",
        fx_spread_percent=2.0
    )
    db_session.add(supplier)
    db_session.commit()
    
    product = db_session.scalar(select(HardwareProduct).where(HardwareProduct.slug == "intel-core-i5-14400"))
    
    rate, _, _, _, _ = fx_service.get_latest_rate(db_session, "USD", "VND")
    assert rate == 25400.0
    
    offer = SupplierOffer(
        supplier_id=supplier.id,
        product_id=product.id,
        foreign_unit_price=100.0,
        foreign_currency="USD",
        unit_price_vnd=round(100.0 * rate),
        min_order_quantity=1,
        available_quantity=10,
        warranty_months=12
    )
    db_session.add(offer)
    db_session.commit()
    
    assert offer.unit_price_vnd == 2540000
    
    offers = supplier_service.list_offers(db_session)
    matching = [o for o in offers if o.id == offer.id][0]
    assert matching.effective_unit_price_vnd == 2590800
    assert matching.effective_fx_rate_to_vnd == 25400.0
    assert matching.effective_fx_is_fallback is True


def test_purchase_order_stores_fx_snapshot(db_session: Session):
    from app.models.entities import SaveGame
    from app.schemas.game import PurchaseOrderCreate, PurchaseOrderItemCreate
    
    save_game = SaveGame(name="Test Save", cash=100000000)
    supplier = Supplier(
        slug="global-tech-import",
        name="Global Tech Import",
        type=SupplierType.WHOLESALE,
        supplier_tier=SupplierTier.IMPORTER,
        trust_score=85,
        relationship_score=40,
        delivery_days=7,
        country_code="US",
        invoice_currency="USD",
        fx_spread_percent=2.0,
        import_fee_percent=5.0,
        payment_fee_flat_vnd=250000
    )
    product = db_session.scalar(select(HardwareProduct).where(HardwareProduct.slug == "intel-core-i5-14400"))
    
    offer = SupplierOffer(
        supplier=supplier,
        product_id=product.id,
        foreign_unit_price=185.0,
        foreign_currency="USD",
        unit_price_vnd=4699000,
        min_order_quantity=1,
        available_quantity=36,
        warranty_months=12
    )
    
    db_session.add(save_game)
    db_session.add(supplier)
    db_session.add(offer)
    db_session.commit()
    
    payload = PurchaseOrderCreate(
        supplier_id=supplier.id,
        items=[
            PurchaseOrderItemCreate(
                product_id=product.id,
                quantity=10,
                unit_price_vnd=4699000,
                warranty_months=12
            )
        ]
    )
    
    po = supplier_service.create_purchase_order(db_session, save_game.id, payload)
    
    assert po.invoice_currency == "USD"
    assert po.foreign_subtotal == 1850.0
    assert po.fx_rate_to_vnd == 25400.0
    assert po.fx_spread_percent == 2.0
    assert po.fx_provider == "static_fallback"
    assert po.fx_is_fallback is True
    
    assert po.subtotal_vnd == 47929800
    assert po.fx_fee_vnd == 2646490
    assert po.final_total_vnd == 50576290
