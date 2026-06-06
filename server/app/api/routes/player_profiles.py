from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.errors import forbidden, bad_request
from app.schemas.player_profile import (
    PlayerProfileRead,
    PlayerProfileCreate,
    ProfileUnlockPayload,
    ProfileUnlockResponse,
    ProfilePinPayload,
    ProfilePinDisablePayload,
)
from app.schemas.game import SaveGameRead
from app.services import player_profile_service


router = APIRouter(tags=["player profiles"])


class AssignProfilePayload(BaseModel):
    profile_id: int


@router.get("/api/player-profiles", response_model=list[PlayerProfileRead])
def list_profiles(db: Session = Depends(get_db)):
    return player_profile_service.list_profiles(db)


@router.post("/api/player-profiles", response_model=PlayerProfileRead)
def create_profile(payload: PlayerProfileCreate, db: Session = Depends(get_db)):
    return player_profile_service.create_profile(db, payload.display_name, payload.pin)


@router.get("/api/player-profiles/{profile_id}", response_model=PlayerProfileRead)
def get_profile(profile_id: int, db: Session = Depends(get_db)):
    return player_profile_service.get_profile(db, profile_id)


@router.post("/api/player-profiles/{profile_id}/unlock", response_model=ProfileUnlockResponse)
def unlock_profile(profile_id: int, payload: ProfileUnlockPayload, db: Session = Depends(get_db)):
    # Verify PIN
    success = player_profile_service.verify_profile_pin(db, profile_id, payload.pin)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid PIN")
        
    # Generate unlock session
    token, expires_at = player_profile_service.create_unlock_session(db, profile_id)
    return ProfileUnlockResponse(token=token, expires_at=expires_at)


@router.post("/api/player-profiles/{profile_id}/lock")
def lock_profile(
    profile_id: int,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db)
):
    if x_profile_unlock_token:
        player_profile_service.revoke_unlock_session(db, profile_id, x_profile_unlock_token)
    return {"message": "Profile locked successfully"}


@router.patch("/api/player-profiles/{profile_id}/pin", response_model=PlayerProfileRead)
def change_profile_pin(profile_id: int, payload: ProfilePinPayload, db: Session = Depends(get_db)):
    return player_profile_service.set_profile_pin(
        db, profile_id, payload.pin, payload.current_pin
    )


@router.delete("/api/player-profiles/{profile_id}/pin", response_model=PlayerProfileRead)
def disable_profile_pin(profile_id: int, payload: ProfilePinDisablePayload, db: Session = Depends(get_db)):
    return player_profile_service.disable_profile_pin(
        db, profile_id, payload.current_pin
    )


@router.post("/api/save-games/{save_game_id}/assign-profile", response_model=SaveGameRead)
def assign_profile(
    save_game_id: int,
    payload: AssignProfilePayload,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db)
):
    # If the save game is currently assigned to a profile, verify access first
    player_profile_service.require_profile_access(db, save_game_id, x_profile_unlock_token)
    return player_profile_service.attach_save_to_profile(db, save_game_id, payload.profile_id)
