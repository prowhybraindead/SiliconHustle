from random import Random
from uuid import uuid4
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.errors import bad_request, not_found
from app.services import progression_service
from app.services import fx_service, market_service
from app.models.entities import (
    Brand,
    HardwareProduct,
    InventoryUnit,
    PurchaseOrder,
    PurchaseOrderItem,
    Supplier,
    SupplierOffer,
)
from app.models.enums import ConditionType, Grade, InventorySource, InventoryStatus, PurchaseOrderStatus
from app.schemas.game import PurchaseOrderCreate
from app.services.save_game_service import get_save_game


def list_suppliers(db: Session) -> list[Supplier]:
    return list(db.scalars(select(Supplier).order_by(Supplier.name)))


def list_offers(
    db: Session,
    category: str | None = None,
    brand_slug: str | None = None,
    supplier_id: int | None = None,
    q: str | None = None,
    currency: str | None = None,
    save_game_id: int | None = None,
) -> list[SupplierOffer]:
    stmt = select(SupplierOffer).outerjoin(SupplierOffer.product).outerjoin(SupplierOffer.supplier)
    
    if category:
        stmt = stmt.where(HardwareProduct.category == category)
    if brand_slug:
        stmt = stmt.join(HardwareProduct.brand_record).where(Brand.slug == brand_slug)
    if supplier_id:
        stmt = stmt.where(SupplierOffer.supplier_id == supplier_id)
    if q:
        stmt = stmt.where(
            HardwareProduct.name.ilike(f"%{q}%") | Supplier.name.ilike(f"%{q}%")
        )
    if currency:
        stmt = stmt.where(
            (SupplierOffer.foreign_currency == currency) |
            ((SupplierOffer.foreign_currency.is_(None)) & (Supplier.invoice_currency == currency))
        )
        
    stmt = stmt.options(
        selectinload(SupplierOffer.supplier),
        selectinload(SupplierOffer.product).selectinload(HardwareProduct.brand_record).selectinload(Brand.categories),
        selectinload(SupplierOffer.product).selectinload(HardwareProduct.chip_vendor_brand).selectinload(Brand.categories),
    ).order_by(SupplierOffer.unit_price_vnd)
    
    offers = list(db.scalars(stmt))
    settings = get_settings()
    
    for offer in offers:
        if offer.supplier.invoice_currency != "VND":
            curr = offer.foreign_currency or offer.supplier.invoice_currency
            price = offer.foreign_unit_price if offer.foreign_unit_price is not None else offer.unit_price_vnd
            spread = offer.supplier.fx_spread_percent if offer.supplier.fx_spread_percent is not None else settings.fx_spread_percent_default
            
            rate, provider, _, fetched_at, is_fallback = fx_service.get_latest_rate(db, curr, "VND")
            _, _, _, _, _, _, converted = fx_service.convert_to_vnd(db, price, curr, spread)
            
            offer.effective_unit_price_vnd = converted
            offer.effective_fx_rate_to_vnd = rate
            offer.effective_fx_provider = provider
            offer.effective_fx_is_fallback = is_fallback
            offer.effective_fx_fetched_at = fetched_at
        else:
            offer.effective_unit_price_vnd = offer.unit_price_vnd
            offer.effective_fx_rate_to_vnd = 1.0
            offer.effective_fx_provider = "identity"
            offer.effective_fx_is_fallback = False
            offer.effective_fx_fetched_at = datetime.now(timezone.utc)

        # Integrate market service multiplier
        if save_game_id is not None:
            mult = market_service.get_effective_supplier_offer_multiplier(db, save_game_id, offer)
            offer.market_multiplier = mult
            offer.market_adjusted_unit_price_vnd = round(offer.effective_unit_price_vnd * mult)
            
            # Find active event titles matching this offer
            active_events = market_service.get_active_market_events(db, save_game_id)
            titles = []
            
            brand_slug_val = None
            if offer.product.brand_ref and offer.product.brand_ref.slug:
                brand_slug_val = offer.product.brand_ref.slug
            elif offer.product.brand:
                brand_slug_val = market_service._slugify(offer.product.brand)
                
            for event in active_events:
                matches = False
                if event.affected_product_id is not None:
                    if event.affected_product_id == offer.product_id:
                        matches = True
                elif event.affected_category is not None:
                    prod_cat = offer.product.category.value if hasattr(offer.product.category, "value") else str(offer.product.category)
                    if event.affected_category == prod_cat:
                        matches = True
                elif event.affected_brand_slug is not None:
                    if brand_slug_val and event.affected_brand_slug == brand_slug_val:
                        matches = True
                elif event.affected_origin_code is not None:
                    if offer.product.origin_code and event.affected_origin_code == offer.product.origin_code:
                        matches = True
                elif event.affected_currency is not None:
                    if offer.foreign_currency and event.affected_currency == offer.foreign_currency:
                        matches = True
                    elif offer.supplier.invoice_currency and event.affected_currency == offer.supplier.invoice_currency:
                        matches = True
                        
                if matches:
                    titles.append(event.title)
            offer.active_market_event_titles = titles
        else:
            offer.market_multiplier = 1.0
            offer.market_adjusted_unit_price_vnd = offer.effective_unit_price_vnd
            offer.active_market_event_titles = []
            
    return offers


