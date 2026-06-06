from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import bad_request, not_found
from app.models.entities import Brand, Customer, CustomerConversation, CustomerRequest, HardwareProduct, InventoryUnit, Order, OrderItem, Quote, QuoteItem
from app.models.enums import (
    ConditionType,
    CustomerArchetype,
    CustomerRequestStatus,
    Grade,
    HardwareCategory,
    InventoryStatus,
    OrderStatus,
    QuoteItemSource,
    QuoteStatus,
    RequestType,
    RiskTolerance,
)
from app.schemas.game import QuoteCreate, QuoteUpdate
from app.services import compatibility_service
from app.services import customer_persona_service
from app.services import customer_conversation_service
from app.services.save_game_service import get_save_game
from app.services import fx_service


BUILD_CATEGORIES = [
    HardwareCategory.CPU,
    HardwareCategory.GPU,
    HardwareCategory.RAM,
    HardwareCategory.SSD,
    HardwareCategory.PSU,
    HardwareCategory.MOTHERBOARD,
    HardwareCategory.CASE,
]

BLOCKED_INVENTORY_STATUSES = {
    InventoryStatus.DEFECTIVE,
    InventoryStatus.FOR_PARTS,
    InventoryStatus.SOLD,
    InventoryStatus.WARRANTY_RETURN,
    InventoryStatus.RETIRED,
    InventoryStatus.INSTALLED_IN_BUILD,
    InventoryStatus.RESERVED,
}


@dataclass
class QuoteCandidate:
    product: HardwareProduct
    inventory_unit: InventoryUnit | None
    quantity: int
    unit_price_vnd: int
    unit_cost_vnd: int
    source: QuoteItemSource
    notes: str | None = None


def list_quotes(db: Session, save_game_id: int) -> list[Quote]:
    get_save_game(db, save_game_id)
    quotes = list(
        db.scalars(
            _quote_query()
            .where(Quote.save_game_id == save_game_id)
            .order_by(Quote.updated_at.desc())
        )
    )
    for quote in quotes:
        compatibility_service.evaluate_quote_compatibility(db, quote)
        customer_persona_service.evaluate_quote_for_persona(db, quote)
    return quotes


def list_quotes_for_request(db: Session, save_game_id: int, request_id: int) -> list[Quote]:
    get_save_game(db, save_game_id)
    quotes = list(
        db.scalars(
            _quote_query()
            .where(Quote.save_game_id == save_game_id, Quote.customer_request_id == request_id)
            .order_by(Quote.updated_at.desc())
        )
    )
    for quote in quotes:
        compatibility_service.evaluate_quote_compatibility(db, quote)
        customer_persona_service.evaluate_quote_for_persona(db, quote)
    return quotes


def get_quote(db: Session, save_game_id: int, quote_id: int) -> Quote:
    quote = db.scalar(_quote_query().where(Quote.save_game_id == save_game_id, Quote.id == quote_id))
    if not quote:
        raise not_found("Quote not found")
    compatibility_service.evaluate_quote_compatibility(db, quote)
    customer_persona_service.evaluate_quote_for_persona(db, quote)
    return quote


