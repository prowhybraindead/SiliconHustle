from random import Random

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.entities import Customer, CustomerRequest, InventoryUnit, MarketEvent, PurchasedShopUpgrade, StaffMember
from app.models.enums import CustomerArchetype, InventoryStatus, KnowledgeLevel, RequestType, RiskTolerance, StaffStatus
from app.services.save_game_service import get_save_game
from app.services import customer_persona_service


from app.services import fx_service

NAMES = ["Minh Tran", "Linh Pham", "Bao Nguyen", "An Vo", "Khoa Le", "Trang Do"]
USE_CASES = ["esports cafe rig", "quiet creator workstation", "budget school PC", "upgrade for 144Hz gaming"]
FOREIGN_CURRENCIES = {
    "USD": "US",
    "EUR": "DE",
    "JPY": "JP",
    "CNY": "CN",
    "TWD": "TW",
    "HKD": "HK",
    "KRW": "KR",
    "SGD": "SG",
    "THB": "TH"
}

PREMIUM_ARCHETYPES = [CustomerArchetype.CREATOR, CustomerArchetype.TECH_NERD, CustomerArchetype.BUSINESS, CustomerArchetype.GAMER]
VALUE_ARCHETYPES = [CustomerArchetype.BUDGET_BUYER, CustomerArchetype.SELLER, CustomerArchetype.OFFICE]


def _weighted_choice(rng: Random, choices: list[tuple[object, int]]):
    weighted = [(choice, max(1, weight)) for choice, weight in choices if weight > 0]
    total = sum(weight for _, weight in weighted)
    pick = rng.uniform(0, total)
    upto = 0.0
    for choice, weight in weighted:
        upto += weight
        if pick <= upto:
            return choice
    return weighted[-1][0]


def _showroom_context(db: Session, save_game_id: int) -> dict[str, float | int]:
    inventory_count = db.scalar(select(func.count()).select_from(InventoryUnit).where(InventoryUnit.save_game_id == save_game_id)) or 0
    ready_count = (
        db.scalar(
            select(func.count())
            .select_from(InventoryUnit)
            .where(InventoryUnit.save_game_id == save_game_id, InventoryUnit.status == InventoryStatus.READY_FOR_SALE)
        )
        or 0
    )
    untested_count = (
        db.scalar(
            select(func.count())
            .select_from(InventoryUnit)
            .where(InventoryUnit.save_game_id == save_game_id, InventoryUnit.status == InventoryStatus.UNTESTED)
        )
        or 0
    )
    staff_count = db.scalar(select(func.count()).select_from(StaffMember).where(StaffMember.save_game_id == save_game_id)) or 0
    available_staff_count = (
        db.scalar(
            select(func.count())
            .select_from(StaffMember)
            .where(StaffMember.save_game_id == save_game_id, StaffMember.status == StaffStatus.AVAILABLE)
        )
        or 0
    )
    upgrade_count = db.scalar(select(func.count()).select_from(PurchasedShopUpgrade).where(PurchasedShopUpgrade.save_game_id == save_game_id)) or 0
    active_market_events = (
        db.scalar(
            select(func.count())
            .select_from(MarketEvent)
            .where(MarketEvent.save_game_id == save_game_id, MarketEvent.is_active == True)  # noqa: E712
        )
        or 0
    )
    return {
        "inventory_count": inventory_count,
        "ready_count": ready_count,
        "untested_count": untested_count,
        "staff_count": staff_count,
        "available_staff_count": available_staff_count,
        "upgrade_count": upgrade_count,
        "active_market_events": active_market_events,
    }


