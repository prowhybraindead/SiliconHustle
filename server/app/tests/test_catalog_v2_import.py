import pytest
import json
import csv
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.models.entities import HardwareProduct, ProductPriceSnapshot, Brand
from app.models.enums import HardwareCategory
from app.services import fx_service


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


def test_validate_hardware_products_supports_file():
    from scripts.product_data import validate_products
    result = validate_products(known_brand_slugs={"intel"})
    assert result is not None
    assert isinstance(result.errors, list)


def test_import_hardware_products_idempotency(db_session: Session):
    from scripts.import_hardware_products import apply_payload
    p = db_session.scalar(select(HardwareProduct).where(HardwareProduct.slug == "intel-core-i5-14400"))
    assert p is not None

    payload = {
        "slug": "intel-core-i5-14400",
        "name": "Intel Core i5-14400 Updated",
        "brand": "Intel",
        "category": "CPU",
        "release_year": 2024,
        "base_performance_score": 80,
    }

    changed = apply_payload(p, payload)
    assert changed is True
    assert p.name == "Intel Core i5-14400 Updated"

    changed2 = apply_payload(p, payload)
    assert changed2 is False


def test_product_price_snapshot_model(db_session: Session):
    product = db_session.scalar(select(HardwareProduct).where(HardwareProduct.slug == "intel-core-i5-14400"))

    snapshot = ProductPriceSnapshot(
        product_id=product.id,
        product_slug=product.slug,
        price_type="MSRP",
        currency="USD",
        amount=185.0,
        amount_vnd=4699000,
        confidence="OFFICIAL",
        observed_at=datetime.now(timezone.utc),
        is_current=True
    )
    db_session.add(snapshot)
    db_session.commit()

    assert snapshot.id is not None
    assert snapshot.amount == 185.0


def test_price_validation_catches_unsupported_slug_and_currency(db_session: Session):
    from scripts.price_data import validate_prices
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv", encoding="utf-8") as temp:
        temp.write(
            "product_slug,price_type,currency,amount,region,source_name,source_url,observed_at,confidence,notes\n"
            "unknown-slug,MSRP,USD,100,US,Source,http://url,2026-06-04 12:00:00,OFFICIAL,notes\n"
            "intel-core-i5-14400,MSRP,ABC,100,US,Source,http://url,2026-06-04 12:00:00,OFFICIAL,notes\n"
        )
        temp_path = temp.name

    try:
        report = validate_prices(path=temp_path)
        assert len(report.errors) > 0
        assert any("unknown product_slug" in err for err in report.errors)
        assert any("unsupported currency" in err for err in report.errors)
    finally:
        os.unlink(temp_path)


def test_vnd_price_import_stores_amount_vnd_directly(db_session: Session):
    rate, _, _, _, _, _ = fx_service.get_rate_to_vnd(db_session, "USD")
    assert rate == 25400.0

    amount_usd = 185.0
    amount_vnd = round(amount_usd * rate)

    p = db_session.scalar(select(HardwareProduct).where(HardwareProduct.slug == "intel-core-i5-14400"))
    snapshot = ProductPriceSnapshot(
        product_id=p.id,
        product_slug=p.slug,
        price_type="MSRP",
        currency="USD",
        amount=amount_usd,
        amount_vnd=amount_vnd,
        fx_rate_to_vnd=rate,
        confidence="OFFICIAL",
        observed_at=datetime.now(timezone.utc),
        is_current=True
    )
    db_session.add(snapshot)
    db_session.commit()

    assert snapshot.amount_vnd == 4699000


def test_previous_snapshot_marked_non_current_on_new_import(db_session: Session):
    p = db_session.scalar(select(HardwareProduct).where(HardwareProduct.slug == "intel-core-i5-14400"))

    s1 = ProductPriceSnapshot(
        product_id=p.id,
        product_slug=p.slug,
        price_type="MSRP",
        currency="USD",
        amount=185.0,
        amount_vnd=4699000,
        region="US",
        source_name="Intel",
        confidence="OFFICIAL",
        observed_at=datetime(2026, 6, 4, 10, 0, tzinfo=timezone.utc),
        is_current=True
    )
    db_session.add(s1)
    db_session.commit()

    db_session.query(ProductPriceSnapshot).filter(
        ProductPriceSnapshot.product_slug == p.slug,
        ProductPriceSnapshot.price_type == "MSRP",
        ProductPriceSnapshot.region == "US",
        ProductPriceSnapshot.source_name == "Intel",
        ProductPriceSnapshot.is_current == True
    ).update({ProductPriceSnapshot.is_current: False})

    s2 = ProductPriceSnapshot(
        product_id=p.id,
        product_slug=p.slug,
        price_type="MSRP",
        currency="USD",
        amount=190.0,
        amount_vnd=4826000,
        region="US",
        source_name="Intel",
        confidence="OFFICIAL",
        observed_at=datetime(2026, 6, 4, 11, 0, tzinfo=timezone.utc),
        is_current=True
    )
    db_session.add(s2)
    db_session.commit()

    db_session.refresh(s1)
    db_session.refresh(s2)

    assert s1.is_current is False
    assert s2.is_current is True
