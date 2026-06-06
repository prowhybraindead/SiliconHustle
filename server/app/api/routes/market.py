from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.schemas.market import MarketEventRead, MarketSummary, MarketEventCreate
from app.services import market_service

router = APIRouter(prefix="/api/save-games/{save_game_id}", tags=["market"])

@router.get("/market/events", response_model=List[MarketEventRead])
def list_market_events(
    save_game_id: int,
    active_only: bool = Query(False, description="Filter only active events"),
    db: Session = Depends(get_db)
):
    return market_service.list_market_events(db, save_game_id, active_only)

@router.get("/market/events/active", response_model=List[MarketEventRead])
def get_active_market_events(save_game_id: int, db: Session = Depends(get_db)):
    return market_service.get_active_market_events(db, save_game_id)

@router.post("/market/events/generate", response_model=MarketEventRead)
def generate_market_event(
    save_game_id: int,
    mode: str = Query("rule", description="Generation mode: rule | ai | auto"),
    db: Session = Depends(get_db)
):
    return market_service.generate_market_event(db, save_game_id, mode)

@router.post("/advance-day", response_model=MarketSummary)
def advance_market_day(save_game_id: int, db: Session = Depends(get_db)):
    return market_service.advance_market_day(db, save_game_id)

@router.get("/market/summary", response_model=MarketSummary)
def summarize_market_state(save_game_id: int, db: Session = Depends(get_db)):
    return market_service.summarize_market_state(db, save_game_id)

@router.post("/market/events", response_model=MarketEventRead)
def create_market_event(
    save_game_id: int,
    payload: MarketEventCreate,
    db: Session = Depends(get_db)
):
    return market_service.create_market_event(db, save_game_id, payload.model_dump())
