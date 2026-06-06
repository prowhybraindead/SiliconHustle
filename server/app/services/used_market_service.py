import random
import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import not_found, bad_request
from app.models.entities import SaveGame, HardwareProduct, UsedPartListing, UsedPartNegotiation, NegotiationMessage, InventoryUnit, Brand
from app.models.enums import UsedPartListingStatus, UsedPartNegotiationStatus, NegotiationSender, ConditionType, InventoryStatus, Grade, InventorySource, MarketEventType
from app.services import market_service


SELLER_NAMES = [
    "Hùng Kênh Rác", "Tuấn Ve Chai", "Bình Chợ Trời", "Lâm Sắt Vụn", 
    "Phúc Đồng Nát", "Lan Sỉ Lẻ", "Nam Ve Chai", "Lợi PC Cũ",
    "Khánh Rã Máy", "Quân Nát Net", "Dương Đồ Cổ", "Minh Linh Kiện"
]

CLAIMED_CONDITIONS = [
    "Như mới, chỉ bóc hộp cắm test", 
    "Dùng giữ gìn, thổi bụi thường xuyên", 
    "Hơi bụi tí nhưng chạy cực êm", 
    "Hàng tháo máy văn phòng siêu bền", 
    "Để lâu không dùng, hơi rỉ sét nhẹ", 
    "Ngoại hình cá sấu nhưng hiệu năng vô địch"
]

CLAIMED_USAGES = [
    "Chỉ lướt web và chơi LOL nhẹ nhàng",
    "Dùng render nhẹ nhàng 2 tiếng/ngày",
    "Cắm clone game cày cuốc 24/7",
    "Trâu cày hoàn lương, đã vệ sinh sạch sẽ",
    "Hàng backup dự phòng ít khi bật",
    "Máy học online của con em"
]

VISIBLE_GRADES = ["A_PLUS", "A", "B", "C", "D", "F"]


def list_used_part_listings(db: Session, save_game_id: int, active_only: bool = True) -> List[UsedPartListing]:
    stmt = select(UsedPartListing).where(UsedPartListing.save_game_id == save_game_id)
    if active_only:
        stmt = stmt.where(UsedPartListing.status == UsedPartListingStatus.AVAILABLE)
    return list(db.scalars(stmt.order_by(UsedPartListing.created_at.desc())))


def get_used_part_listing(db: Session, save_game_id: int, listing_id: int) -> UsedPartListing:
    listing = db.scalar(
        select(UsedPartListing).where(
            UsedPartListing.save_game_id == save_game_id,
            UsedPartListing.id == listing_id
        )
    )
    if not listing:
        raise not_found("Used part listing not found")
    return listing


def estimate_used_fair_value(db: Session, save_game_id: int, product: HardwareProduct) -> int:
    # 1. Base price resolution
    if product.latest_used_market_vnd is not None:
        base_price = product.latest_used_market_vnd
    elif product.latest_local_retail_vnd is not None:
        base_price = int(product.latest_local_retail_vnd * 0.75)
    elif product.latest_supplier_cost_vnd is not None:
        base_price = int(product.latest_supplier_cost_vnd * 0.80)
    elif product.msrp_vnd is not None:
        base_price = int(product.msrp_vnd * 0.70)
    else:
        # Score heuristic fallback
        perf = product.base_performance_score or 50
        base_price = perf * 150000
        
    # 2. Integrate market multiplier
    mult = market_service.get_effective_product_multiplier(db, save_game_id, product)
    fair_value = int(base_price * mult)
    
    # 3. Clamp fair value to minimum 100,000 VND
    return max(100000, fair_value)


