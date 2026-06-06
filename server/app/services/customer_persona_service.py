from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.core.errors import not_found
from app.models.entities import Customer, CustomerRequest, HardwareProduct, InventoryUnit, Quote, QuoteItem
from app.models.enums import ConditionType, CustomerArchetype, Grade, HardwareCategory, InventoryStatus


@dataclass(frozen=True)
class PersonaDefinition:
    persona_type: str
    label: str
    description: str
    budget_multiplier_range: tuple[float, float]
    accepts_used_parts_default: bool
    price_sensitivity: int
    performance_priority: int
    reliability_priority: int
    aesthetics_priority: int
    warranty_sensitivity: int
    preferred_priorities: list[str]
    default_min_compatibility_score: int
    default_min_build_quality_score: int
    preference_hints: list[str]
    preferred_brand_slugs: list[str]
    disliked_brand_slugs: list[str]
    used_part_tolerance: int
    warranty_expectation_days: int
    sample_use_case: str


PERSONA_REGISTRY: dict[str, PersonaDefinition] = {
    "BUDGET_GAMER": PersonaDefinition(
        persona_type="BUDGET_GAMER",
        label="Budget Gamer",
        description="Cares about FPS per VND and will accept a smart used-parts deal when the value is strong.",
        budget_multiplier_range=(0.65, 0.95),
        accepts_used_parts_default=True,
        price_sensitivity=92,
        performance_priority=80,
        reliability_priority=58,
        aesthetics_priority=32,
        warranty_sensitivity=55,
        preferred_priorities=["PRICE", "GAMING_PERFORMANCE", "USED_VALUE"],
        default_min_compatibility_score=60,
        default_min_build_quality_score=55,
        preference_hints=["Wants the highest FPS for the money.", "Used GPU is fine if inspection confidence is strong."],
        preferred_brand_slugs=["amd", "intel", "nvidia", "corsair", "msi"],
        disliked_brand_slugs=[],
        used_part_tolerance=78,
        warranty_expectation_days=30,
        sample_use_case="Budget esports student looking for high FPS on a tight budget.",
    ),
    "ESPORTS_PLAYER": PersonaDefinition(
        persona_type="ESPORTS_PLAYER",
        label="Esports Player",
        description="Prioritizes low latency, high FPS, and a balanced CPU/GPU pairing.",
        budget_multiplier_range=(0.8, 1.15),
        accepts_used_parts_default=False,
        price_sensitivity=60,
        performance_priority=95,
        reliability_priority=70,
        aesthetics_priority=18,
        warranty_sensitivity=62,
        preferred_priorities=["ESPORTS_FPS", "GAMING_PERFORMANCE", "LOW_POWER"],
        default_min_compatibility_score=75,
        default_min_build_quality_score=70,
        preference_hints=["Avoids bottlenecks and lag spikes.", "Wants a strong CPU/GPU balance for competitive play."],
        preferred_brand_slugs=["intel", "amd", "nvidia", "msi", "asus"],
        disliked_brand_slugs=[],
        used_part_tolerance=35,
        warranty_expectation_days=30,
        sample_use_case="Competitive player wants low-latency 240Hz-ready frame pacing.",
    ),
    "STREAMER": PersonaDefinition(
        persona_type="STREAMER",
        label="Streamer",
        description="Needs a balanced CPU/GPU setup with enough storage and RAM for encoding and multitasking.",
        budget_multiplier_range=(0.9, 1.3),
        accepts_used_parts_default=False,
        price_sensitivity=52,
        performance_priority=84,
        reliability_priority=74,
        aesthetics_priority=46,
        warranty_sensitivity=66,
        preferred_priorities=["STREAMING", "PRODUCTIVITY", "STORAGE_CAPACITY"],
        default_min_compatibility_score=70,
        default_min_build_quality_score=68,
        preference_hints=["Needs smooth CPU/GPU balance for streaming and capture.", "Prefers stable thermals during long sessions."],
        preferred_brand_slugs=["intel", "amd", "nvidia", "corsair", "asus", "nzxt"],
        disliked_brand_slugs=[],
        used_part_tolerance=42,
        warranty_expectation_days=45,
        sample_use_case="Streamer wants a balanced build for gameplay, chat, and encoding.",
    ),
    "OFFICE_BUYER": PersonaDefinition(
        persona_type="OFFICE_BUYER",
        label="Office Buyer",
        description="Wants a quiet, reliable, and low-maintenance machine more than raw speed.",
        budget_multiplier_range=(0.8, 1.1),
        accepts_used_parts_default=False,
        price_sensitivity=68,
        performance_priority=38,
        reliability_priority=94,
        aesthetics_priority=28,
        warranty_sensitivity=88,
        preferred_priorities=["RELIABILITY", "QUIETNESS", "LOW_POWER"],
        default_min_compatibility_score=72,
        default_min_build_quality_score=74,
        preference_hints=["Prefers quiet cooling and dependable parts.", "Used parts are usually a hard sell."],
        preferred_brand_slugs=["intel", "samsung", "corsair", "asus"],
        disliked_brand_slugs=["gray-market"],
        used_part_tolerance=18,
        warranty_expectation_days=60,
        sample_use_case="Quiet PC lover wants a cool, hushed workstation with low fan noise.",
    ),
    "CREATOR_EDITOR": PersonaDefinition(
        persona_type="CREATOR_EDITOR",
        label="Creator / Editor",
        description="Wants RAM, storage, CPU, and GPU balance for editing and content work.",
        budget_multiplier_range=(1.0, 1.45),
        accepts_used_parts_default=True,
        price_sensitivity=48,
        performance_priority=88,
        reliability_priority=80,
        aesthetics_priority=48,
        warranty_sensitivity=70,
        preferred_priorities=["PRODUCTIVITY", "STORAGE_CAPACITY", "RAM"],
        default_min_compatibility_score=68,
        default_min_build_quality_score=68,
        preference_hints=["Likes large RAM and fast SSDs.", "Needs a comfortable balance between CPU and GPU."],
        preferred_brand_slugs=["intel", "amd", "nvidia", "samsung", "corsair", "asus", "lian-li"],
        disliked_brand_slugs=[],
        used_part_tolerance=52,
        warranty_expectation_days=45,
        sample_use_case="Creator wants responsive editing performance with lots of memory and storage.",
    ),
    "AI_WORKSTATION": PersonaDefinition(
        persona_type="AI_WORKSTATION",
        label="AI Workstation",
        description="Wants high-end RAM, VRAM, storage, and a dependable power budget for heavier workloads.",
        budget_multiplier_range=(1.15, 1.8),
        accepts_used_parts_default=False,
        price_sensitivity=34,
        performance_priority=96,
        reliability_priority=84,
        aesthetics_priority=30,
        warranty_sensitivity=74,
        preferred_priorities=["AI_WORKLOAD", "RAM", "STORAGE_CAPACITY"],
        default_min_compatibility_score=78,
        default_min_build_quality_score=76,
        preference_hints=["Needs enough VRAM and RAM headroom.", "Will pay more for stable, high-end components."],
        preferred_brand_slugs=["nvidia", "intel", "amd", "samsung", "corsair", "seasonic", "asus"],
        disliked_brand_slugs=[],
        used_part_tolerance=20,
        warranty_expectation_days=60,
        sample_use_case="AI workstation buyer wants lots of RAM, VRAM, and storage headroom.",
    ),
    "STUDENT": PersonaDefinition(
        persona_type="STUDENT",
        label="Student",
        description="Very budget sensitive and open to good used-value deals.",
        budget_multiplier_range=(0.55, 0.85),
        accepts_used_parts_default=True,
        price_sensitivity=96,
        performance_priority=62,
        reliability_priority=48,
        aesthetics_priority=26,
        warranty_sensitivity=42,
        preferred_priorities=["PRICE", "USED_VALUE", "STORAGE_CAPACITY"],
        default_min_compatibility_score=55,
        default_min_build_quality_score=50,
        preference_hints=["Needs a strong deal, not a premium flex build.", "Used parts are acceptable if they look clean and tested."],
        preferred_brand_slugs=["intel", "amd", "samsung", "kingston", "corsair"],
        disliked_brand_slugs=[],
        used_part_tolerance=84,
        warranty_expectation_days=21,
        sample_use_case="Student needs a dependable everyday machine on a tight budget.",
    ),
    "RGB_ENTHUSIAST": PersonaDefinition(
        persona_type="RGB_ENTHUSIAST",
        label="RGB Enthusiast",
        description="Cares about aesthetics, lighting, and a polished showcase build.",
        budget_multiplier_range=(1.0, 1.5),
        accepts_used_parts_default=False,
        price_sensitivity=40,
        performance_priority=76,
        reliability_priority=62,
        aesthetics_priority=98,
        warranty_sensitivity=58,
        preferred_priorities=["AESTHETICS", "RGB", "PRODUCTIVITY"],
        default_min_compatibility_score=65,
        default_min_build_quality_score=64,
        preference_hints=["Wants white cases, RGB fans, and a tidy presentation.", "Premium showcase parts are worth the extra spend."],
        preferred_brand_slugs=["nzxt", "lian-li", "corsair", "asus", "gigabyte", "deepcool"],
        disliked_brand_slugs=[],
        used_part_tolerance=25,
        warranty_expectation_days=45,
        sample_use_case="RGB enthusiast wants a clean white build with lighting.",
    ),
    "QUIET_PC_LOVER": PersonaDefinition(
        persona_type="QUIET_PC_LOVER",
        label="Quiet PC Lover",
        description="Prioritizes quiet fans, cool thermals, and low-power reliability.",
        budget_multiplier_range=(0.85, 1.25),
        accepts_used_parts_default=False,
        price_sensitivity=54,
        performance_priority=44,
        reliability_priority=90,
        aesthetics_priority=34,
        warranty_sensitivity=82,
        preferred_priorities=["QUIETNESS", "LOW_POWER", "RELIABILITY"],
        default_min_compatibility_score=72,
        default_min_build_quality_score=74,
        preference_hints=["Dislikes hot or noisy builds.", "Wants a calm, low-drama workstation feel."],
        preferred_brand_slugs=["seasonic", "corsair", "samsung", "intel", "be quiet"],
        disliked_brand_slugs=[],
        used_part_tolerance=20,
        warranty_expectation_days=60,
        sample_use_case="Office buyer wants a quiet and reliable PC with low warranty risk.",
    ),
    "BRAND_LOYALIST": PersonaDefinition(
        persona_type="BRAND_LOYALIST",
        label="Brand Loyalist",
        description="Has favorite brands and punishes parts that feel off-brand or gray-market.",
        budget_multiplier_range=(0.9, 1.35),
        accepts_used_parts_default=False,
        price_sensitivity=44,
        performance_priority=68,
        reliability_priority=74,
        aesthetics_priority=42,
        warranty_sensitivity=68,
        preferred_priorities=["BRAND", "RELIABILITY", "AESTHETICS"],
        default_min_compatibility_score=65,
        default_min_build_quality_score=66,
        preference_hints=["Likes trusted logos and recognizable lineups.", "Gray-market parts are a hard no."],
        preferred_brand_slugs=["intel", "amd", "nvidia", "corsair", "samsung", "asus", "msi"],
        disliked_brand_slugs=["gray-market"],
        used_part_tolerance=30,
        warranty_expectation_days=45,
        sample_use_case="Brand loyalist wants a build from trusted, familiar manufacturers.",
    ),
    "WARRANTY_SENSITIVE": PersonaDefinition(
        persona_type="WARRANTY_SENSITIVE",
        label="Warranty Sensitive",
        description="Wants high inspection confidence, strong warranty coverage, and low-risk parts.",
        budget_multiplier_range=(0.85, 1.2),
        accepts_used_parts_default=False,
        price_sensitivity=36,
        performance_priority=64,
        reliability_priority=96,
        aesthetics_priority=24,
        warranty_sensitivity=100,
        preferred_priorities=["WARRANTY", "RELIABILITY", "QUIETNESS"],
        default_min_compatibility_score=80,
        default_min_build_quality_score=82,
        preference_hints=["Low-confidence used parts are heavily penalized.", "Will pay for a safer, cleaner build."],
        preferred_brand_slugs=["intel", "samsung", "corsair", "seasonic", "asus"],
        disliked_brand_slugs=[],
        used_part_tolerance=12,
        warranty_expectation_days=90,
        sample_use_case="Warranty-sensitive buyer wants a high-confidence build with low support risk.",
    ),
    "BARGAIN_HUNTER": PersonaDefinition(
        persona_type="BARGAIN_HUNTER",
        label="Bargain Hunter",
        description="Extremely price aware and comfortable with used/refurbished value hunting.",
        budget_multiplier_range=(0.5, 0.8),
        accepts_used_parts_default=True,
        price_sensitivity=98,
        performance_priority=56,
        reliability_priority=42,
        aesthetics_priority=18,
        warranty_sensitivity=28,
        preferred_priorities=["PRICE", "USED_VALUE", "LOW_POWER"],
        default_min_compatibility_score=50,
        default_min_build_quality_score=48,
        preference_hints=["Will accept gray-market or used stock if the price is right.", "Needs visible value more than prestige."],
        preferred_brand_slugs=["intel", "amd", "nvidia", "kingston", "samsung"],
        disliked_brand_slugs=[],
        used_part_tolerance=94,
        warranty_expectation_days=14,
        sample_use_case="Bargain hunter wants the cheapest workable build with acceptable risk.",
    ),
    "PREMIUM_BUILDER": PersonaDefinition(
        persona_type="PREMIUM_BUILDER",
        label="Premium Builder",
        description="High budget, high reliability, and strong aesthetics with low tolerance for weak parts.",
        budget_multiplier_range=(1.35, 2.1),
        accepts_used_parts_default=False,
        price_sensitivity=30,
        performance_priority=94,
        reliability_priority=88,
        aesthetics_priority=90,
        warranty_sensitivity=76,
        preferred_priorities=["GAMING_PERFORMANCE", "RELIABILITY", "AESTHETICS"],
        default_min_compatibility_score=82,
        default_min_build_quality_score=84,
        preference_hints=["Likes clean, expensive-looking builds.", "Weak compatibility or risky parts are deal breakers."],
        preferred_brand_slugs=["asus", "nvidia", "intel", "corsair", "nzxt", "lian-li", "seasonic"],
        disliked_brand_slugs=[],
        used_part_tolerance=12,
        warranty_expectation_days=60,
        sample_use_case="Premium buyer wants a polished high-end build with strong reliability.",
    ),
}

