from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import not_found
from app.models.entities import Brand, HardwareProduct
from app.models.enums import HardwareCategory


def list_products(
    db: Session,
    category: HardwareCategory | None = None,
    brand_id: int | None = None,
    brand_slug: str | None = None,
    chip_vendor_slug: str | None = None,
    q: str | None = None,
    data_confidence: str | None = None,
    origin_code: str | None = None,
    min_performance_score: int | None = None,
    max_power_watts: int | None = None,
    save_game_id: int | None = None,
) -> list[HardwareProduct]:
    statement = (
        select(HardwareProduct)
        .options(
            selectinload(HardwareProduct.brand_record).selectinload(Brand.categories),
            selectinload(HardwareProduct.chip_vendor_brand).selectinload(Brand.categories),
        )
        .order_by(HardwareProduct.category, HardwareProduct.name)
    )
    if category:
        statement = statement.where(HardwareProduct.category == category)
    if brand_id:
        statement = statement.where(HardwareProduct.brand_id == brand_id)
    if brand_slug:
        statement = statement.join(HardwareProduct.brand_record).where(Brand.slug == brand_slug.strip().lower())
    if chip_vendor_slug:
        statement = statement.join(HardwareProduct.chip_vendor_brand).where(Brand.slug == chip_vendor_slug.strip().lower())
    if q:
        needle = f"%{q.strip()}%"
        statement = statement.where(HardwareProduct.name.ilike(needle) | HardwareProduct.brand.ilike(needle) | HardwareProduct.slug.ilike(needle))
    if data_confidence:
        statement = statement.where(HardwareProduct.data_confidence == data_confidence.strip().upper())
    if origin_code:
        statement = statement.where(HardwareProduct.origin_code == origin_code.strip().upper())
    if min_performance_score is not None:
        statement = statement.where(HardwareProduct.base_performance_score >= min_performance_score)
    if max_power_watts is not None:
        statement = statement.where(HardwareProduct.base_power_watts <= max_power_watts)
    
    products = list(db.scalars(statement).unique())
    for product in products:
        populate_market_prices(db, product, save_game_id)
    return products


def get_product(db: Session, product_id: int, save_game_id: int | None = None) -> HardwareProduct:
    product = db.scalar(
        select(HardwareProduct)
        .options(
            selectinload(HardwareProduct.brand_record).selectinload(Brand.categories),
            selectinload(HardwareProduct.chip_vendor_brand).selectinload(Brand.categories),
        )
        .where(HardwareProduct.id == product_id)
    )
    if not product:
        raise not_found("Hardware product not found")
    
    populate_market_prices(db, product, save_game_id)
    return product


def populate_market_prices(db: Session, product: HardwareProduct, save_game_id: int | None):
    if save_game_id is None:
        product.market_multiplier = 1.0
        product.market_adjusted_local_retail_vnd = product.latest_local_retail_vnd
        product.market_adjusted_used_market_vnd = product.latest_used_market_vnd
        product.market_adjusted_supplier_cost_vnd = product.latest_supplier_cost_vnd
        product.active_market_event_titles = []
    else:
        from app.services import market_service
        mult = market_service.get_effective_product_multiplier(db, save_game_id, product)
        product.market_multiplier = mult
        product.market_adjusted_local_retail_vnd = round(product.latest_local_retail_vnd * mult) if product.latest_local_retail_vnd is not None else None
        product.market_adjusted_used_market_vnd = round(product.latest_used_market_vnd * mult) if product.latest_used_market_vnd is not None else None
        product.market_adjusted_supplier_cost_vnd = round(product.latest_supplier_cost_vnd * mult) if product.latest_supplier_cost_vnd is not None else None
        
        # Find active event titles matching this product
        active_events = market_service.get_active_market_events(db, save_game_id)
        titles = []
        brand_slug_val = None
        if product.brand_ref and product.brand_ref.slug:
            brand_slug_val = product.brand_ref.slug
        elif product.brand:
            brand_slug_val = market_service._slugify(product.brand)
            
        for event in active_events:
            matches = False
            if event.affected_product_id is not None:
                if event.affected_product_id == product.id:
                    matches = True
            elif event.affected_category is not None:
                prod_cat = product.category.value if hasattr(product.category, "value") else str(product.category)
                if event.affected_category == prod_cat:
                    matches = True
            elif event.affected_brand_slug is not None:
                if brand_slug_val and event.affected_brand_slug == brand_slug_val:
                    matches = True
            elif event.affected_origin_code is not None:
                if product.origin_code and event.affected_origin_code == product.origin_code:
                    matches = True
            if matches:
                titles.append(event.title)
        product.active_market_event_titles = titles

