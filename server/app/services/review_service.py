from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import bad_request, not_found
from app.models.entities import CustomerReview, Order, ResaleListing, SaveGame, WarrantyClaim
from app.models.enums import OrderStatus, ResaleListingStatus, WarrantyClaimStatus, WarrantyResolutionType
from app.services.save_game_service import get_save_game

SOURCE_ORDER = "ORDER_DELIVERY"
SOURCE_RESALE = "RESALE_SALE"
SOURCE_WARRANTY = "WARRANTY_RMA"
SOURCE_MANUAL = "MANUAL"

SENTIMENT_POSITIVE = "POSITIVE"
SENTIMENT_NEUTRAL = "NEUTRAL"
SENTIMENT_NEGATIVE = "NEGATIVE"


def list_reviews(
    db: Session,
    save_game_id: int,
    source_type: str | None = None,
    sentiment: str | None = None,
    limit: int | None = None,
) -> list[CustomerReview]:
    get_save_game(db, save_game_id)
    query = select(CustomerReview).where(CustomerReview.save_game_id == save_game_id)
    if source_type:
        query = query.where(CustomerReview.source_type == source_type)
    if sentiment:
        query = query.where(CustomerReview.sentiment == sentiment)
    query = query.order_by(CustomerReview.created_at.desc())
    if limit is not None:
        query = query.limit(limit)
    return list(db.scalars(query))


def get_review(db: Session, save_game_id: int, review_id: int) -> CustomerReview:
    review = db.scalar(
        select(CustomerReview).where(
            CustomerReview.save_game_id == save_game_id,
            CustomerReview.id == review_id,
        )
    )
    if not review:
        raise not_found("Review not found")
    return review


def summarize_reputation(db: Session, save_game_id: int) -> dict[str, Any]:
    save_game = get_save_game(db, save_game_id)
    total_reviews = db.scalar(
        select(func.count()).select_from(CustomerReview).where(CustomerReview.save_game_id == save_game_id)
    ) or 0
    average_rating = db.scalar(
        select(func.avg(CustomerReview.rating)).where(CustomerReview.save_game_id == save_game_id)
    )
    source_counts = {
        source_type: int(
            db.scalar(
                select(func.count())
                .select_from(CustomerReview)
                .where(CustomerReview.save_game_id == save_game_id, CustomerReview.source_type == source_type)
            )
            or 0
        )
        for source_type in [SOURCE_ORDER, SOURCE_RESALE, SOURCE_WARRANTY, SOURCE_MANUAL]
    }
    sentiment_counts = {
        sentiment: int(
            db.scalar(
                select(func.count())
                .select_from(CustomerReview)
                .where(CustomerReview.save_game_id == save_game_id, CustomerReview.sentiment == sentiment)
            )
            or 0
        )
        for sentiment in [SENTIMENT_POSITIVE, SENTIMENT_NEUTRAL, SENTIMENT_NEGATIVE]
    }
    return {
        "save_game_id": save_game_id,
        "reputation": save_game.reputation,
        "total_reviews": int(total_reviews),
        "average_rating": round(float(average_rating), 2) if average_rating is not None else None,
        "positive_reviews": sentiment_counts[SENTIMENT_POSITIVE],
        "neutral_reviews": sentiment_counts[SENTIMENT_NEUTRAL],
        "negative_reviews": sentiment_counts[SENTIMENT_NEGATIVE],
        "sentiment_counts": sentiment_counts,
        "source_counts": source_counts,
    }


