from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.database import get_db
from app.models.entities import ProductPriceSnapshot
from app.schemas.game import ProductPriceSnapshotRead

router = APIRouter(tags=["product-prices"])


@router.get("/api/product-prices", response_model=list[ProductPriceSnapshotRead])
def list_product_prices(
    product_slug: str | None = Query(None, description="Filter by product slug"),
    product_id: int | None = Query(None, description="Filter by product ID"),
    price_type: str | None = Query(None, description="Filter by price type (e.g. MSRP, LOCAL_RETAIL)"),
    region: str | None = Query(None, description="Filter by region (e.g. US, VN)"),
    current_only: bool = Query(True, description="Filter only current snapshots"),
    currency: str | None = Query(None, description="Filter by currency"),
    confidence: str | None = Query(None, description="Filter by confidence level"),
    db: Session = Depends(get_db)
):
    stmt = select(ProductPriceSnapshot)
    if product_slug:
        stmt = stmt.where(ProductPriceSnapshot.product_slug == product_slug)
    if product_id:
        stmt = stmt.where(ProductPriceSnapshot.product_id == product_id)
    if price_type:
        stmt = stmt.where(ProductPriceSnapshot.price_type == price_type)
    if region:
        stmt = stmt.where(ProductPriceSnapshot.region == region)
    if current_only:
        stmt = stmt.where(ProductPriceSnapshot.is_current == True)
    if currency:
        stmt = stmt.where(ProductPriceSnapshot.currency == currency)
    if confidence:
        stmt = stmt.where(ProductPriceSnapshot.confidence == confidence)

    return db.scalars(stmt).all()
