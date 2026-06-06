from collections.abc import Generator
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models.entities import Customer, HardwareProduct, InventoryUnit, Order, OrderItem, PlayerProfile, ResaleBuyerOffer, ResaleListing, SaveGame, WarrantyClaim
from app.models.enums import (
    ConditionType,
    CustomerArchetype,
    Grade,
    HardwareCategory,
    InventoryStatus,
    KnowledgeLevel,
    OrderStatus,
    ResaleBuyerOfferStatus,
    ResaleListingStatus,
    RiskTolerance,
    WarrantyClaimReason,
    WarrantyClaimStatus,
    WarrantyClaimType,
    WarrantyResolutionType,
)
from app.seed.initial_data import seed_database
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


def _db() -> Session:
    return next(app.dependency_overrides[get_db]())


def _create_save(client: TestClient, name: str) -> int:
    response = client.post("/api/save-games", json={"name": name})
    assert response.status_code == 200
    return response.json()["id"]


def _seed_customer_and_order(db: Session, save_id: int) -> tuple[Customer, Order]:
    product = db.scalar(select(HardwareProduct).where(HardwareProduct.category == HardwareCategory.GPU))
    assert product is not None
    customer = Customer(
        save_game_id=save_id,
        name="Warranty Fan",
        archetype=CustomerArchetype.GAMER,
        knowledge_level=KnowledgeLevel.HIGH,
        patience=80,
        negotiation_score=72,
        risk_tolerance=RiskTolerance.MEDIUM,
    )
    order = Order(
        save_game_id=save_id,
        customer=customer,
        status=OrderStatus.DELIVERED,
        quoted_price_vnd=12_000_000,
        cost_vnd=9_000_000,
        profit_vnd=3_000_000,
        customer_fit_score=88,
        build_quality_score=91,
        final_test_score=94,
        final_warranty_risk="LOW",
        delivered_at=datetime.now(timezone.utc),
        warranty_eligible=True,
        warranty_expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        warranty_status="ELIGIBLE",
        delivery_summary="Delivered cleanly.",
    )
    db.add(customer)
    db.add(order)
    db.flush()
    db.add(
        OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=1,
            unit_price_vnd=12_000_000,
            cost_vnd=9_000_000,
        )
    )
    db.commit()
    return customer, order


def _seed_resale_source(db: Session, save_id: int) -> tuple[InventoryUnit, ResaleListing]:
    product = db.scalar(select(HardwareProduct).where(HardwareProduct.category == HardwareCategory.GPU))
    assert product is not None
    unit = InventoryUnit(
        save_game_id=save_id,
        product_id=product.id,
        condition_type=ConditionType.USED,
        status=InventoryStatus.READY_FOR_SALE,
        grade=Grade.A,
        inspection_confidence=92,
        purchase_price_vnd=6_000_000,
        hidden_condition_json={"overheat": True, "fan_noise": True},
    )
    db.add(unit)
    db.flush()
    listing = ResaleListing(
        save_game_id=save_id,
        inventory_unit_id=unit.id,
        title="Used GPU - Grade A",
        description="Clean resale unit.",
        asking_price_vnd=7_200_000,
        estimated_market_value_vnd=7_000_000,
        minimum_accept_price_vnd=6_600_000,
        status=ResaleListingStatus.SOLD,
        listing_quality_score=84,
        buyer_interest_score=66,
        market_multiplier_at_listing=1.0,
        grade_at_listing="A",
        inspection_confidence_at_listing=92,
        warranty_days_offered=30,
        created_on_day=1,
        sold_on_day=2,
        final_sale_price_vnd=7_100_000,
        notes="Sold cleanly.",
    )
    db.add(listing)
    db.flush()
    db.add(
        ResaleBuyerOffer(
            listing_id=listing.id,
            save_game_id=save_id,
            buyer_name="An",
            offer_price_vnd=7_100_000,
            status=ResaleBuyerOfferStatus.ACCEPTED,
            message="Looks good.",
            buyer_patience=60,
            buyer_strictness=40,
            created_on_day=2,
        )
    )
    db.commit()
    return unit, listing


def _seed_warranty_source(db: Session, save_id: int) -> WarrantyClaim:
    customer = Customer(
        save_game_id=save_id,
        name="RMA Customer",
        archetype=CustomerArchetype.BUSINESS,
        knowledge_level=KnowledgeLevel.MEDIUM,
        patience=55,
        negotiation_score=50,
        risk_tolerance=RiskTolerance.LOW,
    )
    db.add(customer)
    db.flush()
    claim = WarrantyClaim(
        save_game_id=save_id,
        customer_id=customer.id,
        claim_type=WarrantyClaimType.POWER_ISSUE,
        status=WarrantyClaimStatus.RESOLVED,
        claim_reason=WarrantyClaimReason.RANDOM_SHUTDOWN,
        title="Power issue",
        complaint_summary="System powers off unexpectedly.",
        severity=5,
        claimed_on_day=3,
        resolved_on_day=5,
        internal_risk_score=78,
        estimated_cost_vnd=1_200_000,
        final_cost_vnd=0,
        resolution_summary="Claim rejected after review.",
        resolution_type=WarrantyResolutionType.REJECT,
        warranty_valid=True,
    )
    db.add(claim)
    db.commit()
    return claim