def generate_review_from_order(db: Session, save_game_id: int, order_id: int) -> CustomerReview:
    from app.services.order_service import get_order
    from app.services.order_fulfillment_service import calculate_reputation_delta

    order = get_order(db, save_game_id, order_id)
    if order.status != OrderStatus.DELIVERED:
        raise bad_request("Order must be delivered before a review can be generated")
    source_key = f"order:{order.id}"
    existing = _existing_review(db, save_game_id, source_key)
    if existing:
        _sync_order_reputation(order, existing.reputation_delta)
        return existing

    reputation_delta = calculate_reputation_delta(order)
    rating = _rating_from_order(order, reputation_delta)
    persona_type = getattr(order.customer, "persona_type", None) if order.customer else None
    sentiment = _sentiment_from_rating(rating)
    title, body, tags, source_summary = _build_order_review(order, persona_type, rating, sentiment)
    review = CustomerReview(
        save_game_id=save_game_id,
        customer_id=order.customer_id,
        order_id=order.id,
        source_type=SOURCE_ORDER,
        source_key=source_key,
        sentiment=sentiment,
        rating=rating,
        title=title,
        body=body,
        tags_json=tags,
        persona_type=persona_type,
        source_summary=source_summary,
        quote_fit_score=order.customer_fit_score,
        compatibility_score=getattr(order, "compatibility_score", None),
        build_quality_score=order.build_quality_score,
        warranty_risk_score=_warranty_risk_score(order.final_warranty_risk),
        final_price_vnd=order.quoted_price_vnd,
        reputation_delta=reputation_delta,
        generated_on_day=_current_game_day(order.save_game),
        is_public=True,
    )
    _apply_reputation_delta(db, order.save_game, reputation_delta)
    order.reputation_delta = reputation_delta
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def generate_review_from_resale(db: Session, save_game_id: int, resale_listing_id: int) -> CustomerReview:
    listing = db.scalar(
        select(ResaleListing).where(
            ResaleListing.save_game_id == save_game_id,
            ResaleListing.id == resale_listing_id,
        )
    )
    if not listing:
        raise not_found("Resale listing not found")
    if listing.status != ResaleListingStatus.SOLD and listing.final_sale_price_vnd is None:
        raise bad_request("Resale listing must be sold before a review can be generated")

    source_key = f"resale:{listing.id}"
    existing = _existing_review(db, save_game_id, source_key)
    if existing:
        return existing

    from app.services.resale_service import compute_reputation_delta

    accepted_offer = next((offer for offer in listing.offers if offer.status.value == "ACCEPTED"), None)
    reputation_delta = compute_reputation_delta(listing, accepted_offer, listing.inventory_unit) if accepted_offer else 0
    rating = _rating_from_resale(listing, reputation_delta)
    sentiment = _sentiment_from_rating(rating)
    persona_type = None
    title, body, tags, source_summary = _build_resale_review(listing, rating, sentiment)
    review = CustomerReview(
        save_game_id=save_game_id,
        customer_id=None,
        order_id=None,
        resale_listing_id=listing.id,
        source_type=SOURCE_RESALE,
        source_key=source_key,
        sentiment=sentiment,
        rating=rating,
        title=title,
        body=body,
        tags_json=tags,
        persona_type=persona_type,
        source_summary=source_summary,
        quote_fit_score=None,
        compatibility_score=None,
        build_quality_score=listing.listing_quality_score,
        warranty_risk_score=None,
        final_price_vnd=listing.final_sale_price_vnd,
        reputation_delta=reputation_delta,
        generated_on_day=_current_game_day(listing.save_game),
        is_public=True,
    )
    _apply_reputation_delta(db, listing.save_game, reputation_delta)
    listing.reputation_delta = reputation_delta
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def generate_review_from_warranty(db: Session, save_game_id: int, warranty_claim_id: int) -> CustomerReview:
    claim = db.scalar(
        select(WarrantyClaim).where(
            WarrantyClaim.save_game_id == save_game_id,
            WarrantyClaim.id == warranty_claim_id,
        )
    )
    if not claim:
        raise not_found("Warranty claim not found")
    if claim.resolution_type is None and claim.status not in {
        WarrantyClaimStatus.REJECTED,
        WarrantyClaimStatus.RESOLVED,
        WarrantyClaimStatus.CLOSED,
        WarrantyClaimStatus.REPLACED,
        WarrantyClaimStatus.REFUNDED,
        WarrantyClaimStatus.RMA_COMPLETED,
    }:
        raise bad_request("Warranty claim must be resolved before a review can be generated")

    source_key = f"warranty:{claim.id}"
    existing = _existing_review(db, save_game_id, source_key)
    if existing:
        return existing

    from app.services.warranty_service import _reputation_delta_for_resolution

    resolution_type = claim.resolution_type or WarrantyResolutionType.REJECT
    reputation_delta = _reputation_delta_for_resolution(claim, resolution_type)
    rating = _rating_from_warranty(claim, resolution_type, reputation_delta)
    sentiment = _sentiment_from_rating(rating)
    persona_type = claim.customer.persona_type if claim.customer else None
    title, body, tags, source_summary = _build_warranty_review(claim, persona_type, rating, sentiment)
    save_game = get_save_game(db, save_game_id)
    review = CustomerReview(
        save_game_id=save_game_id,
        customer_id=claim.customer_id,
        order_id=claim.order_id,
        resale_listing_id=claim.resale_listing_id,
        warranty_claim_id=claim.id,
        source_type=SOURCE_WARRANTY,
        source_key=source_key,
        sentiment=sentiment,
        rating=rating,
        title=title,
        body=body,
        tags_json=tags,
        persona_type=persona_type,
        source_summary=source_summary,
        quote_fit_score=None,
        compatibility_score=None,
        build_quality_score=None,
        warranty_risk_score=claim.internal_risk_score,
        final_price_vnd=claim.final_cost_vnd,
        reputation_delta=reputation_delta,
        generated_on_day=_current_game_day(save_game),
        is_public=True,
    )
    _apply_reputation_delta(db, save_game, reputation_delta)
    claim.reputation_delta = reputation_delta
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def generate_review_from_source(
    db: Session,
    save_game_id: int,
    source_type: str | None = None,
    order_id: int | None = None,
    resale_listing_id: int | None = None,
    warranty_claim_id: int | None = None,
) -> CustomerReview:
    normalized = _normalize_source_type(source_type, order_id, resale_listing_id, warranty_claim_id)
    if normalized == SOURCE_MANUAL and order_id is None and resale_listing_id is None and warranty_claim_id is None and not source_type:
        return generate_random_recent_review(db, save_game_id)
    if normalized == SOURCE_ORDER:
        if order_id is None:
            order = _latest_delivered_order(db, save_game_id)
            if not order:
                raise bad_request("No delivered order is available to generate a review")
            return generate_review_from_order(db, save_game_id, order.id)
        return generate_review_from_order(db, save_game_id, order_id)
    if normalized == SOURCE_RESALE:
        if resale_listing_id is None:
            listing = _latest_sold_listing(db, save_game_id)
            if not listing:
                raise bad_request("No sold resale listing is available to generate a review")
            return generate_review_from_resale(db, save_game_id, listing.id)
        return generate_review_from_resale(db, save_game_id, resale_listing_id)
    if normalized == SOURCE_WARRANTY:
        if warranty_claim_id is None:
            claim = _latest_resolved_claim(db, save_game_id)
            if not claim:
                raise bad_request("No resolved warranty claim is available to generate a review")
            return generate_review_from_warranty(db, save_game_id, claim.id)
        return generate_review_from_warranty(db, save_game_id, warranty_claim_id)
    if normalized == SOURCE_MANUAL:
        raise bad_request("Manual review generation is not supported in this build")
    raise bad_request("Unable to determine review source")


