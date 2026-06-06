from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.game import DeliverOrderRequest, DeliverOrderResponse, OrderCreate, OrderDetailRead, OrderFulfillmentEventRead, OrderRead
from app.services import order_fulfillment_service, order_service

router = APIRouter(prefix="/api/save-games/{save_game_id}/orders", tags=["orders"])


@router.get("", response_model=list[OrderRead])
def list_orders(save_game_id: int, db: Session = Depends(get_db)):
    return order_service.list_orders(db, save_game_id)


@router.post("", response_model=OrderRead)
def create_order(save_game_id: int, payload: OrderCreate, db: Session = Depends(get_db)):
    return order_service.create_order(db, save_game_id, payload)


def _detail(order) -> dict[str, object]:
    return {
        "order": order,
        "fulfillment_events": order.fulfillment_events,
        "compatibility_result": getattr(order, "compatibility_result", None),
    }


@router.get("/{order_id}", response_model=OrderDetailRead)
def get_order(save_game_id: int, order_id: int, db: Session = Depends(get_db)):
    return _detail(order_service.get_order(db, save_game_id, order_id))


@router.post("/{order_id}/start-build", response_model=OrderDetailRead)
def start_build(save_game_id: int, order_id: int, db: Session = Depends(get_db)):
    return _detail(order_fulfillment_service.start_order_build(db, save_game_id, order_id))


@router.post("/{order_id}/run-build-test", response_model=OrderDetailRead)
def run_build_test(save_game_id: int, order_id: int, db: Session = Depends(get_db)):
    return _detail(order_fulfillment_service.run_order_build_test(db, save_game_id, order_id))


@router.post("/{order_id}/deliver", response_model=DeliverOrderResponse)
def deliver_order(
    save_game_id: int,
    order_id: int,
    payload: DeliverOrderRequest | None = None,
    db: Session = Depends(get_db),
):
    result = order_fulfillment_service.deliver_order(db, save_game_id, order_id, force=payload.force if payload else False)
    return {
        "order_detail": _detail(result["order"]),
        "cash_delta": result["cash_delta"],
        "reputation_delta": result["reputation_delta"],
    }


@router.get("/{order_id}/fulfillment-events", response_model=list[OrderFulfillmentEventRead])
def list_fulfillment_events(save_game_id: int, order_id: int, db: Session = Depends(get_db)):
    return order_service.list_fulfillment_events(db, save_game_id, order_id)


@router.post("/{order_id}/cancel", response_model=OrderDetailRead)
def cancel_order(save_game_id: int, order_id: int, db: Session = Depends(get_db)):
    return _detail(order_fulfillment_service.cancel_order(db, save_game_id, order_id))
