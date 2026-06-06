from fastapi import APIRouter, Body, Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.errors import bad_request, not_found
from app.models.entities import HardwareProduct, InventoryUnit
from app.schemas.game import CompatibilityEvaluateRequest, CompatibilityResultRead
from app.services import compatibility_service, order_service, quote_service
from app.services.player_profile_service import require_profile_access

router = APIRouter(prefix="/api", tags=["compatibility"])


@router.post("/compatibility/evaluate", response_model=CompatibilityResultRead)
def evaluate_compatibility(
    payload: CompatibilityEvaluateRequest = Body(...),
    db: Session = Depends(get_db),
    x_profile_unlock_token: str | None = Header(None, alias="X-Profile-Unlock-Token"),
):
    components: list[object] = []

    if payload.product_ids:
        unique_product_ids = list(dict.fromkeys(payload.product_ids))
        products = list(
            db.scalars(
                select(HardwareProduct).where(HardwareProduct.id.in_(unique_product_ids))
            )
        )
        if len(products) != len(unique_product_ids):
            raise not_found("Hardware product not found")
        product_map = {product.id: product for product in products}
        components.extend(product_map[product_id] for product_id in payload.product_ids)

    if payload.inventory_unit_ids:
        if payload.save_game_id is None:
            raise bad_request("save_game_id is required when evaluating inventory units")
        require_profile_access(db, payload.save_game_id, x_profile_unlock_token)
        unique_inventory_ids = list(dict.fromkeys(payload.inventory_unit_ids))
        inventory_units = list(
            db.scalars(
                select(InventoryUnit)
                .options(selectinload(InventoryUnit.product))
                .where(
                    InventoryUnit.id.in_(unique_inventory_ids),
                    InventoryUnit.save_game_id == payload.save_game_id,
                )
            )
        )
        if len(inventory_units) != len(unique_inventory_ids):
            raise not_found("Inventory unit not found")
        inventory_map = {unit.id: unit for unit in inventory_units}
        components.extend(inventory_map[inventory_id] for inventory_id in payload.inventory_unit_ids)

    return compatibility_service.evaluate_build_compatibility(db, components)


@router.get("/save-games/{save_game_id}/quotes/{quote_id}/compatibility", response_model=CompatibilityResultRead)
def get_quote_compatibility(save_game_id: int, quote_id: int, db: Session = Depends(get_db)):
    quote = quote_service.get_quote(db, save_game_id, quote_id)
    return compatibility_service.evaluate_quote_compatibility(db, quote)


@router.get("/save-games/{save_game_id}/orders/{order_id}/compatibility", response_model=CompatibilityResultRead)
def get_order_compatibility(save_game_id: int, order_id: int, db: Session = Depends(get_db)):
    order = order_service.get_order(db, save_game_id, order_id)
    return compatibility_service.evaluate_order_compatibility(db, order)
