from collections.abc import Generator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import datetime, timezone, timedelta

from app.core.database import Base, get_db
from app.main import app
from app.models.entities import Brand, BrandCategory, HardwareProduct, SaveGame, PlayerProfile, UsedPartListing
from app.models.enums import UsedPartListingStatus, UsedPartNegotiationStatus, ConditionType, InventoryStatus, BrandCategoryName, BrandType, MarketTier
from app.seed.initial_data import seed_database
from app.services import player_profile_service, used_market_service, test_bench_service


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


def test_player_profile_crud_and_pin_lockout(client: TestClient) -> None:
    # 1. Create Profile
    res = client.post("/api/player-profiles", json={"display_name": "Gamer Pro", "pin": "1234"})
    assert res.status_code == 200
    profile = res.json()
    assert profile["display_name"] == "Gamer Pro"
    assert profile["pin_enabled"] is True
    assert "pin_hash" not in profile  # Expose safety check
    assert "pin_salt" not in profile
    
    profile_id = profile["id"]
    
    # 2. Unlock profile - fail attempts
    for i in range(4):
        res_fail = client.post(f"/api/player-profiles/{profile_id}/unlock", json={"pin": "0000"})
        assert res_fail.status_code == 400
        assert res_fail.json()["detail"] == "Invalid PIN"
        
    # Check it is not locked yet (attempts = 4)
    res_get = client.get(f"/api/player-profiles/{profile_id}")
    assert res_get.json()["failed_unlock_attempts"] == 4
    assert res_get.json()["locked_until"] is None
    
    # 5th failure -> Locks profile
    res_fail_5 = client.post(f"/api/player-profiles/{profile_id}/unlock", json={"pin": "0000"})
    assert res_fail_5.status_code == 400
    
    # 6th attempt should return 403 Forbidden due to lockout
    res_locked = client.post(f"/api/player-profiles/{profile_id}/unlock", json={"pin": "1234"})
    assert res_locked.status_code == 403
    assert "Profile temporarily locked" in res_locked.json()["detail"]


def test_save_game_profile_access_protection(client: TestClient) -> None:
    # Create save game
    res_save = client.post("/api/save-games", json={"name": "Save 1"})
    assert res_save.status_code == 200
    save_id = res_save.json()["id"]
    
    # Save is accessible with no profile
    res_get = client.get(f"/api/save-games/{save_id}")
    assert res_get.status_code == 200
    
    # Create profile
    res_prof = client.post("/api/player-profiles", json={"display_name": "User 1", "pin": "9999"})
    profile_id = res_prof.json()["id"]
    
    # Assign save to profile
    res_assign = client.post(f"/api/save-games/{save_id}/assign-profile", json={"profile_id": profile_id})
    assert res_assign.status_code == 200
    
    # Save now requires X-Profile-Unlock-Token header
    res_unauthorized = client.get(f"/api/save-games/{save_id}")
    assert res_unauthorized.status_code == 403
    assert "PIN lock is enabled" in res_unauthorized.json()["detail"]
    
    # Unlock profile to get token
    res_unlock = client.post(f"/api/player-profiles/{profile_id}/unlock", json={"pin": "9999"})
    assert res_unlock.status_code == 200
    token = res_unlock.json()["token"]
    
    # Access with valid token header
    headers = {"X-Profile-Unlock-Token": token}
    res_authorized = client.get(f"/api/save-games/{save_id}", headers=headers)
    assert res_authorized.status_code == 200
    
    # Access state with valid token header
    res_state = client.get(f"/api/save-games/{save_id}/state", headers=headers)
    assert res_state.status_code == 200
    assert "used_market_summary" in res_state.json()


