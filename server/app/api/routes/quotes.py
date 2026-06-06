from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.game import QuoteAcceptRequest, QuoteCreate, QuoteDetailRead, QuoteGenerateRequest, QuoteUpdate, OrderRead
from app.services import quote_service

router = APIRouter(prefix="/api/save-games/{save_game_id}", tags=["quotes"])


def _detail(quote) -> dict[str, object]:
    return {
        "quote": quote,
        "quote_items": quote.items,
        "compatibility_result": getattr(quote, "compatibility_result", None),
    }


@router.get("/quotes", response_model=list[QuoteDetailRead])
def list_quotes(save_game_id: int, db: Session = Depends(get_db)):
    return [_detail(quote) for quote in quote_service.list_quotes(db, save_game_id)]


@router.post("/quotes", response_model=QuoteDetailRead)
def create_quote(save_game_id: int, payload: QuoteCreate, db: Session = Depends(get_db)):
    return _detail(quote_service.create_quote(db, save_game_id, payload))


@router.get("/quotes/{quote_id}", response_model=QuoteDetailRead)
def get_quote(save_game_id: int, quote_id: int, db: Session = Depends(get_db)):
    return _detail(quote_service.get_quote(db, save_game_id, quote_id))


@router.patch("/quotes/{quote_id}", response_model=QuoteDetailRead)
def update_quote(save_game_id: int, quote_id: int, payload: QuoteUpdate, db: Session = Depends(get_db)):
    return _detail(quote_service.update_quote(db, save_game_id, quote_id, payload))


@router.post("/customer-requests/{request_id}/generate-quote", response_model=QuoteDetailRead)
def generate_quote(save_game_id: int, request_id: int, payload: QuoteGenerateRequest | None = None, db: Session = Depends(get_db)):
    notes = payload.notes if payload else None
    return _detail(quote_service.generate_quote_from_customer_request(db, save_game_id, request_id, notes))


@router.post("/quotes/{quote_id}/reserve", response_model=QuoteDetailRead)
def reserve_quote(save_game_id: int, quote_id: int, db: Session = Depends(get_db)):
    return _detail(quote_service.reserve_quote_items(db, save_game_id, quote_id))


@router.post("/quotes/{quote_id}/release", response_model=QuoteDetailRead)
def release_quote(save_game_id: int, quote_id: int, db: Session = Depends(get_db)):
    return _detail(quote_service.release_quote_reservations(db, save_game_id, quote_id))


@router.post("/quotes/{quote_id}/reject", response_model=QuoteDetailRead)
def reject_quote(save_game_id: int, quote_id: int, db: Session = Depends(get_db)):
    return _detail(quote_service.delete_or_reject_quote(db, save_game_id, quote_id))


@router.post("/quotes/{quote_id}/accept", response_model=OrderRead)
def accept_quote(
    save_game_id: int,
    quote_id: int,
    payload: QuoteAcceptRequest | None = None,
    db: Session = Depends(get_db),
):
    return quote_service.accept_quote_to_order(db, save_game_id, quote_id)
