from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import not_found
from app.models.entities import (
    CustomerRequest,
    CustomerConversation,
    CustomerConversationMessage,
    InventoryUnit,
    Order,
    OrderFulfillmentEvent,
    PurchaseOrder,
    Quote,
    SaveGame,
    SupplierOffer,
    TestResult,
    WarrantyClaim,
    WarrantyEvent,
    UsedPartListing,
    UsedPartNegotiation,
    InventoryRefurbishEvent,
    ResaleListing,
    ResaleBuyerOffer,
)
from app.models.enums import (
    CustomerRequestStatus,
    CustomerConversationStage,
    CustomerConversationStatus,
    InventoryStatus,
    OrderStatus,
    PurchaseOrderStatus,
    QuoteStatus,
    WarrantyClaimStatus,
    UsedPartListingStatus,
    UsedPartNegotiationStatus,
    ResaleListingStatus,
    ResaleBuyerOfferStatus,
)
from app.services import market_service


def list_save_games(db: Session) -> list[SaveGame]:
    return list(db.scalars(select(SaveGame).order_by(SaveGame.updated_at.desc())))


def create_save_game(db: Session, name: str) -> SaveGame:
    save_game = SaveGame(name=name)
    db.add(save_game)
    db.commit()
    db.refresh(save_game)
    return save_game


def get_save_game(db: Session, save_game_id: int) -> SaveGame:
    save_game = db.get(SaveGame, save_game_id)
    if not save_game:
        raise not_found("Save game not found")
    return save_game


def autosave(db: Session, save_game_id: int, client_state_json: dict[str, Any] | None) -> SaveGame:
    save_game = get_save_game(db, save_game_id)
    save_game.client_state_json = client_state_json
    save_game.last_autosave_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(save_game)
    return save_game