def generate_hidden_condition(product: HardwareProduct, market_context: Dict[str, Any]) -> Dict[str, Any]:
    # Determine usage
    usages = ["GAMING", "OFFICE", "SERVER", "UNKNOWN"]
    # If GPU, add MINING option
    if product.category.value == "GPU":
        usages.append("MINING")
        
    # Mining crash event boosts MINING chance
    weights = None
    if "MINING" in usages:
        mining_weight = 1.0
        if market_context.get("is_mining_crash"):
            mining_weight = 5.0
        elif market_context.get("is_mining_boom"):
            mining_weight = 0.2
        weights = [4.0, 3.0, 1.0, 2.0, mining_weight]
        
    previous_usage = random.choices(usages, weights=weights)[0]
    
    # Visible grade determination determines basic range for true health
    visible_grade = market_context.get("visible_grade", "B")
    grade_ranges = {
        "A_PLUS": (90, 100),
        "A": (80, 92),
        "B": (65, 83),
        "C": (50, 68),
        "D": (35, 53),
        "F": (5, 38)
    }
    
    health_range = grade_ranges.get(visible_grade, (60, 80))
    # Honesty factor may skew it downwards (seller lying about visible grade)
    honesty = market_context.get("seller_honesty", 100)
    if honesty < 50:
        # True health is lower than grade suggests
        skew = int((50 - honesty) * 0.4)
        health_range = (max(5, health_range[0] - skew), max(10, health_range[1] - skew))
        
    true_health = random.randint(*health_range)
    true_performance = max(10, min(100, true_health + random.randint(-5, 5)))
    true_thermal = max(10, min(100, true_health + random.randint(-10, 5)))
    true_fan = max(5, min(100, true_health + random.randint(-15, 8))) if product.category.value in ["GPU", "PSU", "COOLER"] else 100
    true_stability = max(10, min(100, true_health + random.randint(-8, 5)))
    true_vram = max(10, min(100, true_health + random.randint(-12, 5))) if product.category.value == "GPU" else 100
    
    # Defect selection
    hidden_defect = "NONE"
    if true_health < 45 or random.random() < 0.15:
        defects = ["NONE"]
        if product.category.value == "GPU":
            defects += ["VRAM_INSTABILITY", "ARTIFACTING", "FAN_WEAR", "HIGH_TEMPERATURE"]
        elif product.category.value == "CPU":
            defects += ["BENT_PINS", "RANDOM_CRASH"]
        elif product.category.value in ["SSD", "STORAGE"]:
            defects += ["BAD_SECTORS", "WEAK_CONTROLLER"]
        elif product.category.value == "RAM":
            defects += ["RANDOM_CRASH"]
        else:
            defects += ["RANDOM_CRASH"]
        hidden_defect = random.choice(defects)
        
    dust_level = random.randint(10, 100)
    if previous_usage == "MINING":
        dust_level = random.randint(50, 100)
        true_fan = max(5, true_fan - 15)
        
    warranty_risk = "LOW" if true_stability >= 80 and true_health >= 80 else "MEDIUM" if true_stability >= 55 else "HIGH"
    
    return {
        "true_health": true_health,
        "true_performance": true_performance,
        "true_thermal": true_thermal,
        "true_fan": true_fan,
        "true_stability": true_stability,
        "true_vram": true_vram,
        "previous_usage": previous_usage,
        "hidden_defect": hidden_defect,
        "dust_level": dust_level,
        "warranty_risk": warranty_risk,
        "repair_history": random.choices(["NONE", "REPAIRED_FAN", "REPAIRED_MOSFET", "RE-PASTED"], weights=[8, 1, 1, 3])[0]
    }