def list_purchase_orders(db: Session, save_game_id: int) -> list[PurchaseOrder]:
    get_save_game(db, save_game_id)
    return list(
        db.scalars(
            select(PurchaseOrder)
            .options(
                selectinload(PurchaseOrder.supplier),
                selectinload(PurchaseOrder.items).selectinload(PurchaseOrderItem.product).selectinload(HardwareProduct.brand_record).selectinload(Brand.categories),
                selectinload(PurchaseOrder.items)
                .selectinload(PurchaseOrderItem.product)
                .selectinload(HardwareProduct.chip_vendor_brand)
                .selectinload(Brand.categories),
            )
            .where(PurchaseOrder.save_game_id == save_game_id)
            .order_by(PurchaseOrder.created_at.desc())
        )
    )


def get_purchase_order(db: Session, save_game_id: int, purchase_order_id: int) -> PurchaseOrder:
    order = db.scalar(
        select(PurchaseOrder)
        .options(
            selectinload(PurchaseOrder.supplier),
            selectinload(PurchaseOrder.items).selectinload(PurchaseOrderItem.product).selectinload(HardwareProduct.brand_record).selectinload(Brand.categories),
            selectinload(PurchaseOrder.items).selectinload(PurchaseOrderItem.product).selectinload(HardwareProduct.chip_vendor_brand).selectinload(Brand.categories),
        )
        .where(PurchaseOrder.save_game_id == save_game_id, PurchaseOrder.id == purchase_order_id)
    )
    if not order:
        raise not_found("Purchase order not found")
    return order