def test_order_review_generation_is_idempotent_and_updates_reputation_once(client: TestClient) -> None:
    save_id = _create_save(client, "Order Review Save")
    db = _db()
    _, order = _seed_customer_and_order(db, save_id)

    response = client.post(
        f"/api/save-games/{save_id}/reviews/generate",
        json={"source_type": "ORDER_DELIVERY", "order_id": order.id},
    )
    assert response.status_code == 200
    review = response.json()
    assert review["source_type"] == "ORDER_DELIVERY"
    assert 1 <= review["rating"] <= 5
    assert "hidden_condition_json" not in review

    save_after_first = client.get(f"/api/save-games/{save_id}").json()
    first_reputation = save_after_first["reputation"]

    repeat = client.post(
        f"/api/save-games/{save_id}/reviews/generate",
        json={"source_type": "ORDER_DELIVERY", "order_id": order.id},
    )
    assert repeat.status_code == 200
    assert repeat.json()["id"] == review["id"]

    save_after_second = client.get(f"/api/save-games/{save_id}").json()
    assert save_after_second["reputation"] == first_reputation

    summary = client.get(f"/api/save-games/{save_id}/reputation/summary").json()
    assert summary["total_reviews"] == 1
    assert summary["positive_reviews"] + summary["neutral_reviews"] + summary["negative_reviews"] == 1
    assert summary["source_counts"]["ORDER_DELIVERY"] == 1


def test_resale_and_warranty_reviews_clamp_reputation_and_hide_sensitive_data(client: TestClient) -> None:
    save_id = _create_save(client, "Resale Warranty Save")
    db = _db()
    _, listing = _seed_resale_source(db, save_id)
    claim = _seed_warranty_source(db, save_id)

    save = db.get(SaveGame, save_id)
    assert save is not None
    save.reputation = 99
    db.commit()

    resale_response = client.post(
        f"/api/save-games/{save_id}/reviews/generate",
        json={"source_type": "RESALE_SALE", "resale_listing_id": listing.id},
    )
    assert resale_response.status_code == 200
    resale_review = resale_response.json()
    assert resale_review["customer_id"] is None
    assert "hidden_condition_json" not in resale_review

    save_after_resale = client.get(f"/api/save-games/{save_id}").json()
    assert save_after_resale["reputation"] == 100

    save.reputation = 1
    db.commit()

    warranty_response = client.post(
        f"/api/save-games/{save_id}/reviews/generate",
        json={"source_type": "WARRANTY_RMA", "warranty_claim_id": claim.id},
    )
    assert warranty_response.status_code == 200
    warranty_review = warranty_response.json()
    assert 1 <= warranty_review["rating"] <= 5
    assert warranty_review["customer_id"] is not None

    save_after_warranty = client.get(f"/api/save-games/{save_id}").json()
    assert save_after_warranty["reputation"] == 0

    summary = client.get(f"/api/save-games/{save_id}/reputation/summary").json()
    assert summary["total_reviews"] == 2
    assert summary["source_counts"]["RESALE_SALE"] == 1
    assert summary["source_counts"]["WARRANTY_RMA"] == 1
    assert summary["average_rating"] is not None
    assert summary["sentiment_counts"]["POSITIVE"] + summary["sentiment_counts"]["NEUTRAL"] + summary["sentiment_counts"]["NEGATIVE"] == 2


def test_review_generation_requires_profile_token_when_save_is_locked(client: TestClient) -> None:
    save_id = _create_save(client, "Locked Review Save")
    db = _db()
    _, order = _seed_customer_and_order(db, save_id)

    profile = client.post("/api/player-profiles", json={"display_name": "Locked Player", "pin": "2468"}).json()
    assign_response = client.post(f"/api/save-games/{save_id}/assign-profile", json={"profile_id": profile["id"]})
    assert assign_response.status_code == 200

    blocked = client.post(
        f"/api/save-games/{save_id}/reviews/generate",
        json={"source_type": "ORDER_DELIVERY", "order_id": order.id},
    )
    assert blocked.status_code == 403

    unlock = client.post(f"/api/player-profiles/{profile['id']}/unlock", json={"pin": "2468"})
    assert unlock.status_code == 200
    token = unlock.json()["token"]

    allowed = client.post(
        f"/api/save-games/{save_id}/reviews/generate",
        json={"source_type": "ORDER_DELIVERY", "order_id": order.id},
        headers={"X-Profile-Unlock-Token": token},
    )
    assert allowed.status_code == 200
    assert allowed.json()["source_type"] == "ORDER_DELIVERY"