ARCHETYPE_TO_PERSONA_TYPES: dict[CustomerArchetype, list[str]] = {
    CustomerArchetype.GAMER: ["BUDGET_GAMER", "ESPORTS_PLAYER", "RGB_ENTHUSIAST", "PREMIUM_BUILDER"],
    CustomerArchetype.CREATOR: ["CREATOR_EDITOR", "AI_WORKSTATION", "PREMIUM_BUILDER"],
    CustomerArchetype.OFFICE: ["OFFICE_BUYER", "QUIET_PC_LOVER", "WARRANTY_SENSITIVE"],
    CustomerArchetype.BUDGET_BUYER: ["STUDENT", "BARGAIN_HUNTER", "BUDGET_GAMER"],
    CustomerArchetype.TECH_NERD: ["BRAND_LOYALIST", "PREMIUM_BUILDER", "RGB_ENTHUSIAST"],
    CustomerArchetype.BUSINESS: ["OFFICE_BUYER", "WARRANTY_SENSITIVE", "QUIET_PC_LOVER"],
    CustomerArchetype.SELLER: ["BARGAIN_HUNTER", "BRAND_LOYALIST", "STUDENT"],
}


def list_personas() -> list[dict[str, Any]]:
    return [to_persona_read_model(definition) for definition in PERSONA_REGISTRY.values()]