def generate_used_part_listing(db: Session, save_game_id: int) -> UsedPartListing:
    save_game = db.get(SaveGame, save_game_id)
    if not save_game:
        raise not_found("Save game not found")
        
    # Get random hardware product
    products = db.scalars(select(HardwareProduct)).all()
    if not products:
        raise bad_request("No hardware products in catalog to generate listings")
    product = random.choice(products)
    
    seller_name = random.choice(SELLER_NAMES)
    claimed_condition = random.choice(CLAIMED_CONDITIONS)
    claimed_usage = random.choice(CLAIMED_USAGES)
    claimed_warranty_months = random.choice([0, 0, 1, 3, 6, 12])
    
    visible_grade = random.choice(VISIBLE_GRADES)
    seller_honesty = random.randint(25, 100)
    seller_patience = random.randint(30, 100)
    risk_score = random.randint(0, 100)
    
    fair_value = estimate_used_fair_value(db, save_game_id, product)
    
    # Bounded asking price (minimum 50,000 VND)
    asking_factor = random.uniform(0.95, 1.25)
    asking_price = max(50000, int(fair_value * asking_factor))
    
    # min accept price must never exceed asking price
    min_accept_factor = random.uniform(0.65, 0.90)
    min_accept_price = min(asking_price, max(50000, int(fair_value * min_accept_factor)))
    
    # Check active market events for context
    active_events = market_service.get_active_market_events(db, save_game_id)
    is_mining_crash = any(e.event_type == MarketEventType.MINING_CRASH for e in active_events)
    is_mining_boom = any(e.event_type == MarketEventType.MINING_BOOM for e in active_events)
    
    market_context = {
        "visible_grade": visible_grade,
        "seller_honesty": seller_honesty,
        "is_mining_crash": is_mining_crash,
        "is_mining_boom": is_mining_boom
    }
    
    hidden_cond = generate_hidden_condition(product, market_context)
    mult = market_service.get_effective_product_multiplier(db, save_game_id, product)
    
    listing = UsedPartListing(
        save_game_id=save_game_id,
        seller_name=seller_name,
        product_id=product.id,
        asking_price_vnd=asking_price,
        estimated_fair_value_vnd=fair_value,
        min_accept_price_vnd=min_accept_price,
        status=UsedPartListingStatus.AVAILABLE,
        seller_honesty=seller_honesty,
        seller_patience=seller_patience,
        claimed_condition=claimed_condition,
        claimed_usage=claimed_usage,
        claimed_warranty_months=claimed_warranty_months,
        visible_condition_grade=visible_grade,
        hidden_condition_json=hidden_cond,
        risk_score=risk_score,
        market_multiplier_at_creation=mult,
        created_on_day=save_game.game_day,
        expires_on_day=save_game.game_day + random.randint(3, 7)
    )
    
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


def generate_batch_used_part_listings(db: Session, save_game_id: int, count: int = 5) -> List[UsedPartListing]:
    listings = []
    for _ in range(count):
        listings.append(generate_used_part_listing(db, save_game_id))
    return listings


def start_negotiation(db: Session, save_game_id: int, listing_id: int) -> UsedPartNegotiation:
    listing = get_used_part_listing(db, save_game_id, listing_id)
    if listing.status != UsedPartListingStatus.AVAILABLE:
        raise bad_request(f"Listing is not available for negotiation (Current status: {listing.status.value})")
        
    # Check if a negotiation already exists
    existing = db.scalar(
        select(UsedPartNegotiation).where(
            UsedPartNegotiation.listing_id == listing_id,
            UsedPartNegotiation.save_game_id == save_game_id
        )
    )
    if existing:
        return existing
        
    listing.status = UsedPartListingStatus.NEGOTIATING
    negotiation = UsedPartNegotiation(
        listing_id=listing_id,
        save_game_id=save_game_id,
        status=UsedPartNegotiationStatus.OPEN,
        rounds_count=0
    )
    db.add(negotiation)
    db.commit()
    db.refresh(negotiation)
    
    # Create system and seller greeting messages
    msg_system = NegotiationMessage(
        negotiation_id=negotiation.id,
        sender=NegotiationSender.SYSTEM,
        message=f"Bắt đầu thương lượng với {listing.seller_name} về sản phẩm {listing.product.name}."
    )
    msg_seller = NegotiationMessage(
        negotiation_id=negotiation.id,
        sender=NegotiationSender.SELLER,
        message=f"Chào bạn, mình đang muốn bán con {listing.product.name} này giá {listing.asking_price_vnd.toLocaleString() if hasattr(listing.asking_price_vnd, 'toLocaleString') else listing.asking_price_vnd} VND. Bạn trả được bao nhiêu?"
    )
    db.add(msg_system)
    db.add(msg_seller)
    db.commit()
    db.refresh(negotiation)
    return negotiation


