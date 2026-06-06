from fastapi import APIRouter, Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.errors import not_found
from app.models.entities import Customer, CustomerRequest
from app.models.enums import CustomerRequestStatus
from app.schemas.game import (
    CustomerPersonaAssignRequest,
    CustomerPersonaDefinitionRead,
    CustomerRead,
    QuotePersonaEvaluationRead,
)
from app.services import customer_persona_service, quote_service, player_profile_service


router = APIRouter(tags=["customer personas"])


@router.get("/api/customer-personas", response_model=list[CustomerPersonaDefinitionRead])
def list_customer_personas():
    return customer_persona_service.list_personas()


@router.get("/api/customer-personas/{persona_type}", response_model=CustomerPersonaDefinitionRead)
def get_customer_persona(persona_type: str):
    return customer_persona_service.get_persona_definition(persona_type)


@router.post("/api/save-games/{save_game_id}/customers/{customer_id}/persona", response_model=CustomerRead)
def assign_customer_persona(
    save_game_id: int,
    customer_id: int,
    payload: CustomerPersonaAssignRequest,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    player_profile_service.require_profile_access(db, save_game_id, x_profile_unlock_token)
    customer = db.scalar(
        select(Customer)
        .options(selectinload(Customer.requests))
        .where(Customer.id == customer_id, Customer.save_game_id == save_game_id)
    )
    if not customer:
        raise not_found("Customer not found")

    customer_persona_service.apply_persona_to_customer(db, customer, payload.persona_type)
    for request in customer.requests:
        if request.status in {CustomerRequestStatus.NEW, CustomerRequestStatus.IN_CONSULTATION, CustomerRequestStatus.QUOTED}:
            customer_persona_service.apply_persona_to_request(db, request, customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.post(
    "/api/save-games/{save_game_id}/customer-requests/{request_id}/evaluate-quotes",
    response_model=list[QuotePersonaEvaluationRead],
)
def evaluate_request_quotes(
    save_game_id: int,
    request_id: int,
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
    db: Session = Depends(get_db),
):
    player_profile_service.require_profile_access(db, save_game_id, x_profile_unlock_token)
    customer_request = db.scalar(
        select(CustomerRequest)
        .join(CustomerRequest.customer)
        .options(selectinload(CustomerRequest.customer))
        .where(CustomerRequest.id == request_id, Customer.save_game_id == save_game_id)
    )
    if not customer_request:
        raise not_found("Customer request not found")

    quotes = quote_service.list_quotes_for_request(db, save_game_id, request_id)
    evaluations: list[dict[str, object]] = []
    for quote in quotes:
        evaluation = customer_persona_service.evaluate_quote_for_persona(db, quote)
        evaluation["quote_id"] = quote.id
        evaluations.append(evaluation)
    db.commit()
    return evaluations