def get_persona_definition(persona_type: str) -> dict[str, Any]:
    definition = PERSONA_REGISTRY.get(_normalize_persona_type(persona_type))
    if not definition:
        raise not_found("Customer persona not found")
    return to_persona_read_model(definition)


def generate_customer_persona(db: Session, customer: Customer | None = None) -> dict[str, Any]:
    definition = _choose_persona_definition(customer)
    return to_persona_read_model(definition)


def apply_persona_to_customer(db: Session, customer: Customer, persona_type: str | None = None) -> Customer:
    definition = _choose_persona_definition(customer, persona_type)
    customer.persona_type = definition.persona_type
    customer.preference_json = {
        "persona_type": definition.persona_type,
        "label": definition.label,
        "description": definition.description,
        "budget_multiplier_range": list(definition.budget_multiplier_range),
        "accepts_used_parts_default": definition.accepts_used_parts_default,
        "preferred_priorities": definition.preferred_priorities,
        "preference_hints": definition.preference_hints,
        "sample_use_case": definition.sample_use_case,
        "default_min_compatibility_score": definition.default_min_compatibility_score,
        "default_min_build_quality_score": definition.default_min_build_quality_score,
        "preferred_brand_slugs": definition.preferred_brand_slugs,
        "disliked_brand_slugs": definition.disliked_brand_slugs,
        "used_part_tolerance": definition.used_part_tolerance,
        "warranty_expectation_days": definition.warranty_expectation_days,
    }
    customer.preferred_brand_slugs_json = definition.preferred_brand_slugs
    customer.disliked_brand_slugs_json = definition.disliked_brand_slugs
    customer.accepts_used_parts = definition.accepts_used_parts_default
    customer.warranty_sensitivity = definition.warranty_sensitivity
    customer.price_sensitivity = definition.price_sensitivity
    customer.performance_priority = definition.performance_priority
    customer.aesthetics_priority = definition.aesthetics_priority
    customer.reliability_priority = definition.reliability_priority
    return customer


def apply_persona_to_request(db: Session, customer_request: CustomerRequest, customer: Customer | None = None) -> CustomerRequest:
    resolved_customer = customer or customer_request.customer
    if resolved_customer and resolved_customer.persona_type:
        definition = _choose_persona_definition(resolved_customer, resolved_customer.persona_type)
    elif resolved_customer:
        definition = _choose_persona_definition(resolved_customer)
    else:
        definition = _generic_persona_definition()

    customer_request.persona_type = definition.persona_type
    customer_request.preference_json = {
        "persona_type": definition.persona_type,
        "label": definition.label,
        "description": definition.description,
        "budget_multiplier_range": list(definition.budget_multiplier_range),
        "accepts_used_parts_default": definition.accepts_used_parts_default,
        "preferred_priorities": definition.preferred_priorities,
        "preference_hints": definition.preference_hints,
        "sample_use_case": definition.sample_use_case,
        "preferred_brand_slugs": definition.preferred_brand_slugs,
        "disliked_brand_slugs": definition.disliked_brand_slugs,
        "used_part_tolerance": definition.used_part_tolerance,
        "warranty_expectation_days": definition.warranty_expectation_days,
    }
    customer_request.priority_tags_json = list(definition.preferred_priorities)
    customer_request.accepts_used_parts = definition.accepts_used_parts_default
    customer_request.min_compatibility_score = definition.default_min_compatibility_score
    customer_request.min_build_quality_score = definition.default_min_build_quality_score
    customer_request.used_part_tolerance = definition.used_part_tolerance
    customer_request.warranty_expectation_days = definition.warranty_expectation_days
    return customer_request


def evaluate_quote_for_persona(db: Session, quote: Quote) -> dict[str, Any]:
    customer_request = getattr(quote, "customer_request", None)
    customer = getattr(quote, "customer", None) or (customer_request.customer if customer_request else None)
    context = customer_request or customer
    result = evaluate_quote_items_for_preferences(db, context, quote.items, getattr(quote, "compatibility_result", None))

    quote.customer_fit_score = result["customer_fit_score"]
    quote.persona_match_score = result["persona_match_score"]
    quote.price_fit_score = result["price_fit_score"]
    quote.performance_fit_score = result["performance_fit_score"]
    quote.reliability_fit_score = result["reliability_fit_score"]
    quote.aesthetics_fit_score = result["aesthetics_fit_score"]
    quote.used_part_fit_score = result["used_part_fit_score"]
    quote.quote_acceptance_chance = result["quote_acceptance_chance"]
    quote.customer_feedback_summary = result["customer_feedback_summary"]
    quote.persona_warnings_json = result["warnings"]
    return result


