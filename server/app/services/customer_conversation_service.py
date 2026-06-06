from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import bad_request, not_found
from app.models.entities import (
    Customer,
    CustomerConversation,
    CustomerConversationMessage,
    CustomerRequest,
    Quote,
    SaveGame,
    StaffMember,
)
from app.models.enums import (
    CustomerConversationStage,
    CustomerConversationStatus,
    CustomerRequestStatus,
    ConversationActionType,
    ConversationMessageSender,
    ConversationMessageType,
    QuoteStatus,
    StaffRole,
)
from app.services import staff_service
from app.services.save_game_service import get_save_game


def list_conversations(db: Session, save_game_id: int, status: CustomerConversationStatus | str | None = None) -> list[CustomerConversation]:
    get_save_game(db, save_game_id)
    query = (
        select(CustomerConversation)
        .options(
            selectinload(CustomerConversation.customer),
            selectinload(CustomerConversation.customer_request).selectinload(CustomerRequest.customer),
            selectinload(CustomerConversation.assigned_staff),
        )
        .where(CustomerConversation.save_game_id == save_game_id)
        .order_by(CustomerConversation.updated_at.desc())
    )
    if status is not None:
        query = query.where(CustomerConversation.status == _coerce_status(status))
    conversations = list(db.scalars(query))
    for conversation in conversations:
        conversation.conversion_probability = compute_conversion_probability(db, conversation)
    return conversations


def get_conversation(db: Session, save_game_id: int, conversation_id: int) -> CustomerConversation:
    conversation = db.scalar(_conversation_query(include_messages=True).where(
        CustomerConversation.save_game_id == save_game_id,
        CustomerConversation.id == conversation_id,
    ))
    if not conversation:
        raise not_found("Customer conversation not found")
    conversation.conversion_probability = compute_conversion_probability(db, conversation)
    return conversation


def get_or_create_conversation_for_request(db: Session, save_game_id: int, request_id: int) -> CustomerConversation:
    request = _get_customer_request(db, save_game_id, request_id)
    if request.conversation_id:
        existing = db.scalar(
            _conversation_query(include_messages=True).where(
                CustomerConversation.save_game_id == save_game_id,
                CustomerConversation.id == request.conversation_id,
            )
        )
        if existing:
            _sync_request_state(request, existing)
            db.commit()
            return get_conversation(db, save_game_id, existing.id)

    existing = db.scalar(
        _conversation_query(include_messages=True).where(
            CustomerConversation.save_game_id == save_game_id,
            CustomerConversation.customer_request_id == request.id,
        )
    )
    if existing:
        _sync_request_state(request, existing)
        db.commit()
        return get_conversation(db, save_game_id, existing.id)

    return create_conversation_for_customer(db, save_game_id, customer_id=request.customer_id, request_id=request.id)


def create_conversation_for_customer(
    db: Session,
    save_game_id: int,
    customer_id: int | None = None,
    request_id: int | None = None,
) -> CustomerConversation:
    save_game = get_save_game(db, save_game_id)
    customer: Customer | None = None
    request: CustomerRequest | None = None

    if request_id is not None:
        request = _get_customer_request(db, save_game_id, request_id)
        customer = request.customer
        if customer_id is not None and customer_id != customer.id:
            raise bad_request("Conversation customer does not match the customer request")
    elif customer_id is not None:
        customer = db.scalar(select(Customer).where(Customer.save_game_id == save_game_id, Customer.id == customer_id))
        if not customer:
            raise not_found("Customer not found")
    else:
        raise bad_request("A customer or customer request is required to open a conversation")

    persona_type = _persona_type(request, customer)
    detected_preferences = extract_basic_intent_from_request(request, customer)
    accepts_used_parts = _accepts_used_parts(request, customer, detected_preferences)
    conversation = CustomerConversation(
        save_game_id=save_game_id,
        save_game=save_game,
        customer_id=customer.id if customer else None,
        customer_request_id=request.id if request else None,
        status=CustomerConversationStatus.OPEN,
        stage=CustomerConversationStage.NEW_REQUEST,
        persona_type=persona_type,
        title=_build_conversation_title(request, customer),
        customer_mood=_build_customer_mood(customer, request),
        engagement_score=_initial_engagement_score(customer, request),
        urgency_score=_initial_urgency_score(customer, request),
        conversion_probability=None,
        detected_budget_vnd=detected_preferences.get("budget_vnd"),
        detected_use_case=detected_preferences.get("use_case"),
        detected_preferences_json=detected_preferences,
        accepts_used_parts=accepts_used_parts,
        created_on_day=save_game.game_day,
    )
    db.add(conversation)
    db.flush()

    if request:
        request.conversation_id = conversation.id
        request.conversation_status = conversation.status.value

    add_system_message(
        db,
        save_game_id,
        conversation.id,
        "Conversation opened for customer request.",
        metadata={
            "event": "conversation_opened",
            "persona_type": persona_type,
            "detected_preferences": detected_preferences,
        },
    )
    add_message(
        db,
        save_game_id,
        conversation.id,
        sender_type=ConversationMessageSender.CUSTOMER,
        body=_build_customer_opening_message(request, customer, conversation),
        sender_label=customer.name if customer else "Customer",
        message_type=ConversationMessageType.TEXT,
        metadata={
            "persona_type": persona_type,
            "detected_preferences": detected_preferences,
        },
    )
    add_system_message(
        db,
        save_game_id,
        conversation.id,
        "Intent parsed: "
        f"budget={_format_vnd(conversation.detected_budget_vnd)}, "
        f"use_case={conversation.detected_use_case or 'n/a'}, "
        f"used_parts={conversation.accepts_used_parts if conversation.accepts_used_parts is not None else 'unknown'}, "
        f"warranty_sensitivity={detected_preferences.get('warranty_sensitivity', 'unknown')}.",
        metadata={
            "intent": detected_preferences,
        },
    )

    conversation.conversion_probability = compute_conversion_probability(db, conversation)
    db.commit()
    return get_conversation(db, save_game_id, conversation.id)