def create_quote(db: Session, save_game_id: int, payload: QuoteCreate) -> Quote:
    customer_request = _get_customer_request(db, save_game_id, payload.customer_request_id)
    items: list[QuoteItem] = []
    quoted_price = payload.quoted_price_vnd or sum(item.quantity * item.unit_price_vnd for item in payload.items)
    estimated_cost = payload.estimated_cost_vnd or sum(item.quantity * item.unit_cost_vnd for item in payload.items)
    for item in payload.items:
        product = db.get(HardwareProduct, item.product_id)
        if not product:
            raise not_found("Hardware product not found")
        inventory_unit = db.get(InventoryUnit, item.inventory_unit_id) if item.inventory_unit_id else None
        items.append(
            QuoteItem(
                product_id=item.product_id,
                inventory_unit_id=item.inventory_unit_id,
                product=product,
                inventory_unit=inventory_unit,
                quantity=item.quantity,
                unit_price_vnd=item.unit_price_vnd,
                unit_cost_vnd=item.unit_cost_vnd,
                source=item.source,
                notes=item.notes,
            )
        )
    # Calculate FX snapshot
    pref_currency = customer_request.customer.preferred_currency or "VND"
    if pref_currency != "VND":
        rate, provider, _, fetched_at, is_fallback, _ = fx_service.get_rate_to_vnd(db, pref_currency)
        foreign_price = round(quoted_price / rate, 2)
    else:
        rate = 1.0
        provider = "identity"
        fetched_at = datetime.now(timezone.utc)
        is_fallback = False
        foreign_price = None

    quote = Quote(
        save_game_id=save_game_id,
        customer_id=customer_request.customer_id,
        customer_request_id=customer_request.id,
        customer=customer_request.customer,
        customer_request=customer_request,
        title=payload.title,
        summary=payload.summary or "Manual quote draft.",
        quoted_price_vnd=quoted_price,
        estimated_cost_vnd=estimated_cost,
        estimated_profit_vnd=quoted_price - estimated_cost,
        notes=payload.notes,
        items=items,
        quote_currency=pref_currency,
        foreign_quoted_price=foreign_price,
        fx_rate_to_vnd=rate,
        fx_provider=provider,
        fx_fetched_at=fetched_at,
        fx_is_fallback=is_fallback,
    )
    _apply_scores(quote, customer_request)
    compatibility_service.evaluate_quote_compatibility(db, quote)
    customer_persona_service.evaluate_quote_for_persona(db, quote)
    customer_request.status = CustomerRequestStatus.QUOTED
    db.add(quote)
    db.commit()
    _maybe_log_quote_to_conversation(db, quote)
    return get_quote(db, save_game_id, quote.id)


def update_quote(db: Session, save_game_id: int, quote_id: int, payload: QuoteUpdate) -> Quote:
    quote = get_quote(db, save_game_id, quote_id)
    if quote.status == QuoteStatus.CONVERTED_TO_ORDER:
        raise bad_request("Converted quotes cannot be edited")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(quote, field, value)
    if payload.quoted_price_vnd is not None or payload.estimated_cost_vnd is not None:
        quote.estimated_profit_vnd = quote.quoted_price_vnd - quote.estimated_cost_vnd
    db.commit()
    return get_quote(db, save_game_id, quote_id)


def delete_or_reject_quote(db: Session, save_game_id: int, quote_id: int) -> Quote:
    quote = release_quote_reservations(db, save_game_id, quote_id)
    quote.status = QuoteStatus.REJECTED
    db.commit()
    return get_quote(db, save_game_id, quote_id)


