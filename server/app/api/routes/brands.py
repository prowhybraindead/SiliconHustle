from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.enums import BrandCategoryName, BrandType, MarketTier
from app.schemas.game import BrandRead
from app.services import brand_service

router = APIRouter(prefix="/api/brands", tags=["brands"])


@router.get("", response_model=list[BrandRead])
def list_brands(
    category: BrandCategoryName | None = None,
    q: str | None = Query(default=None, min_length=1),
    market_tier: MarketTier | None = None,
    brand_type: BrandType | None = None,
    origin_code: str | None = None,
    db: Session = Depends(get_db),
):
    return brand_service.list_brands(
        db,
        category=category,
        q=q,
        market_tier=market_tier,
        brand_type=brand_type,
        origin_code=origin_code,
    )


@router.get("/{brand_id}", response_model=BrandRead)
def get_brand(brand_id: int, db: Session = Depends(get_db)):
    return brand_service.get_brand(db, brand_id)