def generate_random_recent_review(db: Session, save_game_id: int) -> CustomerReview:
    candidates: list[tuple[datetime, str, int]] = []
    latest_order = _latest_delivered_order(db, save_game_id)
    if latest_order and latest_order.delivered_at:
        candidates.append((latest_order.delivered_at, SOURCE_ORDER, latest_order.id))
    latest_listing = _latest_sold_listing(db, save_game_id)
    if latest_listing and latest_listing.created_at:
        candidates.append((latest_listing.created_at, SOURCE_RESALE, latest_listing.id))
    latest_claim = _latest_resolved_claim(db, save_game_id)
    if latest_claim and latest_claim.resolved_at:
        candidates.append((latest_claim.resolved_at, SOURCE_WARRANTY, latest_claim.id))
    if not candidates:
        raise bad_request("No recent review source is available")
    _, source_type, source_id = max(candidates, key=lambda item: item[0])
    return generate_review_from_source(
        db,
        save_game_id,
        source_type,
        source_id if source_type == SOURCE_ORDER else None,
        source_id if source_type == SOURCE_RESALE else None,
        source_id if source_type == SOURCE_WARRANTY else None,
    )


def create_manual_review(
    db: Session,
    save_game_id: int,
    title: str,
    body: str,
    rating: int,
    source_type: str = SOURCE_MANUAL,
    source_key: str | None = None,
    notes: str | None = None,
) -> CustomerReview:
    save_game = get_save_game(db, save_game_id)
    rating = _clamp(rating, 1, 5)
    source_key = source_key or f"manual:{save_game_id}:{datetime.now(timezone.utc).timestamp():.0f}"
    if _existing_review(db, save_game_id, source_key):
        raise bad_request("A review already exists for this manual source key")
    sentiment = _sentiment_from_rating(rating)
    delta = rating - 3
    review = CustomerReview(
        save_game_id=save_game_id,
        customer_id=None,
        order_id=None,
        resale_listing_id=None,
        warranty_claim_id=None,
        source_type=source_type,
        source_key=source_key,
        sentiment=sentiment,
        rating=rating,
        title=title,
        body=body,
        tags_json=[],
        persona_type=None,
        source_summary="Manual review entry.",
        quote_fit_score=None,
        compatibility_score=None,
        build_quality_score=None,
        warranty_risk_score=None,
        final_price_vnd=None,
        reputation_delta=delta,
        generated_on_day=save_game.game_day,
        is_public=True,
        notes=notes,
    )
    _apply_reputation_delta(db, save_game, delta)
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def apply_reputation_delta(db: Session, save_game: SaveGame, delta: int) -> None:
    _apply_reputation_delta(db, save_game, delta)