def list_messages(db: Session, save_game_id: int, conversation_id: int) -> list[CustomerConversationMessage]:
    conversation = get_conversation(db, save_game_id, conversation_id)
    return list(
        db.scalars(
            select(CustomerConversationMessage)
            .where(
                CustomerConversationMessage.save_game_id == save_game_id,
                CustomerConversationMessage.conversation_id == conversation.id,
            )
            .order_by(CustomerConversationMessage.created_at.asc())
        )
    )


def add_message(
    db: Session,
    save_game_id: int,
    conversation_id: int,
    sender_type: ConversationMessageSender | str,
    body: str,
    sender_label: str | None = None,
    staff_id: int | None = None,
    message_type: ConversationMessageType | str = ConversationMessageType.TEXT,
    action_type: ConversationActionType | str | None = None,
    quote_id: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> CustomerConversationMessage:
    conversation = _get_conversation_row(db, save_game_id, conversation_id)
    sender = _coerce_sender(sender_type)
    message_kind = _coerce_message_type(message_type)
    action = _coerce_action(action_type)
    if staff_id is not None:
        staff = staff_service.get_staff_member(db, save_game_id, staff_id)
        if sender == ConversationMessageSender.STAFF and not sender_label:
            sender_label = staff.name
    message = CustomerConversationMessage(
        conversation_id=conversation.id,
        save_game_id=save_game_id,
        sender_type=sender,
        sender_label=sender_label or _default_sender_label(conversation, sender),
        staff_id=staff_id,
        message_type=message_kind,
        body=body.strip(),
        action_type=action,
        quote_id=quote_id,
        metadata_json=metadata or {},
        created_on_day=_current_day(conversation),
    )
    conversation.last_message_at = datetime.now(timezone.utc)
    if sender in {ConversationMessageSender.PLAYER, ConversationMessageSender.STAFF} and conversation.status not in {
        CustomerConversationStatus.CLOSED_WON,
        CustomerConversationStatus.CLOSED_LOST,
        CustomerConversationStatus.ARCHIVED,
    }:
        conversation.status = CustomerConversationStatus.WAITING_FOR_CUSTOMER
    elif sender == ConversationMessageSender.CUSTOMER and conversation.status not in {
        CustomerConversationStatus.CLOSED_WON,
        CustomerConversationStatus.CLOSED_LOST,
        CustomerConversationStatus.ARCHIVED,
    }:
        conversation.status = CustomerConversationStatus.WAITING_FOR_PLAYER
    conversation.conversion_probability = compute_conversion_probability(db, conversation)
    db.add(message)
    db.flush()
    return message


def add_system_message(
    db: Session,
    save_game_id: int,
    conversation_id: int,
    body: str,
    metadata: dict[str, Any] | None = None,
) -> CustomerConversationMessage:
    return add_message(
        db,
        save_game_id,
        conversation_id,
        sender_type=ConversationMessageSender.SYSTEM,
        sender_label="System",
        message_type=ConversationMessageType.SYSTEM_NOTE,
        body=body,
        metadata=metadata,
    )


def assign_sales_staff(db: Session, save_game_id: int, conversation_id: int, staff_id: int) -> CustomerConversation:
    conversation = _get_conversation_row(db, save_game_id, conversation_id)
    staff = staff_service.get_staff_member(db, save_game_id, staff_id)
    conversation.assigned_staff_id = staff.id
    conversation.status = CustomerConversationStatus.WAITING_FOR_CUSTOMER if conversation.status == CustomerConversationStatus.OPEN else conversation.status
    add_system_message(
        db,
        save_game_id,
        conversation.id,
        f"Assigned sales staff: {staff.name} ({staff.role.value}).",
        metadata={
            "staff_id": staff.id,
            "staff_role": staff.role.value,
        },
    )
    conversation.conversion_probability = compute_conversion_probability(db, conversation)
    _sync_request_from_conversation(conversation)
    db.commit()
    return get_conversation(db, save_game_id, conversation.id)


def quick_reply(db: Session, save_game_id: int, conversation_id: int, action_type: ConversationActionType | str) -> CustomerConversation:
    conversation = _get_conversation_row(db, save_game_id, conversation_id)
    action = _coerce_action(action_type)
    request = conversation.customer_request
    customer = conversation.customer

    if action == ConversationActionType.ASK_BUDGET:
        add_message(
            db,
            save_game_id,
            conversation.id,
            ConversationMessageSender.PLAYER,
            "What budget range are you trying to stay within?",
            sender_label="You",
            message_type=ConversationMessageType.QUICK_REPLY,
            action_type=action,
        )
        add_message(
            db,
            save_game_id,
            conversation.id,
            ConversationMessageSender.CUSTOMER,
            _budget_reply(conversation),
            sender_label=customer.name if customer else "Customer",
            message_type=ConversationMessageType.TEXT,
        )
        conversation.stage = CustomerConversationStage.QUALIFYING_NEEDS
        conversation.status = CustomerConversationStatus.WAITING_FOR_PLAYER
        conversation.engagement_score = _clamp(conversation.engagement_score + 3)
    elif action == ConversationActionType.ASK_USE_CASE:
        add_message(
            db,
            save_game_id,
            conversation.id,
            ConversationMessageSender.PLAYER,
            "What will you mainly use the PC for?",
            sender_label="You",
            message_type=ConversationMessageType.QUICK_REPLY,
            action_type=action,
        )
        add_message(
            db,
            save_game_id,
            conversation.id,
            ConversationMessageSender.CUSTOMER,
            _use_case_reply(request, customer),
            sender_label=customer.name if customer else "Customer",
            message_type=ConversationMessageType.TEXT,
        )
        conversation.stage = CustomerConversationStage.QUALIFYING_NEEDS
        conversation.status = CustomerConversationStatus.WAITING_FOR_PLAYER
        conversation.engagement_score = _clamp(conversation.engagement_score + 3)
    elif action == ConversationActionType.ASK_USED_PARTS:
        add_message(
            db,
            save_game_id,
            conversation.id,
            ConversationMessageSender.PLAYER,
            "Would you accept tested used parts if it keeps the build under budget?",
            sender_label="You",
            message_type=ConversationMessageType.QUICK_REPLY,
            action_type=action,
        )
        reply = _used_parts_reply(conversation, customer)
        add_message(
            db,
            save_game_id,
            conversation.id,
            ConversationMessageSender.CUSTOMER,
            reply,
            sender_label=customer.name if customer else "Customer",
            message_type=ConversationMessageType.TEXT,
            metadata={"accepts_used_parts": conversation.accepts_used_parts},
        )
        conversation.stage = CustomerConversationStage.DISCUSSING_USED_PARTS
        conversation.status = CustomerConversationStatus.WAITING_FOR_PLAYER
        conversation.engagement_score = _clamp(conversation.engagement_score + (5 if conversation.accepts_used_parts else 2))
    elif action == ConversationActionType.RECOMMEND_VALUE_BUILD:
        add_message(
            db,
            save_game_id,
            conversation.id,
            ConversationMessageSender.STAFF if conversation.assigned_staff_id else ConversationMessageSender.PLAYER,
            "A hybrid value build may fit your budget better while preserving performance.",
            sender_label=_assigned_staff_name(conversation),
            message_type=ConversationMessageType.QUICK_REPLY,
            action_type=action,
            staff_id=conversation.assigned_staff_id,
        )
        add_message(
            db,
            save_game_id,
            conversation.id,
            ConversationMessageSender.CUSTOMER,
            _value_build_reply(conversation, customer),
            sender_label=customer.name if customer else "Customer",
            message_type=ConversationMessageType.TEXT,
        )
        conversation.stage = CustomerConversationStage.QUOTE_BUILDING
        conversation.status = CustomerConversationStatus.WAITING_FOR_PLAYER
        conversation.engagement_score = _clamp(conversation.engagement_score + 4)
        conversation.urgency_score = _clamp(conversation.urgency_score + 1)
    elif action == ConversationActionType.RECOMMEND_ALL_NEW_BUILD:
        add_message(
            db,
            save_game_id,
            conversation.id,
            ConversationMessageSender.STAFF if conversation.assigned_staff_id else ConversationMessageSender.PLAYER,
            "An all-new build improves warranty confidence, but it may stretch the budget.",
            sender_label=_assigned_staff_name(conversation),
            message_type=ConversationMessageType.QUICK_REPLY,
            action_type=action,
            staff_id=conversation.assigned_staff_id,
        )
        add_message(
            db,
            save_game_id,
            conversation.id,
            ConversationMessageSender.CUSTOMER,
            _all_new_reply(conversation, customer),
            sender_label=customer.name if customer else "Customer",
            message_type=ConversationMessageType.TEXT,
        )
        conversation.stage = CustomerConversationStage.QUOTE_BUILDING
        conversation.status = CustomerConversationStatus.WAITING_FOR_PLAYER
        conversation.engagement_score = _clamp(conversation.engagement_score + 2)
        conversation.urgency_score = _clamp(conversation.urgency_score + 2)
    elif action == ConversationActionType.EXPLAIN_WARRANTY_RISK:
        add_message(
            db,
            save_game_id,
            conversation.id,
            ConversationMessageSender.STAFF if conversation.assigned_staff_id else ConversationMessageSender.PLAYER,
            "Used or low-confidence parts can save money, but may increase warranty risk.",
            sender_label=_assigned_staff_name(conversation),
            message_type=ConversationMessageType.QUICK_REPLY,
            action_type=action,
            staff_id=conversation.assigned_staff_id,
        )
        add_message(
            db,
            save_game_id,
            conversation.id,
            ConversationMessageSender.CUSTOMER,
            _warranty_reply(conversation, customer),
            sender_label=customer.name if customer else "Customer",
            message_type=ConversationMessageType.TEXT,
        )
        conversation.stage = CustomerConversationStage.NEEDS_CONSULTATION
        conversation.status = CustomerConversationStatus.WAITING_FOR_PLAYER
        conversation.engagement_score = _clamp(conversation.engagement_score + 2)
    elif action == ConversationActionType.GENERATE_QUOTE:
        add_message(
            db,
            save_game_id,
            conversation.id,
            ConversationMessageSender.SYSTEM,
            "Quote build initiated for the current request.",
            sender_label="System",
            message_type=ConversationMessageType.ACTION_EVENT,
            action_type=action,
        )
        conversation.stage = CustomerConversationStage.QUOTE_BUILDING
        conversation.status = CustomerConversationStatus.WAITING_FOR_PLAYER
        conversation.engagement_score = _clamp(conversation.engagement_score + 2)
    elif action == ConversationActionType.CONVERT_TO_ORDER:
        return mark_ready_to_order(db, save_game_id, conversation_id)
    elif action == ConversationActionType.CLOSE_WON:
        return close_conversation(db, save_game_id, conversation_id, won=True)
    elif action == ConversationActionType.CLOSE_LOST:
        return close_conversation(db, save_game_id, conversation_id, won=False)
    else:
        raise bad_request(f"Unsupported quick reply action: {action.value}")

    conversation.conversion_probability = compute_conversion_probability(db, conversation)
    _sync_request_from_conversation(conversation)
    db.commit()
    return get_conversation(db, save_game_id, conversation.id)


def send_quote_to_customer(db: Session, save_game_id: int, conversation_id: int, quote_id: int) -> CustomerConversationMessage:
    conversation = _get_conversation_row(db, save_game_id, conversation_id)
    quote = _get_quote(db, save_game_id, quote_id)
    if conversation.customer_request_id and quote.customer_request_id != conversation.customer_request_id:
        raise bad_request("Quote does not belong to this customer request")
    if conversation.customer_id and quote.customer_id != conversation.customer_id:
        raise bad_request("Quote does not belong to this customer")

    if quote.status == QuoteStatus.DRAFT:
        quote.status = QuoteStatus.PRESENTED

    message = add_message(
        db,
        save_game_id,
        conversation.id,
        sender_type=ConversationMessageSender.SYSTEM,
        sender_label="System",
        message_type=ConversationMessageType.QUOTE_ATTACHMENT,
        action_type=ConversationActionType.SEND_QUOTE,
        quote_id=quote.id,
        body=f"Quote attached: #{quote.id} - {quote.title}",
        metadata={
            "quote_id": quote.id,
            "quote_status": quote.status.value,
            "quoted_price_vnd": quote.quoted_price_vnd,
            "estimated_cost_vnd": quote.estimated_cost_vnd,
            "estimated_profit_vnd": quote.estimated_profit_vnd,
            "quote_acceptance_chance": quote.quote_acceptance_chance,
            "customer_fit_score": quote.customer_fit_score,
            "compatibility_score": getattr(quote, "compatibility_score", None),
            "build_quality_score_estimate": getattr(quote, "build_quality_score_estimate", None),
            "warranty_risk": quote.warranty_risk,
        },
    )
    if quote.quote_acceptance_chance is not None and quote.quote_acceptance_chance >= 75:
        conversation.status = CustomerConversationStatus.READY_TO_ORDER
    else:
        conversation.status = CustomerConversationStatus.QUOTE_PROPOSED
    conversation.stage = CustomerConversationStage.QUOTE_SENT
    conversation.engagement_score = _clamp(conversation.engagement_score + 4)
    conversation.conversion_probability = compute_conversion_probability(db, conversation, quote)
    _sync_request_from_conversation(conversation)
    db.commit()
    return message


def mark_ready_to_order(db: Session, save_game_id: int, conversation_id: int) -> CustomerConversation:
    conversation = _get_conversation_row(db, save_game_id, conversation_id)
    conversation.status = CustomerConversationStatus.READY_TO_ORDER
    conversation.stage = CustomerConversationStage.READY_TO_ORDER
    conversation.engagement_score = _clamp(conversation.engagement_score + 5)
    add_system_message(
        db,
        save_game_id,
        conversation.id,
        "Customer is ready to order. Quote can now be converted using the existing quote workflow.",
        metadata={"event": "ready_to_order"},
    )
    conversation.conversion_probability = compute_conversion_probability(db, conversation)
    _sync_request_from_conversation(conversation)
    db.commit()
    return get_conversation(db, save_game_id, conversation.id)


def close_conversation(db: Session, save_game_id: int, conversation_id: int, won: bool) -> CustomerConversation:
    conversation = _get_conversation_row(db, save_game_id, conversation_id)
    conversation.status = CustomerConversationStatus.CLOSED_WON if won else CustomerConversationStatus.CLOSED_LOST
    conversation.stage = CustomerConversationStage.CLOSED
    conversation.closed_on_day = _current_day(conversation)
    conversation.conversion_probability = 100 if won else 0
    add_system_message(
        db,
        save_game_id,
        conversation.id,
        "Conversation closed as won." if won else "Conversation closed as lost.",
        metadata={"won": won, "event": "conversation_closed"},
    )
    _sync_request_from_conversation(conversation)
    db.commit()
    return get_conversation(db, save_game_id, conversation.id)


def compute_conversion_probability(db: Session, conversation: CustomerConversation, quote: Quote | None = None) -> int:
    request = conversation.customer_request
    customer = conversation.customer
    base = 20
    base += min(20, conversation.engagement_score // 3)
    base += max(0, conversation.urgency_score // 8)
    if conversation.status == CustomerConversationStatus.QUOTE_PROPOSED:
        base += 10
    elif conversation.status == CustomerConversationStatus.READY_TO_ORDER:
        base += 18
    elif conversation.status in {CustomerConversationStatus.CLOSED_WON, CustomerConversationStatus.CLOSED_LOST}:
        base = 100 if conversation.status == CustomerConversationStatus.CLOSED_WON else 0
    if conversation.stage in {CustomerConversationStage.QUOTE_SENT, CustomerConversationStage.QUOTE_BUILDING}:
        base += 8

    if quote is not None:
        if quote.quote_acceptance_chance is not None:
            base = int(round((base * 0.45) + (quote.quote_acceptance_chance * 0.55)))
        if quote.customer_fit_score is not None:
            base += (quote.customer_fit_score - 50) // 3
        if quote.performance_score is not None and request and request.target_performance_score:
            base += 4 if quote.performance_score >= request.target_performance_score else -4
        if quote.warranty_risk == "LOW":
            base += _warranty_bonus(request, customer, 6)
        elif quote.warranty_risk == "HIGH":
            base -= _warranty_bonus(request, customer, 8)

    if request:
        if request.accepts_used_parts is not None:
            if conversation.accepts_used_parts == request.accepts_used_parts:
                base += 10
            else:
                base -= 8
        if request.min_compatibility_score:
            base += 4 if request.min_compatibility_score >= 75 else 2
        if request.min_build_quality_score:
            base += 4 if request.min_build_quality_score >= 75 else 2
        if request.warranty_expectation_days:
            base += 4 if request.warranty_expectation_days >= 60 else 1
        if request.budget_vnd:
            if quote is not None and quote.quoted_price_vnd:
                price_ratio = quote.quoted_price_vnd / max(1, request.budget_vnd)
                if price_ratio <= 0.9:
                    base += 10
                elif price_ratio <= 1.0:
                    base += 6
                elif price_ratio <= 1.15:
                    base += 2
                else:
                    base -= 8
            else:
                base += 2 if request.budget_vnd <= 30_000_000 else 0

    if customer:
        if customer.price_sensitivity is not None:
            base += max(0, 8 - (customer.price_sensitivity // 15))
        if customer.reliability_priority is not None:
            base += max(0, customer.reliability_priority // 18)
        if customer.warranty_sensitivity is not None:
            base += max(0, customer.warranty_sensitivity // 16)
        if customer.accepts_used_parts is True:
            base += 4
        elif customer.accepts_used_parts is False:
            base -= 4

    if conversation.assigned_staff_id:
        staff = db.get(StaffMember, conversation.assigned_staff_id)
        if staff:
            if staff.role in {StaffRole.SALES, StaffRole.MARKETING}:
                base += max(2, staff.sales_skill // 16)
            else:
                base += max(1, staff.support_skill // 20)
            base -= min(5, staff.fatigue // 20)

    return _clamp(base)


def extract_basic_intent_from_request(customer_request: CustomerRequest | None, customer: Customer | None) -> dict[str, Any]:
    request = customer_request
    source_customer = customer or (request.customer if request else None)
    detected = {
        "budget_vnd": request.budget_vnd if request else None,
        "use_case": request.use_case if request else None,
        "persona_type": request.persona_type if request and request.persona_type else (source_customer.persona_type if source_customer else None),
        "accepts_used_parts": request.accepts_used_parts if request and request.accepts_used_parts is not None else (source_customer.accepts_used_parts if source_customer else None),
        "warranty_sensitivity": request.warranty_expectation_days if request and request.warranty_expectation_days is not None else (source_customer.warranty_sensitivity if source_customer else None),
        "price_sensitivity": source_customer.price_sensitivity if source_customer else None,
        "performance_priority": source_customer.performance_priority if source_customer else None,
        "reliability_priority": source_customer.reliability_priority if source_customer else None,
        "aesthetics_priority": source_customer.aesthetics_priority if source_customer else None,
        "preferred_brand_slugs": source_customer.preferred_brand_slugs_json if source_customer else None,
        "disliked_brand_slugs": source_customer.disliked_brand_slugs_json if source_customer else None,
        "priority_tags": request.priority_tags_json if request else None,
    }
    return {key: value for key, value in detected.items() if value is not None}


def _conversation_query(include_messages: bool = False):
    query = select(CustomerConversation).options(
        selectinload(CustomerConversation.save_game),
        selectinload(CustomerConversation.customer),
        selectinload(CustomerConversation.customer_request).selectinload(CustomerRequest.customer),
        selectinload(CustomerConversation.assigned_staff),
    )
    if include_messages:
        query = query.options(
            selectinload(CustomerConversation.messages),
        )
    return query


def _get_conversation_row(db: Session, save_game_id: int, conversation_id: int) -> CustomerConversation:
    conversation = db.scalar(
        _conversation_query(include_messages=True).where(
            CustomerConversation.save_game_id == save_game_id,
            CustomerConversation.id == conversation_id,
        )
    )
    if not conversation:
        raise not_found("Customer conversation not found")
    return conversation


def _get_customer_request(db: Session, save_game_id: int, request_id: int) -> CustomerRequest:
    request = db.scalar(
        select(CustomerRequest)
        .join(CustomerRequest.customer)
        .options(selectinload(CustomerRequest.customer))
        .where(CustomerRequest.id == request_id, Customer.save_game_id == save_game_id)
    )
    if not request:
        raise not_found("Customer request not found")
    return request


def _get_quote(db: Session, save_game_id: int, quote_id: int) -> Quote:
    quote = db.scalar(
        select(Quote)
        .where(Quote.save_game_id == save_game_id, Quote.id == quote_id)
        .options(selectinload(Quote.customer_request).selectinload(CustomerRequest.customer))
    )
    if not quote:
        raise not_found("Quote not found")
    return quote


def _sync_request_state(request: CustomerRequest, conversation: CustomerConversation) -> None:
    request.conversation_id = conversation.id
    request.conversation_status = conversation.status.value


def _sync_request_from_conversation(conversation: CustomerConversation) -> None:
    request = conversation.customer_request
    if request is None:
        return
    request.conversation_id = conversation.id
    request.conversation_status = conversation.status.value
    if conversation.status == CustomerConversationStatus.CLOSED_LOST and request.status not in {
        CustomerRequestStatus.ACCEPTED,
        CustomerRequestStatus.COMPLETED,
    }:
        request.status = CustomerRequestStatus.REJECTED


def _build_conversation_title(request: CustomerRequest | None, customer: Customer | None) -> str | None:
    if not customer and not request:
        return None
    if request:
        return f"{customer.name if customer else 'Customer'} - {request.use_case[:70]}"
    return f"{customer.name if customer else 'Customer'} consultation"


def _build_customer_opening_message(request: CustomerRequest | None, customer: Customer | None, conversation: CustomerConversation) -> str:
    if request:
        budget = _format_vnd(request.budget_vnd)
        use_case = request.use_case.rstrip(".")
        if request.request_type.value == "BUILD_PC":
            return f"I need a PC for {use_case}. My budget is around {budget}."
        if request.request_type.value == "BUY_COMPONENT":
            return f"I'm looking for a component for {use_case}. I can spend about {budget}."
        if request.request_type.value == "UPGRADE_PC":
            return f"I want to upgrade my PC for {use_case}. I can stay near {budget}."
        if request.request_type.value == "REPAIR":
            return f"My PC needs repair for {use_case}. I'd like to keep it near {budget}."
    persona_text = conversation.persona_type or (customer.persona_type if customer else "GENERIC")
    return f"I'm here to talk about a build and I care about a {persona_text.lower().replace('_', ' ')} plan."


def _build_customer_mood(customer: Customer | None, request: CustomerRequest | None) -> str | None:
    persona = _persona_type(request, customer) or "GENERIC"
    mapping = {
        "BUDGET_GAMER": "pragmatic",
        "BARGAIN_HUNTER": "careful",
        "WARRANTY_SENSITIVE": "cautious",
        "PREMIUM_BUILDER": "focused",
        "RGB_ENTHUSIAST": "excited",
        "STREAMER": "busy",
        "CREATOR_EDITOR": "detailed",
        "OFFICE_BUYER": "efficient",
        "AI_WORKSTATION": "technical",
    }
    return mapping.get(persona, "curious")


def _initial_engagement_score(customer: Customer | None, request: CustomerRequest | None) -> int:
    score = 50
    if customer:
        score += max(0, (customer.patience - 50) // 8)
        score += max(0, (customer.negotiation_score - 50) // 12)
    if request:
        if request.accepts_used_parts is True:
            score += 4
        if request.request_type.value == "BUILD_PC":
            score += 4
        elif request.request_type.value == "REPAIR":
            score -= 2
    return _clamp(score)


def _initial_urgency_score(customer: Customer | None, request: CustomerRequest | None) -> int:
    score = 50
    if request:
        if request.budget_vnd <= 15_000_000:
            score += 4
        if request.request_type.value == "REPAIR":
            score += 8
        if request.request_type.value == "UPGRADE_PC":
            score += 3
    if customer and customer.risk_tolerance.value == "LOW":
        score += 4
    return _clamp(score)


def _accepts_used_parts(request: CustomerRequest | None, customer: Customer | None, detected: dict[str, Any]) -> bool | None:
    if request and request.accepts_used_parts is not None:
        return request.accepts_used_parts
    if customer and customer.accepts_used_parts is not None:
        return customer.accepts_used_parts
    persona = detected.get("persona_type")
    if persona in {"BUDGET_GAMER", "BARGAIN_HUNTER"}:
        return True
    if persona in {"WARRANTY_SENSITIVE", "PREMIUM_BUILDER"}:
        return False
    return None


def _persona_type(request: CustomerRequest | None, customer: Customer | None) -> str | None:
    if request and request.persona_type:
        return request.persona_type
    if customer and customer.persona_type:
        return customer.persona_type
    return None


def _budget_reply(conversation: CustomerConversation) -> str:
    if conversation.detected_budget_vnd:
        return f"I would like to stay near {_format_vnd(conversation.detected_budget_vnd)} if possible."
    return "I want to keep the budget sensible if we can."


def _use_case_reply(request: CustomerRequest | None, customer: Customer | None) -> str:
    if request:
        return f"Mostly for {request.use_case.rstrip('.')}. That's the main thing I need to cover."
    return f"Mostly for {customer.persona_type if customer and customer.persona_type else 'general use'}."


def _used_parts_reply(conversation: CustomerConversation, customer: Customer | None) -> str:
    if conversation.accepts_used_parts is True:
        return "Used parts are okay if they are tested and not risky."
    if conversation.accepts_used_parts is False:
        return "I prefer new parts. I care about warranty and reliability."
    if customer and customer.risk_tolerance.value == "HIGH":
        return "I might consider used parts if the savings are worth it."
    return "I'm not sure yet, but I want to hear the tradeoffs first."


def _value_build_reply(conversation: CustomerConversation, customer: Customer | None) -> str:
    if customer and customer.price_sensitivity is not None and customer.price_sensitivity >= 60:
        return "That sounds practical. I just want it to stay within budget."
    return "That sounds sensible if it keeps the performance balanced."


def _all_new_reply(conversation: CustomerConversation, customer: Customer | None) -> str:
    if customer and customer.warranty_sensitivity is not None and customer.warranty_sensitivity >= 60:
        return "I prefer new parts if the price still works and the warranty feels safer."
    return "I like the warranty angle, but we need to keep an eye on price."


def _warranty_reply(conversation: CustomerConversation, customer: Customer | None) -> str:
    if customer and customer.warranty_sensitivity is not None and customer.warranty_sensitivity >= 60:
        return "Warranty matters a lot to me, so I want the safer option."
    return "I understand the risk. Let's balance warranty and budget."


def _assigned_staff_name(conversation: CustomerConversation) -> str:
    return conversation.assigned_staff.name if conversation.assigned_staff else "Staff"


def _default_sender_label(conversation: CustomerConversation, sender: ConversationMessageSender) -> str:
    if sender == ConversationMessageSender.CUSTOMER:
        return conversation.customer.name if conversation.customer else "Customer"
    if sender == ConversationMessageSender.STAFF:
        return conversation.assigned_staff.name if conversation.assigned_staff else "Staff"
    if sender == ConversationMessageSender.PLAYER:
        return "You"
    return "System"


def _coerce_status(status: CustomerConversationStatus | str) -> CustomerConversationStatus:
    if isinstance(status, CustomerConversationStatus):
        return status
    return CustomerConversationStatus[str(status)]


def _coerce_sender(sender: ConversationMessageSender | str) -> ConversationMessageSender:
    if isinstance(sender, ConversationMessageSender):
        return sender
    return ConversationMessageSender[str(sender)]


def _coerce_message_type(message_type: ConversationMessageType | str) -> ConversationMessageType:
    if isinstance(message_type, ConversationMessageType):
        return message_type
    return ConversationMessageType[str(message_type)]


def _coerce_action(action_type: ConversationActionType | str | None) -> ConversationActionType | None:
    if action_type is None:
        return None
    if isinstance(action_type, ConversationActionType):
        return action_type
    return ConversationActionType[str(action_type)]


def _current_day(conversation: CustomerConversation) -> int | None:
    if conversation.save_game and conversation.save_game.game_day:
        return conversation.save_game.game_day
    if conversation.created_on_day is not None:
        return conversation.created_on_day
    return None


def _format_vnd(amount: int | None) -> str:
    if amount is None:
        return "N/A"
    return f"₫{amount:,}"


def _clamp(value: int, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, value))


def _warranty_bonus(request: CustomerRequest | None, customer: Customer | None, amount: int) -> int:
    if request and request.warranty_expectation_days and request.warranty_expectation_days >= 60:
        amount += 2
    if customer and customer.warranty_sensitivity is not None and customer.warranty_sensitivity >= 60:
        amount += 2
    return amount
