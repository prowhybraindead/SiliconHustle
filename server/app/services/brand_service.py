from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import not_found
from app.models.entities import Brand, BrandCategory
from app.models.enums import BrandCategoryName, BrandType, MarketTier


def list_brands(
    db: Session,
    category: BrandCategoryName | None = None,
    q: str | None = None,
    market_tier: MarketTier | None = None,
    brand_type: BrandType | None = None,
    origin_code: str | None = None,
) -> list[Brand]:
    statement = select(Brand).options(selectinload(Brand.categories))
    if category:
        statement = statement.join(BrandCategory).where(BrandCategory.category == category)
    if q:
        needle = f"%{q.strip()}%"
        statement = statement.where(Brand.name.ilike(needle) | Brand.slug.ilike(needle))
    if market_tier:
        statement = statement.where(Brand.market_tier == market_tier)
    if brand_type:
        statement = statement.where(Brand.brand_type == brand_type)
    if origin_code:
        statement = statement.where(Brand.origin_code == origin_code.strip().upper())
    return list(db.scalars(statement.order_by(Brand.name)).unique())


def get_brand(db: Session, brand_id: int) -> Brand:
    brand = db.scalar(select(Brand).options(selectinload(Brand.categories)).where(Brand.id == brand_id))
    if not brand:
        raise not_found("Brand not found")
    return brand