def _select_archetype(rng: Random, save_game, showroom_state: dict[str, float | int]) -> CustomerArchetype:
    reputation = int(save_game.reputation or 0)
    shop_level = int(save_game.shop_level or 1)
    ready_count = int(showroom_state["ready_count"])
    untested_count = int(showroom_state["untested_count"])
    upgrade_count = int(showroom_state["upgrade_count"])
    available_staff = int(showroom_state["available_staff_count"])

    premium_bias = min(5, 1 + reputation // 20 + shop_level // 2 + upgrade_count // 3 + ready_count // 4)
    value_bias = min(5, 1 + max(0, 60 - reputation) // 15 + untested_count // 4)
    service_bias = min(5, 1 + available_staff // 2 + shop_level // 3)

    if reputation >= 70 or shop_level >= 4:
        choices = [
            (CustomerArchetype.CREATOR, 4 + premium_bias),
            (CustomerArchetype.TECH_NERD, 4 + premium_bias),
            (CustomerArchetype.BUSINESS, 3 + service_bias),
            (CustomerArchetype.GAMER, 3 + premium_bias),
            (CustomerArchetype.OFFICE, 2 + service_bias),
            (CustomerArchetype.BUDGET_BUYER, 1 + value_bias),
            (CustomerArchetype.SELLER, 1 + value_bias),
        ]
    elif reputation <= 45 or untested_count > ready_count:
        choices = [
            (CustomerArchetype.BUDGET_BUYER, 5 + value_bias),
            (CustomerArchetype.SELLER, 4 + value_bias),
            (CustomerArchetype.OFFICE, 3 + service_bias),
            (CustomerArchetype.GAMER, 2 + premium_bias),
            (CustomerArchetype.TECH_NERD, 1 + premium_bias),
            (CustomerArchetype.CREATOR, 1 + premium_bias),
            (CustomerArchetype.BUSINESS, 1 + service_bias),
        ]
    else:
        choices = [
            (CustomerArchetype.GAMER, 4 + premium_bias),
            (CustomerArchetype.CREATOR, 3 + premium_bias),
            (CustomerArchetype.OFFICE, 3 + service_bias),
            (CustomerArchetype.BUSINESS, 3 + service_bias),
            (CustomerArchetype.TECH_NERD, 3 + premium_bias),
            (CustomerArchetype.BUDGET_BUYER, 2 + value_bias),
            (CustomerArchetype.SELLER, 2 + value_bias),
        ]

    return _weighted_choice(rng, choices)


def _select_request_type(rng: Random, showroom_state: dict[str, float | int], archetype: CustomerArchetype) -> RequestType:
    ready_count = int(showroom_state["ready_count"])
    untested_count = int(showroom_state["untested_count"])
    active_events = int(showroom_state["active_market_events"])

    if archetype in {CustomerArchetype.BUSINESS, CustomerArchetype.OFFICE}:
        choices = [
            (RequestType.BUILD_PC, 3 + ready_count // 3),
            (RequestType.UPGRADE_PC, 3 + ready_count // 2),
            (RequestType.BUY_COMPONENT, 2 + ready_count // 4),
            (RequestType.REPAIR, 2 + untested_count // 3),
            (RequestType.SELL_USED_PART, 1 + active_events),
        ]
    elif archetype in {CustomerArchetype.SELLER, CustomerArchetype.BUDGET_BUYER}:
        choices = [
            (RequestType.SELL_USED_PART, 4 + active_events),
            (RequestType.REPAIR, 4 + untested_count // 2),
            (RequestType.BUY_COMPONENT, 2 + ready_count // 4),
            (RequestType.UPGRADE_PC, 1 + ready_count // 5),
            (RequestType.BUILD_PC, 1 + ready_count // 5),
        ]
    else:
        choices = [
            (RequestType.BUILD_PC, 4 + ready_count // 3),
            (RequestType.UPGRADE_PC, 3 + ready_count // 4),
            (RequestType.BUY_COMPONENT, 3 + ready_count // 5),
            (RequestType.REPAIR, 2 + untested_count // 3),
            (RequestType.SELL_USED_PART, 1 + active_events),
        ]

    return _weighted_choice(rng, choices)


def generate_sample_customer(db: Session, save_game_id: int) -> tuple[Customer, CustomerRequest]:
    save_game = get_save_game(db, save_game_id)
    existing_count = len(save_game.customers)
    showroom_state = _showroom_context(db, save_game_id)
    seed = "|".join(
        [
            "customer",
            str(save_game_id),
            str(save_game.game_day),
            str(existing_count),
            str(save_game.reputation),
            str(save_game.shop_level),
            str(showroom_state["inventory_count"]),
            str(showroom_state["ready_count"]),
            str(showroom_state["untested_count"]),
            str(showroom_state["staff_count"]),
            str(showroom_state["upgrade_count"]),
        ]
    )
    rng = Random(seed)
    prestige_score = min(100, int(save_game.reputation * 0.75 + save_game.shop_level * 10 + showroom_state["upgrade_count"] * 4 + showroom_state["ready_count"] * 2))
    pressure_score = min(100, int(max(0, 60 - save_game.reputation) * 1.2 + showroom_state["untested_count"] * 3 + showroom_state["active_market_events"] * 6))

    archetype = _select_archetype(rng, save_game, showroom_state)

    # Better showrooms pull in more foreign and premium buyers.
    foreign_chance = max(0.05, min(0.28, 0.08 + (save_game.reputation / 400.0) + (save_game.shop_level * 0.02) + (showroom_state["upgrade_count"] * 0.01) - (pressure_score / 600.0)))
    is_foreign = rng.random() < foreign_chance
    if is_foreign:
        pref_currency = rng.choice(list(FOREIGN_CURRENCIES.keys()))
        country_code = FOREIGN_CURRENCIES[pref_currency]
    else:
        pref_currency = "VND"
        country_code = "VN"

    knowledge_roll = rng.random()
    if prestige_score >= 75:
        knowledge_level = KnowledgeLevel.HIGH if knowledge_roll < 0.55 else KnowledgeLevel.MEDIUM
    elif pressure_score >= 60:
        knowledge_level = KnowledgeLevel.LOW if knowledge_roll < 0.5 else KnowledgeLevel.MEDIUM
    else:
        knowledge_level = rng.choice(list(KnowledgeLevel))

    patience_base = 40 + min(35, save_game.reputation // 3) + min(15, save_game.shop_level * 2)
    patience = max(20, min(100, patience_base + rng.randint(-12, 16) - pressure_score // 6))
    negotiation_floor = 20 + pressure_score // 4
    negotiation_ceiling = 85 + prestige_score // 6
    negotiation_score = max(10, min(100, rng.randint(negotiation_floor, negotiation_ceiling)))

    risk_tolerance = (
        RiskTolerance.HIGH
        if archetype in {CustomerArchetype.BUDGET_BUYER, CustomerArchetype.SELLER} and pressure_score >= 40
        else RiskTolerance.MEDIUM
        if prestige_score < 60
        else RiskTolerance.LOW
    )

    customer = Customer(
        save_game_id=save_game_id,
        name=NAMES[rng.randrange(len(NAMES))],
        archetype=archetype,
        knowledge_level=knowledge_level,
        patience=patience,
        negotiation_score=negotiation_score,
        risk_tolerance=risk_tolerance,
        country_code=country_code,
        preferred_currency=pref_currency,
    )
    persona = customer_persona_service.generate_customer_persona(db, customer)
    customer_persona_service.apply_persona_to_customer(db, customer, persona["persona_type"])

    budget_floor = max(2_000_000, int(4_000_000 + (save_game.shop_level * 650_000) + (save_game.reputation * 55_000) + (showroom_state["ready_count"] * 120_000) - (pressure_score * 25_000)))
    budget_ceiling = max(
        budget_floor + 1_000_000,
        int(18_000_000 + (save_game.shop_level * 5_000_000) + (save_game.reputation * 220_000) + (showroom_state["upgrade_count"] * 900_000)),
    )
    budget_base = rng.randrange(budget_floor, budget_ceiling + 1, 1_000_000)
    budget_multiplier_min, budget_multiplier_max = persona["budget_multiplier_range"]
    showroom_budget_bias = 1.0 + min(0.18, prestige_score / 600.0) - min(0.12, pressure_score / 800.0)
    budget_vnd = int(round(budget_base * rng.uniform(budget_multiplier_min, budget_multiplier_max) * showroom_budget_bias))
    budget_vnd = max(2_000_000, min(85_000_000, budget_vnd))
    
    if is_foreign:
        rate, _, _, _, _, _ = fx_service.get_rate_to_vnd(db, pref_currency)
        foreign_budget = round(budget_vnd / rate, 2)
        budget_fx_rate = rate
    else:
        foreign_budget = None
        budget_fx_rate = 1.0

    request = CustomerRequest(
        customer=customer,
        request_type=_select_request_type(rng, showroom_state, archetype),
        budget_vnd=budget_vnd,
        use_case=persona["sample_use_case"] or rng.choice(USE_CASES),
        target_performance_score=max(40, min(95, rng.randint(45, 90) + prestige_score // 20 - pressure_score // 18)),
        requirements_json={
            "tone": "sample",
            "ai_generated": False,
            "persona_type": persona["persona_type"],
            "persona_label": persona["label"],
            "persona_hints": persona["preference_hints"],
            "showroom_context": {
                "reputation": save_game.reputation,
                "shop_level": save_game.shop_level,
                "ready_stock": showroom_state["ready_count"],
                "untested_stock": showroom_state["untested_count"],
                "staff_on_site": showroom_state["staff_count"],
                "active_market_events": showroom_state["active_market_events"],
            },
        },
        budget_currency=pref_currency,
        foreign_budget_amount=foreign_budget,
        budget_fx_rate_to_vnd=budget_fx_rate,
    )
    customer_persona_service.apply_persona_to_request(db, request, customer)
    db.add(customer)
    db.add(request)
    db.flush()
    from app.services import customer_conversation_service

    customer_conversation_service.create_conversation_for_customer(
        db,
        save_game_id,
        customer_id=customer.id,
        request_id=request.id,
    )
    db.commit()
    db.refresh(customer)
    db.refresh(request)
    return customer, get_request(db, request.id)


def list_customers(db: Session, save_game_id: int) -> list[Customer]:
    get_save_game(db, save_game_id)
    return list(db.scalars(select(Customer).where(Customer.save_game_id == save_game_id).order_by(Customer.created_at.desc())))


def list_requests(db: Session, save_game_id: int) -> list[CustomerRequest]:
    get_save_game(db, save_game_id)
    return list(
        db.scalars(
            select(CustomerRequest)
            .join(CustomerRequest.customer)
            .options(selectinload(CustomerRequest.customer))
            .where(Customer.save_game_id == save_game_id)
            .order_by(CustomerRequest.created_at.desc())
        )
    )


def get_request(db: Session, request_id: int) -> CustomerRequest:
    return db.scalar(select(CustomerRequest).options(selectinload(CustomerRequest.customer)).where(CustomerRequest.id == request_id))