def _apply_reputation_delta(db: Session, save_game: SaveGame, delta: int) -> None:
    save_game.reputation = max(0, min(100, int((save_game.reputation or 0) + delta)))
    db.flush()


def _existing_review(db: Session, save_game_id: int, source_key: str) -> CustomerReview | None:
    return db.scalar(
        select(CustomerReview).where(
            CustomerReview.save_game_id == save_game_id,
            CustomerReview.source_key == source_key,
        )
    )


def _normalize_source_type(
    source_type: str | None,
    order_id: int | None,
    resale_listing_id: int | None,
    warranty_claim_id: int | None,
) -> str:
    explicit = (source_type or "").upper() if source_type else None
    if explicit in {SOURCE_ORDER, SOURCE_RESALE, SOURCE_WARRANTY, SOURCE_MANUAL}:
        return explicit
    if order_id is not None:
        return SOURCE_ORDER
    if resale_listing_id is not None:
        return SOURCE_RESALE
    if warranty_claim_id is not None:
        return SOURCE_WARRANTY
    return SOURCE_MANUAL


def _rating_from_order(order: Order, reputation_delta: int) -> int:
    score = 50
    if order.final_test_score is not None:
        score += (order.final_test_score - 50) * 0.45
    if order.build_quality_score is not None:
        score += (order.build_quality_score - 50) * 0.25
    if order.customer_fit_score is not None:
        score += (order.customer_fit_score - 50) * 0.15
    score += {
        "LOW": 10,
        "MEDIUM": 0,
        "HIGH": -10,
        "CRITICAL": -25,
    }.get(order.final_warranty_risk or "MEDIUM", 0)
    if reputation_delta >= 5:
        score += 8
    elif reputation_delta <= -5:
        score -= 8
    return _rating_from_score(score)


