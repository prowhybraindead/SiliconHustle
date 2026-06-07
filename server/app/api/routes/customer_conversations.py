from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.game import (
    ConversationAssignStaffRequest,
    ConversationCloseRequest,
    ConversationMessageCreateRequest,
    ConversationQuickReplyRequest,
    ConversationSendQuoteResponse,
    CustomerConversationCreateResponse,
    CustomerConversationDetailRead,
    CustomerConversationMessageRead,
    CustomerConversationRead,
)
from app.services import customer_conversation_service, player_profile_service, quote_service

router = APIRouter(prefix="/api/save-games/{save_game_id}", tags=["customer conversations"])


def _require_access(db: Session, save_game_id: int, token: str | None) -> None:
    player_profile_service.require_profile_access(db, save_game_id, token)


@router.get("/customer-conversations", response_model=list[CustomerConversationRead])
def list_conversations(
    save_game_id: int,
    status: str | None = None,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    _require_access(db, save_game_id, x_profile_unlock_token)
    return [CustomerConversationRead.model_validate(conversation) for conversation in customer_conversation_service.list_conversations(db, save_game_id, status=status)]


@router.post("/customer-requests/{request_id}/conversation", response_model=CustomerConversationCreateResponse)
def create_conversation_for_request(
    save_game_id: int,
    request_id: int,
    locale: str | None = None,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    _require_access(db, save_game_id, x_profile_unlock_token)
    request = customer_conversation_service._get_customer_request(db, save_game_id, request_id)
    created = request.conversation_id is None
    conversation = customer_conversation_service.get_or_create_conversation_for_request(db, save_game_id, request_id, locale=locale)
    return CustomerConversationCreateResponse(conversation=CustomerConversationDetailRead.model_validate(conversation), created=created)


@router.get("/customer-conversations/{conversation_id}", response_model=CustomerConversationDetailRead)
def get_conversation(
    save_game_id: int,
    conversation_id: int,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    _require_access(db, save_game_id, x_profile_unlock_token)
    return CustomerConversationDetailRead.model_validate(customer_conversation_service.get_conversation(db, save_game_id, conversation_id))


@router.get("/customer-conversations/{conversation_id}/messages", response_model=list[CustomerConversationMessageRead])
def list_messages(
    save_game_id: int,
    conversation_id: int,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    _require_access(db, save_game_id, x_profile_unlock_token)
    return customer_conversation_service.list_messages(db, save_game_id, conversation_id)


@router.post("/customer-conversations/{conversation_id}/messages", response_model=CustomerConversationDetailRead)
def add_message(
    save_game_id: int,
    conversation_id: int,
    payload: ConversationMessageCreateRequest,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    _require_access(db, save_game_id, x_profile_unlock_token)
    conversation = customer_conversation_service.handle_player_message(
        db,
        save_game_id,
        conversation_id,
        body=payload.body,
        locale=payload.locale,
    )
    return CustomerConversationDetailRead.model_validate(conversation)


@router.post("/customer-conversations/{conversation_id}/quick-reply", response_model=CustomerConversationDetailRead)
def quick_reply(
    save_game_id: int,
    conversation_id: int,
    payload: ConversationQuickReplyRequest,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    _require_access(db, save_game_id, x_profile_unlock_token)
    return CustomerConversationDetailRead.model_validate(
        customer_conversation_service.quick_reply(db, save_game_id, conversation_id, payload.action_type, locale=payload.locale)
    )


@router.post("/customer-conversations/{conversation_id}/assign-staff", response_model=CustomerConversationDetailRead)
def assign_staff(
    save_game_id: int,
    conversation_id: int,
    payload: ConversationAssignStaffRequest,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    _require_access(db, save_game_id, x_profile_unlock_token)
    return CustomerConversationDetailRead.model_validate(
        customer_conversation_service.assign_sales_staff(db, save_game_id, conversation_id, payload.staff_id, locale=payload.locale)
    )


@router.post("/customer-conversations/{conversation_id}/send-quote/{quote_id}", response_model=ConversationSendQuoteResponse)
def send_quote(
    save_game_id: int,
    conversation_id: int,
    quote_id: int,
    locale: str | None = None,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    _require_access(db, save_game_id, x_profile_unlock_token)
    message = customer_conversation_service.send_quote_to_customer(db, save_game_id, conversation_id, quote_id, locale=locale)
    conversation = customer_conversation_service.get_conversation(db, save_game_id, conversation_id)
    quote = quote_service.get_quote(db, save_game_id, quote_id)
    return ConversationSendQuoteResponse(
        conversation=CustomerConversationDetailRead.model_validate(conversation),
        quote=quote,
        message=message,
        conversion_probability=conversation.conversion_probability,
    )


@router.post("/customer-conversations/{conversation_id}/ready-to-order", response_model=CustomerConversationDetailRead)
def ready_to_order(
    save_game_id: int,
    conversation_id: int,
    locale: str | None = None,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    _require_access(db, save_game_id, x_profile_unlock_token)
    return CustomerConversationDetailRead.model_validate(
        customer_conversation_service.mark_ready_to_order(db, save_game_id, conversation_id, locale=locale)
    )


@router.post("/customer-conversations/{conversation_id}/close", response_model=CustomerConversationDetailRead)
def close_conversation(
    save_game_id: int,
    conversation_id: int,
    payload: ConversationCloseRequest,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    _require_access(db, save_game_id, x_profile_unlock_token)
    return CustomerConversationDetailRead.model_validate(
        customer_conversation_service.close_conversation(db, save_game_id, conversation_id, payload.won, locale=payload.locale)
    )