def get_state(db: Session, save_game_id: int) -> dict[str, Any]:
    from app.services import progression_service
    from app.services import staff_service

    save_game = get_save_game(db, save_game_id)
    inventory_count = db.scalar(select(func.count()).select_from(InventoryUnit).where(InventoryUnit.save_game_id == save_game_id)) or 0
    untested_count = (
        db.scalar(
            select(func.count())
            .select_from(InventoryUnit)
            .where(InventoryUnit.save_game_id == save_game_id, InventoryUnit.status == InventoryStatus.UNTESTED)
        )
        or 0
    )
    ready_count = (
        db.scalar(
            select(func.count())
            .select_from(InventoryUnit)
            .where(InventoryUnit.save_game_id == save_game_id, InventoryUnit.status == InventoryStatus.READY_FOR_SALE)
        )
        or 0
    )
    reserved_count = (
        db.scalar(
            select(func.count())
            .select_from(InventoryUnit)
            .where(InventoryUnit.save_game_id == save_game_id, InventoryUnit.status == InventoryStatus.RESERVED)
        )
        or 0
    )
    active_requests = list(
        db.scalars(
            select(CustomerRequest)
            .join(CustomerRequest.customer)
            .where(CustomerRequest.customer.has(save_game_id=save_game_id))
            .where(CustomerRequest.status.not_in([CustomerRequestStatus.REJECTED, CustomerRequestStatus.COMPLETED]))
            .order_by(CustomerRequest.created_at.desc())
            .limit(5)
        )
    )
    active_orders = list(
        db.scalars(
            select(Order)
            .where(Order.save_game_id == save_game_id, Order.status.not_in([OrderStatus.DELIVERED, OrderStatus.CANCELLED]))
            .order_by(Order.created_at.desc())
            .limit(5)
        )
    )
    orders_in_progress = (
        db.scalar(select(func.count()).select_from(Order).where(Order.save_game_id == save_game_id, Order.status == OrderStatus.IN_PROGRESS))
        or 0
    )
    orders_in_testing = (
        db.scalar(select(func.count()).select_from(Order).where(Order.save_game_id == save_game_id, Order.status == OrderStatus.TESTING))
        or 0
    )
    delivered_orders = (
        db.scalar(select(func.count()).select_from(Order).where(Order.save_game_id == save_game_id, Order.status == OrderStatus.DELIVERED))
        or 0
    )
    estimated_pending_revenue = (
        db.scalar(
            select(func.coalesce(func.sum(Order.quoted_price_vnd), 0)).where(
                Order.save_game_id == save_game_id,
                Order.status.in_([OrderStatus.ACCEPTED, OrderStatus.IN_PROGRESS, OrderStatus.TESTING]),
            )
        )
        or 0
    )
    active_quotes_count = (
        db.scalar(
            select(func.count())
            .select_from(Quote)
            .where(
                Quote.save_game_id == save_game_id,
                Quote.status.in_([QuoteStatus.DRAFT, QuoteStatus.PRESENTED, QuoteStatus.ACCEPTED]),
            )
        )
        or 0
    )
    quoted_not_accepted_count = (
        db.scalar(
            select(func.count())
            .select_from(Quote)
            .where(Quote.save_game_id == save_game_id, Quote.status.in_([QuoteStatus.DRAFT, QuoteStatus.PRESENTED]))
        )
        or 0
    )
    recent_quotes = list(
        db.scalars(
            select(Quote)
            .where(Quote.save_game_id == save_game_id)
            .order_by(Quote.updated_at.desc())
            .limit(5)
        )
    )
    offer_count = db.scalar(select(func.count()).select_from(SupplierOffer)) or 0
    active_purchase_orders = (
        db.scalar(
            select(func.count())
            .select_from(PurchaseOrder)
            .where(PurchaseOrder.save_game_id == save_game_id, PurchaseOrder.status != PurchaseOrderStatus.RECEIVED)
        )
        or 0
    )
    recent_tests = list(
        db.scalars(
            select(TestResult)
            .join(TestResult.inventory_unit)
            .options(selectinload(TestResult.inventory_unit).selectinload(InventoryUnit.product))
            .where(InventoryUnit.save_game_id == save_game_id)
            .order_by(TestResult.created_at.desc())
            .limit(5)
        )
    )
    recent_fulfillment_events = list(
        db.scalars(
            select(OrderFulfillmentEvent)
            .join(OrderFulfillmentEvent.order)
            .where(Order.save_game_id == save_game_id)
            .order_by(OrderFulfillmentEvent.created_at.desc())
            .limit(5)
        )
    )
    open_warranty_claims = (
        db.scalar(
            select(func.count())
            .select_from(WarrantyClaim)
            .where(WarrantyClaim.save_game_id == save_game_id, WarrantyClaim.status == WarrantyClaimStatus.OPEN)
        )
        or 0
    )
    diagnosing_warranty_claims = (
        db.scalar(
            select(func.count())
            .select_from(WarrantyClaim)
            .where(WarrantyClaim.save_game_id == save_game_id, WarrantyClaim.status == WarrantyClaimStatus.DIAGNOSING)
        )
        or 0
    )
    pending_warranty_resolution = (
        db.scalar(
            select(func.count())
            .select_from(WarrantyClaim)
            .where(
                WarrantyClaim.save_game_id == save_game_id,
                WarrantyClaim.status.in_([
                    WarrantyClaimStatus.AWAITING_DECISION,
                    WarrantyClaimStatus.APPROVED,
                    WarrantyClaimStatus.RMA_SUBMITTED,
                    WarrantyClaimStatus.IN_REVIEW,
                ]),
            )
        )
        or 0
    )
    approved_warranty_claims = (
        db.scalar(
            select(func.count())
            .select_from(WarrantyClaim)
            .where(WarrantyClaim.save_game_id == save_game_id, WarrantyClaim.status == WarrantyClaimStatus.APPROVED)
        )
        or 0
    )
    resolved_warranty_claims = (
        db.scalar(
            select(func.count())
            .select_from(WarrantyClaim)
            .where(WarrantyClaim.save_game_id == save_game_id, WarrantyClaim.status.in_([WarrantyClaimStatus.RESOLVED, WarrantyClaimStatus.CLOSED]))
        )
        or 0
    )
    due_warranty_claims = (
        db.scalar(
            select(func.count())
            .select_from(WarrantyClaim)
            .where(
                WarrantyClaim.save_game_id == save_game_id,
                WarrantyClaim.status.not_in([
                    WarrantyClaimStatus.CLOSED,
                    WarrantyClaimStatus.REJECTED,
                    WarrantyClaimStatus.RESOLVED,
                    WarrantyClaimStatus.CANCELLED,
                    WarrantyClaimStatus.REPLACED,
                    WarrantyClaimStatus.REFUNDED,
                    WarrantyClaimStatus.RMA_COMPLETED,
                ]),
                WarrantyClaim.due_on_day.is_not(None),
                WarrantyClaim.due_on_day <= save_game.game_day + 2,
            )
        )
        or 0
    )
    warranty_cost_exposure = (
        db.scalar(
            select(func.coalesce(func.sum(WarrantyClaim.estimated_cost_vnd), 0))
            .select_from(WarrantyClaim)
            .where(
                WarrantyClaim.save_game_id == save_game_id,
                WarrantyClaim.status.not_in(
                    [
                        WarrantyClaimStatus.CLOSED,
                        WarrantyClaimStatus.REJECTED,
                        WarrantyClaimStatus.RESOLVED,
                        WarrantyClaimStatus.CANCELLED,
                        WarrantyClaimStatus.REPLACED,
                        WarrantyClaimStatus.REFUNDED,
                        WarrantyClaimStatus.RMA_COMPLETED,
                    ]
                ),
            )
        )
        or 0
    )
    recent_warranty_events = list(
        db.scalars(
            select(WarrantyEvent)
            .join(WarrantyEvent.warranty_claim)
            .where(WarrantyClaim.save_game_id == save_game_id)
            .order_by(WarrantyEvent.created_at.desc())
            .limit(5)
        )
    )

    active_used_listings_count = (
        db.scalar(
            select(func.count())
            .select_from(UsedPartListing)
            .where(UsedPartListing.save_game_id == save_game_id, UsedPartListing.status == UsedPartListingStatus.AVAILABLE)
        )
        or 0
    )
    open_negotiations_count = (
        db.scalar(
            select(func.count())
            .select_from(UsedPartNegotiation)
            .where(UsedPartNegotiation.save_game_id == save_game_id, UsedPartNegotiation.status == UsedPartNegotiationStatus.OPEN)
        )
        or 0
    )
    recent_used_listings = list(
        db.scalars(
            select(UsedPartListing)
            .where(UsedPartListing.save_game_id == save_game_id)
            .order_by(UsedPartListing.created_at.desc())
            .limit(5)
        )
    )

    refurbish_queue_count = (
        db.scalar(
            select(func.count())
            .select_from(InventoryUnit)
            .where(
                InventoryUnit.save_game_id == save_game_id,
                InventoryUnit.status.not_in([
                    InventoryStatus.SOLD,
                    InventoryStatus.INSTALLED_IN_BUILD,
                    InventoryStatus.RESERVED,
                    InventoryStatus.READY_FOR_SALE,
                ])
            )
        )
        or 0
    )
    ready_for_resale_count = (
        db.scalar(
            select(func.count())
            .select_from(InventoryUnit)
            .where(
                InventoryUnit.save_game_id == save_game_id,
                InventoryUnit.ready_for_resale == True
            )
        )
        or 0
    )
    recent_refurbish_events = list(
        db.scalars(
            select(InventoryRefurbishEvent)
            .where(InventoryRefurbishEvent.save_game_id == save_game_id)
            .order_by(InventoryRefurbishEvent.created_at.desc())
            .limit(5)
        )
    )

    active_resale_listings_count = (
        db.scalar(
            select(func.count())
            .select_from(ResaleListing)
            .where(
                ResaleListing.save_game_id == save_game_id,
                ResaleListing.status.in_([ResaleListingStatus.ACTIVE, ResaleListingStatus.OFFER_RECEIVED])
            )
        )
        or 0
    )
    pending_resale_offers_count = (
        db.scalar(
            select(func.count())
            .select_from(ResaleBuyerOffer)
            .where(
                ResaleBuyerOffer.save_game_id == save_game_id,
                ResaleBuyerOffer.status == ResaleBuyerOfferStatus.PENDING
            )
        )
        or 0
    )
    recent_resale_revenue = (
        db.scalar(
            select(func.coalesce(func.sum(ResaleListing.final_sale_price_vnd), 0))
            .where(
                ResaleListing.save_game_id == save_game_id,
                ResaleListing.status == ResaleListingStatus.SOLD
            )
        )
        or 0
    )
    recent_resale_listings = list(
        db.scalars(
            select(ResaleListing)
            .where(ResaleListing.save_game_id == save_game_id)
            .order_by(ResaleListing.created_at.desc())
            .limit(5)
        )
    )
    progression_summary = progression_service.summarize_progression(db, save_game_id)
    upgrade_effect_summary = progression_service.get_upgrade_effects(db, save_game_id)
    inventory_capacity_summary = progression_summary.get("inventory_capacity", 50)
    staff_summary = staff_service.summarize_staff_state(db, save_game_id)
    recent_staff_assignments = staff_summary.get("recent_assignments", [])
    from app.services import review_service

    reputation_summary = review_service.summarize_reputation(db, save_game_id)
    recent_reviews = review_service.list_reviews(db, save_game_id, limit=5)
    open_conversations_count = (
        db.scalar(
            select(func.count())
            .select_from(CustomerConversation)
            .where(
                CustomerConversation.save_game_id == save_game_id,
                CustomerConversation.status.in_([
                    CustomerConversationStatus.OPEN,
                    CustomerConversationStatus.WAITING_FOR_PLAYER,
                    CustomerConversationStatus.WAITING_FOR_CUSTOMER,
                ]),
            )
        )
        or 0
    )
    waiting_for_player_conversations_count = (
        db.scalar(
            select(func.count())
            .select_from(CustomerConversation)
            .where(
                CustomerConversation.save_game_id == save_game_id,
                CustomerConversation.status == CustomerConversationStatus.WAITING_FOR_PLAYER,
            )
        )
        or 0
    )
    quote_proposed_conversations_count = (
        db.scalar(
            select(func.count())
            .select_from(CustomerConversation)
            .where(
                CustomerConversation.save_game_id == save_game_id,
                CustomerConversation.status.in_([
                    CustomerConversationStatus.QUOTE_PROPOSED,
                    CustomerConversationStatus.READY_TO_ORDER,
                ]),
            )
        )
        or 0
    )
    customers_needing_consultation_count = (
        db.scalar(
            select(func.count())
            .select_from(CustomerConversation)
            .where(
                CustomerConversation.save_game_id == save_game_id,
                CustomerConversation.stage.in_([
                    CustomerConversationStage.NEW_REQUEST,
                    CustomerConversationStage.NEEDS_CONSULTATION,
                    CustomerConversationStage.QUALIFYING_NEEDS,
                    CustomerConversationStage.DISCUSSING_USED_PARTS,
                ]),
            )
        )
        or 0
    )
    recent_conversation_messages = list(
        db.scalars(
            select(CustomerConversationMessage)
            .join(CustomerConversationMessage.conversation)
            .where(CustomerConversation.save_game_id == save_game_id)
            .order_by(CustomerConversationMessage.created_at.desc())
            .limit(5)
        )
    )

    return {
        "staff_count": int(staff_summary.get("staff_count", 0) or 0),
        "available_staff_count": int(staff_summary.get("available_staff_count", 0) or 0),
        "daily_salary_total_vnd": int(staff_summary.get("daily_salary_total_vnd", 0) or 0),
        "recent_staff_assignments": recent_staff_assignments,
        "staff_summary": {
            key: value
            for key, value in staff_summary.items()
            if key != "recent_assignments"
        },
        "refurbish_summary": {
            "queue_count": refurbish_queue_count,
            "ready_for_resale_count": ready_for_resale_count,
            "recent_events": [
                {
                    "id": event.id,
                    "inventory_unit_id": event.inventory_unit_id,
                    "action_type": event.action_type.value,
                    "status": event.status.value,
                    "cost_vnd": event.cost_vnd,
                    "summary": event.summary,
                    "created_at": event.created_at.isoformat(),
                }
                for event in recent_refurbish_events
            ]
        },
        "save_game": save_game,
        "cash": save_game.cash,
        "shop_level": save_game.shop_level,
        "shop_xp": save_game.shop_xp,
        "purchased_upgrades_count": progression_summary.get("purchased_upgrades_count", 0),
        "upgrade_effect_summary": upgrade_effect_summary,
        "inventory_capacity_summary": {
            "base_capacity": 50,
            "bonus_capacity": int(upgrade_effect_summary.get("inventory_capacity_bonus", 0) or 0),
            "total_capacity": int(inventory_capacity_summary),
            "current_inventory": int(progression_summary.get("inventory_count", 0)),
            "remaining_capacity": int(progression_summary.get("inventory_headroom", 0)),
        },
        "reputation": save_game.reputation,
        "reputation_summary": reputation_summary,
        "recent_reviews": recent_reviews,
        "open_conversations_count": int(open_conversations_count),
        "waiting_for_player_conversations_count": int(waiting_for_player_conversations_count),
        "quote_proposed_conversations_count": int(quote_proposed_conversations_count),
        "customers_needing_consultation_count": int(customers_needing_consultation_count),
        "recent_conversation_messages": [
            {
                "id": message.id,
                "conversation_id": message.conversation_id,
                "sender_type": message.sender_type.value,
                "sender_label": message.sender_label,
                "message_type": message.message_type.value,
                "body": message.body,
                "action_type": message.action_type.value if message.action_type else None,
                "quote_id": message.quote_id,
                "created_at": message.created_at.isoformat(),
            }
            for message in recent_conversation_messages
        ],
        "game_day": save_game.game_day,
        "inventory_summary": {
            "total": inventory_count,
            "untested": untested_count,
            "ready_for_sale": ready_count,
            "reserved": reserved_count,
        },
        "active_customer_requests": [
            {
                "id": request.id,
                "type": request.request_type,
                "budget_vnd": request.budget_vnd,
                "status": request.status,
                "use_case": request.use_case,
            }
            for request in active_requests
        ],
        "active_orders": [
            {
                "id": order.id,
                "status": order.status,
                "quoted_price_vnd": order.quoted_price_vnd,
                "profit_vnd": order.profit_vnd,
            }
            for order in active_orders
        ],
        "order_fulfillment_summary": {
            "orders_in_progress": orders_in_progress,
            "orders_in_testing": orders_in_testing,
            "delivered_orders": delivered_orders,
            "estimated_pending_revenue": int(estimated_pending_revenue),
            "warranty_placeholder": open_warranty_claims + diagnosing_warranty_claims + pending_warranty_resolution,
        },
        "recent_fulfillment_events": [
            {
                "id": event.id,
                "order_id": event.order_id,
                "event_type": event.event_type,
                "summary": event.summary,
                "created_at": event.created_at.isoformat(),
            }
            for event in recent_fulfillment_events
        ],
        "quote_summary": {
            "active": active_quotes_count,
            "quoted_not_accepted": quoted_not_accepted_count,
            "reserved_inventory": reserved_count,
        },
        "warranty_summary": {
            "open_warranty_claims": open_warranty_claims,
            "diagnosing_warranty_claims": diagnosing_warranty_claims,
            "pending_warranty_resolution": pending_warranty_resolution,
            "warranty_approved_claims": approved_warranty_claims,
            "warranty_resolved_claims": resolved_warranty_claims,
            "warranty_due_soon_claims": due_warranty_claims,
            "warranty_cost_exposure": int(warranty_cost_exposure),
        },
        "recent_warranty_events": [
            {
                "id": event.id,
                "claim_id": event.warranty_claim_id,
                "event_type": event.event_type,
                "summary": event.summary,
                "created_at": event.created_at.isoformat(),
            }
            for event in recent_warranty_events
        ],
        "recent_quotes": [
            {
                "id": quote.id,
                "title": quote.title,
                "status": quote.status,
                "quoted_price_vnd": quote.quoted_price_vnd,
                "estimated_profit_vnd": quote.estimated_profit_vnd,
                "customer_fit_score": quote.customer_fit_score,
            }
            for quote in recent_quotes
        ],
        "supplier_offers_summary": {
            "available_offers": offer_count,
            "active_purchase_orders": active_purchase_orders,
        },
        "recent_test_results": [
            {
                "id": result.id,
                "test_type": result.test_type,
                "summary": result.summary,
                "product_name": result.inventory_unit.product.name,
                "created_at": result.created_at.isoformat(),
            }
            for result in recent_tests
        ],
        "market_summary": market_service.summarize_market_state(db, save_game_id),
        "used_market_summary": {
            "active_listings_count": active_used_listings_count,
            "open_negotiations_count": open_negotiations_count,
            "recent_listings": [
                {
                    "id": listing.id,
                    "seller_name": listing.seller_name,
                    "product_name": listing.product.name,
                    "asking_price_vnd": listing.asking_price_vnd,
                    "estimated_fair_value_vnd": listing.estimated_fair_value_vnd,
                    "status": listing.status.value,
                    "visible_condition_grade": listing.visible_condition_grade,
                    "expires_on_day": listing.expires_on_day
                }
                for listing in recent_used_listings
            ]
        },
        "resale_summary": {
            "active_listings_count": active_resale_listings_count,
            "pending_offers_count": pending_resale_offers_count,
            "recent_revenue_vnd": int(recent_resale_revenue),
            "recent_listings": [
                {
                    "id": listing.id,
                    "title": listing.title,
                    "asking_price_vnd": listing.asking_price_vnd,
                    "estimated_market_value_vnd": listing.estimated_market_value_vnd,
                    "status": listing.status.value,
                    "grade_at_listing": listing.grade_at_listing,
                    "created_on_day": listing.created_on_day,
                    "expires_on_day": listing.expires_on_day
                }
                for listing in recent_resale_listings
            ]
        }
    }
