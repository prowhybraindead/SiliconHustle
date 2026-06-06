from typing import Optional

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.enums import StaffRole, StaffStatus, StaffTaskType
from app.schemas.game import (
    StaffAssignRequest,
    StaffAssignResponse,
    StaffAssignmentLogRead,
    StaffCandidateRead,
    StaffMemberCreate,
    StaffMemberRead,
    StaffSummaryRead,
)
from app.services import player_profile_service, staff_service

router = APIRouter(prefix="/api/save-games/{save_game_id}/staff", tags=["staff"])


def _require_access(db: Session, save_game_id: int, token: str | None) -> None:
    player_profile_service.require_profile_access(db, save_game_id, token)


@router.get("", response_model=list[StaffMemberRead])
def list_staff(
    save_game_id: int,
    role: StaffRole | None = None,
    status: StaffStatus | None = None,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    _require_access(db, save_game_id, x_profile_unlock_token)
    return staff_service.list_staff(db, save_game_id, role=role, status=status)


@router.post("", response_model=StaffMemberRead)
def hire_staff(
    save_game_id: int,
    payload: StaffMemberCreate,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    _require_access(db, save_game_id, x_profile_unlock_token)
    return staff_service.hire_staff_member(db, save_game_id, payload)


@router.post("/candidates/generate", response_model=list[StaffCandidateRead])
def generate_candidates(
    save_game_id: int,
    role: StaffRole | None = None,
    count: int = 3,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    _require_access(db, save_game_id, x_profile_unlock_token)
    return staff_service.generate_staff_candidates(db, save_game_id, count=count, role=role)


@router.get("/summary", response_model=StaffSummaryRead)
def staff_summary(
    save_game_id: int,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    _require_access(db, save_game_id, x_profile_unlock_token)
    summary = staff_service.summarize_staff_state(db, save_game_id)
    return {key: value for key, value in summary.items() if key != "recent_assignments"}


@router.get("/assignments", response_model=list[StaffAssignmentLogRead])
def staff_assignments(
    save_game_id: int,
    limit: int = 20,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    _require_access(db, save_game_id, x_profile_unlock_token)
    return staff_service.list_staff_assignments(db, save_game_id, limit=limit)


@router.get("/{staff_id}", response_model=StaffMemberRead)
def get_staff(
    save_game_id: int,
    staff_id: int,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    _require_access(db, save_game_id, x_profile_unlock_token)
    return staff_service.get_staff_member(db, save_game_id, staff_id)


@router.delete("/{staff_id}", response_model=StaffMemberRead)
def fire_staff(
    save_game_id: int,
    staff_id: int,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    _require_access(db, save_game_id, x_profile_unlock_token)
    return staff_service.fire_staff_member(db, save_game_id, staff_id)


@router.post("/{staff_id}/assign", response_model=StaffAssignResponse)
def assign_staff(
    save_game_id: int,
    staff_id: int,
    payload: StaffAssignRequest,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    _require_access(db, save_game_id, x_profile_unlock_token)
    log = staff_service.assign_staff_to_task(
        db,
        save_game_id,
        staff_id,
        payload.task_type,
        payload.target_type,
        payload.target_id,
    )
    staff_member = staff_service.get_staff_member(db, save_game_id, staff_id)
    return {
        "staff_member": staff_member,
        "assignment_log": log,
        "effect_json": log.effect_json or {},
        "summary": log.result_summary or "",
    }
