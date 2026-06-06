from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.models.enums import RefurbishActionType
from app.schemas.game import (
    RefurbishActionEstimateRead,
    InventoryRefurbishEventRead,
    RefurbishActionRunResponse,
    InventoryUnitRead,
    StaffAssistRequest,
)
from app.services import refurbish_service, player_profile_service

router = APIRouter(tags=["refurbish"])


@router.get("/api/save-games/{save_game_id}/inventory/{inventory_unit_id}/refurbish/actions", response_model=List[RefurbishActionEstimateRead])
def get_available_actions(
    save_game_id: int,
    inventory_unit_id: int,
    x_profile_unlock_token: Optional[str] = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db)
):
    player_profile_service.require_profile_access(db, save_game_id, x_profile_unlock_token)
    return refurbish_service.get_available_refurbish_actions(db, save_game_id, inventory_unit_id)


@router.post("/api/save-games/{save_game_id}/inventory/{inventory_unit_id}/refurbish/actions/{action_type}", response_model=RefurbishActionRunResponse)
def run_action(
    save_game_id: int,
    inventory_unit_id: int,
    action_type: RefurbishActionType,
    payload: StaffAssistRequest | None = None,
    x_profile_unlock_token: Optional[str] = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db)
):
    player_profile_service.require_profile_access(db, save_game_id, x_profile_unlock_token)
    event = refurbish_service.run_refurbish_action(
        db,
        save_game_id,
        inventory_unit_id,
        action_type,
        staff_id=payload.staff_id if payload else None,
    )
    # Re-fetch unit to reflect new status/grades/etc
    from app.services.inventory_service import get_inventory_unit
    unit = get_inventory_unit(db, save_game_id, inventory_unit_id)
    return {"event": event, "unit": unit}


@router.get("/api/save-games/{save_game_id}/inventory/{inventory_unit_id}/refurbish/events", response_model=List[InventoryRefurbishEventRead])
def list_unit_events(
    save_game_id: int,
    inventory_unit_id: int,
    x_profile_unlock_token: Optional[str] = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db)
):
    player_profile_service.require_profile_access(db, save_game_id, x_profile_unlock_token)
    return refurbish_service.list_refurbish_events(db, save_game_id, inventory_unit_id)


@router.get("/api/save-games/{save_game_id}/refurbish/events", response_model=List[InventoryRefurbishEventRead])
def list_all_events(
    save_game_id: int,
    x_profile_unlock_token: Optional[str] = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db)
):
    player_profile_service.require_profile_access(db, save_game_id, x_profile_unlock_token)
    return refurbish_service.list_refurbish_events(db, save_game_id)


@router.post("/api/save-games/{save_game_id}/inventory/{inventory_unit_id}/ready-for-resale", response_model=InventoryUnitRead)
def mark_ready(
    save_game_id: int,
    inventory_unit_id: int,
    x_profile_unlock_token: Optional[str] = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db)
):
    player_profile_service.require_profile_access(db, save_game_id, x_profile_unlock_token)
    return refurbish_service.mark_ready_for_resale(db, save_game_id, inventory_unit_id)


@router.delete("/api/save-games/{save_game_id}/inventory/{inventory_unit_id}/ready-for-resale", response_model=InventoryUnitRead)
def unmark_ready(
    save_game_id: int,
    inventory_unit_id: int,
    x_profile_unlock_token: Optional[str] = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db)
):
    player_profile_service.require_profile_access(db, save_game_id, x_profile_unlock_token)
    return refurbish_service.unmark_ready_for_resale(db, save_game_id, inventory_unit_id)
