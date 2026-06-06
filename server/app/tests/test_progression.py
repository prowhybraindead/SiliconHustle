from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models.entities import SaveGame
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


def test_progression_catalog_and_purchase_updates_state(client: TestClient) -> None:
    res_save = client.post("/api/save-games", json={"name": "Progression Save"})
    assert res_save.status_code == 200
    save_id = res_save.json()["id"]

    res_catalog = client.get(f"/api/save-games/{save_id}/progression/upgrades")
    assert res_catalog.status_code == 200
    catalog = res_catalog.json()
    assert len(catalog) >= 18
    assert any(upgrade["category"] == "STAFF" for upgrade in catalog)
    assert any(upgrade["key"] == "STAFF_TRAINING_PROGRAM_I" for upgrade in catalog)

    res_state_before = client.get(f"/api/save-games/{save_id}/progression")
    assert res_state_before.status_code == 200
    state_before = res_state_before.json()
    assert state_before["purchased_upgrades"] == []
    assert state_before["summary"]["purchased_upgrades_count"] == 0

    res_purchase = client.post(f"/api/save-games/{save_id}/progression/upgrades/OPERATIONS_BOARD/purchase")
    assert res_purchase.status_code == 200
    payload = res_purchase.json()
    assert payload["cash_delta"] < 0
    assert payload["upgrade"]["upgrade_key"] == "OPERATIONS_BOARD"
    assert payload["progression"]["upgrade_effect_summary"]["dashboard_summary_bonus"] is True

    res_state_after = client.get(f"/api/save-games/{save_id}/progression")
    assert res_state_after.status_code == 200
    state_after = res_state_after.json()
    assert state_after["summary"]["purchased_upgrades_count"] == 1
    assert state_after["upgrade_effect_summary"]["dashboard_summary_bonus"] is True
    assert state_after["summary"]["dashboard_summary_bonus"] is True


def test_progression_purchase_validation_rules(client: TestClient) -> None:
    res_save = client.post("/api/save-games", json={"name": "Progression Rules"})
    assert res_save.status_code == 200
    save_id = res_save.json()["id"]

    res_locked = client.post(f"/api/save-games/{save_id}/progression/upgrades/ADVANCED_TEST_BENCH/purchase")
    assert res_locked.status_code == 400
    assert "Requires" in res_locked.json()["detail"]

    res_unknown = client.post(f"/api/save-games/{save_id}/progression/upgrades/NOT_A_REAL_UPGRADE/purchase")
    assert res_unknown.status_code == 404

    res_buy = client.post(f"/api/save-games/{save_id}/progression/upgrades/BASIC_DIAGNOSTIC_KIT/purchase")
    assert res_buy.status_code == 200

    res_buy_again = client.post(f"/api/save-games/{save_id}/progression/upgrades/BASIC_DIAGNOSTIC_KIT/purchase")
    assert res_buy_again.status_code == 400
    assert "fully purchased" in res_buy_again.json()["detail"]

    db = next(app.dependency_overrides[get_db]())
    save_game = db.get(SaveGame, save_id)
    assert save_game is not None
    save_game.cash = 0
    db.commit()

    res_no_cash = client.post(f"/api/save-games/{save_id}/progression/upgrades/REFURBISH_TOOLKIT_I/purchase")
    assert res_no_cash.status_code == 400
    assert "Not enough cash" in res_no_cash.json()["detail"]


def test_progression_purchase_respects_profile_lock_token(client: TestClient) -> None:
    res_profile = client.post("/api/player-profiles", json={"display_name": "Locked Player", "pin": "1234"})
    assert res_profile.status_code == 200
    profile_id = res_profile.json()["id"]

    res_save = client.post("/api/save-games", json={"name": "Locked Save"})
    assert res_save.status_code == 200
    save_id = res_save.json()["id"]

    res_assign = client.post(f"/api/save-games/{save_id}/assign-profile", json={"profile_id": profile_id})
    assert res_assign.status_code == 200

    res_locked = client.post(f"/api/save-games/{save_id}/progression/upgrades/OPERATIONS_BOARD/purchase")
    assert res_locked.status_code == 403
    assert "PIN lock" in res_locked.json()["detail"]

    res_unlock = client.post(f"/api/player-profiles/{profile_id}/unlock", json={"pin": "1234"})
    assert res_unlock.status_code == 200
    token = res_unlock.json()["token"]

    headers = {"X-Profile-Unlock-Token": token}
    res_purchase = client.post(
        f"/api/save-games/{save_id}/progression/upgrades/OPERATIONS_BOARD/purchase",
        headers=headers,
    )
    assert res_purchase.status_code == 200
