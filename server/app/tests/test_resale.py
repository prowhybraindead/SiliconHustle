from collections.abc import Generator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models.entities import HardwareProduct, SaveGame, InventoryUnit, ResaleListing, ResaleBuyerOffer, PlayerProfile
from app.models.enums import ConditionType, InventoryStatus, Grade, HardwareCategory, ResaleListingStatus, ResaleBuyerOfferStatus
from app.seed.initial_data import seed_database
from app.tests.test_profile_and_used_market import seed_test_brand_master
from app.services import player_profile_service


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


def test_resale_listing_creation_eligibility_and_ownership(client: TestClient) -> None:
    # 1. Create two save games
    res_save1 = client.post("/api/save-games", json={"name": "Save 1"})
    assert res_save1.status_code == 200
    save_id1 = res_save1.json()["id"]

    res_save2 = client.post("/api/save-games", json={"name": "Save 2"})
    assert res_save2.status_code == 200
    save_id2 = res_save2.json()["id"]

    db = next(app.dependency_overrides[get_db]())
    gpu_prod = db.scalar(select(HardwareProduct).where(HardwareProduct.category == HardwareCategory.GPU))
    assert gpu_prod is not None

    # Unit belonging to save 1, ready_for_resale = True
    unit_ready = InventoryUnit(
        save_game_id=save_id1,
        product_id=gpu_prod.id,
        condition_type=ConditionType.USED,
        status=InventoryStatus.UNTESTED,
        grade=Grade.B,
        inspection_confidence=80,
        purchase_price_vnd=2000000,
        ready_for_resale=True
    )
    # Unit belonging to save 1, NOT ready, low confidence
    unit_not_ready = InventoryUnit(
        save_game_id=save_id1,
        product_id=gpu_prod.id,
        condition_type=ConditionType.USED,
        status=InventoryStatus.UNTESTED,
        grade=Grade.UNKNOWN,
        inspection_confidence=10,
        purchase_price_vnd=1500000,
        ready_for_resale=False
    )
    # Unit belonging to save 2
    unit_save2 = InventoryUnit(
        save_game_id=save_id2,
        product_id=gpu_prod.id,
        condition_type=ConditionType.USED,
        status=InventoryStatus.UNTESTED,
        grade=Grade.B,
        inspection_confidence=80,
        purchase_price_vnd=2000000,
        ready_for_resale=True
    )
    db.add_all([unit_ready, unit_not_ready, unit_save2])
    db.commit()

    # Try listing unit from save 2 in save 1 context (Ownership block)
    res = client.post(f"/api/save-games/{save_id1}/resale/listings", json={
        "inventory_unit_id": unit_save2.id
    })
    assert res.status_code == 404

    # Try listing unit that is not eligible
    res = client.post(f"/api/save-games/{save_id1}/resale/listings", json={
        "inventory_unit_id": unit_not_ready.id
    })
    assert res.status_code == 400
    assert "not eligible" in res.json()["detail"]

    # List the eligible unit successfully
    res = client.post(f"/api/save-games/{save_id1}/resale/listings", json={
        "inventory_unit_id": unit_ready.id,
        "asking_price_vnd": 3000000,
        "warranty_days_offered": 90
    })
    assert res.status_code == 200
    data = res.json()
    assert data["title"].startswith("Used")
    assert data["asking_price_vnd"] == 3000000
    assert data["status"] == ResaleListingStatus.ACTIVE.value
    assert data["warranty_days_offered"] == 90
    assert "hidden_condition_json" not in data


