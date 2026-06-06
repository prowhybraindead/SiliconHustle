from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.game import CustomerReviewRead, ReputationSummaryRead, ReviewGenerateRequest
from app.services import player_profile_service, review_service

router = APIRouter(prefix="/api/save-games/{save_game_id}", tags=["reviews"])


def _require_access(db: Session, save_game_id: int, token: str | None) -> None:
    player_profile_service.require_profile_access(db, save_game_id, token)


@router.get("/reviews", response_model=list[CustomerReviewRead])
def list_reviews(
    save_game_id: int,
    source_type: str | None = None,
    sentiment: str | None = None,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    _require_access(db, save_game_id, x_profile_unlock_token)
    return review_service.list_reviews(db, save_game_id, source_type=source_type, sentiment=sentiment)


@router.get("/reviews/{review_id}", response_model=CustomerReviewRead)
def get_review(
    save_game_id: int,
    review_id: int,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    _require_access(db, save_game_id, x_profile_unlock_token)
    return review_service.get_review(db, save_game_id, review_id)


@router.get("/reputation/summary", response_model=ReputationSummaryRead)
def reputation_summary(
    save_game_id: int,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    _require_access(db, save_game_id, x_profile_unlock_token)
    return review_service.summarize_reputation(db, save_game_id)


@router.post("/reviews/generate", response_model=CustomerReviewRead)
def generate_review(
    save_game_id: int,
    payload: ReviewGenerateRequest | None = None,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    _require_access(db, save_game_id, x_profile_unlock_token)
    if payload is None:
        return review_service.generate_random_recent_review(db, save_game_id)
    return review_service.generate_review_from_source(
        db,
        save_game_id,
        payload.source_type,
        payload.order_id,
        payload.resale_listing_id,
        payload.warranty_claim_id,
    )


@router.post("/orders/{order_id}/generate-review", response_model=CustomerReviewRead)
def generate_order_review(
    save_game_id: int,
    order_id: int,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    _require_access(db, save_game_id, x_profile_unlock_token)
    return review_service.generate_review_from_order(db, save_game_id, order_id)


@router.post("/resale/listings/{listing_id}/generate-review", response_model=CustomerReviewRead)
def generate_resale_review(
    save_game_id: int,
    listing_id: int,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    _require_access(db, save_game_id, x_profile_unlock_token)
    return review_service.generate_review_from_resale(db, save_game_id, listing_id)


@router.post("/warranty/claims/{claim_id}/generate-review", response_model=CustomerReviewRead)
def generate_warranty_review(
    save_game_id: int,
    claim_id: int,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    _require_access(db, save_game_id, x_profile_unlock_token)
    return review_service.generate_review_from_warranty(db, save_game_id, claim_id)