def generate_quote_from_customer_request(db: Session, save_game_id: int, customer_request_id: int, notes: str | None = None) -> Quote:
    customer_request = _get_customer_request(db, save_game_id, customer_request_id)
    if customer_request.request_type == RequestType.BUILD_PC:
        candidates = [_select_candidate_for_category(db, save_game_id, customer_request, category) for category in BUILD_CATEGORIES]
        summary = (
            "Draft build proposal generated from current inventory and catalog placeholders. "
            "TODO: add deep compatibility scoring and NestyAI explanation copy."
        )
        title = f"{customer_request.customer.name} build proposal"
    elif customer_request.request_type == RequestType.BUY_COMPONENT:
        category = _category_from_request(customer_request)
        candidates = [_select_candidate_for_category(db, save_game_id, customer_request, category)]
        summary = "Component quote generated with a simple use-case match. TODO: expand product intent parsing."
        title = f"{customer_request.customer.name} component quote"
    else:
        candidates = []
        summary = "Detailed workflow for this request type is not implemented yet. This placeholder keeps the quote pipeline ready."
        title = f"{customer_request.request_type.value.replace('_', ' ').title()} placeholder quote"

    quote = Quote(
        save_game_id=save_game_id,
        customer_id=customer_request.customer_id,
        customer_request_id=customer_request.id,
        customer=customer_request.customer,
        customer_request=customer_request,
        title=title,
        summary=summary,
        notes=notes,
        items=[
            QuoteItem(
                product_id=candidate.product.id,
                inventory_unit_id=candidate.inventory_unit.id if candidate.inventory_unit else None,
                product=candidate.product,
                inventory_unit=candidate.inventory_unit,
                quantity=candidate.quantity,
                unit_price_vnd=candidate.unit_price_vnd,
                unit_cost_vnd=candidate.unit_cost_vnd,
                source=candidate.source,
                notes=candidate.notes,
            )
            for candidate in candidates
        ],
    )
    quote.quoted_price_vnd = sum(item.quantity * item.unit_price_vnd for item in quote.items)
    quote.estimated_cost_vnd = sum(item.quantity * item.unit_cost_vnd for item in quote.items)
    quote.estimated_profit_vnd = quote.quoted_price_vnd - quote.estimated_cost_vnd

    pref_currency = customer_request.customer.preferred_currency or "VND"
    if pref_currency != "VND":
        rate, provider, _, fetched_at, is_fallback, _ = fx_service.get_rate_to_vnd(db, pref_currency)
        foreign_price = round(quote.quoted_price_vnd / rate, 2)
    else:
        rate = 1.0
        provider = "identity"
        fetched_at = datetime.now(timezone.utc)
        is_fallback = False
        foreign_price = None

    quote.quote_currency = pref_currency
    quote.foreign_quoted_price = foreign_price
    quote.fx_rate_to_vnd = rate
    quote.fx_provider = provider
    quote.fx_fetched_at = fetched_at
    quote.fx_is_fallback = is_fallback

    _apply_scores(quote, customer_request)
    compatibility_service.evaluate_quote_compatibility(db, quote)
    customer_persona_service.evaluate_quote_for_persona(db, quote)
    customer_request.status = CustomerRequestStatus.QUOTED
    db.add(quote)
    db.commit()
    _maybe_log_quote_to_conversation(db, quote)
    return get_quote(db, save_game_id, quote.id)


def reserve_quote_items(db: Session, save_game_id: int, quote_id: int) -> Quote:
    quote = get_quote(db, save_game_id, quote_id)
    if quote.status == QuoteStatus.CONVERTED_TO_ORDER:
        raise bad_request("Converted quotes cannot be reserved again")
    for item in quote.items:
        if not item.inventory_unit_id:
            continue
        unit = item.inventory_unit
        if item.is_reserved:
            continue
        if unit.status in BLOCKED_INVENTORY_STATUSES and unit.status != InventoryStatus.RESERVED:
            raise bad_request(f"Inventory unit {unit.id} is not ready to reserve")
        unit.status = InventoryStatus.RESERVED
        item.is_reserved = True
    quote.status = QuoteStatus.PRESENTED
    db.commit()
    return get_quote(db, save_game_id, quote_id)


def release_quote_reservations(db: Session, save_game_id: int, quote_id: int) -> Quote:
    quote = get_quote(db, save_game_id, quote_id)
    if quote.status == QuoteStatus.CONVERTED_TO_ORDER:
        raise bad_request("Converted quote reservations cannot be released")
    for item in quote.items:
        if item.is_reserved and item.inventory_unit:
            item.inventory_unit.status = InventoryStatus.READY_FOR_SALE
            item.is_reserved = False
    db.commit()
    return get_quote(db, save_game_id, quote_id)