def _rating_from_resale(listing: ResaleListing, reputation_delta: int) -> int:
    score = float(listing.listing_quality_score or 50)
    if listing.final_sale_price_vnd and listing.estimated_market_value_vnd:
        price_ratio = listing.final_sale_price_vnd / max(1, listing.estimated_market_value_vnd)
        if 0.95 <= price_ratio <= 1.1:
            score += 12
        elif price_ratio > 1.1:
            score += 5
        else:
            score -= 10
    if listing.inspection_confidence_at_listing is not None:
        score += (listing.inspection_confidence_at_listing - 50) * 0.2
    if reputation_delta >= 3:
        score += 6
    elif reputation_delta < 0:
        score -= 6
    return _rating_from_score(score)


def _rating_from_warranty(claim: WarrantyClaim, resolution_type: WarrantyResolutionType, reputation_delta: int) -> int:
    score = 45
    score += {
        WarrantyResolutionType.REPAIR: 15,
        WarrantyResolutionType.REPLACE: 20,
        WarrantyResolutionType.REFUND: 25,
        WarrantyResolutionType.GOODWILL_CREDIT: 10,
        WarrantyResolutionType.REJECT: -20,
    }.get(resolution_type, 0)
    if claim.warranty_valid:
        score += 10
    else:
        score -= 10
    score += max(0, 6 - claim.severity) * 2
    if reputation_delta >= 3:
        score += 5
    elif reputation_delta < 0:
        score -= 8
    return _rating_from_score(score)


def _rating_from_score(score: float) -> int:
    return _clamp(round(score / 20), 1, 5)


def _sentiment_from_rating(rating: int) -> str:
    if rating >= 4:
        return SENTIMENT_POSITIVE
    if rating <= 2:
        return SENTIMENT_NEGATIVE
    return SENTIMENT_NEUTRAL


def _build_order_review(
    order: Order,
    persona_type: str | None,
    rating: int,
    sentiment: str,
) -> tuple[str, str, list[str], str]:
    vibe = _persona_vibe(persona_type)
    title_map = {
        SENTIMENT_POSITIVE: "Delivered build landed well",
        SENTIMENT_NEUTRAL: "Delivered build was acceptable",
        SENTIMENT_NEGATIVE: "Delivered build needs attention",
    }
    title = title_map[sentiment]
    if vibe:
        title = f"{title} for {vibe}"
    tags = _persona_tags(persona_type)
    if order.final_warranty_risk:
        tags.append(f"risk:{order.final_warranty_risk.lower()}")
    if order.build_quality_score is not None:
        tags.append("build-quality")
    if order.final_test_score is not None:
        tags.append("delivery-test")
    body = _compose_body(
        sentiment,
        [
            f"Order #{order.id} was delivered with a {order.final_warranty_risk or 'MEDIUM'} warranty profile.",
            _order_persona_line(persona_type),
            f"Build quality landed at {order.build_quality_score or 0}/100 and final test score was {order.final_test_score or 0}/100.",
            f"Customer fit score was {order.customer_fit_score or 0}/100, with {order.quoted_price_vnd:,} VND quoted.",
        ],
    )
    source_summary = f"Order #{order.id} delivered for {order.quoted_price_vnd:,} VND."
    return title, body, tags, source_summary


def _build_resale_review(
    listing: ResaleListing,
    rating: int,
    sentiment: str,
) -> tuple[str, str, list[str], str]:
    title_map = {
        SENTIMENT_POSITIVE: "Resale sale felt fair",
        SENTIMENT_NEUTRAL: "Resale sale was steady",
        SENTIMENT_NEGATIVE: "Resale sale felt rough",
    }
    title = title_map[sentiment]
    tags = ["resale", f"grade:{(listing.grade_at_listing or 'unknown').lower()}"]
    if listing.warranty_days_offered:
        tags.append(f"warranty:{listing.warranty_days_offered}d")
    if listing.listing_quality_score >= 70:
        tags.append("well-presented")
    elif listing.listing_quality_score <= 40:
        tags.append("rough-listing")
    body = _compose_body(
        sentiment,
        [
            f"Listing #{listing.id} sold for {listing.final_sale_price_vnd or 0:,} VND against an estimated market value of {listing.estimated_market_value_vnd:,} VND.",
            f"Listing quality was {listing.listing_quality_score}/100 with inspection confidence {listing.inspection_confidence_at_listing or 0}/100.",
            f"Warranty offered: {listing.warranty_days_offered} days.",
        ],
    )
    source_summary = f"Listing #{listing.id} sold for {listing.final_sale_price_vnd or 0:,} VND."
    return title, body, tags, source_summary


