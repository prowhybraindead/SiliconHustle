from typing import Optional

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.enums import WarrantyClaimStatus, WarrantyResolutionType
from app.schemas.game import (
    WarrantyClaimCreate,
    WarrantyClaimDetailRead,
    WarrantyClaimGenerateRequest,
    WarrantyClaimResolveRequest,
    WarrantyClaimResolveResponse,
    WarrantyClaimReviewRequest,
    WarrantyClaimSummary,
    WarrantyDiagnosisRequest,
    WarrantyEventRead,
    WarrantyRejectRequest,
    WarrantyResolutionRequest,
)
from app.services import player_profile_service, warranty_service

router = APIRouter(prefix="/api/save-games/{save_game_id}", tags=["warranty"])


def _detail(claim) -> dict[str, object]:
    return {
        "claim": claim,
        "claim_items": claim.items,
        "order": claim.order,
        "resale_listing": getattr(claim, "resale_listing", None),
        "events": claim.events,
    }


def _require_access(db: Session, save_game_id: int, token: str | None) -> None:
    player_profile_service.require_profile_access(db, save_game_id, token)


@router.get("/warranty/summary", response_model=WarrantyClaimSummary)
def warranty_summary(save_game_id: int, db: Session = Depends(get_db)):
    summary = warranty_service.summarize_warranty_state(db, save_game_id)
    recent_claims = warranty_service.list_warranty_claims(db, save_game_id)[:5]
    return {**summary, "recent_claims": recent_claims}


@router.get("/warranty/claims", response_model=list[WarrantyClaimDetailRead])
def list_claims(save_game_id: int, status: WarrantyClaimStatus | None = None, db: Session = Depends(get_db)):
    return [_detail(claim) for claim in warranty_service.list_warranty_claims(db, save_game_id, status=status)]