def evaluate_quote_items_for_preferences(
    db: Session,
    request_or_customer: CustomerRequest | Customer | None,
    quote_items: Iterable[QuoteItem],
    compatibility_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    persona = _persona_from_request_or_customer(request_or_customer)
    items = list(quote_items or [])
    context = _quote_metric_context(items)
    quote_price = sum(item.quantity * item.unit_price_vnd for item in items)
    budget = _request_budget(request_or_customer) or max(quote_price, 1)

    price_fit_score = _score_price_fit(persona, budget, quote_price)
    performance_fit_score = _score_performance_fit(persona, context, compatibility_result)
    reliability_fit_score = _score_reliability_fit(persona, context, compatibility_result)
    aesthetics_fit_score = _score_aesthetics_fit(persona, context)
    used_part_fit_score = _score_used_part_fit(persona, context)
    brand_fit_score = _score_brand_fit(persona, context, request_or_customer)
    persona_match_score = _score_persona_match(
        persona,
        price_fit_score=price_fit_score,
        performance_fit_score=performance_fit_score,
        reliability_fit_score=reliability_fit_score,
        aesthetics_fit_score=aesthetics_fit_score,
        used_part_fit_score=used_part_fit_score,
        brand_fit_score=brand_fit_score,
    )
    customer_fit_score = _score_customer_fit(
        persona_match_score=persona_match_score,
        price_fit_score=price_fit_score,
        compatibility_result=compatibility_result,
        used_part_fit_score=used_part_fit_score,
    )
    warnings = _build_persona_warnings(
        persona,
        context,
        budget=budget,
        quote_price=quote_price,
        compatibility_result=compatibility_result,
        price_fit_score=price_fit_score,
        performance_fit_score=performance_fit_score,
        reliability_fit_score=reliability_fit_score,
        aesthetics_fit_score=aesthetics_fit_score,
        used_part_fit_score=used_part_fit_score,
        brand_fit_score=brand_fit_score,
    )
    quote_acceptance_chance = _score_acceptance_chance(
        customer_fit_score=customer_fit_score,
        price_fit_score=price_fit_score,
        reliability_fit_score=reliability_fit_score,
        compatibility_result=compatibility_result,
        request_or_customer=request_or_customer,
        warnings=warnings,
    )

    return {
        "customer_fit_score": customer_fit_score,
        "persona_match_score": persona_match_score,
        "price_fit_score": price_fit_score,
        "performance_fit_score": performance_fit_score,
        "reliability_fit_score": reliability_fit_score,
        "aesthetics_fit_score": aesthetics_fit_score,
        "used_part_fit_score": used_part_fit_score,
        "brand_fit_score": brand_fit_score,
        "quote_acceptance_chance": quote_acceptance_chance,
        "warnings": warnings,
        "customer_feedback_summary": build_customer_feedback_summary(
            {
                "customer_fit_score": customer_fit_score,
                "persona_match_score": persona_match_score,
                "price_fit_score": price_fit_score,
                "performance_fit_score": performance_fit_score,
                "reliability_fit_score": reliability_fit_score,
                "aesthetics_fit_score": aesthetics_fit_score,
                "used_part_fit_score": used_part_fit_score,
                "quote_acceptance_chance": quote_acceptance_chance,
            },
            warnings,
        ),
    }


def compute_quote_acceptance_chance(db: Session, quote: Quote) -> int:
    return int(evaluate_quote_for_persona(db, quote)["quote_acceptance_chance"])


def build_customer_feedback_summary(scores: dict[str, Any], warnings: list[dict[str, Any]]) -> str:
    fit = int(scores.get("customer_fit_score") or 0)
    acceptance = int(scores.get("quote_acceptance_chance") or 0)
    price_fit = int(scores.get("price_fit_score") or 0)
    reliability = int(scores.get("reliability_fit_score") or 0)
    performance = int(scores.get("performance_fit_score") or 0)

    if acceptance >= 80 and fit >= 75:
        summary = "Strong match for this customer."
    elif acceptance >= 60:
        summary = "Mostly aligned, with a few tradeoffs."
    elif acceptance >= 40:
        summary = "Borderline fit; the customer may need convincing."
    else:
        summary = "Weak fit for the customer's stated preferences."

    if warnings:
        top_warning = warnings[0]["message"]
        summary = f"{summary} {top_warning}"
    elif price_fit < 50:
        summary = f"{summary} The price is still a bit sharp for this buyer."
    elif reliability < 55:
        summary = f"{summary} Reliability is the main concern."
    elif performance < 55:
        summary = f"{summary} Performance is a little under target."
    return summary


def to_persona_read_model(definition: PersonaDefinition) -> dict[str, Any]:
    data = asdict(definition)
    data["budget_multiplier_range"] = list(definition.budget_multiplier_range)
    return data


def _choose_persona_definition(customer: Customer | None = None, persona_type: str | None = None) -> PersonaDefinition:
    if persona_type:
        definition = PERSONA_REGISTRY.get(_normalize_persona_type(persona_type))
        if definition:
            return definition
        raise not_found("Customer persona not found")
    if customer and customer.persona_type:
        definition = PERSONA_REGISTRY.get(_normalize_persona_type(customer.persona_type))
        if definition:
            return definition
    if customer:
        return _choose_persona_for_customer(customer)
    return _choose_persona_by_seed("default")


def _choose_persona_for_customer(customer: Customer) -> PersonaDefinition:
    candidate_types = _persona_candidates_for_archetype(customer.archetype)
    seed = _customer_seed(customer)
    if not candidate_types:
        return _choose_persona_by_seed(seed)
    index = int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8], 16) % len(candidate_types)
    persona_type = candidate_types[index]
    return PERSONA_REGISTRY.get(persona_type, _generic_persona_definition())


def _choose_persona_by_seed(seed: str) -> PersonaDefinition:
    values = list(PERSONA_REGISTRY.values())
    if not values:
        return _generic_persona_definition()
    index = int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8], 16) % len(values)
    return values[index]


def _persona_candidates_for_archetype(archetype: CustomerArchetype | str | None) -> list[str]:
    if archetype is None:
        return list(PERSONA_REGISTRY.keys())
    archetype_value = archetype.value if hasattr(archetype, "value") else str(archetype)
    try:
        archetype_enum = CustomerArchetype(archetype_value)
    except Exception:
        return list(PERSONA_REGISTRY.keys())
    return ARCHETYPE_TO_PERSONA_TYPES.get(archetype_enum, list(PERSONA_REGISTRY.keys()))


