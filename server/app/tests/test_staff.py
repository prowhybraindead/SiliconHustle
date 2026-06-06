from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models.entities import HardwareProduct, InventoryUnit, SaveGame
from app.models.enums import ConditionType, Grade, HardwareCategory, InventoryStatus, StaffRole, StaffStatus
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


def _hire_payload(candidate: dict[str, object]) -> dict[str, object]:
    keys = [
        "name",
        "role",
        "status",
        "level",
        "xp",
        "salary_per_day_vnd",
        "morale",
        "fatigue",
        "traits_json",
        "sales_skill",
        "marketing_skill",
        "diagnostic_skill",
        "repair_skill",
        "procurement_skill",
        "support_skill",
        "market_skill",
        "speed",
        "carefulness",
        "hired_on_day",
        "last_assigned_on_day",
        "notes",
    ]
    return {key: candidate.get(key) for key in keys}


def test_staff_management_workflow_and_dashboard_state(client: TestClient) -> None:
    res_save = client.post("/api/save-games", json={"name": "Staff Save"})
    assert res_save.status_code == 200
    save_id = res_save.json()["id"]

    res_candidates = client.post(f"/api/save-games/{save_id}/staff/candidates/generate?role=SALES&count=2")
    assert res_candidates.status_code == 200
    candidates = res_candidates.json()
    assert len(candidates) == 2
    assert "preview_effects" in candidates[0]

    res_hire = client.post(f"/api/save-games/{save_id}/staff", json=_hire_payload(candidates[0]))
    assert res_hire.status_code == 200
    staff = res_hire.json()
    assert staff["name"] == candidates[0]["name"]
    assert staff["status"] == StaffStatus.AVAILABLE.value

    res_list = client.get(f"/api/save-games/{save_id}/staff")
    assert res_list.status_code == 200
    assert len(res_list.json()) == 1

    res_summary = client.get(f"/api/save-games/{save_id}/staff/summary")
    assert res_summary.status_code == 200
    summary = res_summary.json()
    assert summary["staff_count"] == 1
    assert summary["available_staff_count"] == 1
    assert summary["daily_salary_total_vnd"] > 0

    res_state = client.get(f"/api/save-games/{save_id}/state")
    assert res_state.status_code == 200
    state = res_state.json()
    assert state["staff_count"] == 1
    assert state["available_staff_count"] == 1
    assert state["staff_summary"]["staff_count"] == 1

    res_assign = client.post(
        f"/api/save-games/{save_id}/staff/{staff['id']}/assign",
        json={"task_type": "OPERATIONS"},
    )
    assert res_assign.status_code == 200
    assignment = res_assign.json()["assignment_log"]
    assert assignment["task_type"] == "OPERATIONS"
    assert assignment["xp_gained"] >= 0

    res_assignments = client.get(f"/api/save-games/{save_id}/staff/assignments")
    assert res_assignments.status_code == 200
    assert len(res_assignments.json()) == 1

    res_fire = client.delete(f"/api/save-games/{save_id}/staff/{staff['id']}")
    assert res_fire.status_code == 200
    assert res_fire.json()["status"] == StaffStatus.INACTIVE.value

    res_summary_after = client.get(f"/api/save-games/{save_id}/staff/summary")
    assert res_summary_after.status_code == 200
    summary_after = res_summary_after.json()
    assert summary_after["inactive_staff_count"] == 1
    assert summary_after["available_staff_count"] == 0


def test_staff_assists_refurbish_and_resale_workflows(client: TestClient) -> None:
    res_save = client.post("/api/save-games", json={"name": "Staff Assist Save"})
    assert res_save.status_code == 200
    save_id = res_save.json()["id"]

    db = next(app.dependency_overrides[get_db]())
    gpu_prod = db.scalar(select(HardwareProduct).where(HardwareProduct.category == HardwareCategory.GPU))
    assert gpu_prod is not None

    refurbish_unit = InventoryUnit(
        save_game_id=save_id,
        product_id=gpu_prod.id,
        condition_type=ConditionType.USED,
        status=InventoryStatus.UNTESTED,
        grade=Grade.UNKNOWN,
        inspection_confidence=0,
        purchase_price_vnd=2_000_000,
        hidden_condition_json={
            "true_health": 68,
            "true_performance": 70,
            "true_thermal": 58,
            "true_fan": 55,
            "true_stability": 60,
            "true_vram": 66,
            "previous_usage": "GAMING",
            "hidden_defect": "DUST",
            "dust_level": 80,
            "warranty_risk": "MEDIUM",
            "repair_history": "NONE",
        },
    )
    resale_unit = InventoryUnit(
        save_game_id=save_id,
        product_id=gpu_prod.id,
        condition_type=ConditionType.USED,
        status=InventoryStatus.UNTESTED,
        grade=Grade.B,
        inspection_confidence=80,
        purchase_price_vnd=2_200_000,
        ready_for_resale=True,
        hidden_condition_json={
            "true_health": 82,
            "true_performance": 80,
            "true_thermal": 78,
            "true_fan": 90,
            "true_stability": 79,
            "true_vram": 80,
            "previous_usage": "GAMING",
            "hidden_defect": "NONE",
            "dust_level": 20,
            "warranty_risk": "LOW",
            "repair_history": "NONE",
        },
    )
    db.add_all([refurbish_unit, resale_unit])
    db.commit()
    db.refresh(refurbish_unit)
    db.refresh(resale_unit)

    res_tech = client.post(f"/api/save-games/{save_id}/staff/candidates/generate?role=TECHNICIAN&count=1")
    tech_candidate = res_tech.json()[0]
    res_tech_hire = client.post(f"/api/save-games/{save_id}/staff", json=_hire_payload(tech_candidate))
    tech_staff_id = res_tech_hire.json()["id"]

    res_repair = client.post(
        f"/api/save-games/{save_id}/inventory/{refurbish_unit.id}/refurbish/actions/CLEAN_DUST",
        json={"staff_id": tech_staff_id},
    )
    assert res_repair.status_code == 200
    assert res_repair.json()["event"]["action_type"] == "CLEAN_DUST"

    res_sales = client.post(f"/api/save-games/{save_id}/staff/candidates/generate?role=SALES&count=1")
    sales_candidate = res_sales.json()[0]
    res_sales_hire = client.post(f"/api/save-games/{save_id}/staff", json=_hire_payload(sales_candidate))
    sales_staff_id = res_sales_hire.json()["id"]

    res_listing = client.post(
        f"/api/save-games/{save_id}/resale/listings",
        json={"inventory_unit_id": resale_unit.id, "asking_price_vnd": 3_500_000, "warranty_days_offered": 60},
    )
    assert res_listing.status_code == 200
    listing_id = res_listing.json()["id"]

    res_offer = client.post(
        f"/api/save-games/{save_id}/resale/listings/{listing_id}/generate-offer",
        json={"staff_id": sales_staff_id},
    )
    assert res_offer.status_code == 200
    assert len(res_offer.json()["listing"]["offers"]) == 1

    res_assignments = client.get(f"/api/save-games/{save_id}/staff/assignments")
    assert res_assignments.status_code == 200
    tasks = {entry["task_type"] for entry in res_assignments.json()}
    assert "REFURBISH" in tasks
    assert "RESALE" in tasks