@router.post("/warranty/claims/generate", response_model=WarrantyClaimDetailRead)
def generate_claim(
    save_game_id: int,
    payload: WarrantyClaimGenerateRequest | None = None,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    _require_access(db, save_game_id, x_profile_unlock_token)
    if payload and (payload.order_id or payload.resale_listing_id or payload.inventory_unit_id):
        claim = warranty_service.generate_warranty_claim(
            db,
            save_game_id,
            payload.source_type,
            payload.order_id,
            payload.resale_listing_id,
            payload.inventory_unit_id,
        )
    elif payload and payload.source_type:
        claim = warranty_service.generate_warranty_claim(db, save_game_id, payload.source_type)
    else:
        claim = warranty_service.generate_random_warranty_claim(db, save_game_id)
    return _detail(claim)


@router.get("/warranty/claims/{claim_id}", response_model=WarrantyClaimDetailRead)
def get_claim(save_game_id: int, claim_id: int, db: Session = Depends(get_db)):
    return _detail(warranty_service.get_warranty_claim(db, save_game_id, claim_id))


@router.post("/warranty/claims/{claim_id}/review", response_model=WarrantyClaimDetailRead)
def review_claim(
    save_game_id: int,
    claim_id: int,
    payload: WarrantyClaimReviewRequest | None = None,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    _require_access(db, save_game_id, x_profile_unlock_token)
    return _detail(warranty_service.review_warranty_claim(db, save_game_id, claim_id, payload))


@router.post("/warranty/claims/{claim_id}/resolve", response_model=WarrantyClaimResolveResponse)
def resolve_claim(
    save_game_id: int,
    claim_id: int,
    payload: WarrantyClaimResolveRequest,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    _require_access(db, save_game_id, x_profile_unlock_token)
    claim = warranty_service.resolve_warranty_claim(db, save_game_id, claim_id, payload.resolution_type, payload.notes)
    return {
        "claim": claim,
        "cash_delta": -(claim.final_cost_vnd or 0) if payload.resolution_type != WarrantyResolutionType.REJECT else 0,
        "reputation_delta": claim.reputation_delta or 0,
    }


@router.get("/warranty-claims", response_model=list[WarrantyClaimDetailRead])
def list_warranty_claims(save_game_id: int, status: WarrantyClaimStatus | None = None, db: Session = Depends(get_db)):
    return [_detail(claim) for claim in warranty_service.list_warranty_claims(db, save_game_id, status=status)]


@router.get("/warranty-claims/{claim_id}", response_model=WarrantyClaimDetailRead)
def get_warranty_claim(save_game_id: int, claim_id: int, db: Session = Depends(get_db)):
    return _detail(warranty_service.get_warranty_claim(db, save_game_id, claim_id))


@router.post("/orders/{order_id}/warranty-claims", response_model=WarrantyClaimDetailRead)
def open_warranty_claim(
    save_game_id: int,
    order_id: int,
    payload: WarrantyClaimCreate,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    _require_access(db, save_game_id, x_profile_unlock_token)
    return _detail(warranty_service.create_warranty_claim_from_order(db, save_game_id, order_id, payload))


@router.post("/warranty-claims/{claim_id}/start-diagnosis", response_model=WarrantyClaimDetailRead)
def start_diagnosis(
    save_game_id: int,
    claim_id: int,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    _require_access(db, save_game_id, x_profile_unlock_token)
    return _detail(warranty_service.start_diagnosis(db, save_game_id, claim_id))


@router.post("/warranty-claims/{claim_id}/complete-diagnosis", response_model=WarrantyClaimDetailRead)
def complete_diagnosis(
    save_game_id: int,
    claim_id: int,
    payload: WarrantyDiagnosisRequest | None = None,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    _require_access(db, save_game_id, x_profile_unlock_token)
    return _detail(warranty_service.complete_diagnosis(db, save_game_id, claim_id, payload))


@router.post("/warranty-claims/{claim_id}/approve", response_model=WarrantyClaimDetailRead)
def approve_claim(
    save_game_id: int,
    claim_id: int,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    _require_access(db, save_game_id, x_profile_unlock_token)
    return _detail(warranty_service.approve_claim(db, save_game_id, claim_id))


@router.post("/warranty-claims/{claim_id}/reject", response_model=WarrantyClaimDetailRead)
def reject_claim(
    save_game_id: int,
    claim_id: int,
    payload: WarrantyRejectRequest | None = None,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    _require_access(db, save_game_id, x_profile_unlock_token)
    return _detail(warranty_service.reject_claim(db, save_game_id, claim_id, payload))


@router.post("/warranty-claims/{claim_id}/resolve/repair", response_model=WarrantyClaimDetailRead)
def resolve_repair(
    save_game_id: int,
    claim_id: int,
    payload: WarrantyResolutionRequest | None = None,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    _require_access(db, save_game_id, x_profile_unlock_token)
    return _detail(warranty_service.resolve_claim_repair(db, save_game_id, claim_id, payload))


@router.post("/warranty-claims/{claim_id}/resolve/replace", response_model=WarrantyClaimDetailRead)
def resolve_replace(
    save_game_id: int,
    claim_id: int,
    payload: WarrantyResolutionRequest | None = None,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    _require_access(db, save_game_id, x_profile_unlock_token)
    return _detail(warranty_service.resolve_claim_replace(db, save_game_id, claim_id, payload))


@router.post("/warranty-claims/{claim_id}/resolve/refund", response_model=WarrantyClaimDetailRead)
def resolve_refund(
    save_game_id: int,
    claim_id: int,
    payload: WarrantyResolutionRequest | None = None,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    _require_access(db, save_game_id, x_profile_unlock_token)
    return _detail(warranty_service.resolve_claim_refund(db, save_game_id, claim_id, payload))


@router.post("/warranty-claims/{claim_id}/resolve/rma", response_model=WarrantyClaimDetailRead)
def resolve_rma(
    save_game_id: int,
    claim_id: int,
    payload: WarrantyResolutionRequest | None = None,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    _require_access(db, save_game_id, x_profile_unlock_token)
    return _detail(warranty_service.resolve_claim_rma(db, save_game_id, claim_id, payload))


@router.post("/warranty-claims/{claim_id}/close", response_model=WarrantyClaimDetailRead)
def close_claim(
    save_game_id: int,
    claim_id: int,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    _require_access(db, save_game_id, x_profile_unlock_token)
    return _detail(warranty_service.close_claim(db, save_game_id, claim_id))


@router.get("/warranty-claims/{claim_id}/events", response_model=list[WarrantyEventRead])
def list_events(save_game_id: int, claim_id: int, db: Session = Depends(get_db)):
    return warranty_service.list_events(db, save_game_id, claim_id)
