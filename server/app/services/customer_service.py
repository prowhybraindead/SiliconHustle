from random import Random

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.entities import Customer, CustomerRequest
from app.models.enums import CustomerArchetype, KnowledgeLevel, RequestType, RiskTolerance
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


def generate_sample_customer(db: Session, save_game_id: int) -> tuple[Customer, CustomerRequest]:
    save_game = get_save_game(db, save_game_id)
    existing_count = len(save_game.customers)
    rng = Random(f"customer:{save_game_id}:{save_game.game_day}:{existing_count}")
    archetypes = list(CustomerArchetype)
    request_types = [RequestType.BUILD_PC, RequestType.BUY_COMPONENT, RequestType.UPGRADE_PC, RequestType.REPAIR]
    archetype = archetypes[rng.randrange(len(archetypes))]

    # 15% chance of foreign customer
    is_foreign = rng.random() < 0.15
    if is_foreign:
        pref_currency = rng.choice(list(FOREIGN_CURRENCIES.keys()))
        country_code = FOREIGN_CURRENCIES[pref_currency]
    else:
        pref_currency = "VND"
        country_code = "VN"

    customer = Customer(
        save_game_id=save_game_id,
        name=NAMES[rng.randrange(len(NAMES))],
        archetype=archetype,
        knowledge_level=rng.choice(list(KnowledgeLevel)),
        patience=rng.randint(35, 95),
        negotiation_score=rng.randint(20, 90),
        risk_tolerance=rng.choice(list(RiskTolerance)),
        country_code=country_code,
        preferred_currency=pref_currency,
    )
    persona = customer_persona_service.generate_customer_persona(db, customer)
    customer_persona_service.apply_persona_to_customer(db, customer, persona["persona_type"])

    budget_floor = 8_000_000
    budget_ceiling = 45_000_000
    budget_base = rng.randrange(budget_floor, budget_ceiling + 1, 1_000_000)
    budget_multiplier_min, budget_multiplier_max = persona["budget_multiplier_range"]
    budget_vnd = int(round(budget_base * rng.uniform(budget_multiplier_min, budget_multiplier_max)))
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
        request_type=rng.choice(request_types),
        budget_vnd=budget_vnd,
        use_case=persona["sample_use_case"] or rng.choice(USE_CASES),
        target_performance_score=rng.randint(45, 90),
        requirements_json={
            "tone": "sample",
            "ai_generated": False,
            "persona_type": persona["persona_type"],
            "persona_label": persona["label"],
            "persona_hints": persona["preference_hints"],
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