def _persona_from_request_or_customer(request_or_customer: CustomerRequest | Customer | None) -> PersonaDefinition:
    if request_or_customer is None:
        return _generic_persona_definition()
    persona_type = getattr(request_or_customer, "persona_type", None)
    if persona_type:
        definition = PERSONA_REGISTRY.get(_normalize_persona_type(persona_type))
        if definition:
            return definition
    customer = getattr(request_or_customer, "customer", None)
    if customer and getattr(customer, "persona_type", None):
        definition = PERSONA_REGISTRY.get(_normalize_persona_type(customer.persona_type))
        if definition:
            return definition
    if isinstance(request_or_customer, Customer):
        return _choose_persona_for_customer(request_or_customer)
    if isinstance(request_or_customer, CustomerRequest) and customer:
        return _choose_persona_for_customer(customer)
    return _generic_persona_definition()


def _generic_persona_definition() -> PersonaDefinition:
    return PersonaDefinition(
        persona_type="GENERIC",
        label="Generic Customer",
        description="A neutral customer with balanced expectations and no strong persona bias.",
        budget_multiplier_range=(0.9, 1.1),
        accepts_used_parts_default=True,
        price_sensitivity=55,
        performance_priority=55,
        reliability_priority=55,
        aesthetics_priority=40,
        warranty_sensitivity=55,
        preferred_priorities=["PRICE", "RELIABILITY"],
        default_min_compatibility_score=55,
        default_min_build_quality_score=55,
        preference_hints=["Neutral buyer with balanced expectations."],
        preferred_brand_slugs=[],
        disliked_brand_slugs=[],
        used_part_tolerance=50,
        warranty_expectation_days=30,
        sample_use_case="General-purpose customer wants a sensible balanced PC.",
    )


def _customer_seed(customer: Customer) -> str:
    return "|".join(
        [
            str(customer.save_game_id),
            customer.name,
            customer.archetype.value if hasattr(customer.archetype, "value") else str(customer.archetype),
            customer.knowledge_level.value if hasattr(customer.knowledge_level, "value") else str(customer.knowledge_level),
            str(customer.patience),
            str(customer.negotiation_score),
            customer.risk_tolerance.value if hasattr(customer.risk_tolerance, "value") else str(customer.risk_tolerance),
        ]
    )


def _request_budget(request_or_customer: CustomerRequest | Customer | None) -> int:
    if isinstance(request_or_customer, CustomerRequest):
        return int(request_or_customer.budget_vnd or 0)
    return 0


def _quote_metric_context(quote_items: Iterable[QuoteItem]) -> dict[str, Any]:
    products = [item.product for item in quote_items if item.product]
    inventory_units = [item.inventory_unit for item in quote_items if item.inventory_unit]
    brands = [_brand_slug(product) for product in products if _brand_slug(product)]
    used_units = [unit for unit in inventory_units if unit and unit.condition_type not in {ConditionType.NEW, ConditionType.OPEN_BOX}]
    used_confidences = [unit.inspection_confidence for unit in used_units if unit]

    return {
        "products": products,
        "inventory_units": inventory_units,
        "brands": brands,
        "used_units": used_units,
        "used_confidence_avg": int(sum(used_confidences) / len(used_confidences)) if used_confidences else None,
        "cpu_performance": _category_score(products, HardwareCategory.CPU),
        "gpu_performance": _category_score(products, HardwareCategory.GPU),
        "ram_capacity_gb": _ram_capacity_gb(products),
        "storage_capacity_tb": _storage_capacity_tb(products),
        "gpu_vram_gb": _gpu_vram_gb(products),
        "total_performance": int(sum(product.base_performance_score for product in products) / len(products)) if products else 0,
        "total_reliability": int(sum(product.base_reliability_score for product in products) / len(products)) if products else 0,
        "total_heat": int(sum(product.base_heat_score for product in products) / len(products)) if products else 0,
        "total_power": int(sum(product.base_power_watts for product in products) / len(products)) if products else 0,
        "has_rgb": any(_has_aesthetic_keyword(product) for product in products),
        "aesthetic_hits": sum(1 for product in products if _has_aesthetic_keyword(product)),
        "brand_slugs": brands,
        "used_risk_points": sum(_used_risk_points(unit) for unit in used_units if unit),
        "ready_for_resale_count": sum(1 for unit in inventory_units if unit and unit.ready_for_resale),
    }


def _score_price_fit(persona: PersonaDefinition, budget: int, quote_price: int) -> int:
    if quote_price <= 0:
        return 50
    ratio = quote_price / max(budget, 1)
    if ratio <= 0.85:
        score = 96
    elif ratio <= 1.0:
        score = 88
    elif ratio <= 1.1:
        score = 72
    elif ratio <= 1.2:
        score = 58
    elif ratio <= 1.35:
        score = 42
    else:
        score = 25

    if persona.price_sensitivity >= 90:
        score += 4 if ratio <= 1.0 else -18 if ratio > 1.0 else 0
    elif persona.price_sensitivity <= 40:
        score += 8 if ratio <= 1.15 else -8 if ratio > 1.35 else 0
    return _clamp(score)


