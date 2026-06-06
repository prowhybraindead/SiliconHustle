import random
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import not_found, bad_request
from app.models.entities import MarketEvent, HardwareProduct, SaveGame, SupplierOffer, Supplier, PurchaseOrder
from app.models.enums import MarketEventType, MarketEventGenerationSource
from app.services.ai_service import AIService

def get_save_game_local(db: Session, save_game_id: int) -> SaveGame:
    save_game = db.get(SaveGame, save_game_id)
    if not save_game:
        raise not_found("Save game not found")
    return save_game

TEMPLATES = [
    {
        "event_type": "MINING_BOOM",
        "title": "Crypto Mining Resurgence",
        "summary": "A sudden surge in proof-of-work cryptocurrency profitability has miners grabbing high-performance GPUs.",
        "affected_category": "GPU",
        "price_multiplier": 1.75,
        "demand_delta": 40,
        "supply_delta": -30,
        "reliability_delta": 0,
        "quality_risk_delta": 15
    },
    {
        "event_type": "MINING_CRASH",
        "title": "Crypto Hashrate Crash",
        "summary": "Mining profitability crashes. Ex-mining GPUs flood the used market, causing prices to plummet.",
        "affected_category": "GPU",
        "price_multiplier": 0.55,
        "demand_delta": -25,
        "supply_delta": 60,
        "reliability_delta": -10,
        "quality_risk_delta": 25
    },
    {
        "event_type": "AI_DATACENTER_DEMAND",
        "title": "AI Datacenter Expansion",
        "summary": "Enterprise demand for AI training cluster components triggers extreme shortages of RAM and high-capacity SSDs.",
        "affected_category": "RAM",
        "price_multiplier": 1.6,
        "demand_delta": 35,
        "supply_delta": -20,
        "reliability_delta": 0,
        "quality_risk_delta": 0
    },
    {
        "event_type": "NEW_GPU_GENERATION",
        "title": "Next-Gen Graphics Launch",
        "summary": "The release of ultra-fast next-generation graphics cards drives down demand and pricing for older models.",
        "affected_category": "GPU",
        "price_multiplier": 0.7,
        "demand_delta": -15,
        "supply_delta": 20,
        "reliability_delta": 0,
        "quality_risk_delta": 0
    },
    {
        "event_type": "SUPPLY_SHORTAGE",
        "title": "Silicon Wafer Shortage",
        "summary": "Global logistics disruptions bottleneck major silicon wafer fabricators, raising costs for all components.",
        "affected_category": "CPU",
        "price_multiplier": 1.3,
        "demand_delta": 10,
        "supply_delta": -30,
        "reliability_delta": 0,
        "quality_risk_delta": 5
    },
    {
        "event_type": "OVERSUPPLY_CLEARANCE",
        "title": "Retailer Inventory Clearance",
        "summary": "Major retail brands clear warehouse stock, offering steep discounts on older cases.",
        "affected_category": "CASE",
        "price_multiplier": 0.6,
        "demand_delta": 5,
        "supply_delta": 40,
        "reliability_delta": 0,
        "quality_risk_delta": 0
    },
    {
        "event_type": "ESPORTS_SEASON",
        "title": "Esports Championship Season",
        "summary": "Gaming tournaments spark a demand spike for gaming GPUs and high-refresh-rate monitors.",
        "affected_category": "MONITOR",
        "price_multiplier": 1.2,
        "demand_delta": 25,
        "supply_delta": -5,
        "reliability_delta": 0,
        "quality_risk_delta": 0
    },
    {
        "event_type": "BACK_TO_SCHOOL",
        "title": "Back-to-School Season Rush",
        "summary": "Student laptop and home computer purchases drive high demand for entry-level CPUs, RAM, and SSDs.",
        "affected_category": "CPU",
        "price_multiplier": 1.15,
        "demand_delta": 20,
        "supply_delta": -10,
        "reliability_delta": 0,
        "quality_risk_delta": 0
    },
    {
        "event_type": "DEFECTIVE_BATCH_RUMOR",
        "title": "Defective Controller Rumor",
        "summary": "Rumors of high failure rates in a popular brand of storage controllers lower consumer demand and trust.",
        "affected_category": "STORAGE",
        "price_multiplier": 0.8,
        "demand_delta": -30,
        "supply_delta": 10,
        "reliability_delta": -20,
        "quality_risk_delta": 30
    },
    {
        "event_type": "DRIVER_DRAMA",
        "title": "GPU Driver Incompatibility",
        "summary": "A buggy software driver update causes gaming crashes on select GPUs, triggering consumer backlash.",
        "affected_category": "GPU",
        "price_multiplier": 0.85,
        "demand_delta": -15,
        "supply_delta": 5,
        "reliability_delta": -5,
        "quality_risk_delta": 10
    },
    {
        "event_type": "TAIWAN_SUPPLY_DELAY",
        "title": "Hsinchu Science Park Logistic Delay",
        "summary": "Logistic delays in Hsinchu, Taiwan affect shipments of premium board partner components.",
        "affected_origin_code": "TW",
        "price_multiplier": 1.25,
        "demand_delta": 15,
        "supply_delta": -25,
        "reliability_delta": 0,
        "quality_risk_delta": 0
    },
    {
        "event_type": "CHINA_BUDGET_PARTS_FLOOD",
        "title": "Shenzhen Gray Market Flood",
        "summary": "Shenzhen suppliers flood the region with cheap components, driving down costs but increasing failure risk.",
        "affected_origin_code": "CN",
        "price_multiplier": 0.65,
        "demand_delta": 10,
        "supply_delta": 50,
        "reliability_delta": -15,
        "quality_risk_delta": 20
    },
    {
        "event_type": "CURRENCY_SHOCK",
        "title": "USD Appreciation Surge",
        "summary": "Sudden strengthening of the USD currency raises pricing for all foreign supplier invoice settlements.",
        "affected_currency": "USD",
        "price_multiplier": 1.2,
        "demand_delta": 0,
        "supply_delta": -5,
        "reliability_delta": 0,
        "quality_risk_delta": 0
    },
    {
        "event_type": "RANDOM_DEMAND_SPIKE",
        "title": "Viral PC Build Trend",
        "summary": "A viral social media build trend drives a sudden local craze for boutique water-cooling components.",
        "affected_category": "WATER_COOLING",
        "price_multiplier": 1.4,
        "demand_delta": 50,
        "supply_delta": -20,
        "reliability_delta": 0,
        "quality_risk_delta": 0
    },
    {
        "event_type": "RANDOM_PRICE_CRASH",
        "title": "Manufacturer Overproduction",
        "summary": "A manufacturing miscalculation leads to an oversupply of power supply units, sparking a pricing crash.",
        "affected_category": "PSU",
        "price_multiplier": 0.7,
        "demand_delta": 0,
        "supply_delta": 30,
        "reliability_delta": 0,
        "quality_risk_delta": 0
    }
]