def _build_warranty_review(
    claim: WarrantyClaim,
    persona_type: str | None,
    rating: int,
    sentiment: str,
) -> tuple[str, str, list[str], str]:
    title_map = {
        SENTIMENT_POSITIVE: "Warranty handled cleanly",
        SENTIMENT_NEUTRAL: "Warranty resolution was acceptable",
        SENTIMENT_NEGATIVE: "Warranty follow-up disappointed",
    }
    title = title_map[sentiment]
    if persona_type:
        title = f"{title} for {_persona_vibe(persona_type)}"
    tags = ["warranty", claim.claim_type.value.lower(), claim.claim_reason.value.lower()]
    if claim.resolution_type:
        tags.append(claim.resolution_type.value.lower())
    if claim.warranty_valid:
        tags.append("valid-warranty")
    else:
        tags.append("invalid-warranty")
    body = _compose_body(
        sentiment,
        [
            f"Warranty claim #{claim.id} on order #{claim.order_id or 0} was resolved with status {claim.status.value}.",
            f"Resolution type was {claim.resolution_type.value if claim.resolution_type else 'REVIEW'} and claim severity was {claim.severity}/5.",
            f"Internal risk score sat at {claim.internal_risk_score}/100 with final cost {claim.final_cost_vnd or 0:,} VND.",
        ],
    )
    source_summary = f"Warranty claim #{claim.id} resolved as {claim.status.value}."
    return title, body, tags, source_summary


def _compose_body(sentiment: str, lines: list[str]) -> str:
    lead = {
        SENTIMENT_POSITIVE: "Feedback came back positive.",
        SENTIMENT_NEUTRAL: "Feedback landed in the middle.",
        SENTIMENT_NEGATIVE: "Feedback was less favorable.",
    }[sentiment]
    return " ".join([lead, *lines])


def _persona_vibe(persona_type: str | None) -> str | None:
    if not persona_type:
        return None
    vibe_map = {
        "BUDGET_GAMER": "budget gaming rig",
        "ESPORTS_PLAYER": "esports build",
        "STREAMER": "streaming setup",
        "OFFICE_BUYER": "office workstation",
        "CREATOR_EDITOR": "creator workstation",
        "AI_WORKSTATION": "AI workstation",
        "STUDENT": "student budget rig",
        "RGB_ENTHUSIAST": "showcase RGB build",
        "QUIET_PC_LOVER": "quiet PC build",
        "BRAND_LOYALIST": "trusted-brand setup",
        "WARRANTY_SENSITIVE": "warranty-first setup",
        "BARGAIN_HUNTER": "deal-hunter setup",
        "PREMIUM_BUILDER": "premium showcase build",
    }
    return vibe_map.get(persona_type, persona_type.lower().replace("_", " "))


def _persona_tags(persona_type: str | None) -> list[str]:
    if not persona_type:
        return []
    tags_by_persona = {
        "BUDGET_GAMER": ["value", "fps", "budget"],
        "ESPORTS_PLAYER": ["fps", "latency", "balance"],
        "STREAMER": ["streaming", "multitask", "capture"],
        "OFFICE_BUYER": ["quiet", "productivity", "reliability"],
        "CREATOR_EDITOR": ["workflow", "storage", "memory"],
        "AI_WORKSTATION": ["vram", "ram", "throughput"],
        "STUDENT": ["budget", "value", "study"],
        "RGB_ENTHUSIAST": ["rgb", "aesthetics", "showcase"],
        "QUIET_PC_LOVER": ["quiet", "thermals", "low-power"],
        "BRAND_LOYALIST": ["brand", "trust", "consistency"],
        "WARRANTY_SENSITIVE": ["warranty", "support", "confidence"],
        "BARGAIN_HUNTER": ["deal", "discount", "value"],
        "PREMIUM_BUILDER": ["premium", "finish", "quality"],
    }
    return tags_by_persona.get(persona_type, [persona_type.lower()])