def accept_quote_to_order(db: Session, save_game_id: int, quote_id: int) -> Order:
    quote = get_quote(db, save_game_id, quote_id)
    if quote.status == QuoteStatus.CONVERTED_TO_ORDER:
        raise bad_request("Quote has already been converted to an order")
    quote = reserve_quote_items(db, save_game_id, quote_id)

    order = Order(
        save_game_id=save_game_id,
        customer_id=quote.customer_id,
        request_id=quote.customer_request_id,
        status=OrderStatus.ACCEPTED,
        quoted_price_vnd=quote.quoted_price_vnd,
        cost_vnd=quote.estimated_cost_vnd,
        profit_vnd=quote.estimated_profit_vnd,
        customer_fit_score=quote.customer_fit_score,
        notes=f"Created from quote #{quote.id}. Inventory units move to INSTALLED_IN_BUILD on acceptance.",
        order_currency=quote.quote_currency,
        foreign_order_amount=quote.foreign_quoted_price,
        fx_rate_to_vnd=quote.fx_rate_to_vnd,
        fx_provider=quote.fx_provider,
        fx_fetched_at=quote.fx_fetched_at,
        fx_is_fallback=quote.fx_is_fallback,
        fx_spread_percent=quote.fx_spread_percent,
        items=[
            OrderItem(
                inventory_unit_id=item.inventory_unit_id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price_vnd=item.unit_price_vnd,
                cost_vnd=item.unit_cost_vnd,
            )
            for item in quote.items
        ],
    )
    for item in quote.items:
        if item.inventory_unit:
            item.inventory_unit.status = InventoryStatus.INSTALLED_IN_BUILD
    quote.status = QuoteStatus.CONVERTED_TO_ORDER
    quote.customer_request.status = CustomerRequestStatus.ACCEPTED
    db.add(order)
    compatibility_result = getattr(quote, "compatibility_result", None)
    if compatibility_result:
        compatibility_service.apply_compatibility_snapshot(order, compatibility_result)
    else:
        compatibility_service.evaluate_order_compatibility(db, order)
    db.commit()
    created_order = db.scalar(
        select(Order)
        .options(
            selectinload(Order.customer),
            selectinload(Order.items).selectinload(OrderItem.product).selectinload(HardwareProduct.brand_record).selectinload(Brand.categories),
            selectinload(Order.items).selectinload(OrderItem.product).selectinload(HardwareProduct.chip_vendor_brand).selectinload(Brand.categories),
            selectinload(Order.items).selectinload(OrderItem.inventory_unit).selectinload(InventoryUnit.product).selectinload(HardwareProduct.brand_record).selectinload(Brand.categories),
            selectinload(Order.items).selectinload(OrderItem.inventory_unit).selectinload(InventoryUnit.product).selectinload(HardwareProduct.chip_vendor_brand).selectinload(Brand.categories),
        )
        .where(Order.id == order.id)
    )
    if compatibility_result:
        compatibility_service.apply_compatibility_snapshot(created_order, compatibility_result)
    else:
        compatibility_service.evaluate_order_compatibility(db, created_order)
    if quote.customer_request and quote.customer_request.conversation_id:
        customer_conversation_service.close_conversation(db, save_game_id, quote.customer_request.conversation_id, won=True)
    return created_order


def _quote_query():
    return select(Quote).options(
        selectinload(Quote.customer),
        selectinload(Quote.customer_request).selectinload(CustomerRequest.customer),
        selectinload(Quote.items).selectinload(QuoteItem.product).selectinload(HardwareProduct.brand_record).selectinload(Brand.categories),
        selectinload(Quote.items).selectinload(QuoteItem.product).selectinload(HardwareProduct.chip_vendor_brand).selectinload(Brand.categories),
        selectinload(Quote.items)
        .selectinload(QuoteItem.inventory_unit)
        .selectinload(InventoryUnit.product)
        .selectinload(HardwareProduct.brand_record)
        .selectinload(Brand.categories),
        selectinload(Quote.items)
        .selectinload(QuoteItem.inventory_unit)
        .selectinload(InventoryUnit.product)
        .selectinload(HardwareProduct.chip_vendor_brand)
        .selectinload(Brand.categories),
    )


def _get_customer_request(db: Session, save_game_id: int, customer_request_id: int) -> CustomerRequest:
    customer_request = db.scalar(
        select(CustomerRequest)
        .join(CustomerRequest.customer)
        .options(selectinload(CustomerRequest.customer))
        .where(CustomerRequest.id == customer_request_id, Customer.save_game_id == save_game_id)
    )
    if not customer_request:
        raise not_found("Customer request not found")
    return customer_request