def create_purchase_order(db: Session, save_game_id: int, payload: PurchaseOrderCreate) -> PurchaseOrder:
    save_game = get_save_game(db, save_game_id)
    supplier = db.get(Supplier, payload.supplier_id)
    if not supplier:
        raise not_found("Supplier not found")
    if not payload.items:
        raise bad_request("Purchase order needs at least one item")

    settings = get_settings()
    invoice_currency = supplier.invoice_currency or "VND"
    is_foreign = (invoice_currency != "VND")
    
    subtotal = 0
    foreign_subtotal = 0.0 if is_foreign else None
    
    # Resolve rate and spread
    if is_foreign:
        spread_percent = supplier.fx_spread_percent if supplier.fx_spread_percent is not None else settings.fx_spread_percent_default
        rate, provider, _, fetched_at, is_fallback, _ = fx_service.get_rate_to_vnd(db, invoice_currency)
    else:
        spread_percent = 0.0
        rate = 1.0
        provider = "identity"
        fetched_at = datetime.now(timezone.utc)
        is_fallback = False

    order_items: list[PurchaseOrderItem] = []
    for item in payload.items:
        product = db.get(HardwareProduct, item.product_id)
        if not product:
            raise not_found("Hardware product not found")
        
        # Look up SupplierOffer to see if there is a foreign_unit_price specified
        offer = db.scalar(
            select(SupplierOffer).where(
                SupplierOffer.supplier_id == supplier.id,
                SupplierOffer.product_id == item.product_id
            )
        )
        
        if offer:
            if is_foreign:
                foreign_price = float(offer.foreign_unit_price if offer.foreign_unit_price is not None else offer.unit_price_vnd)
                foreign_subtotal += item.quantity * foreign_price
                curr = offer.foreign_currency or offer.supplier.invoice_currency
                spread = offer.supplier.fx_spread_percent if offer.supplier.fx_spread_percent is not None else settings.fx_spread_percent_default
                _, _, _, _, _, _, converted = fx_service.convert_to_vnd(db, foreign_price, curr, spread)
                effective_price = converted
            else:
                effective_price = offer.unit_price_vnd
            mult = market_service.get_effective_supplier_offer_multiplier(db, save_game_id, offer)
            unit_price_vnd = round(effective_price * mult)
        else:
            mult = market_service.get_effective_product_multiplier(db, save_game_id, product)
            if is_foreign:
                foreign_price = float(item.unit_price_vnd)
                foreign_subtotal += item.quantity * foreign_price
                _, _, _, _, _, _, converted_price_vnd = fx_service.convert_to_vnd(
                    db, foreign_price, invoice_currency, spread_percent
                )
                unit_price_vnd = round(converted_price_vnd * mult)
            else:
                unit_price_vnd = round(item.unit_price_vnd * mult)

        subtotal += item.quantity * unit_price_vnd
        order_items.append(
            PurchaseOrderItem(
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price_vnd=unit_price_vnd,
                warranty_months=item.warranty_months,
            )
        )

    if is_foreign:
        fee_reduction = int(progression_service.get_effect_value(db, save_game_id, "supplier_import_fee_reduction_percent", 0) or 0)
        import_fee_percent = max(0.0, (supplier.import_fee_percent or 0.0) - fee_reduction)
        import_fee_vnd = round(subtotal * import_fee_percent / 100.0)
        flat_fee_vnd = supplier.payment_fee_flat_vnd or 0
        fx_fee_vnd = import_fee_vnd + flat_fee_vnd
        final_total_vnd = subtotal + fx_fee_vnd
    else:
        fx_fee_vnd = 0
        final_total_vnd = subtotal

    if save_game.cash < final_total_vnd:
        raise bad_request("Not enough cash for this purchase order")

    # Calculate snapshots
    active_events = market_service.get_active_market_events(db, save_game_id)
    event_titles = set()
    multipliers = []
    for item in payload.items:
        prod = db.get(HardwareProduct, item.product_id)
        if prod:
            off = db.scalar(
                select(SupplierOffer).where(
                    SupplierOffer.supplier_id == supplier.id,
                    SupplierOffer.product_id == item.product_id
                )
            )
            if off:
                m_val = market_service.get_effective_supplier_offer_multiplier(db, save_game_id, off)
                multipliers.append(m_val)
                brand_slug_val = None
                if prod.brand_ref and prod.brand_ref.slug:
                    brand_slug_val = prod.brand_ref.slug
                elif prod.brand:
                    brand_slug_val = market_service._slugify(prod.brand)
                    
                for event in active_events:
                    matches = False
                    if event.affected_product_id is not None:
                        if event.affected_product_id == prod.id:
                            matches = True
                    elif event.affected_category is not None:
                        prod_cat = prod.category.value if hasattr(prod.category, "value") else str(prod.category)
                        if event.affected_category == prod_cat:
                            matches = True
                    elif event.affected_brand_slug is not None:
                        if brand_slug_val and event.affected_brand_slug == brand_slug_val:
                            matches = True
                    elif event.affected_origin_code is not None:
                        if prod.origin_code and event.affected_origin_code == prod.origin_code:
                            matches = True
                    elif event.affected_currency is not None:
                        if off.foreign_currency and event.affected_currency == off.foreign_currency:
                            matches = True
                        elif off.supplier.invoice_currency and event.affected_currency == supplier.invoice_currency:
                            matches = True
                    if matches:
                        event_titles.add(event.title)
            else:
                m_val = market_service.get_effective_product_multiplier(db, save_game_id, prod)
                multipliers.append(m_val)
                brand_slug_val = None
                if prod.brand_ref and prod.brand_ref.slug:
                    brand_slug_val = prod.brand_ref.slug
                elif prod.brand:
                    brand_slug_val = market_service._slugify(prod.brand)
                for event in active_events:
                    matches = False
                    if event.affected_product_id is not None:
                        if event.affected_product_id == prod.id:
                            matches = True
                    elif event.affected_category is not None:
                        prod_cat = prod.category.value if hasattr(prod.category, "value") else str(prod.category)
                        if event.affected_category == prod_cat:
                            matches = True
                    elif event.affected_brand_slug is not None:
                        if brand_slug_val and event.affected_brand_slug == brand_slug_val:
                            matches = True
                    elif event.affected_origin_code is not None:
                        if prod.origin_code and event.affected_origin_code == prod.origin_code:
                            matches = True
                    if matches:
                        event_titles.add(event.title)
                        
    import json
    market_multiplier_snapshot = sum(multipliers) / len(multipliers) if multipliers else 1.0
    market_event_titles_snapshot = json.dumps(list(event_titles)) if event_titles else None

    save_game.cash -= final_total_vnd
    purchase_order = PurchaseOrder(
        save_game_id=save_game_id,
        supplier_id=payload.supplier_id,
        status=PurchaseOrderStatus.ORDERED,
        subtotal_vnd=subtotal,
        delivery_due_day=save_game.game_day + max(0, supplier.delivery_days - int(progression_service.get_effect_value(db, save_game_id, "delivery_days_reduction", 0) or 0)),
        items=order_items,
        invoice_currency=invoice_currency,
        foreign_subtotal=foreign_subtotal,
        fx_rate_to_vnd=rate,
        fx_provider=provider,
        fx_fetched_at=fetched_at,
        fx_is_fallback=is_fallback,
        fx_spread_percent=spread_percent if is_foreign else None,
        fx_fee_vnd=fx_fee_vnd,
        final_total_vnd=final_total_vnd,
        market_multiplier_snapshot=market_multiplier_snapshot,
        market_event_titles_snapshot=market_event_titles_snapshot,
    )
    db.add(purchase_order)
    db.commit()
    db.refresh(purchase_order)
    return get_purchase_order(db, save_game_id, purchase_order.id)