def _score_performance_fit(
    persona: PersonaDefinition,
    context: dict[str, Any],
    compatibility_result: dict[str, Any] | None,
) -> int:
    compatibility_bonus = int(compatibility_result.get("bottleneck_score", 70)) if compatibility_result else 70
    if persona.persona_type == "ESPORTS_PLAYER":
        base = _weighted_pair_score(context["cpu_performance"], context["gpu_performance"], compatibility_bonus)
    elif persona.persona_type == "STREAMER":
        base = _weighted_streamer_score(context, compatibility_bonus)
    elif persona.persona_type == "CREATOR_EDITOR":
        base = _weighted_creator_score(context, compatibility_bonus)
    elif persona.persona_type == "AI_WORKSTATION":
        base = _weighted_ai_score(context, compatibility_bonus)
    elif persona.persona_type == "OFFICE_BUYER" or persona.persona_type == "QUIET_PC_LOVER":
        base = 62 + min(18, compatibility_bonus // 6)
    elif persona.persona_type == "BUDGET_GAMER" or persona.persona_type == "BARGAIN_HUNTER" or persona.persona_type == "STUDENT":
        base = _clamp(int(context["total_performance"] * 0.55 + compatibility_bonus * 0.25 + _value_ratio_bonus(context)))
    else:
        base = _clamp(int(context["total_performance"] * 0.65 + compatibility_bonus * 0.35))
    return _clamp(base)


def _score_reliability_fit(
    persona: PersonaDefinition,
    context: dict[str, Any],
    compatibility_result: dict[str, Any] | None,
) -> int:
    score = int(context["total_reliability"] * 0.75)
    score += min(14, int((compatibility_result or {}).get("build_quality_score_estimate", 70)) // 8)
    score += min(10, int((compatibility_result or {}).get("warranty_risk_delta", 0)) * -2)

    used_risk_points = context["used_risk_points"]
    score -= min(24, used_risk_points * 3)
    if persona.warranty_sensitivity >= 80:
        score += 6 if used_risk_points == 0 else -12
    elif persona.warranty_sensitivity <= 35:
        score += 4 if used_risk_points > 0 else 0
    return _clamp(score)


def _score_aesthetics_fit(persona: PersonaDefinition, context: dict[str, Any]) -> int:
    score = 48
    if context["has_rgb"]:
        score += 28
    score += min(18, context["aesthetic_hits"] * 6)
    combined_text = " ".join(" ".join(_product_text(product)) for product in context["products"]).upper()
    score += 8 if any(keyword in combined_text for keyword in ["WHITE", "SAKURA", "ROYAL", "O11", "H9"]) else 0
    if persona.persona_type == "RGB_ENTHUSIAST":
        score += 20
    elif persona.aesthetics_priority < 30:
        score -= 8
    return _clamp(score)


def _score_used_part_fit(persona: PersonaDefinition, context: dict[str, Any]) -> int:
    used_units = context["used_units"]
    if not used_units:
        return 78 if persona.accepts_used_parts_default else 72

    total = 0
    for unit in used_units:
        total += _used_unit_fit_score(unit)
    score = total // len(used_units)

    if persona.accepts_used_parts_default:
        score += 10
    else:
        score -= 8

    if persona.warranty_sensitivity >= 80:
        score -= 12
    if persona.used_part_tolerance >= 80:
        score += 8
    return _clamp(score)


def _score_persona_match(
    persona: PersonaDefinition,
    *,
    price_fit_score: int,
    performance_fit_score: int,
    reliability_fit_score: int,
    aesthetics_fit_score: int,
    used_part_fit_score: int,
    brand_fit_score: int,
) -> int:
    weighted_total = (
        price_fit_score * max(1, persona.price_sensitivity)
        + performance_fit_score * max(1, persona.performance_priority)
        + reliability_fit_score * max(1, persona.reliability_priority)
        + aesthetics_fit_score * max(1, persona.aesthetics_priority)
        + used_part_fit_score * max(1, persona.used_part_tolerance)
        + brand_fit_score * max(1, 80 if persona.persona_type == "BRAND_LOYALIST" else 35 if persona.persona_type in {"RGB_ENTHUSIAST", "PREMIUM_BUILDER"} else 20)
    )
    weight_sum = (
        max(1, persona.price_sensitivity)
        + max(1, persona.performance_priority)
        + max(1, persona.reliability_priority)
        + max(1, persona.aesthetics_priority)
        + max(1, persona.used_part_tolerance)
        + max(1, 80 if persona.persona_type == "BRAND_LOYALIST" else 35 if persona.persona_type in {"RGB_ENTHUSIAST", "PREMIUM_BUILDER"} else 20)
    )
    return _clamp(round(weighted_total / weight_sum))


def _score_customer_fit(
    *,
    persona_match_score: int,
    price_fit_score: int,
    compatibility_result: dict[str, Any] | None,
    used_part_fit_score: int,
) -> int:
    compatibility_score = int((compatibility_result or {}).get("compatibility_score", 70))
    build_quality = int((compatibility_result or {}).get("build_quality_score_estimate", 70))
    score = round(
        persona_match_score * 0.42
        + price_fit_score * 0.24
        + compatibility_score * 0.18
        + build_quality * 0.10
        + used_part_fit_score * 0.06
    )
    return _clamp(score)


def _score_acceptance_chance(
    *,
    customer_fit_score: int,
    price_fit_score: int,
    reliability_fit_score: int,
    compatibility_result: dict[str, Any] | None,
    request_or_customer: CustomerRequest | Customer | None,
    warnings: list[dict[str, Any]],
) -> int:
    compatibility_score = int((compatibility_result or {}).get("compatibility_score", 70))
    build_quality = int((compatibility_result or {}).get("build_quality_score_estimate", 70))
    min_compatibility = int(getattr(request_or_customer, "min_compatibility_score", 0) or 0)
    min_build_quality = int(getattr(request_or_customer, "min_build_quality_score", 0) or 0)

    score = round(
        customer_fit_score * 0.48
        + price_fit_score * 0.18
        + reliability_fit_score * 0.10
        + compatibility_score * 0.12
        + build_quality * 0.12
    )
    if compatibility_score < min_compatibility:
        score -= 20
    if build_quality < min_build_quality:
        score -= 12
    if any(warning["severity"] == "CRITICAL" for warning in warnings):
        score -= 18
    if any(warning["code"] == "USED_PART_RISK" for warning in warnings):
        score -= 10
    if any(warning["code"] == "OVER_BUDGET" for warning in warnings):
        score -= 8
    return _clamp(score)


def _score_brand_fit(persona: PersonaDefinition, context: dict[str, Any], request_or_customer: CustomerRequest | Customer | None) -> int:
    brand_slugs = context["brand_slugs"]
    if not brand_slugs:
        return 70 if not persona.preferred_brand_slugs else 55

    preferred = set(persona.preferred_brand_slugs) | set(_request_or_customer_preferred_brands(request_or_customer))
    disliked = set(persona.disliked_brand_slugs) | set(_request_or_customer_disliked_brands(request_or_customer))
    matches = preferred.intersection(brand_slugs)
    negatives = disliked.intersection(brand_slugs)
    score = 60
    if matches:
        score += min(30, len(matches) * 12)
    else:
        score -= 8 if preferred else 0
    if negatives:
        score -= min(30, len(negatives) * 12)
    if persona.persona_type == "BRAND_LOYALIST":
        score += 10 if matches else -10
    return _clamp(score)


def _build_persona_warnings(
    persona: PersonaDefinition,
    context: dict[str, Any],
    *,
    budget: int,
    quote_price: int,
    compatibility_result: dict[str, Any] | None,
    price_fit_score: int,
    performance_fit_score: int,
    reliability_fit_score: int,
    aesthetics_fit_score: int,
    used_part_fit_score: int,
    brand_fit_score: int,
) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    compatibility_score = int((compatibility_result or {}).get("compatibility_score", 70))
    build_quality = int((compatibility_result or {}).get("build_quality_score_estimate", 70))
    warranty_risk_delta = int((compatibility_result or {}).get("warranty_risk_delta", 0))
    bottleneck_score = int((compatibility_result or {}).get("bottleneck_score", 70))
    thermal_score = int((compatibility_result or {}).get("thermal_score", 70))

    if quote_price > budget:
        _add_persona_warning(
            warnings,
            "WARNING",
            "OVER_BUDGET",
            f"Quote is above budget by {quote_price - budget:,} VND.",
            ["PRICE"],
        )
    if compatibility_score < persona.default_min_compatibility_score:
        _add_persona_warning(
            warnings,
            "WARNING",
            "LOW_COMPATIBILITY",
            f"Compatibility score {compatibility_score} is below the buyer's comfort threshold.",
            ["COMPATIBILITY"],
        )
    if build_quality < persona.default_min_build_quality_score:
        _add_persona_warning(
            warnings,
            "WARNING",
            "LOW_BUILD_QUALITY",
            f"Build quality estimate {build_quality} is below the buyer's expected level.",
            ["BUILD_QUALITY"],
        )
    if used_part_fit_score < 55 and context["used_units"]:
        _add_persona_warning(
            warnings,
            "WARNING",
            "USED_PART_RISK",
            "Used or refurbished parts feel too risky for this customer.",
            [unit.product.category.value if hasattr(unit.product.category, "value") else str(unit.product.category) for unit in context["used_units"][:3]],
        )
    if persona.persona_type == "BRAND_LOYALIST" and context["brand_slugs"]:
        preferred = set(persona.preferred_brand_slugs)
        disliked = set(persona.disliked_brand_slugs)
        if not preferred.intersection(context["brand_slugs"]):
            _add_persona_warning(
                warnings,
                "INFO",
                "BRAND_MISMATCH",
                "The quote does not include any of the customer's favorite brands.",
                ["BRAND"],
            )
        if disliked.intersection(context["brand_slugs"]):
            _add_persona_warning(
                warnings,
                "WARNING",
                "BRAND_MISMATCH",
                "The quote includes a brand the customer tends to avoid.",
                ["BRAND"],
            )
    elif brand_fit_score < 55:
        _add_persona_warning(
            warnings,
            "INFO",
            "BRAND_MISMATCH",
            "The brands in this quote do not line up especially well with the customer's preferences.",
            ["BRAND"],
        )
    if persona.persona_type == "RGB_ENTHUSIAST" and aesthetics_fit_score < 65:
        _add_persona_warning(
            warnings,
            "INFO",
            "AESTHETICS_MISMATCH",
            "The build does not feel flashy enough for an RGB-focused buyer.",
            ["AESTHETICS"],
        )
    if persona.persona_type == "QUIET_PC_LOVER" and thermal_score < 70:
        _add_persona_warning(
            warnings,
            "WARNING",
            "QUIETNESS_RISK",
            "Thermal headroom looks a little noisy or hot for a quiet-build customer.",
            ["COOLING"],
        )
    if persona.persona_type in {"ESPORTS_PLAYER", "PREMIUM_BUILDER"} and bottleneck_score < 70:
        _add_persona_warning(
            warnings,
            "INFO",
            "BALANCE_RISK",
            "The CPU/GPU balance is a little uneven for this customer.",
            ["CPU", "GPU"],
        )
    if reliability_fit_score < 55:
        _add_persona_warning(
            warnings,
            "WARNING",
            "RELIABILITY_RISK",
            "The overall reliability feels below this buyer's comfort level.",
            ["RELIABILITY"],
        )
    if price_fit_score < 55:
        _add_persona_warning(
            warnings,
            "INFO",
            "PRICE_SQUEEZE",
            "The pricing leaves less room for comfort or upgrades.",
            ["PRICE"],
        )
    if warranty_risk_delta >= 8 or any(unit.inspection_confidence < 40 for unit in context["used_units"]):
        _add_persona_warning(
            warnings,
            "WARNING",
            "WARRANTY_RISK",
            "Warranty exposure is elevated for this quote.",
            ["WARRANTY"],
        )
    return warnings


def _add_persona_warning(
    warnings: list[dict[str, Any]],
    severity: str,
    code: str,
    message: str,
    affected_categories: list[str],
) -> None:
    warning = {
        "severity": severity,
        "code": code,
        "message": message,
        "affected_categories": _dedupe_preserve_order([category for category in affected_categories if category]),
    }
    if any(existing["code"] == code and existing["message"] == message for existing in warnings):
        return
    warnings.append(warning)


def _weighted_pair_score(cpu_performance: int | None, gpu_performance: int | None, compatibility_bonus: int) -> int:
    values = [value for value in (cpu_performance, gpu_performance) if value is not None]
    if not values:
        return 55 + min(20, compatibility_bonus // 5)
    balance = _balance_bonus(values)
    return _clamp(int(sum(values) / len(values) * 0.72 + compatibility_bonus * 0.18 + balance))


def _weighted_streamer_score(context: dict[str, Any], compatibility_bonus: int) -> int:
    score = (
        context["cpu_performance"] * 0.28
        + context["gpu_performance"] * 0.26
        + min(100, context["ram_capacity_gb"] * 2.0) * 0.22
        + min(100, context["storage_capacity_tb"] * 25.0) * 0.18
        + compatibility_bonus * 0.06
    )
    return _clamp(round(score))


def _weighted_creator_score(context: dict[str, Any], compatibility_bonus: int) -> int:
    score = (
        context["cpu_performance"] * 0.35
        + min(100, context["ram_capacity_gb"] * 1.6) * 0.27
        + min(100, context["storage_capacity_tb"] * 26.0) * 0.18
        + context["gpu_performance"] * 0.14
        + compatibility_bonus * 0.06
    )
    return _clamp(round(score))


def _weighted_ai_score(context: dict[str, Any], compatibility_bonus: int) -> int:
    score = (
        context["cpu_performance"] * 0.22
        + min(100, context["ram_capacity_gb"] * 2.1) * 0.30
        + min(100, context["gpu_vram_gb"] * 8.0) * 0.26
        + min(100, context["storage_capacity_tb"] * 22.0) * 0.14
        + compatibility_bonus * 0.08
    )
    return _clamp(round(score))


def _value_ratio_bonus(context: dict[str, Any]) -> int:
    parts = max(1, len(context["products"]))
    return min(16, round(context["total_performance"] / parts * 0.2))


def _balance_bonus(values: list[int]) -> int:
    if len(values) < 2:
        return 8
    strongest = max(values)
    weakest = min(values)
    ratio = weakest / max(strongest, 1)
    return 10 if ratio >= 0.85 else 6 if ratio >= 0.7 else 2 if ratio >= 0.5 else -6


def _category_score(products: list[HardwareProduct], category: HardwareCategory) -> int:
    values = [product.base_performance_score for product in products if product.category == category]
    return int(sum(values) / len(values)) if values else 0


def _ram_capacity_gb(products: list[HardwareProduct]) -> int:
    total = 0
    for product in products:
        if product.category != HardwareCategory.RAM:
            continue
        total += _int_from_specs(product, ("capacity_gb", "capacity"))
    return total


def _storage_capacity_tb(products: list[HardwareProduct]) -> float:
    total = 0.0
    for product in products:
        if product.category not in {HardwareCategory.SSD, HardwareCategory.STORAGE}:
            continue
        tb = _float_from_specs(product, ("capacity_tb", "capacity"))
        if tb is not None:
            total += tb
            continue
        gb = _int_from_specs(product, ("capacity_gb",))
        if gb is not None:
            total += gb / 1024
    return total


def _gpu_vram_gb(products: list[HardwareProduct]) -> int:
    values = []
    for product in products:
        if product.category != HardwareCategory.GPU:
            continue
        vram = _int_from_specs(product, ("vram_gb", "memory_gb"))
        if vram is not None:
            values.append(vram)
    return max(values) if values else 0


def _int_from_specs(product: HardwareProduct, keys: tuple[str, ...]) -> int | None:
    for source in (product.real_specs_json, product.specs_json, product.game_balance_json):
        if not isinstance(source, dict):
            continue
        for key in keys:
            value = source.get(key)
            if value not in (None, "", [], {}):
                parsed = _parse_int(value)
                if parsed is not None:
                    return parsed
    return None


def _float_from_specs(product: HardwareProduct, keys: tuple[str, ...]) -> float | None:
    for source in (product.real_specs_json, product.specs_json, product.game_balance_json):
        if not isinstance(source, dict):
            continue
        for key in keys:
            value = source.get(key)
            if value not in (None, "", [], {}):
                try:
                    return float(str(value).replace(",", ""))
                except ValueError:
                    continue
    return None


def _brand_slug(product: HardwareProduct) -> str | None:
    if getattr(product, "brand_ref", None) and getattr(product.brand_ref, "slug", None):
        return product.brand_ref.slug
    return _slugify(product.brand)


def _has_aesthetic_keyword(product: HardwareProduct) -> bool:
    text = " ".join(_product_text(product)).upper()
    keywords = ("RGB", "WHITE", "SAKURA", "ROYAL", "O11", "H9", "VISION", "SUPRIM", "AERO", "FLOW", "STEALTH")
    return any(keyword in text for keyword in keywords)


def _product_text(product: HardwareProduct) -> list[str]:
    parts = [product.name, product.brand, product.source_name or "", product.notes or ""]
    specs = product.real_specs_json or product.specs_json or product.game_balance_json or {}
    if isinstance(specs, dict):
        parts.extend(str(value) for value in specs.values() if value is not None)
    return [part for part in parts if part]


def _used_unit_fit_score(unit: InventoryUnit) -> int:
    score = 60
    score += {
        ConditionType.NEW: 25,
        ConditionType.OPEN_BOX: 18,
        ConditionType.REFURBISHED: 16,
        ConditionType.USED: -8,
        ConditionType.DEFECTIVE: -40,
        ConditionType.FOR_PARTS: -55,
    }[unit.condition_type]
    score += {
        Grade.A_PLUS: 10,
        Grade.A: 8,
        Grade.B: 4,
        Grade.C: 0,
        Grade.D: -8,
        Grade.F: -24,
        Grade.UNKNOWN: -14,
    }[unit.grade]
    score += min(12, unit.inspection_confidence // 8)
    if unit.ready_for_resale:
        score += 6
    if unit.status == InventoryStatus.UNTESTED:
        score -= 8
    if unit.inspection_confidence < 40:
        score -= 10
    return _clamp(score)


def _used_risk_points(unit: InventoryUnit) -> int:
    points = 0
    if unit.condition_type == ConditionType.USED:
        points += 4
    elif unit.condition_type == ConditionType.REFURBISHED:
        points += 2
    elif unit.condition_type in {ConditionType.DEFECTIVE, ConditionType.FOR_PARTS}:
        points += 12
    if unit.grade in {Grade.D, Grade.F, Grade.UNKNOWN}:
        points += 4
    if unit.inspection_confidence < 30:
        points += 6
    elif unit.inspection_confidence < 50:
        points += 3
    return points


def _parse_int(value: Any) -> int | None:
    if value in (None, "", False):
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    match = re.search(r"-?\d+", text.replace(",", ""))
    if not match:
        return None
    return int(match.group(0))


def _request_or_customer_preferred_brands(request_or_customer: CustomerRequest | Customer | None) -> list[str]:
    if request_or_customer is None:
        return []
    brands = getattr(request_or_customer, "preferred_brand_slugs_json", None)
    if brands:
        return [str(brand) for brand in brands if brand]
    if getattr(request_or_customer, "customer", None) is not None:
        customer = request_or_customer.customer
        if getattr(customer, "preferred_brand_slugs_json", None):
            return [str(brand) for brand in (customer.preferred_brand_slugs_json or []) if brand]
    preference_json = getattr(request_or_customer, "preference_json", None)
    if isinstance(preference_json, dict):
        preferred_brands = preference_json.get("preferred_brand_slugs")
        if isinstance(preferred_brands, list):
            return [str(brand) for brand in preferred_brands if brand]
    return []


def _request_or_customer_disliked_brands(request_or_customer: CustomerRequest | Customer | None) -> list[str]:
    if request_or_customer is None:
        return []
    brands = getattr(request_or_customer, "disliked_brand_slugs_json", None)
    if brands:
        return [str(brand) for brand in brands if brand]
    customer = getattr(request_or_customer, "customer", None)
    if customer and getattr(customer, "disliked_brand_slugs_json", None):
        return [str(brand) for brand in (customer.disliked_brand_slugs_json or []) if brand]
    preference_json = getattr(request_or_customer, "preference_json", None)
    if isinstance(preference_json, dict):
        disliked_brands = preference_json.get("disliked_brand_slugs")
        if isinstance(disliked_brands, list):
            return [str(brand) for brand in disliked_brands if brand]
    return []


def _request_or_customer_priority_tags(request_or_customer: CustomerRequest | Customer | None) -> list[str]:
    if request_or_customer is None:
        return []
    tags = getattr(request_or_customer, "priority_tags_json", None)
    if tags:
        return list(tags)
    preference_json = getattr(request_or_customer, "preference_json", None)
    if isinstance(preference_json, dict):
        return list(preference_json.get("preferred_priorities", []))
    customer = getattr(request_or_customer, "customer", None)
    if customer and isinstance(customer.preference_json, dict):
        return list(customer.preference_json.get("preferred_priorities", []))
    return []


def _normalize_persona_type(persona_type: str) -> str:
    return str(persona_type).strip().upper().replace(" ", "_")


def _slugify(value: str) -> str:
    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def _dedupe_preserve_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen or value is None:
            continue
        seen.add(value)
        result.append(value)
    return result


def _clamp(value: int | float, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, int(round(value))))