def _select_candidate_for_category(
    db: Session, save_game_id: int, customer_request: CustomerRequest, category: HardwareCategory
) -> QuoteCandidate:
    inventory_units = list(
        db.scalars(
            select(InventoryUnit)
            .join(InventoryUnit.product)
            .options(
                selectinload(InventoryUnit.product).selectinload(HardwareProduct.brand_record).selectinload(Brand.categories),
                selectinload(InventoryUnit.product).selectinload(HardwareProduct.chip_vendor_brand).selectinload(Brand.categories),
            )
            .where(InventoryUnit.save_game_id == save_game_id, HardwareProduct.category == category)
            .where(InventoryUnit.status.not_in(BLOCKED_INVENTORY_STATUSES))
        )
    )
    ready_units = [unit for unit in inventory_units if unit.status == InventoryStatus.READY_FOR_SALE]
    candidate_pool = ready_units or inventory_units
    if candidate_pool:
        unit = sorted(candidate_pool, key=lambda item: _inventory_rank(item, customer_request), reverse=True)[0]
        msrp = unit.product.msrp_vnd or unit.purchase_price_vnd
        unit_price = unit.listed_price_vnd or max(int(unit.purchase_price_vnd * 1.22), int(msrp * 0.72))
        return QuoteCandidate(
            product=unit.product,
            inventory_unit=unit,
            quantity=1,
            unit_price_vnd=unit_price,
            unit_cost_vnd=unit.purchase_price_vnd,
            source=QuoteItemSource.INVENTORY,
            notes="Selected from available inventory.",
        )

    product = db.scalar(
        select(HardwareProduct)
        .options(
            selectinload(HardwareProduct.brand_record).selectinload(Brand.categories),
            selectinload(HardwareProduct.chip_vendor_brand).selectinload(Brand.categories),
        )
        .where(HardwareProduct.category == category)
        .order_by(HardwareProduct.base_performance_score.desc(), HardwareProduct.base_reliability_score.desc())
        .limit(1)
    )
    if not product:
        raise not_found(f"No product found for category {category.value}")
    return QuoteCandidate(
        product=product,
        inventory_unit=None,
        quantity=1,
        unit_price_vnd=product.msrp_vnd or product.base_local_price_vnd or 0,
        unit_cost_vnd=product.supplier_cost_vnd or int((product.msrp_vnd or product.base_local_price_vnd or 0) * 0.84),
        source=QuoteItemSource.SUPPLIER_NEEDED,
        notes="Catalog placeholder. Player needs to procure this part.",
    )


def _inventory_rank(unit: InventoryUnit, customer_request: CustomerRequest) -> int:
    risk = customer_request.customer.risk_tolerance
    condition_bonus = {
        ConditionType.NEW: 28,
        ConditionType.REFURBISHED: 20,
        ConditionType.OPEN_BOX: 18,
        ConditionType.USED: 5 if risk != RiskTolerance.LOW else -12,
        ConditionType.DEFECTIVE: -80,
        ConditionType.FOR_PARTS: -100,
    }[unit.condition_type]
    grade_bonus = {
        Grade.A_PLUS: 18,
        Grade.A: 14,
        Grade.B: 7,
        Grade.C: 0,
        Grade.D: -14,
        Grade.F: -40,
        Grade.UNKNOWN: -10,
    }[unit.grade]
    confidence_bonus = unit.inspection_confidence // 4
    budget_bonus = 10 if customer_request.customer.archetype == CustomerArchetype.BUDGET_BUYER and unit.condition_type == ConditionType.USED else 0
    return unit.product.base_performance_score + condition_bonus + grade_bonus + confidence_bonus + budget_bonus


def _category_from_request(customer_request: CustomerRequest) -> HardwareCategory:
    text = f"{customer_request.use_case} {customer_request.requirements_json or {}}".lower()
    if "gpu" in text or "gaming" in text or "144hz" in text:
        return HardwareCategory.GPU
    if "cpu" in text or "workstation" in text:
        return HardwareCategory.CPU
    if "storage" in text or "ssd" in text:
        return HardwareCategory.SSD
    return HardwareCategory.GPU


