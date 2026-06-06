from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.schemas.game import AutosavePayload, DashboardState, SaveGameCreate, SaveGameRead
from app.services import save_game_service, player_profile_service

router = APIRouter(prefix="/api/save-games", tags=["save games"])


@router.get("", response_model=list[SaveGameRead])
def list_save_games(db: Session = Depends(get_db)):
    return save_game_service.list_save_games(db)


@router.post("", response_model=SaveGameRead)
def create_save_game(payload: SaveGameCreate, db: Session = Depends(get_db)):
    return save_game_service.create_save_game(db, payload.name)


@router.get("/{save_game_id}", response_model=SaveGameRead)
def get_save_game(
    save_game_id: int,
    x_profile_unlock_token: Optional[str] = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db)
):
    player_profile_service.require_profile_access(db, save_game_id, x_profile_unlock_token)
    return save_game_service.get_save_game(db, save_game_id)


@router.get("/{save_game_id}/state", response_model=DashboardState)
def get_state(
    save_game_id: int,
    x_profile_unlock_token: Optional[str] = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db)
):
    player_profile_service.require_profile_access(db, save_game_id, x_profile_unlock_token)
    return save_game_service.get_state(db, save_game_id)


@router.post("/{save_game_id}/autosave", response_model=SaveGameRead)
def autosave(
    save_game_id: int,
    payload: AutosavePayload,
    x_profile_unlock_token: Optional[str] = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db)
):
    player_profile_service.require_profile_access(db, save_game_id, x_profile_unlock_token)
    return save_game_service.autosave(db, save_game_id, payload.client_state_json)
