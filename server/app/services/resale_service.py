import random
from typing import Any, Dict, List, Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.errors import not_found, bad_request
from app.models.entities import SaveGame, InventoryUnit, ResaleListing, ResaleBuyerOffer
from app.models.enums import (
    InventoryStatus,
    Grade,
    ResaleListingStatus,
    ResaleBuyerOfferStatus,
    StaffStatus,
    StaffTaskType,
)
from app.services import progression_service, staff_service
from app.services.market_service import get_effective_product_multiplier

BUYER_NAMES = [
    "An", "Bình", "Cường", "Dũng", "Giang", "Hải", "Khánh", "Linh",
    "Minh", "Nam", "Phong", "Quân", "Sơn", "Tuấn", "Việt", "Vy"
]

BUYER_MESSAGES_HIGH_QUALITY = [
    "This looks like a clean component. I'm willing to offer {price} VND.",
    "The refurbish history looks good. I can offer {price} VND.",
    "Very high quality. I can pay {price} VND today."
]

BUYER_MESSAGES_LOW_QUALITY = [
    "I am interested, but the condition is risky. Can you do {price} VND?",
    "Looks a bit dirty, but I'll take it for {price} VND.",
    "Has some wear. How about {price} VND?"
]

BUYER_MESSAGES_NORMAL = [
    "Looks clean. I can pick it up today for {price} VND.",
    "I'm interested. I'll offer {price} VND.",
    "Fair price. I can do {price} VND."
]


def list_resale_listings(db: Session, save_game_id: int, status: Optional[ResaleListingStatus] = None) -> List[ResaleListing]:
    query = select(ResaleListing).where(ResaleListing.save_game_id == save_game_id)
    if status:
        query = query.where(ResaleListing.status == status)
    return list(db.scalars(query).all())


def get_resale_listing(db: Session, save_game_id: int, listing_id: int) -> ResaleListing:
    listing = db.scalars(
        select(ResaleListing).where(ResaleListing.save_game_id == save_game_id, ResaleListing.id == listing_id)
    ).first()
    if not listing:
        raise not_found("Resale listing not found")
    return listing


def estimate_resale_market_value(db: Session, save_game_id: int, inventory_unit: InventoryUnit) -> int:
    # 1. Determine base used price
    product = inventory_unit.product
    
    if inventory_unit.resale_value_estimate_vnd and inventory_unit.resale_value_estimate_vnd > 0:
        base_price = inventory_unit.resale_value_estimate_vnd
    elif product.latest_used_market_vnd and product.latest_used_market_vnd > 0:
        base_price = product.latest_used_market_vnd
    elif product.base_used_price_vnd and product.base_used_price_vnd > 0:
        base_price = product.base_used_price_vnd
    elif product.latest_local_retail_vnd and product.latest_local_retail_vnd > 0:
        base_price = int(product.latest_local_retail_vnd * 0.6)
    elif product.latest_supplier_cost_vnd and product.latest_supplier_cost_vnd > 0:
        base_price = int(product.latest_supplier_cost_vnd * 0.6)
    elif product.base_local_price_vnd and product.base_local_price_vnd > 0:
        base_price = int(product.base_local_price_vnd * 0.6)
    elif product.supplier_cost_vnd and product.supplier_cost_vnd > 0:
        base_price = int(product.supplier_cost_vnd * 0.6)
    elif product.msrp_vnd and product.msrp_vnd > 0:
        base_price = int(product.msrp_vnd * 0.6)
    else:
        base_price = 1_000_000  # Fallback

    # 2. Apply active market multiplier
    market_mult = get_effective_product_multiplier(db, save_game_id, product)
    estimated_val = base_price * market_mult

    # 3. Apply Grade multiplier
    grade_val = inventory_unit.grade.value if hasattr(inventory_unit.grade, "value") else str(inventory_unit.grade)
    grade_multipliers = {
        "A_PLUS": 1.15,
        "S": 1.15,
        "A": 1.0,
        "B": 0.9,
        "C": 0.75,
        "D": 0.5,
        "F": 0.25,
        "UNKNOWN": 0.3
    }
    grade_mult = grade_multipliers.get(grade_val, 0.3)
    estimated_val *= grade_mult

    # 4. Apply Inspection Confidence modifier
    # Higher confidence increases value slightly (trust factor)
    confidence_mult = 0.7 + 0.3 * (inventory_unit.inspection_confidence / 100.0)
    estimated_val *= confidence_mult

    # 5. Apply Refurbished & Ready_for_resale modifiers
    if inventory_unit.ready_for_resale:
        estimated_val *= 1.10
    if inventory_unit.refurbish_count > 0:
        estimated_val *= 1.05

    return max(10_000, round(estimated_val))


