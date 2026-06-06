from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.schemas.used_market import UsedPartListingRead, UsedPartNegotiationRead, OfferPayload
from app.services import used_market_service, player_profile_service

router = APIRouter(tags=["used market"])


@router.get("/api/save-games/{save_game_id}/used-market/listings", response_model=List[UsedPartListingRead])
def list_listings(
    save_game_id: int,
    active_only: bool = True,
    x_profile_unlock_token: Optional[str] = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db)
):
    player_profile_service.require_profile_access(db, save_game_id, x_profile_unlock_token)
    used_market_service.expire_old_listings(db, save_game_id)
    return used_market_service.list_used_part_listings(db, save_game_id, active_only)


@router.post("/api/save-games/{save_game_id}/used-market/listings/generate", response_model=UsedPartListingRead)
def generate_listing(
    save_game_id: int,
    x_profile_unlock_token: Optional[str] = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db)
):
    player_profile_service.require_profile_access(db, save_game_id, x_profile_unlock_token)
    return used_market_service.generate_used_part_listing(db, save_game_id)


@router.post("/api/save-games/{save_game_id}/used-market/listings/generate-batch", response_model=List[UsedPartListingRead])
def generate_batch_listings(
    save_game_id: int,
    count: int = 5,
    x_profile_unlock_token: Optional[str] = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db)
):
    player_profile_service.require_profile_access(db, save_game_id, x_profile_unlock_token)
    return used_market_service.generate_batch_used_part_listings(db, save_game_id, count)


@router.get("/api/save-games/{save_game_id}/used-market/listings/{listing_id}", response_model=UsedPartListingRead)
def get_listing(
    save_game_id: int,
    listing_id: int,
    x_profile_unlock_token: Optional[str] = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db)
):
    player_profile_service.require_profile_access(db, save_game_id, x_profile_unlock_token)
    return used_market_service.get_used_part_listing(db, save_game_id, listing_id)


@router.post("/api/save-games/{save_game_id}/used-market/listings/{listing_id}/start-negotiation", response_model=UsedPartNegotiationRead)
def start_negotiation(
    save_game_id: int,
    listing_id: int,
    x_profile_unlock_token: Optional[str] = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db)
):
    player_profile_service.require_profile_access(db, save_game_id, x_profile_unlock_token)
    return used_market_service.start_negotiation(db, save_game_id, listing_id)


@router.post("/api/save-games/{save_game_id}/used-market/negotiations/{negotiation_id}/offer", response_model=UsedPartNegotiationRead)
def submit_offer(
    save_game_id: int,
    negotiation_id: int,
    payload: OfferPayload,
    x_profile_unlock_token: Optional[str] = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db)
):
    player_profile_service.require_profile_access(db, save_game_id, x_profile_unlock_token)
    return used_market_service.submit_offer(db, save_game_id, negotiation_id, payload.offer_vnd, payload.message)


@router.post("/api/save-games/{save_game_id}/used-market/listings/{listing_id}/accept", response_model=UsedPartListingRead)
def accept_listing(
    save_game_id: int,
    listing_id: int,
    final_price_vnd: Optional[int] = None,
    x_profile_unlock_token: Optional[str] = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db)
):
    player_profile_service.require_profile_access(db, save_game_id, x_profile_unlock_token)
    return used_market_service.accept_listing(db, save_game_id, listing_id, final_price_vnd)


@router.post("/api/save-games/{save_game_id}/used-market/listings/{listing_id}/reject", response_model=UsedPartListingRead)
def reject_listing(
    save_game_id: int,
    listing_id: int,
    x_profile_unlock_token: Optional[str] = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db)
):
    player_profile_service.require_profile_access(db, save_game_id, x_profile_unlock_token)
    return used_market_service.reject_listing(db, save_game_id, listing_id)
