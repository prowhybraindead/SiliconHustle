from collections.abc import Generator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models.entities import Brand, BrandCategory, HardwareProduct, SaveGame, InventoryUnit
from app.models.enums import ConditionType, InventoryStatus, Grade, HardwareCategory, RefurbishActionType, BrandCategoryName, BrandType, MarketTier
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


def test_refurbish_bench_actions_applicability_and_secrecy(client: TestClient) -> None:
    # 1. Create a Save Game
    res_save = client.post("/api/save-games", json={"name": "Refurbish Save"})
    assert res_save.status_code == 200
    save_id = res_save.json()["id"]

    # 2. Get a GPU and CPU product from the seeded catalog
    db = next(app.dependency_overrides[get_db]())
    gpu_prod = db.scalar(select(HardwareProduct).where(HardwareProduct.category == HardwareCategory.GPU))
    cpu_prod = db.scalar(select(HardwareProduct).where(HardwareProduct.category == HardwareCategory.CPU))
    
    assert gpu_prod is not None
    assert cpu_prod is not None

    # Create used inventory units for test
    gpu_unit = InventoryUnit(
        save_game_id=save_id,
        product_id=gpu_prod.id,
        condition_type=ConditionType.USED,
        status=InventoryStatus.UNTESTED,
        grade=Grade.UNKNOWN,
        inspection_confidence=0,
        purchase_price_vnd=2000000,
        hidden_condition_json={
            "true_health": 60,
            "true_performance": 65,
            "true_thermal": 55,
            "true_fan": 50,
            "true_stability": 58,
            "true_vram": 62,
            "previous_usage": "MINING",
            "hidden_defect": "FAN_WEAR",
            "dust_level": 80,
            "warranty_risk": "MEDIUM",
            "repair_history": "NONE"
        }
    )
    cpu_unit = InventoryUnit(
        save_game_id=save_id,
        product_id=cpu_prod.id,
        condition_type=ConditionType.USED,
        status=InventoryStatus.UNTESTED,
        grade=Grade.UNKNOWN,
        inspection_confidence=0,
        purchase_price_vnd=1500000,
        hidden_condition_json={
            "true_health": 75,
            "true_performance": 78,
            "true_thermal": 70,
            "true_fan": 100,
            "true_stability": 72,
            "true_vram": 100,
            "previous_usage": "GAMING",
            "hidden_defect": "NONE",
            "dust_level": 20,
            "warranty_risk": "LOW",
            "repair_history": "NONE"
        }
    )
    db.add(gpu_unit)
    db.add(cpu_unit)
    db.commit()
    db.refresh(gpu_unit)
    db.refresh(cpu_unit)

    # 3. Retrieve available refurbish actions for GPU
    res_actions = client.get(f"/api/save-games/{save_id}/inventory/{gpu_unit.id}/refurbish/actions")
    assert res_actions.status_code == 200
    actions = res_actions.json()
    
    # REPASTE should be applicable to GPU
    repaste_action = next(a for a in actions if a["action_type"] == "REPASTE")
    assert repaste_action["applicable"] is True

    # REPLACE_THERMAL_PADS should be applicable to GPU
    pads_action = next(a for a in actions if a["action_type"] == "REPLACE_THERMAL_PADS")
    assert pads_action["applicable"] is True

    # Retrieve available refurbish actions for CPU
    res_cpu_actions = client.get(f"/api/save-games/{save_id}/inventory/{cpu_unit.id}/refurbish/actions")
    assert res_cpu_actions.status_code == 200
    cpu_actions = res_cpu_actions.json()

    # REPLACE_THERMAL_PADS should NOT be applicable to CPU (only GPU, STORAGE, SSD, COOLER)
    cpu_pads_action = next(a for a in cpu_actions if a["action_type"] == "REPLACE_THERMAL_PADS")
    assert cpu_pads_action["applicable"] is False
    assert cpu_pads_action["unavailable_reason"] != ""

    # 4. Try running a non-applicable action -> should fail
    res_run_fail = client.post(f"/api/save-games/{save_id}/inventory/{cpu_unit.id}/refurbish/actions/REPLACE_THERMAL_PADS")
    assert res_run_fail.status_code == 400
    assert "is not applicable" in res_run_fail.json()["detail"]

    # 5. Secrecy verification
    # List actions or get unit and ensure "hidden_condition_json", "true_health", etc. are NOT exposed
    res_unit = client.get(f"/api/save-games/{save_id}/inventory")
    res_inv_units = res_unit.json()
    assert len(res_inv_units) > 0
    res_inv_unit = res_inv_units[0]
    assert "hidden_condition_json" not in res_inv_unit
    assert "true_health" not in res_inv_unit
    assert "true_fan" not in res_inv_unit