def test_resale_listing_duplicate_protection(client: TestClient) -> None:
    res_save = client.post("/api/save-games", json={"name": "Save 1"})
    save_id = res_save.json()["id"]

    db = next(app.dependency_overrides[get_db]())
    gpu_prod = db.scalar(select(HardwareProduct).where(HardwareProduct.category == HardwareCategory.GPU))
    unit = InventoryUnit(
        save_game_id=save_id,
        product_id=gpu_prod.id,
        condition_type=ConditionType.USED,
        status=InventoryStatus.UNTESTED,
        grade=Grade.A,
        inspection_confidence=90,
        purchase_price_vnd=2000000,
        ready_for_resale=True
    )
    db.add(unit)
    db.commit()

    # Create first listing
    res1 = client.post(f"/api/save-games/{save_id}/resale/listings", json={"inventory_unit_id": unit.id})
    assert res1.status_code == 200

    # Try creating second active listing for same unit
    res2 = client.post(f"/api/save-games/{save_id}/resale/listings", json={"inventory_unit_id": unit.id})
    assert res2.status_code == 400
    assert "active resale listing already exists" in res2.json()["detail"]


def test_buyer_offer_generation_and_spam_protection(client: TestClient) -> None:
    res_save = client.post("/api/save-games", json={"name": "Save 1"})
    save_id = res_save.json()["id"]

    db = next(app.dependency_overrides[get_db]())
    gpu_prod = db.scalar(select(HardwareProduct).where(HardwareProduct.category == HardwareCategory.GPU))
    unit = InventoryUnit(
        save_game_id=save_id,
        product_id=gpu_prod.id,
        condition_type=ConditionType.USED,
        status=InventoryStatus.UNTESTED,
        grade=Grade.A,
        inspection_confidence=90,
        purchase_price_vnd=2000000,
        ready_for_resale=True
    )
    db.add(unit)
    db.commit()

    res_list = client.post(f"/api/save-games/{save_id}/resale/listings", json={"inventory_unit_id": unit.id})
    listing_id = res_list.json()["id"]

    # Generate 1st offer
    res_off1 = client.post(f"/api/save-games/{save_id}/resale/listings/{listing_id}/generate-offer")
    assert res_off1.status_code == 200
    offer1 = res_off1.json()["offer"]
    assert offer1["status"] == ResaleBuyerOfferStatus.PENDING.value
    assert offer1["buyer_name"] is not None
    assert offer1["offer_price_vnd"] > 0
    assert "hidden_condition_json" not in offer1

    # Listing status should become OFFER_RECEIVED
    assert res_off1.json()["listing"]["status"] == ResaleListingStatus.OFFER_RECEIVED.value

    # Generate 2nd and 3rd offers
    client.post(f"/api/save-games/{save_id}/resale/listings/{listing_id}/generate-offer")
    client.post(f"/api/save-games/{save_id}/resale/listings/{listing_id}/generate-offer")

    # Try generating 4th offer (should be blocked by spam protection)
    res_off4 = client.post(f"/api/save-games/{save_id}/resale/listings/{listing_id}/generate-offer")
    assert res_off4.status_code == 400
    assert "Spam protection" in res_off4.json()["detail"]


def test_cancel_resale_listing(client: TestClient) -> None:
    res_save = client.post("/api/save-games", json={"name": "Save 1"})
    save_id = res_save.json()["id"]

    db = next(app.dependency_overrides[get_db]())
    gpu_prod = db.scalar(select(HardwareProduct).where(HardwareProduct.category == HardwareCategory.GPU))
    unit = InventoryUnit(
        save_game_id=save_id,
        product_id=gpu_prod.id,
        condition_type=ConditionType.USED,
        status=InventoryStatus.UNTESTED,
        grade=Grade.A,
        inspection_confidence=90,
        purchase_price_vnd=2000000,
        ready_for_resale=True
    )
    db.add(unit)
    db.commit()

    res_list = client.post(f"/api/save-games/{save_id}/resale/listings", json={"inventory_unit_id": unit.id})
    listing_id = res_list.json()["id"]

    # Generate an offer
    res_off = client.post(f"/api/save-games/{save_id}/resale/listings/{listing_id}/generate-offer")
    offer_id = res_off.json()["offer"]["id"]

    # Cancel the listing
    res_cancel = client.delete(f"/api/save-games/{save_id}/resale/listings/{listing_id}")
    assert res_cancel.status_code == 200
    assert res_cancel.json()["status"] == ResaleListingStatus.CANCELLED.value

    # The offer should be marked EXPIRED
    db.expire_all()
    offer = db.get(ResaleBuyerOffer, offer_id)
    assert offer.status == ResaleBuyerOfferStatus.EXPIRED


