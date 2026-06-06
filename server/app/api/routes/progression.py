from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.game import (
    ProgressionStateRead,
    ShopUpgradeDefinitionRead,
    ShopUpgradePurchaseResponse,
)
from app.services import player_profile_service, progression_service

router = APIRouter(prefix="/api/save-games/{save_game_id}", tags=["progression"])


def _require_access(db: Session, save_game_id: int, token: str | None) -> None:
    player_profile_service.require_profile_access(db, save_game_id, token)


@router.get("/progression", response_model=ProgressionStateRead)
def get_progression_state(
    save_game_id: int,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    _require_access(db, save_game_id, x_profile_unlock_token)
    return progression_service.get_progression_state(db, save_game_id)


@router.get("/progression/upgrades", response_model=list[ShopUpgradeDefinitionRead])
def list_progression_upgrades(
    save_game_id: int,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    _require_access(db, save_game_id, x_profile_unlock_token)
    return progression_service.list_progression_upgrades(db, save_game_id)


@router.post("/progression/upgrades/{upgrade_key}/purchase", response_model=ShopUpgradePurchaseResponse)
def purchase_progression_upgrade(
    save_game_id: int,
    upgrade_key: str,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    _require_access(db, save_game_id, x_profile_unlock_token)
    return progression_service.purchase_upgrade(db, save_game_id, upgrade_key)