def test_refurbish_execution_cash_deduction_and_event_reads(client: TestClient) -> None:
    res_save = client.post("/api/save-games", json={"name": "Execution Save"})
    save_id = res_save.json()["id"]

    db = next(app.dependency_overrides[get_db]())
    gpu_prod = db.scalar(select(HardwareProduct).where(HardwareProduct.category == HardwareCategory.GPU))

    gpu_unit = InventoryUnit(
        save_game_id=save_id,
        product_id=gpu_prod.id,
        condition_type=ConditionType.USED,
        status=InventoryStatus.UNTESTED,
        grade=Grade.UNKNOWN,
        inspection_confidence=0,
        purchase_price_vnd=2000000,
        hidden_condition_json={
            "true_health": 60,
            "true_performance": 65,
            "true_thermal": 55,
            "true_fan": 50,
            "true_stability": 58,
            "true_vram": 62,
            "previous_usage": "MINING",
            "hidden_defect": "FAN_WEAR",
            "dust_level": 80,
            "warranty_risk": "MEDIUM",
            "repair_history": "NONE"
        }
    )
    db.add(gpu_unit)
    db.commit()
    db.refresh(gpu_unit)

    # Check cash before action
    save_before = client.get(f"/api/save-games/{save_id}").json()
    cash_before = save_before["cash"]

    # Run CLEAN_DUST (cost: 50,000 VND)
    res_run = client.post(f"/api/save-games/{save_id}/inventory/{gpu_unit.id}/refurbish/actions/CLEAN_DUST")
    assert res_run.status_code == 200
    run_data = res_run.json()
    assert run_data["event"]["status"] == "COMPLETED"
    assert run_data["event"]["action_type"] == "CLEAN_DUST"
    assert run_data["event"]["cost_vnd"] == 50000

    # Ensure hidden condition fields are NOT exposed in the run response event or unit
    assert "hidden_condition_json" not in run_data["unit"]
    assert "hidden_condition_json" not in run_data["event"]["before_condition_json"]
    assert "hidden_condition_json" not in run_data["event"]["after_condition_json"]
    assert "true_health" not in run_data["event"]["before_condition_json"]
    assert "true_health" not in run_data["event"]["after_condition_json"]

    # Check cash after action (strictly deducted)
    save_after = client.get(f"/api/save-games/{save_id}").json()
    assert save_after["cash"] == cash_before - 50000

    # Read events list
    res_events = client.get(f"/api/save-games/{save_id}/refurbish/events")
    assert res_events.status_code == 200
    events = res_events.json()
    assert len(events) == 1
    assert events[0]["action_type"] == "CLEAN_DUST"
    assert "hidden_condition_json" not in events[0]["before_condition_json"]
    assert "hidden_condition_json" not in events[0]["after_condition_json"]

    # Test cash check: modify cash to 0 to test insufficient cash
    save_game_record = db.get(SaveGame, save_id)
    save_game_record.cash = 0
    db.commit()

    # Try running another action (e.g. REPASTE, cost 150,000 VND) -> should be blocked
    res_repaste_fail = client.post(f"/api/save-games/{save_id}/inventory/{gpu_unit.id}/refurbish/actions/REPASTE")
    assert res_repaste_fail.status_code == 400
    repaste_fail_msg = res_repaste_fail.json()["detail"]
    assert "Insufficient cash" in repaste_fail_msg


def test_refurbish_inventory_status_constraints_and_ready_for_resale(client: TestClient) -> None:
    res_save = client.post("/api/save-games", json={"name": "Status Save"})
    save_id = res_save.json()["id"]

    db = next(app.dependency_overrides[get_db]())
    gpu_prod = db.scalar(select(HardwareProduct).where(HardwareProduct.category == HardwareCategory.GPU))

    # Create a unit
    gpu_unit = InventoryUnit(
        save_game_id=save_id,
        product_id=gpu_prod.id,
        condition_type=ConditionType.USED,
        status=InventoryStatus.UNTESTED,
        grade=Grade.UNKNOWN,
        inspection_confidence=30,
        purchase_price_vnd=2000000,
        hidden_condition_json={
            "true_health": 85,
            "true_performance": 85,
            "true_thermal": 85,
            "true_fan": 85,
            "true_stability": 85,
            "true_vram": 85,
            "previous_usage": "GAMING",
            "hidden_defect": "NONE",
            "dust_level": 10,
            "warranty_risk": "LOW",
            "repair_history": "NONE"
        }
    )
    db.add(gpu_unit)
    db.commit()
    db.refresh(gpu_unit)

    # 1. Try marking ready-for-resale with low inspection confidence (30% < 60%) -> should fail
    res_ready_fail = client.post(f"/api/save-games/{save_id}/inventory/{gpu_unit.id}/ready-for-resale")
    assert res_ready_fail.status_code == 400
    assert "Inspection confidence is too low" in res_ready_fail.json()["detail"]

    # 2. Update confidence and grade to allow mark
    gpu_unit.inspection_confidence = 75
    gpu_unit.grade = Grade.B
    db.commit()

    # Mark ready-for-resale -> success
    res_ready_success = client.post(f"/api/save-games/{save_id}/inventory/{gpu_unit.id}/ready-for-resale")
    assert res_ready_success.status_code == 200
    unit_ready = res_ready_success.json()
    assert unit_ready["ready_for_resale"] is True
    assert unit_ready["status"] == "READY_FOR_SALE"

    # 3. Block refurbish on READY_FOR_SALE / SOLD / INSTALLED_IN_BUILD / RESERVED status
    res_refurbish_blocked = client.post(f"/api/save-games/{save_id}/inventory/{gpu_unit.id}/refurbish/actions/CLEAN_DUST")
    assert res_refurbish_blocked.status_code == 400
    assert "Cannot refurbish" in res_refurbish_blocked.json()["detail"]

    # 4. Unmark ready-for-resale -> success
    res_unmark = client.delete(f"/api/save-games/{save_id}/inventory/{gpu_unit.id}/ready-for-resale")
    assert res_unmark.status_code == 200
    unit_unmarked = res_unmark.json()
    assert unit_unmarked["ready_for_resale"] is False
    assert unit_unmarked["status"] != "READY_FOR_SALE"