def test_accept_offer_cash_and_inventory_sold(client: TestClient) -> None:
    res_save = client.post("/api/save-games", json={"name": "Save 1"})
    save_id = res_save.json()["id"]
    initial_cash = res_save.json()["cash"]

    db = next(app.dependency_overrides[get_db]())
    gpu_prod = db.scalar(select(HardwareProduct).where(HardwareProduct.category == HardwareCategory.GPU))
    unit = InventoryUnit(
        save_game_id=save_id,
        product_id=gpu_prod.id,
        condition_type=ConditionType.USED,
        status=InventoryStatus.UNTESTED,
        grade=Grade.A,
        inspection_confidence=90,
        purchase_price_vnd=2000000,
        ready_for_resale=True
    )
    db.add(unit)
    db.commit()

    res_list = client.post(f"/api/save-games/{save_id}/resale/listings", json={"inventory_unit_id": unit.id})
    listing_id = res_list.json()["id"]

    # Generate offer 1 and 2
    res_off1 = client.post(f"/api/save-games/{save_id}/resale/listings/{listing_id}/generate-offer")
    offer_id1 = res_off1.json()["offer"]["id"]
    offer_price1 = res_off1.json()["offer"]["offer_price_vnd"]

    res_off2 = client.post(f"/api/save-games/{save_id}/resale/listings/{listing_id}/generate-offer")
    offer_id2 = res_off2.json()["offer"]["id"]

    # Accept offer 1
    res_accept = client.post(f"/api/save-games/{save_id}/resale/offers/{offer_id1}/accept")
    assert res_accept.status_code == 200
    accept_data = res_accept.json()
    assert accept_data["offer"]["status"] == ResaleBuyerOfferStatus.ACCEPTED.value
    assert accept_data["listing"]["status"] == ResaleListingStatus.SOLD.value
    assert accept_data["cash_after_sale"] == initial_cash + offer_price1

    db.expire_all()
    # Inventory unit must be SOLD
    assert unit.status == InventoryStatus.SOLD
    # Other offer must be EXPIRED
    offer2 = db.get(ResaleBuyerOffer, offer_id2)
    assert offer2.status == ResaleBuyerOfferStatus.EXPIRED


def test_double_accept_offer_blocked(client: TestClient) -> None:
    res_save = client.post("/api/save-games", json={"name": "Save 1"})
    save_id = res_save.json()["id"]

    db = next(app.dependency_overrides[get_db]())
    gpu_prod = db.scalar(select(HardwareProduct).where(HardwareProduct.category == HardwareCategory.GPU))
    unit = InventoryUnit(
        save_game_id=save_id,
        product_id=gpu_prod.id,
        condition_type=ConditionType.USED,
        status=InventoryStatus.UNTESTED,
        grade=Grade.A,
        inspection_confidence=90,
        purchase_price_vnd=2000000,
        ready_for_resale=True
    )
    db.add(unit)
    db.commit()

    res_list = client.post(f"/api/save-games/{save_id}/resale/listings", json={"inventory_unit_id": unit.id})
    listing_id = res_list.json()["id"]

    res_off = client.post(f"/api/save-games/{save_id}/resale/listings/{listing_id}/generate-offer")
    offer_id = res_off.json()["offer"]["id"]

    # Accept the offer
    res_accept1 = client.post(f"/api/save-games/{save_id}/resale/offers/{offer_id}/accept")
    assert res_accept1.status_code == 200

    # Accept again (should fail)
    res_accept2 = client.post(f"/api/save-games/{save_id}/resale/offers/{offer_id}/accept")
    assert res_accept2.status_code == 400


