from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.models.entities import SaveGame
from app.models.enums import ResaleListingStatus, ResaleBuyerOfferStatus
from app.schemas.game import (
    ResaleListingRead,
    ResaleBuyerOfferRead,
    ResaleListingCreate,
    ResaleOfferGenerateResponse,
    ResaleSaleResponse,
    StaffAssistRequest,
)
from app.services import resale_service, player_profile_service

router = APIRouter(tags=["resale"])


@router.get("/api/save-games/{save_game_id}/resale/listings", response_model=List[ResaleListingRead])
def list_listings(
    save_game_id: int,
    status: Optional[ResaleListingStatus] = None,
    x_profile_unlock_token: Optional[str] = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db)
):
    player_profile_service.require_profile_access(db, save_game_id, x_profile_unlock_token)
    return resale_service.list_resale_listings(db, save_game_id, status=status)


@router.post("/api/save-games/{save_game_id}/resale/listings", response_model=ResaleListingRead)
def create_listing(
    save_game_id: int,
    payload: ResaleListingCreate,
    x_profile_unlock_token: Optional[str] = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db)
):
    player_profile_service.require_profile_access(db, save_game_id, x_profile_unlock_token)
    return resale_service.create_resale_listing(
        db,
        save_game_id,
        inventory_unit_id=payload.inventory_unit_id,
        asking_price_vnd=payload.asking_price_vnd,
        warranty_days_offered=payload.warranty_days_offered,
    )


@router.get("/api/save-games/{save_game_id}/resale/listings/{listing_id}", response_model=ResaleListingRead)
def get_listing(
    save_game_id: int,
    listing_id: int,
    x_profile_unlock_token: Optional[str] = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db)
):
    player_profile_service.require_profile_access(db, save_game_id, x_profile_unlock_token)
    return resale_service.get_resale_listing(db, save_game_id, listing_id)


@router.delete("/api/save-games/{save_game_id}/resale/listings/{listing_id}", response_model=ResaleListingRead)
def cancel_listing(
    save_game_id: int,
    listing_id: int,
    x_profile_unlock_token: Optional[str] = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db)
):
    player_profile_service.require_profile_access(db, save_game_id, x_profile_unlock_token)
    return resale_service.cancel_resale_listing(db, save_game_id, listing_id)


@router.post("/api/save-games/{save_game_id}/resale/listings/{listing_id}/generate-offer", response_model=ResaleOfferGenerateResponse)
def generate_offer(
    save_game_id: int,
    listing_id: int,
    payload: StaffAssistRequest | None = None,
    x_profile_unlock_token: Optional[str] = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db)
):
    player_profile_service.require_profile_access(db, save_game_id, x_profile_unlock_token)
    offer = resale_service.generate_buyer_offer(db, save_game_id, listing_id, staff_id=payload.staff_id if payload else None)
    # Re-fetch listing to reflect updated status and offers relationship
    listing = resale_service.get_resale_listing(db, save_game_id, listing_id)
    return {"offer": offer, "listing": listing}


@router.get("/api/save-games/{save_game_id}/resale/offers", response_model=List[ResaleBuyerOfferRead])
def list_offers(
    save_game_id: int,
    listing_id: Optional[int] = None,
    status: Optional[ResaleBuyerOfferStatus] = None,
    x_profile_unlock_token: Optional[str] = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db)
):
    player_profile_service.require_profile_access(db, save_game_id, x_profile_unlock_token)
    offers = resale_service.list_buyer_offers(db, save_game_id, listing_id=listing_id)
    if status:
        offers = [o for o in offers if o.status == status]
    return offers


@router.post("/api/save-games/{save_game_id}/resale/offers/{offer_id}/accept", response_model=ResaleSaleResponse)
def accept_offer(
    save_game_id: int,
    offer_id: int,
    x_profile_unlock_token: Optional[str] = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db)
):
    player_profile_service.require_profile_access(db, save_game_id, x_profile_unlock_token)
    offer = resale_service.accept_buyer_offer(db, save_game_id, offer_id)
    listing = resale_service.get_resale_listing(db, save_game_id, offer.listing_id)
    save_game = db.get(SaveGame, save_game_id)
    return {
        "offer": offer,
        "listing": listing,
        "cash_after_sale": save_game.cash,
        "reputation_after_sale": save_game.reputation,
    }


@router.post("/api/save-games/{save_game_id}/resale/offers/{offer_id}/reject", response_model=ResaleBuyerOfferRead)
def reject_offer(
    save_game_id: int,
    offer_id: int,
    x_profile_unlock_token: Optional[str] = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db)
):
    player_profile_service.require_profile_access(db, save_game_id, x_profile_unlock_token)
    return resale_service.reject_buyer_offer(db, save_game_id, offer_id)