def _apply_scores(quote: Quote, customer_request: CustomerRequest) -> None:
    products = [item.product for item in quote.items if item.product]
    units = [item.inventory_unit for item in quote.items if item.inventory_unit]
    if not products:
        quote.customer_fit_score = 30
        quote.performance_score = 0
        quote.value_score = 40
        quote.thermal_score = 50
        quote.reliability_score = 50
        quote.warranty_risk = "MEDIUM"
        return

    cpu_gpu = [product.base_performance_score for product in products if product.category in {HardwareCategory.CPU, HardwareCategory.GPU}]
    performance = _clamp(sum(cpu_gpu or [product.base_performance_score for product in products]) // len(cpu_gpu or products))
    heat = sum(product.base_heat_score for product in products) // len(products)
    thermal_penalty = sum(8 for unit in units if unit.condition_type == ConditionType.USED)
    thermal = _clamp(100 - heat - thermal_penalty)

    reliability_values = []
    risk_points = 0
    for item in quote.items:
        product = item.product
        unit = item.inventory_unit
        reliability = product.base_reliability_score
        if unit:
            reliability += _condition_reliability_offset(unit.condition_type)
            reliability += min(12, unit.inspection_confidence // 8)
            if unit.health_score is not None:
                reliability = (reliability + unit.health_score) // 2
            if unit.condition_type == ConditionType.USED:
                risk_points += 1
            if unit.inspection_confidence < 40 or unit.status == InventoryStatus.UNTESTED:
                risk_points += 2
        else:
            reliability += 2
        if item.source != QuoteItemSource.INVENTORY:
            risk_points += 1
        reliability_values.append(_clamp(reliability))

    reliability_score = sum(reliability_values) // len(reliability_values)
    budget = max(customer_request.budget_vnd, 1)
    budget_ratio = quote.quoted_price_vnd / budget
    if budget_ratio <= 0.9:
        value = 90
    elif budget_ratio <= 1:
        value = 80
    elif budget_ratio <= 1.15:
        value = 60
    else:
        value = 40

    target = customer_request.target_performance_score or 60
    performance_fit = 85 if performance >= target else max(35, 85 - (target - performance))
    risk_fit = 85 - (risk_points * (10 if customer_request.customer.risk_tolerance == RiskTolerance.LOW else 6))
    quote.performance_score = performance
    quote.value_score = _clamp(value)
    quote.thermal_score = thermal
    quote.reliability_score = _clamp(reliability_score)
    quote.customer_fit_score = _clamp((performance_fit + quote.value_score + risk_fit) // 3)
    quote.warranty_risk = "HIGH" if risk_points >= 6 or reliability_score < 58 else "MEDIUM" if risk_points >= 3 else "LOW"


def _condition_reliability_offset(condition: ConditionType) -> int:
    return {
        ConditionType.NEW: 8,
        ConditionType.OPEN_BOX: 3,
        ConditionType.USED: -12,
        ConditionType.REFURBISHED: 2,
        ConditionType.DEFECTIVE: -45,
        ConditionType.FOR_PARTS: -70,
    }[condition]


def _clamp(value: int, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, value))


def _maybe_log_quote_to_conversation(db: Session, quote: Quote) -> None:
    request = quote.customer_request
    if not request or not request.conversation_id:
        return
    conversation = db.scalar(
        select(CustomerConversation).where(
            CustomerConversation.save_game_id == quote.save_game_id,
            CustomerConversation.id == request.conversation_id,
        )
    )
    if not conversation:
        return
    customer_conversation_service.add_system_message(
        db,
        quote.save_game_id,
        conversation.id,
        f"Quote generated: #{quote.id} - {quote.title}",
        metadata={
            "quote_id": quote.id,
            "quoted_price_vnd": quote.quoted_price_vnd,
            "quote_acceptance_chance": quote.quote_acceptance_chance,
            "customer_fit_score": quote.customer_fit_score,
        },
    )
    db.commit()