def test_resale_responses_secrecy(client: TestClient) -> None:
    res_save = client.post("/api/save-games", json={"name": "Save 1"})
    save_id = res_save.json()["id"]

    db = next(app.dependency_overrides[get_db]())
    gpu_prod = db.scalar(select(HardwareProduct).where(HardwareProduct.category == HardwareCategory.GPU))
    unit = InventoryUnit(
        save_game_id=save_id,
        product_id=gpu_prod.id,
        condition_type=ConditionType.USED,
        status=InventoryStatus.UNTESTED,
        grade=Grade.A,
        inspection_confidence=90,
        purchase_price_vnd=2000000,
        ready_for_resale=True,
        hidden_condition_json={"true_health": 98}
    )
    db.add(unit)
    db.commit()

    # List unit
    res_list = client.post(f"/api/save-games/{save_id}/resale/listings", json={"inventory_unit_id": unit.id})
    data_list = res_list.json()
    assert "hidden_condition_json" not in data_list
    if data_list.get("inventory_unit"):
        assert "hidden_condition_json" not in data_list["inventory_unit"]

    # Get listing details
    listing_id = data_list["id"]
    res_detail = client.get(f"/api/save-games/{save_id}/resale/listings/{listing_id}")
    data_detail = res_detail.json()
    assert "hidden_condition_json" not in data_detail
    if data_detail.get("inventory_unit"):
        assert "hidden_condition_json" not in data_detail["inventory_unit"]

    # Generate offer
    res_off = client.post(f"/api/save-games/{save_id}/resale/listings/{listing_id}/generate-offer")
    data_off = res_off.json()
    assert "hidden_condition_json" not in data_off["offer"]
    assert "hidden_condition_json" not in data_off["listing"]

    # Accept offer
    offer_id = data_off["offer"]["id"]
    res_accept = client.post(f"/api/save-games/{save_id}/resale/offers/{offer_id}/accept")
    data_accept = res_accept.json()
    assert "hidden_condition_json" not in data_accept["offer"]
    assert "hidden_condition_json" not in data_accept["listing"]


def test_profile_pin_token_lock_mutations(client: TestClient) -> None:
    # 1. Create player profile and lock it
    res_prof = client.post("/api/player-profiles", json={"display_name": "Test Prof", "pin": "1234"})
    assert res_prof.status_code == 200
    profile_id = res_prof.json()["id"]

    res_save = client.post("/api/save-games", json={"name": "Locked Save"})
    save_id = res_save.json()["id"]

    # Associate profile to save
    db = next(app.dependency_overrides[get_db]())
    save_game = db.get(SaveGame, save_id)
    save_game.player_profile_id = profile_id
    save_game.pin_required = True
    db.commit()

    gpu_prod = db.scalar(select(HardwareProduct).where(HardwareProduct.category == HardwareCategory.GPU))
    unit = InventoryUnit(
        save_game_id=save_id,
        product_id=gpu_prod.id,
        condition_type=ConditionType.USED,
        status=InventoryStatus.UNTESTED,
        grade=Grade.A,
        inspection_confidence=90,
        purchase_price_vnd=2000000,
        ready_for_resale=True
    )
    db.add(unit)
    db.commit()
    db.close()

    # Mutation without X-Profile-Unlock-Token should fail with 403 Forbidden
    res_list = client.post(f"/api/save-games/{save_id}/resale/listings", json={"inventory_unit_id": unit.id})
    assert res_list.status_code == 403

    # Unlock the profile to get a token
    res_unlock = client.post(f"/api/player-profiles/{profile_id}/unlock", json={"pin": "1234"})
    assert res_unlock.status_code == 200
    token = res_unlock.json()["token"]

    # Mutation with X-Profile-Unlock-Token should succeed
    res_list_ok = client.post(
        f"/api/save-games/{save_id}/resale/listings",
        json={"inventory_unit_id": unit.id},
        headers={"X-Profile-Unlock-Token": token}
    )
    assert res_list_ok.status_code == 200