def receive_purchase_order(db: Session, save_game_id: int, purchase_order_id: int) -> PurchaseOrder:
    purchase_order = get_purchase_order(db, save_game_id, purchase_order_id)
    if purchase_order.status == PurchaseOrderStatus.RECEIVED:
        return purchase_order
    if purchase_order.status == PurchaseOrderStatus.CANCELLED:
        raise bad_request("Cancelled purchase orders cannot be received")

    rng = Random(f"receive:{purchase_order.id}:{purchase_order.subtotal_vnd}")
    for item in purchase_order.items:
        for _ in range(item.quantity):
            product = item.product
            confidence = rng.randint(85, 95)
            health = rng.randint(92, 99)
            db.add(
                InventoryUnit(
                    save_game_id=save_game_id,
                    product_id=item.product_id,
                    serial_number=f"SUP-{purchase_order.id}-{uuid4().hex[:8].upper()}",
                    condition_type=ConditionType.NEW,
                    status=InventoryStatus.READY_FOR_SALE,
                    grade=Grade.A_PLUS if health >= 96 else Grade.A,
                    inspection_confidence=confidence,
                    purchase_price_vnd=item.unit_price_vnd,
                    listed_price_vnd=int(item.unit_price_vnd * 1.18),
                    warranty_months_remaining=item.warranty_months,
                    source=InventorySource.SUPPLIER,
                    health_score=health,
                    performance_score=product.base_performance_score,
                    thermal_score=max(20, 100 - product.base_heat_score + rng.randint(-2, 4)),
                    fan_score=rng.randint(90, 98),
                    vram_score=rng.randint(90, 98) if product.category.value == "GPU" else None,
                    stability_score=rng.randint(91, 99),
                    warranty_risk="LOW",
                    notes="Received from supplier purchase order.",
                )
            )

    purchase_order.status = PurchaseOrderStatus.RECEIVED
    db.commit()
    return get_purchase_order(db, save_game_id, purchase_order_id)
