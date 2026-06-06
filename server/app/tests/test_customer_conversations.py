from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.seed.initial_data import seed_database
from app.tests.test_profile_and_used_market import seed_test_brand_master


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


def _create_save(client: TestClient, name: str) -> int:
    response = client.post("/api/save-games", json={"name": name})
    assert response.status_code == 200
    return response.json()["id"]


def _conversation_id(request: dict[str, object]) -> int:
    assert request["conversation_id"] is not None
    return int(request["conversation_id"])


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    with testing_session_local() as db:
        seed_database(db)
        seed_test_brand_master(db)

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_customer_conversation_seed_and_idempotent_creation(client: TestClient) -> None:
    save_id = _create_save(client, "Chat Save")
    sample = client.post(f"/api/save-games/{save_id}/customers/generate-sample")
    assert sample.status_code == 200
    request = sample.json()["request"]
    conv_id = _conversation_id(request)

    detail = client.get(f"/api/save-games/{save_id}/customer-conversations/{conv_id}")
    assert detail.status_code == 200
    conversation = detail.json()
    assert conversation["id"] == conv_id
    assert len(conversation["messages"]) >= 3
    assert all("hidden_condition_json" not in str(message) for message in conversation["messages"])

    messages = client.get(f"/api/save-games/{save_id}/customer-conversations/{conv_id}/messages")
    assert messages.status_code == 200
    assert len(messages.json()) >= 3

    open_again = client.post(f"/api/save-games/{save_id}/customer-requests/{request['id']}/conversation")
    assert open_again.status_code == 200
    created = open_again.json()
    assert created["created"] is False
    assert created["conversation"]["id"] == conv_id

    state = client.get(f"/api/save-games/{save_id}/state")
    assert state.status_code == 200
    dashboard = state.json()
    assert dashboard["open_conversations_count"] >= 1
    assert dashboard["customers_needing_consultation_count"] >= 1
    assert len(dashboard["recent_conversation_messages"]) >= 1


def test_conversation_quick_reply_quote_and_staff_flow(client: TestClient) -> None:
    save_id = _create_save(client, "Conversation Workflow Save")
    sample = client.post(f"/api/save-games/{save_id}/customers/generate-sample")
    request = sample.json()["request"]
    conv_id = _conversation_id(request)

    quick = client.post(
        f"/api/save-games/{save_id}/customer-conversations/{conv_id}/quick-reply",
        json={"action_type": "ASK_USED_PARTS"},
    )
    assert quick.status_code == 200
    quick_data = quick.json()
    assert quick_data["stage"] == "DISCUSSING_USED_PARTS"
    assert 0 <= quick_data["conversion_probability"] <= 100

    candidate_res = client.post(f"/api/save-games/{save_id}/staff/candidates/generate?role=SALES&count=1")
    assert candidate_res.status_code == 200
    staff_candidate = candidate_res.json()[0]
    hire_res = client.post(f"/api/save-games/{save_id}/staff", json=_hire_payload(staff_candidate))
    assert hire_res.status_code == 200
    staff_id = hire_res.json()["id"]

    assign_res = client.post(
        f"/api/save-games/{save_id}/customer-conversations/{conv_id}/assign-staff",
        json={"staff_id": staff_id},
    )
    assert assign_res.status_code == 200
    assert assign_res.json()["assigned_staff_id"] == staff_id

    quote_res = client.post(f"/api/save-games/{save_id}/customer-requests/{request['id']}/generate-quote", json={})
    assert quote_res.status_code == 200
    quote_id = quote_res.json()["quote"]["id"]

    send_res = client.post(f"/api/save-games/{save_id}/customer-conversations/{conv_id}/send-quote/{quote_id}")
    assert send_res.status_code == 200
    send_data = send_res.json()
    assert send_data["message"]["message_type"] == "QUOTE_ATTACHMENT"
    assert 0 <= send_data["conversion_probability"] <= 100

    ready_res = client.post(f"/api/save-games/{save_id}/customer-conversations/{conv_id}/ready-to-order")
    assert ready_res.status_code == 200
    assert ready_res.json()["status"] == "READY_TO_ORDER"


def test_mutating_customer_conversation_routes_respect_profile_lock(client: TestClient) -> None:
    save_id = _create_save(client, "Locked Chat Save")
    sample = client.post(f"/api/save-games/{save_id}/customers/generate-sample")
    request = sample.json()["request"]
    conv_id = _conversation_id(request)

    profile = client.post("/api/player-profiles", json={"display_name": "Locked Player", "pin": "2468"})
    assert profile.status_code == 200
    assign_profile = client.post(f"/api/save-games/{save_id}/assign-profile", json={"profile_id": profile.json()["id"]})
    assert assign_profile.status_code == 200

    blocked = client.post(
        f"/api/save-games/{save_id}/customer-conversations/{conv_id}/messages",
        json={"body": "Hello from the showroom."},
    )
    assert blocked.status_code == 403

    unlock = client.post(f"/api/player-profiles/{profile.json()['id']}/unlock", json={"pin": "2468"})
    assert unlock.status_code == 200
    token = unlock.json()["token"]

    allowed = client.post(
        f"/api/save-games/{save_id}/customer-conversations/{conv_id}/messages",
        json={"body": "Hello from the showroom."},
        headers={"X-Profile-Unlock-Token": token},
    )
    assert allowed.status_code == 200
    assert allowed.json()["id"] == conv_id
