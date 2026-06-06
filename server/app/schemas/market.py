from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, Field
from app.models.enums import MarketEventType, MarketEventGenerationSource
from app.schemas.game import OrmModel

class MarketEventCreate(BaseModel):
    event_type: MarketEventType = MarketEventType.RANDOM_DEMAND_SPIKE
    title: str = Field(min_length=1, max_length=160)
    summary: str
    severity: int = Field(ge=1, le=5)
    affected_category: Optional[str] = None
    affected_brand_slug: Optional[str] = None
    affected_origin_code: Optional[str] = None
    affected_currency: Optional[str] = None
    affected_product_id: Optional[int] = None
    price_multiplier: float = Field(default=1.0, ge=0.35, le=3.5)
    demand_delta: int = Field(default=0, ge=-100, le=100)
    supply_delta: int = Field(default=0, ge=-100, le=100)
    reliability_delta: int = Field(default=0, ge=-100, le=100)
    quality_risk_delta: int = Field(default=0, ge=-100, le=100)
    starts_on_day: int
    ends_on_day: int
    is_active: bool = True

class MarketEventRead(OrmModel):
    id: int
    save_game_id: Optional[int] = None
    event_type: MarketEventType
    title: str
    summary: str
    severity: int
    affected_category: Optional[str] = None
    affected_brand_slug: Optional[str] = None
    affected_origin_code: Optional[str] = None
    affected_currency: Optional[str] = None
    affected_product_id: Optional[int] = None
    price_multiplier: float
    demand_delta: int
    supply_delta: int
    reliability_delta: int
    quality_risk_delta: int
    starts_on_day: int
    ends_on_day: int
    is_active: bool
    generation_source: MarketEventGenerationSource
    ai_prompt_context_json: Optional[dict] = None
    ai_raw_proposal_json: Optional[dict] = None
    raw_effect_json: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

class MarketSummary(BaseModel):
    active_market_events_count: int
    impacted_categories: List[str]
    impacted_brands: List[str]
    impacted_origins: List[str]
    strongest_market_multiplier: float
    recent_market_events: List[dict]
    market_pressure_summary: str