def submit_offer(db: Session, save_game_id: int, negotiation_id: int, offer_vnd: int, message: Optional[str] = None) -> UsedPartNegotiation:
    negotiation = db.get(UsedPartNegotiation, negotiation_id)
    if not negotiation or negotiation.save_game_id != save_game_id:
        raise not_found("Negotiation not found")
        
    if negotiation.status != UsedPartNegotiationStatus.OPEN:
        raise bad_request(f"Negotiation is already closed/resolved (Status: {negotiation.status.value})")
        
    if offer_vnd <= 0:
        raise bad_request("Offer amount must be positive")
        
    listing = negotiation.listing
    
    # 1. Player message
    player_text = message or f"Tôi xin trả {offer_vnd} VND."
    msg_player = NegotiationMessage(
        negotiation_id=negotiation.id,
        sender=NegotiationSender.PLAYER,
        message=player_text,
        offer_vnd=offer_vnd
    )
    db.add(msg_player)
    negotiation.rounds_count += 1
    
    # 2. Seller decision response
    if offer_vnd >= listing.min_accept_price_vnd:
        # Seller accepts!
        negotiation.status = UsedPartNegotiationStatus.ACCEPTED
        negotiation.accepted_price_vnd = offer_vnd
        negotiation.current_offer_vnd = offer_vnd
        negotiation.last_seller_response = "Chốt giá đó đi. Bạn qua lấy linh kiện giúp mình nhé."
        
        msg_seller = NegotiationMessage(
            negotiation_id=negotiation.id,
            sender=NegotiationSender.SELLER,
            message=negotiation.last_seller_response,
            offer_vnd=offer_vnd
        )
        db.add(msg_seller)
    else:
        # Seller rejects or counters
        patience_loss = 10
        if offer_vnd < int(listing.min_accept_price_vnd * 0.75):
            patience_loss = 25  # Lower offer reduces patience faster
            
        listing.seller_patience = max(0, listing.seller_patience - patience_loss)
        
        if listing.seller_patience <= 0:
            # Patience exhausted - failed
            negotiation.status = UsedPartNegotiationStatus.FAILED
            negotiation.last_seller_response = "Mặc cả thế này thì chịu rồi. Mình không bán nữa đâu nhé."
            listing.status = UsedPartListingStatus.REJECTED # Block listing
            
            msg_seller = NegotiationMessage(
                negotiation_id=negotiation.id,
                sender=NegotiationSender.SELLER,
                message=negotiation.last_seller_response
            )
            db.add(msg_seller)
        else:
            # Seller counters
            # Counter price is patience-scaled between min_accept and asking_price
            counter_price = int(listing.min_accept_price_vnd + (listing.asking_price_vnd - listing.min_accept_price_vnd) * (listing.seller_patience / 100.0))
            # Ensure counter never drops below min accept price
            counter_price = max(listing.min_accept_price_vnd, counter_price)
            # Ensure counter never exceeds asking price
            counter_price = min(listing.asking_price_vnd, counter_price)
            
            negotiation.current_offer_vnd = counter_price
            negotiation.last_seller_response = f"Giá thấp quá không bán được. Mình bớt chút còn {counter_price} VND được không?"
            
            msg_seller = NegotiationMessage(
                negotiation_id=negotiation.id,
                sender=NegotiationSender.SELLER,
                message=negotiation.last_seller_response,
                offer_vnd=counter_price
            )
            db.add(msg_seller)
            
    db.commit()
    db.refresh(negotiation)
    return negotiation