def test_used_market_listings_clamping_and_negotiation(client: TestClient) -> None:
    res_save = client.post("/api/save-games", json={"name": "Market Save"})
    save_id = res_save.json()["id"]
    
    # Generate listings
    res_gen = client.post(f"/api/save-games/{save_id}/used-market/listings/generate")
    assert res_gen.status_code == 200
    listing = res_gen.json()
    
    # Clamping assertions
    assert listing["estimated_fair_value_vnd"] >= 100000
    assert listing["asking_price_vnd"] >= 50000
    assert listing["min_accept_price_vnd"] <= listing["asking_price_vnd"]
    assert "hidden_condition_json" not in listing # Verify not exposed!
    
    listing_id = listing["id"]
    
    # Start negotiation
    res_neg = client.post(f"/api/save-games/{save_id}/used-market/listings/{listing_id}/start-negotiation")
    assert res_neg.status_code == 200
    neg = res_neg.json()
    assert neg["status"] == "OPEN"
    assert len(neg["messages"]) == 2
    
    neg_id = neg["id"]
    
    # Offer validation (negative amount rejected)
    res_bad_offer = client.post(
        f"/api/save-games/{save_id}/used-market/negotiations/{neg_id}/offer",
        json={"offer_vnd": -500}
    )
    assert res_bad_offer.status_code == 422  # Pydantic validation validation gt=0
    
    # Low offer (increases patience loss, counter-offered)
    res_low = client.post(
        f"/api/save-games/{save_id}/used-market/negotiations/{neg_id}/offer",
        json={"offer_vnd": 10000}
    )
    assert res_low.status_code == 200
    neg_after = res_low.json()
    assert neg_after["rounds_count"] == 1
    
    # High offer to trigger accept
    res_high = client.post(
        f"/api/save-games/{save_id}/used-market/negotiations/{neg_id}/offer",
        json={"offer_vnd": listing["asking_price_vnd"]}
    )
    assert res_high.status_code == 200
    neg_accepted = res_high.json()
    assert neg_accepted["status"] == "ACCEPTED"
    assert neg_accepted["accepted_price_vnd"] == listing["asking_price_vnd"]


def test_used_market_accept_listing_and_test_bench(client: TestClient) -> None:
    # We will test accepting a listing and receiving it into inventory
    res_save = client.post("/api/save-games", json={"name": "Accept Save"})
    save_id = res_save.json()["id"]
    
    # Create listing
    res_gen = client.post(f"/api/save-games/{save_id}/used-market/listings/generate")
    listing = res_gen.json()
    listing_id = listing["id"]
    
    # Check cash before
    save_before = client.get(f"/api/save-games/{save_id}").json()
    cash_before = save_before["cash"]
    
    # Accept listing
    res_accept = client.post(f"/api/save-games/{save_id}/used-market/listings/{listing_id}/accept")
    assert res_accept.status_code == 200
    accepted = res_accept.json()
    assert accepted["status"] == "ACCEPTED"
    
    # Verify cash deducted
    save_after = client.get(f"/api/save-games/{save_id}").json()
    assert save_after["cash"] == cash_before - listing["asking_price_vnd"]
    
    # Verify inventory unit created
    res_inv = client.get(f"/api/save-games/{save_id}/inventory")
    inventory = res_inv.json()
    assert len(inventory) == 1
    unit = inventory[0]
    assert unit["condition_type"] == "USED"
    assert unit["status"] == "UNTESTED"
    assert unit["purchase_price_vnd"] == listing["asking_price_vnd"]
    assert unit["source"] == "USED_MARKET"
    assert "hidden_condition_json" not in unit # Verify not exposed!
    
    # Try accepting again -> should be blocked
    res_accept_again = client.post(f"/api/save-games/{save_id}/used-market/listings/{listing_id}/accept")
    assert res_accept_again.status_code == 400
    
    # Test bench integration: Run test on the unit
    res_test = client.post(f"/api/save-games/{save_id}/inventory/{unit['id']}/tests/full-inspection")
    assert res_test.status_code == 200
    test_res = res_test.json()
    tested_unit = test_res["unit"]
    
    # Confirm it is basic inspected/revealed
    assert tested_unit["status"] in ["READY_FOR_SALE", "DEFECTIVE"]
    assert tested_unit["health_score"] is not None
    assert tested_unit["performance_score"] is not None
    assert tested_unit["stability_score"] is not None