def _slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return s


def list_market_events(db: Session, save_game_id: int, active_only: bool = False) -> List[MarketEvent]:
    stmt = select(MarketEvent).where(MarketEvent.save_game_id == save_game_id)
    if active_only:
        stmt = stmt.where(MarketEvent.is_active == True)
    return list(db.scalars(stmt.order_by(MarketEvent.starts_on_day.desc())))


def get_active_market_events(db: Session, save_game_id: int) -> List[MarketEvent]:
    return list_market_events(db, save_game_id, active_only=True)


def generate_random_market_event(db: Session, save_game_id: int) -> MarketEvent:
    save_game = get_save_game_local(db, save_game_id)
    template = random.choice(TEMPLATES)
    
    # 3-14 days duration
    duration = random.randint(3, 14)
    severity = random.randint(1, 5) # 1-5 severity
    
    starts_on_day = save_game.game_day
    ends_on_day = starts_on_day + duration
    
    # Modify multipliers/deltas slightly based on severity
    multiplier_base = template["price_multiplier"]
    if multiplier_base > 1.0:
        multiplier = 1.0 + (multiplier_base - 1.0) * (severity / 3.0)
    elif multiplier_base < 1.0:
        multiplier = 1.0 - (1.0 - multiplier_base) * (severity / 3.0)
    else:
        multiplier = 1.0
        
    settings = get_settings()
    multiplier = max(settings.market_min_multiplier, min(settings.market_max_multiplier, multiplier))
    
    event = MarketEvent(
        save_game_id=save_game_id,
        event_type=MarketEventType(template["event_type"]),
        title=template["title"],
        summary=template["summary"],
        severity=severity,
        affected_category=template.get("affected_category"),
        affected_brand_slug=template.get("affected_brand_slug"),
        affected_origin_code=template.get("affected_origin_code"),
        affected_currency=template.get("affected_currency"),
        price_multiplier=round(multiplier, 2),
        demand_delta=int(template["demand_delta"] * (severity / 3.0)),
        supply_delta=int(template["supply_delta"] * (severity / 3.0)),
        reliability_delta=template["reliability_delta"],
        quality_risk_delta=template["quality_risk_delta"],
        starts_on_day=starts_on_day,
        ends_on_day=ends_on_day,
        is_active=True,
        generation_source=MarketEventGenerationSource.RULE
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def validate_market_event_proposal(db: Session, proposal: Dict[str, Any]) -> Dict[str, Any]:
    validated = {}
    
    # event_type must be allowed or fallback to RANDOM_DEMAND_SPIKE
    event_type_str = proposal.get("event_type")
    try:
        validated["event_type"] = MarketEventType(event_type_str).value
    except Exception:
        validated["event_type"] = MarketEventType.RANDOM_DEMAND_SPIKE.value
        
    # severity must be clamped to 1-5
    severity = proposal.get("severity", 3)
    try:
        validated["severity"] = max(1, min(5, int(severity)))
    except Exception:
        validated["severity"] = 3
        
    # affected fields
    validated["affected_category"] = proposal.get("affected_category")
    validated["affected_brand_slug"] = proposal.get("affected_brand_slug")
    validated["affected_origin_code"] = proposal.get("affected_origin_code")
    validated["affected_currency"] = proposal.get("affected_currency")
    validated["affected_product_id"] = proposal.get("affected_product_id")
    
    # check category validity
    if validated["affected_category"]:
        from app.models.enums import HardwareCategory
        try:
            HardwareCategory(validated["affected_category"])
        except Exception:
            validated["affected_category"] = None
            
    # check brand validity
    if validated["affected_brand_slug"]:
        from app.models.entities import Brand
        brand_exists = db.scalar(select(Brand).where(Brand.slug == validated["affected_brand_slug"]))
        if not brand_exists:
            validated["affected_brand_slug"] = None
            
    # check product validity
    if validated["affected_product_id"]:
        product_exists = db.scalar(select(HardwareProduct).where(HardwareProduct.id == validated["affected_product_id"]))
        if not product_exists:
            validated["affected_product_id"] = None
            
    # price_multiplier must be clamped between 0.35 and 3.5
    settings = get_settings()
    try:
        mult = float(proposal.get("price_multiplier", 1.0))
        validated["price_multiplier"] = max(settings.market_min_multiplier, min(settings.market_max_multiplier, mult))
    except Exception:
        validated["price_multiplier"] = 1.0
        
    # duration_days must be clamped between 1 and 30
    try:
        dur = int(proposal.get("duration_days", 7))
        validated["duration_days"] = max(1, min(30, dur))
    except Exception:
        validated["duration_days"] = 7
        
    # deltas must be clamped to safe range, e.g. -100 to 100
    for delta_key in ["demand_delta", "supply_delta", "reliability_delta", "quality_risk_delta"]:
        try:
            val = int(proposal.get(delta_key, 0))
            validated[delta_key] = max(-100, min(100, val))
        except Exception:
            validated[delta_key] = 0
            
    # title & summary length-limited
    title = str(proposal.get("title", "AI Market Shift"))[:160]
    summary = str(proposal.get("summary", "A shift in local market dynamics has been observed."))[:500]
    validated["title"] = title
    validated["summary"] = summary
    
    return validated


def sanitize_ai_proposal(proposal: Any) -> Any:
    if not isinstance(proposal, dict):
        return str(proposal)[:1000]
    
    allowed_keys = {
        "event_type", "title", "summary", "severity", 
        "affected_category", "affected_brand_slug", 
        "affected_origin_code", "affected_currency", 
        "affected_product_id", "price_multiplier", 
        "demand_delta", "supply_delta", "reliability_delta", 
        "quality_risk_delta", "duration_days"
    }
    
    sanitized = {}
    for k, v in proposal.items():
        if k in allowed_keys:
            if isinstance(v, str):
                sanitized[k] = v[:500]
            else:
                sanitized[k] = v
    return sanitized


def generate_ai_assisted_market_event(db: Session, save_game_id: int) -> MarketEvent:
    save_game = get_save_game_local(db, save_game_id)
    settings = get_settings()
    
    # If AI is disabled in config, fallback directly to rule
    if not settings.ai_market_events_enabled:
        event = generate_random_market_event(db, save_game_id)
        event.generation_source = MarketEventGenerationSource.AI_FALLBACK
        db.commit()
        return event
        
    # Build safe/debuggable context summary
    context = {
        "game_day": save_game.game_day,
        "cash": save_game.cash,
        "reputation": save_game.reputation,
        "active_events_count": len(get_active_market_events(db, save_game_id))
    }
    
    ai_service = AIService()
    try:
        proposal = ai_service.generate_market_event_proposal(context)
        validated = validate_market_event_proposal(db, proposal)
        
        starts_on_day = save_game.game_day
        ends_on_day = starts_on_day + validated["duration_days"]
        
        # Store a small safe prompt context summary to respect data safety rules
        safe_context = {
            "game_day": context["game_day"],
            "active_events_count": context["active_events_count"]
        }
        
        event = MarketEvent(
            save_game_id=save_game_id,
            event_type=MarketEventType(validated["event_type"]),
            title=validated["title"],
            summary=validated["summary"],
            severity=validated["severity"],
            affected_category=validated.get("affected_category"),
            affected_brand_slug=validated.get("affected_brand_slug"),
            affected_origin_code=validated.get("affected_origin_code"),
            affected_currency=validated.get("affected_currency"),
            affected_product_id=validated.get("affected_product_id"),
            price_multiplier=round(validated["price_multiplier"], 2),
            demand_delta=validated["demand_delta"],
            supply_delta=validated["supply_delta"],
            reliability_delta=validated["reliability_delta"],
            quality_risk_delta=validated["quality_risk_delta"],
            starts_on_day=starts_on_day,
            ends_on_day=ends_on_day,
            is_active=True,
            generation_source=MarketEventGenerationSource.AI_PROPOSED,
            ai_prompt_context_json=safe_context,
            ai_raw_proposal_json=sanitize_ai_proposal(proposal)
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event
    except Exception:
        # Fallback to rule generator on any error
        event = generate_random_market_event(db, save_game_id)
        event.generation_source = MarketEventGenerationSource.AI_FALLBACK
        db.commit()
        return event


def generate_market_event(db: Session, save_game_id: int, mode: str = "rule") -> MarketEvent:
    if mode == "rule":
        return generate_random_market_event(db, save_game_id)
    elif mode == "ai":
        return generate_ai_assisted_market_event(db, save_game_id)
    elif mode == "auto":
        settings = get_settings()
        if settings.ai_market_events_enabled:
            return generate_ai_assisted_market_event(db, save_game_id)
        else:
            return generate_random_market_event(db, save_game_id)
    else:
        raise bad_request(f"Invalid generation mode: {mode}")


def create_market_event(db: Session, save_game_id: int, payload: Dict[str, Any]) -> MarketEvent:
    save_game = get_save_game_local(db, save_game_id)
    
    # Validate category & brand if provided
    affected_category = payload.get("affected_category")
    if affected_category:
        from app.models.enums import HardwareCategory
        try:
            HardwareCategory(affected_category)
        except ValueError:
            raise bad_request(f"Invalid category: {affected_category}")
            
    affected_brand_slug = payload.get("affected_brand_slug")
    if affected_brand_slug:
        from app.models.entities import Brand
        b = db.scalar(select(Brand).where(Brand.slug == affected_brand_slug))
        if not b:
            raise bad_request(f"Invalid brand slug: {affected_brand_slug}")

    starts_on_day = payload.get("starts_on_day", save_game.game_day)
    ends_on_day = payload.get("ends_on_day", starts_on_day + 7)
    
    event = MarketEvent(
        save_game_id=save_game_id,
        event_type=MarketEventType(payload.get("event_type", MarketEventType.RANDOM_DEMAND_SPIKE)),
        title=payload.get("title", "Manual Event"),
        summary=payload.get("summary", "Manually generated debug event."),
        severity=payload.get("severity", 3),
        affected_category=affected_category,
        affected_brand_slug=affected_brand_slug,
        affected_origin_code=payload.get("affected_origin_code"),
        affected_currency=payload.get("affected_currency"),
        affected_product_id=payload.get("affected_product_id"),
        price_multiplier=payload.get("price_multiplier", 1.0),
        demand_delta=payload.get("demand_delta", 0),
        supply_delta=payload.get("supply_delta", 0),
        reliability_delta=payload.get("reliability_delta", 0),
        quality_risk_delta=payload.get("quality_risk_delta", 0),
        starts_on_day=starts_on_day,
        ends_on_day=ends_on_day,
        is_active=payload.get("is_active", True),
        generation_source=MarketEventGenerationSource.MANUAL
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def expire_old_events(db: Session, save_game_id: int):
    save_game = get_save_game_local(db, save_game_id)
    stmt = select(MarketEvent).where(
        MarketEvent.save_game_id == save_game_id,
        MarketEvent.is_active == True,
        MarketEvent.ends_on_day < save_game.game_day
    )
    expired = db.scalars(stmt)
    for event in expired:
        event.is_active = False
    db.commit()


def advance_market_day(db: Session, save_game_id: int) -> Dict[str, Any]:
    save_game = get_save_game_local(db, save_game_id)
    save_game.game_day += 1
    db.commit()
    
    # 1. Expire old events first
    expire_old_events(db, save_game_id)
    
    # 2. Check if active event count is below max
    settings = get_settings()
    active_events = get_active_market_events(db, save_game_id)
    
    if len(active_events) < settings.market_max_active_events:
        # Roll a chance to generate a new random event
        if random.random() < settings.market_random_event_chance:
            generate_random_market_event(db, save_game_id)
            
    return summarize_market_state(db, save_game_id)


def get_effective_product_multiplier(db: Session, save_game_id: int | None, product: HardwareProduct) -> float:
    if save_game_id is None:
        return 1.0
        
    active_events = get_active_market_events(db, save_game_id)
    if not active_events:
        return 1.0
        
    multiplier = 1.0
    brand_slug = None
    if product.brand_ref and product.brand_ref.slug:
        brand_slug = product.brand_ref.slug
    elif product.brand:
        brand_slug = _slugify(product.brand)
        
    for event in active_events:
        matches = False
        
        # 1. Specific product matches
        if event.affected_product_id is not None:
            if event.affected_product_id == product.id:
                matches = True
                
        # 2. Category matches
        elif event.affected_category is not None:
            prod_cat = product.category.value if hasattr(product.category, "value") else str(product.category)
            if event.affected_category == prod_cat:
                matches = True
                
        # 3. Brand matches
        elif event.affected_brand_slug is not None:
            if brand_slug and event.affected_brand_slug == brand_slug:
                matches = True
                
        # 4. Origin matches
        elif event.affected_origin_code is not None:
            if product.origin_code and event.affected_origin_code == product.origin_code:
                matches = True
                
        if matches:
            multiplier *= event.price_multiplier
            
    settings = get_settings()
    return max(settings.market_min_multiplier, min(settings.market_max_multiplier, multiplier))


def get_effective_supplier_offer_multiplier(db: Session, save_game_id: int | None, offer: SupplierOffer) -> float:
    if save_game_id is None:
        return 1.0
        
    active_events = get_active_market_events(db, save_game_id)
    if not active_events:
        return 1.0
        
    product_multiplier = get_effective_product_multiplier(db, save_game_id, offer.product)
    
    currency_multiplier = 1.0
    for event in active_events:
        if event.affected_currency is not None:
            matches_currency = False
            # Check offer foreign currency or supplier invoice currency
            if offer.foreign_currency and event.affected_currency == offer.foreign_currency:
                matches_currency = True
            elif offer.supplier.invoice_currency and event.affected_currency == offer.supplier.invoice_currency:
                matches_currency = True
                
            if matches_currency:
                currency_multiplier *= event.price_multiplier
                
    settings = get_settings()
    overall = product_multiplier * currency_multiplier
    return max(settings.market_min_multiplier, min(settings.market_max_multiplier, overall))


def get_effective_supplier_offer_price(db: Session, save_game_id: int | None, offer: SupplierOffer) -> int:
    # Use effective_unit_price_vnd as the base FX-adjusted VND price
    base_price = offer.effective_unit_price_vnd if hasattr(offer, "effective_unit_price_vnd") else offer.unit_price_vnd
    if save_game_id is None:
        return base_price
        
    multiplier = get_effective_supplier_offer_multiplier(db, save_game_id, offer)
    return round(base_price * multiplier)


def summarize_market_state(db: Session, save_game_id: int) -> Dict[str, Any]:
    active_events = get_active_market_events(db, save_game_id)
    all_events = list_market_events(db, save_game_id, active_only=False)
    
    impacted_categories = set()
    impacted_brands = set()
    impacted_origins = set()
    strongest_multiplier = 1.0
    
    for event in active_events:
        if event.affected_category:
            impacted_categories.add(event.affected_category)
        if event.affected_brand_slug:
            impacted_brands.add(event.affected_brand_slug)
        if event.affected_origin_code:
            impacted_origins.add(event.affected_origin_code)
            
        if abs(event.price_multiplier - 1.0) > abs(strongest_multiplier - 1.0):
            strongest_multiplier = event.price_multiplier
            
    recent_events = [
        {
            "id": ev.id,
            "title": ev.title,
            "event_type": ev.event_type.value if hasattr(ev.event_type, "value") else str(ev.event_type),
            "severity": ev.severity,
            "price_multiplier": ev.price_multiplier,
            "starts_on_day": ev.starts_on_day,
            "ends_on_day": ev.ends_on_day,
            "is_active": ev.is_active
        }
        for ev in all_events[:5]
    ]
    
    # Calculate market pressure text summary
    if not active_events:
        pressure_summary = "Markets are stable. No current disruptions detected."
    else:
        pressure_summary = f"Markets are volatile with {len(active_events)} active disruptions. "
        if strongest_multiplier > 1.0:
            pressure_summary += f"Strongest pressure is upward (multiplier x{strongest_multiplier})."
        else:
            pressure_summary += f"Strongest pressure is downward (multiplier x{strongest_multiplier})."
            
    return {
        "active_market_events_count": len(active_events),
        "impacted_categories": list(impacted_categories),
        "impacted_brands": list(impacted_brands),
        "impacted_origins": list(impacted_origins),
        "strongest_market_multiplier": strongest_multiplier,
        "recent_market_events": recent_events,
        "market_pressure_summary": pressure_summary
    }