def _order_persona_line(persona_type: str | None) -> str:
    if persona_type == "BUDGET_GAMER":
        return "The customer wanted the strongest FPS-per-VND tradeoff."
    if persona_type == "ESPORTS_PLAYER":
        return "Competitive latency and a balanced CPU/GPU pair were the priority."
    if persona_type == "STREAMER":
        return "Streaming stability and multitasking headroom mattered most."
    if persona_type == "OFFICE_BUYER":
        return "Quiet operation and low-maintenance reliability were the target."
    if persona_type == "CREATOR_EDITOR":
        return "A smooth editing workflow with enough RAM and storage was the focus."
    if persona_type == "AI_WORKSTATION":
        return "Heavy workloads needed ample RAM, VRAM, and dependable power."
    if persona_type == "STUDENT":
        return "The build had to stay practical, affordable, and dependable."
    if persona_type == "RGB_ENTHUSIAST":
        return "A polished showcase look mattered as much as the raw specs."
    if persona_type == "QUIET_PC_LOVER":
        return "Thermals and noise control were the main priorities."
    if persona_type == "BRAND_LOYALIST":
        return "Trusted brands and a consistent component story were important."
    if persona_type == "WARRANTY_SENSITIVE":
        return "Warranty coverage and service confidence were the core concern."
    if persona_type == "BARGAIN_HUNTER":
        return "The deal had to feel sharp without looking risky."
    if persona_type == "PREMIUM_BUILDER":
        return "The build was expected to feel premium in both look and finish."
    return "The build matched the customer's preferences closely enough."


def _warranty_risk_score(risk: str | None) -> int | None:
    if risk is None:
        return None
    return {
        "LOW": 25,
        "MEDIUM": 50,
        "HIGH": 75,
        "CRITICAL": 90,
    }.get(risk, 50)


def _current_game_day(save_game: SaveGame | None) -> int | None:
    return save_game.game_day if save_game else None


def _latest_delivered_order(db: Session, save_game_id: int) -> Order | None:
    return db.scalar(
        select(Order)
        .where(Order.save_game_id == save_game_id, Order.status == OrderStatus.DELIVERED)
        .order_by(Order.delivered_at.desc().nullslast(), Order.created_at.desc())
    )


def _latest_sold_listing(db: Session, save_game_id: int) -> ResaleListing | None:
    return db.scalar(
        select(ResaleListing)
        .where(ResaleListing.save_game_id == save_game_id, ResaleListing.status == ResaleListingStatus.SOLD)
        .order_by(ResaleListing.sold_on_day.desc().nullslast(), ResaleListing.created_at.desc())
    )


def _latest_resolved_claim(db: Session, save_game_id: int) -> WarrantyClaim | None:
    return db.scalar(
        select(WarrantyClaim)
        .where(
            WarrantyClaim.save_game_id == save_game_id,
            WarrantyClaim.status.in_(
                {
                    WarrantyClaimStatus.REJECTED,
                    WarrantyClaimStatus.RESOLVED,
                    WarrantyClaimStatus.CLOSED,
                    WarrantyClaimStatus.REPLACED,
                    WarrantyClaimStatus.REFUNDED,
                    WarrantyClaimStatus.RMA_COMPLETED,
                }
            ),
        )
        .order_by(WarrantyClaim.resolved_at.desc().nullslast(), WarrantyClaim.updated_at.desc())
    )


def _sync_order_reputation(order: Order, delta: int) -> None:
    if order.reputation_delta is None:
        order.reputation_delta = delta


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))