def compute_listing_quality_score(inventory_unit: InventoryUnit) -> int:
    score = 50
    grade_val = inventory_unit.grade.value if hasattr(inventory_unit.grade, "value") else str(inventory_unit.grade)
    
    if grade_val in ["A_PLUS", "S"]:
        score += 30
    elif grade_val == "A":
        score += 20
    elif grade_val == "B":
        score += 10
    elif grade_val == "C":
        score += 0
    elif grade_val == "D":
        score -= 20
    elif grade_val == "F":
        score -= 40
        
    if inventory_unit.ready_for_resale:
        score += 10
        
    score += min(10, inventory_unit.refurbish_count * 3)
    
    if inventory_unit.inspection_confidence >= 60:
        score += min(10, (inventory_unit.inspection_confidence - 60) // 4)
        
    return max(0, min(100, score))


def compute_buyer_interest_score(asking_price_vnd: int, estimated_market_value_vnd: int, bonus: int = 0) -> int:
    if estimated_market_value_vnd <= 0:
        return max(0, min(100, 50 + bonus))
    price_ratio = asking_price_vnd / estimated_market_value_vnd
    # If asking price is 80% of market value, interest is 100
    # If asking price is 120% of market value, interest is 60
    score = round(100 - (price_ratio - 0.8) * 100)
    return max(0, min(100, score + bonus))


def create_resale_listing(
    db: Session,
    save_game_id: int,
    inventory_unit_id: int,
    asking_price_vnd: Optional[int] = None,
    warranty_days_offered: int = 0
) -> ResaleListing:
    save_game = db.get(SaveGame, save_game_id)
    if not save_game:
        raise not_found("Save game not found")

    inventory_unit = db.get(InventoryUnit, inventory_unit_id)
    if not inventory_unit or inventory_unit.save_game_id != save_game_id:
        raise not_found("Inventory unit not found")

    # Check status block
    if inventory_unit.status in [InventoryStatus.SOLD, InventoryStatus.INSTALLED_IN_BUILD, InventoryStatus.RESERVED]:
        raise bad_request(f"Cannot list inventory unit with status {inventory_unit.status.value}")

    # Check eligibility
    grade_val = inventory_unit.grade.value if hasattr(inventory_unit.grade, "value") else str(inventory_unit.grade)
    is_eligible_grade = grade_val in ["S", "A_PLUS", "A", "B", "C"]
    is_eligible = inventory_unit.ready_for_resale or (inventory_unit.inspection_confidence >= 60 and is_eligible_grade)
    
    if not is_eligible:
        raise bad_request("Inventory unit is not eligible for resale. It must be ready for resale or have at least 60% inspection confidence and grade C or better.")

    # Prevent duplicate active resale listing for this inventory unit
    existing = db.scalars(
        select(ResaleListing).where(
            ResaleListing.save_game_id == save_game_id,
            ResaleListing.inventory_unit_id == inventory_unit_id,
            ResaleListing.status.in_([ResaleListingStatus.ACTIVE, ResaleListingStatus.OFFER_RECEIVED])
        )
    ).first()
    if existing:
        raise bad_request("An active resale listing already exists for this inventory unit.")

    # Calculate values
    est_market_val = estimate_resale_market_value(db, save_game_id, inventory_unit)
    interest_bonus = int(progression_service.get_effect_value(db, save_game_id, "resale_buyer_interest_bonus", 0) or 0)
    
    # Defaults
    if asking_price_vnd is None or asking_price_vnd <= 0:
        asking_price_vnd = round(est_market_val * 1.15)
        
    min_accept_price = min(round(est_market_val * 0.85), asking_price_vnd)
    min_accept_price = max(10_000, min_accept_price)
    quality_score = compute_listing_quality_score(inventory_unit)
    interest_score = compute_buyer_interest_score(asking_price_vnd, est_market_val, interest_bonus)
    market_mult = get_effective_product_multiplier(db, save_game_id, inventory_unit.product)

    # 7 to 14 days expiration
    expires_on_day = save_game.game_day + random.randint(7, 14)
    title = f"Used {inventory_unit.product.name} - Grade {grade_val}"

    # Note: Do NOT change inventory unit status when creating a listing.
    listing = ResaleListing(
        save_game_id=save_game_id,
        inventory_unit_id=inventory_unit_id,
        title=title,
        description=f"Refurbished / tested used hardware. Grade {grade_val}.",
        asking_price_vnd=asking_price_vnd,
        estimated_market_value_vnd=est_market_val,
        minimum_accept_price_vnd=min_accept_price,
        status=ResaleListingStatus.ACTIVE,
        listing_quality_score=quality_score,
        buyer_interest_score=interest_score,
        market_multiplier_at_listing=market_mult,
        grade_at_listing=grade_val,
        inspection_confidence_at_listing=inventory_unit.inspection_confidence,
        warranty_days_offered=warranty_days_offered,
        created_on_day=save_game.game_day,
        expires_on_day=expires_on_day,
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


def cancel_resale_listing(db: Session, save_game_id: int, listing_id: int) -> ResaleListing:
    save_game = db.get(SaveGame, save_game_id)
    if not save_game:
        raise not_found("Save game not found")

    listing = get_resale_listing(db, save_game_id, listing_id)
    if listing.status not in [ResaleListingStatus.ACTIVE, ResaleListingStatus.OFFER_RECEIVED]:
        raise bad_request(f"Cannot cancel resale listing in status {listing.status.value}")

    # Mark pending offers as EXPIRED
    pending_offers = db.scalars(
        select(ResaleBuyerOffer).where(
            ResaleBuyerOffer.listing_id == listing_id,
            ResaleBuyerOffer.status == ResaleBuyerOfferStatus.PENDING
        )
    ).all()
    for offer in pending_offers:
        offer.status = ResaleBuyerOfferStatus.EXPIRED

    listing.status = ResaleListingStatus.CANCELLED
    db.commit()
    db.refresh(listing)
    return listing


def generate_buyer_offer(db: Session, save_game_id: int, listing_id: int, staff_id: int | None = None) -> ResaleBuyerOffer:
    save_game = db.get(SaveGame, save_game_id)
    if not save_game:
        raise not_found("Save game not found")

    listing = get_resale_listing(db, save_game_id, listing_id)
    if listing.status not in [ResaleListingStatus.ACTIVE, ResaleListingStatus.OFFER_RECEIVED]:
        raise bad_request(f"Cannot generate offer for listing in status {listing.status.value}")

    # Spam protection check: maximum 3 pending offers per listing
    pending_count = db.scalar(
        select(func.count(ResaleBuyerOffer.id)).where(
            ResaleBuyerOffer.listing_id == listing_id,
            ResaleBuyerOffer.status == ResaleBuyerOfferStatus.PENDING
        )
    )
    if pending_count >= 3:
        raise bad_request("Spam protection: Listing already has 3 pending offers. Accept or reject them first.")

    staff_member = None
    staff_effects: dict[str, Any] | None = None
    if staff_id is not None:
        staff_member = staff_service.get_staff_member(db, save_game_id, staff_id)
        if staff_member.status not in {StaffStatus.AVAILABLE, StaffStatus.RESTING}:
            raise bad_request("Selected staff member is not available")
        staff_effects = staff_service.compute_staff_effects(staff_member, StaffTaskType.RESALE)

    # Calculate offer price based on estimated market value, quality score, and buyer interest
    # Range modifiers:
    if listing.listing_quality_score < 40:
        min_f, max_f = 0.60, 0.85
        msg_list = BUYER_MESSAGES_LOW_QUALITY
    elif listing.listing_quality_score > 75:
        min_f, max_f = 1.00, 1.20
        msg_list = BUYER_MESSAGES_HIGH_QUALITY
    else:
        min_f, max_f = 0.85, 1.05
        msg_list = BUYER_MESSAGES_NORMAL

    base_factor = random.uniform(min_f, max_f)
    # Interest adjustment: -0.1 to +0.1
    interest_adj = (listing.buyer_interest_score - 50) / 100.0 * 0.2
    final_factor = base_factor + interest_adj
    
    offer_price = round(listing.estimated_market_value_vnd * final_factor)
    if staff_effects:
        buyer_interest_bonus = int(staff_effects.get("buyer_interest_bonus", 0) or 0)
        offer_price_bonus_percent = int(staff_effects.get("offer_price_bonus_percent", 0) or 0)
        listing.buyer_interest_score = max(0, min(100, listing.buyer_interest_score + buyer_interest_bonus))
        if offer_price_bonus_percent > 0:
            offer_price = round(offer_price * (1 + offer_price_bonus_percent / 100.0))
    price_bonus_percent = int(progression_service.get_effect_value(db, save_game_id, "offer_price_bonus_percent", 0) or 0)
    if price_bonus_percent > 0:
        offer_price = round(offer_price * (1 + price_bonus_percent / 100.0))
    # Clamp to asking price and ensure positive
    offer_price = min(offer_price, listing.asking_price_vnd)
    offer_price = max(10_000, offer_price)

    buyer_name = random.choice(BUYER_NAMES)
    message_tmpl = random.choice(msg_list)
    message = message_tmpl.format(price=f"{offer_price:,}")

    buyer_patience = random.randint(30, 90)
    buyer_strictness = random.randint(20, 80)
    # Offer expires in 2 to 4 days
    expires_on_day = save_game.game_day + random.randint(2, 4)

    offer = ResaleBuyerOffer(
        listing_id=listing_id,
        save_game_id=save_game_id,
        buyer_name=buyer_name,
        offer_price_vnd=offer_price,
        status=ResaleBuyerOfferStatus.PENDING,
        message=message,
        buyer_patience=buyer_patience,
        buyer_strictness=buyer_strictness,
        created_on_day=save_game.game_day,
        expires_on_day=expires_on_day
    )
    db.add(offer)
    
    # Update listing status
    listing.status = ResaleListingStatus.OFFER_RECEIVED

    if staff_member is not None:
        staff_service.assign_staff_to_task(db, save_game_id, staff_member.id, StaffTaskType.RESALE, "resale_listing", listing.id)
    db.commit()
    db.refresh(offer)
    return offer


def list_buyer_offers(db: Session, save_game_id: int, listing_id: Optional[int] = None) -> List[ResaleBuyerOffer]:
    query = select(ResaleBuyerOffer).where(ResaleBuyerOffer.save_game_id == save_game_id)
    if listing_id:
        query = query.where(ResaleBuyerOffer.listing_id == listing_id)
    return list(db.scalars(query).all())


def compute_reputation_delta(listing: ResaleListing, offer: ResaleBuyerOffer, inventory_unit: Optional[InventoryUnit]) -> int:
    # Formula for reputation delta:
    # Good Grade + High Confidence + Fair Price = +1 to +3 reputation
    # Extreme Price Gouging (>125% of market value) + Low quality = -3 to -8 reputation
    if listing.estimated_market_value_vnd <= 0:
        return 0
        
    price_ratio = offer.offer_price_vnd / listing.estimated_market_value_vnd
    quality = listing.listing_quality_score
    
    if price_ratio > 1.25 and quality < 40:
        return -random.randint(3, 8)
    elif price_ratio < 0.90 and quality > 75:
        return random.randint(2, 5)
    elif price_ratio <= 1.10 and quality >= 60:
        return random.randint(1, 3)
    else:
        return 0


def accept_buyer_offer(db: Session, save_game_id: int, offer_id: int) -> ResaleBuyerOffer:
    save_game = db.get(SaveGame, save_game_id)
    if not save_game:
        raise not_found("Save game not found")

    offer = db.scalars(
        select(ResaleBuyerOffer).where(
            ResaleBuyerOffer.save_game_id == save_game_id,
            ResaleBuyerOffer.id == offer_id
        )
    ).first()
    if not offer:
        raise not_found("Buyer offer not found")

    if offer.status != ResaleBuyerOfferStatus.PENDING:
        raise bad_request(f"Cannot accept offer with status {offer.status.value}")

    listing = offer.listing
    if listing.status not in [ResaleListingStatus.ACTIVE, ResaleListingStatus.OFFER_RECEIVED]:
        raise bad_request(f"Cannot accept offer on listing in status {listing.status.value}")

    # Mark offer ACCEPTED
    offer.status = ResaleBuyerOfferStatus.ACCEPTED
    
    # Mark listing SOLD
    listing.status = ResaleListingStatus.SOLD
    listing.final_sale_price_vnd = offer.offer_price_vnd
    listing.sold_on_day = save_game.game_day

    # Mark inventory unit SOLD
    if listing.inventory_unit:
        listing.inventory_unit.status = InventoryStatus.SOLD

    # Add cash to save game
    save_game.cash += offer.offer_price_vnd

    # Expire or reject all other pending offers for this listing
    other_pending = db.scalars(
        select(ResaleBuyerOffer).where(
            ResaleBuyerOffer.listing_id == listing.id,
            ResaleBuyerOffer.id != offer_id,
            ResaleBuyerOffer.status == ResaleBuyerOfferStatus.PENDING
        )
    ).all()
    for o in other_pending:
        o.status = ResaleBuyerOfferStatus.EXPIRED

    db.flush()
    from app.services import review_service

    review = review_service.generate_review_from_resale(db, save_game_id, listing.id)
    return offer


def reject_buyer_offer(db: Session, save_game_id: int, offer_id: int) -> ResaleBuyerOffer:
    save_game = db.get(SaveGame, save_game_id)
    if not save_game:
        raise not_found("Save game not found")

    offer = db.scalars(
        select(ResaleBuyerOffer).where(
            ResaleBuyerOffer.save_game_id == save_game_id,
            ResaleBuyerOffer.id == offer_id
        )
    ).first()
    if not offer:
        raise not_found("Buyer offer not found")

    if offer.status != ResaleBuyerOfferStatus.PENDING:
        raise bad_request(f"Cannot reject offer with status {offer.status.value}")

    offer.status = ResaleBuyerOfferStatus.REJECTED

    # If this was the last pending offer for the listing, and listing is OFFER_RECEIVED, restore it to ACTIVE
    listing = offer.listing
    if listing.status == ResaleListingStatus.OFFER_RECEIVED:
        remaining_pending = db.scalar(
            select(func.count(ResaleBuyerOffer.id)).where(
                ResaleBuyerOffer.listing_id == listing.id,
                ResaleBuyerOffer.status == ResaleBuyerOfferStatus.PENDING
            )
        )
        if remaining_pending == 0:
            listing.status = ResaleListingStatus.ACTIVE

    db.commit()
    db.refresh(offer)
    return offer
