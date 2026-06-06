from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field

from app.schemas.game import OrmModel, HardwareProductRead
from app.models.enums import UsedPartListingStatus, UsedPartNegotiationStatus, NegotiationSender


class NegotiationMessageRead(OrmModel):
    id: int
    negotiation_id: int
    sender: NegotiationSender
    message: str
    offer_vnd: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class UsedPartNegotiationRead(OrmModel):
    id: int
    listing_id: int
    save_game_id: int
    status: UsedPartNegotiationStatus
    current_offer_vnd: Optional[int] = None
    last_seller_response: Optional[str] = None
    rounds_count: int
    accepted_price_vnd: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    messages: List[NegotiationMessageRead] = []


class UsedPartListingRead(OrmModel):
    id: int
    save_game_id: int
    seller_name: str
    product_id: int
    product: HardwareProductRead
    asking_price_vnd: int
    estimated_fair_value_vnd: int
    min_accept_price_vnd: int
    status: UsedPartListingStatus
    seller_honesty: int
    seller_patience: int
    claimed_condition: Optional[str] = None
    claimed_usage: Optional[str] = None
    claimed_warranty_months: Optional[int] = None
    visible_condition_grade: Optional[str] = None
    risk_score: int
    market_multiplier_at_creation: float
    created_on_day: int
    expires_on_day: int
    final_price_vnd: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class OfferPayload(BaseModel):
    offer_vnd: int = Field(..., gt=0)
    message: Optional[str] = Field(None, max_length=500)