def accept_listing(db: Session, save_game_id: int, listing_id: int, final_price_vnd: Optional[int] = None) -> UsedPartListing:
    listing = get_used_part_listing(db, save_game_id, listing_id)
    save_game = db.get(SaveGame, save_game_id)
    if not save_game:
        raise not_found("Save game not found")
        
    if listing.status not in [UsedPartListingStatus.AVAILABLE, UsedPartListingStatus.NEGOTIATING]:
        raise bad_request(f"Listing cannot be accepted (Status: {listing.status.value})")
        
    # Determine price
    price = listing.asking_price_vnd
    negotiation = db.scalar(
        select(UsedPartNegotiation).where(
            UsedPartNegotiation.listing_id == listing_id,
            UsedPartNegotiation.save_game_id == save_game_id
        )
    )
    if negotiation and negotiation.status == UsedPartNegotiationStatus.ACCEPTED:
        price = negotiation.accepted_price_vnd
    elif final_price_vnd is not None:
        # Validate that if the player overrides, it must match negotiation accepted price or asking price
        price = final_price_vnd
        
    if save_game.cash < price:
        raise bad_request("Không đủ tiền mặt để thực hiện giao dịch này")
        
    # Deduct cash
    save_game.cash -= price
    
    # Create USED untested InventoryUnit
    notes = f"Mua từ {listing.seller_name} vào ngày {save_game.game_day}. Cam kết: {listing.claimed_condition}. Sử dụng: {listing.claimed_usage}."
    
    unit = InventoryUnit(
        save_game_id=save_game_id,
        product_id=listing.product_id,
        condition_type=ConditionType.USED,
        status=InventoryStatus.UNTESTED,
        grade=Grade.UNKNOWN,
        inspection_confidence=0,
        purchase_price_vnd=price,
        source=InventorySource.USED_MARKET,
        warranty_months_remaining=listing.claimed_warranty_months or 0,
        hidden_condition_json=listing.hidden_condition_json,
        notes=notes
    )
    db.add(unit)
    
    # Close listing and negotiation
    listing.status = UsedPartListingStatus.ACCEPTED
    listing.final_price_vnd = price
    if negotiation:
        negotiation.status = UsedPartNegotiationStatus.CLOSED
        negotiation.accepted_price_vnd = price
        
    db.commit()
    db.refresh(listing)
    return listing


def reject_listing(db: Session, save_game_id: int, listing_id: int) -> UsedPartListing:
    listing = get_used_part_listing(db, save_game_id, listing_id)
    if listing.status not in [UsedPartListingStatus.AVAILABLE, UsedPartListingStatus.NEGOTIATING]:
        raise bad_request("Listing cannot be rejected")
        
    listing.status = UsedPartListingStatus.REJECTED
    negotiation = db.scalar(
        select(UsedPartNegotiation).where(
            UsedPartNegotiation.listing_id == listing_id,
            UsedPartNegotiation.save_game_id == save_game_id
        )
    )
    if negotiation:
        negotiation.status = UsedPartNegotiationStatus.REJECTED
        
    db.commit()
    db.refresh(listing)
    return listing


def expire_old_listings(db: Session, save_game_id: int) -> None:
    save_game = db.get(SaveGame, save_game_id)
    if not save_game:
        return
        
    stmt = select(UsedPartListing).where(
        UsedPartListing.save_game_id == save_game_id,
        UsedPartListing.status == UsedPartListingStatus.AVAILABLE,
        UsedPartListing.expires_on_day < save_game.game_day
    )
    expired = db.scalars(stmt)
    for listing in expired:
        listing.status = UsedPartListingStatus.EXPIRED
        # Close any open negotiation
        negotiation = db.scalar(
            select(UsedPartNegotiation).where(
                UsedPartNegotiation.listing_id == listing.id,
                UsedPartNegotiation.save_game_id == save_game_id
            )
        )
        if negotiation:
            negotiation.status = UsedPartNegotiationStatus.FAILED
    db.commit()
