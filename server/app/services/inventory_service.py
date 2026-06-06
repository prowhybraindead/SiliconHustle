from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import not_found
from app.models.entities import Brand, HardwareProduct, InventoryUnit
from app.models.enums import ConditionType, Grade, InventorySource, InventoryStatus
from app.schemas.game import InventoryUnitCreate, InventoryUnitUpdate
from app.services.save_game_service import get_save_game


def list_inventory(db: Session, save_game_id: int) -> list[InventoryUnit]:
    get_save_game(db, save_game_id)
    return list(
        db.scalars(
            select(InventoryUnit)
            .options(
                selectinload(InventoryUnit.product).selectinload(HardwareProduct.brand_record).selectinload(Brand.categories),
                selectinload(InventoryUnit.product).selectinload(HardwareProduct.chip_vendor_brand).selectinload(Brand.categories),
            )
            .where(InventoryUnit.save_game_id == save_game_id)
            .order_by(InventoryUnit.updated_at.desc())
        )
    )


def get_inventory_unit(db: Session, save_game_id: int, inventory_unit_id: int) -> InventoryUnit:
    unit = db.scalar(
        select(InventoryUnit)
        .options(
            selectinload(InventoryUnit.product).selectinload(HardwareProduct.brand_record).selectinload(Brand.categories),
            selectinload(InventoryUnit.product).selectinload(HardwareProduct.chip_vendor_brand).selectinload(Brand.categories),
        )
        .where(InventoryUnit.save_game_id == save_game_id, InventoryUnit.id == inventory_unit_id)
    )
    if not unit:
        raise not_found("Inventory unit not found")
    return unit


def create_inventory_unit(db: Session, save_game_id: int, payload: InventoryUnitCreate) -> InventoryUnit:
    get_save_game(db, save_game_id)
    product = db.get(HardwareProduct, payload.product_id)
    if not product:
        raise not_found("Hardware product not found")

    is_new_supplier = payload.condition_type == ConditionType.NEW and payload.source == InventorySource.SUPPLIER
    unit = InventoryUnit(
        save_game_id=save_game_id,
        product_id=payload.product_id,
        serial_number=f"SH-{save_game_id}-{uuid4().hex[:8].upper()}",
        condition_type=payload.condition_type,
        source=payload.source,
        purchase_price_vnd=payload.purchase_price_vnd,
        listed_price_vnd=payload.listed_price_vnd,
        warranty_months_remaining=payload.warranty_months_remaining,
        notes=payload.notes,
        status=InventoryStatus.READY_FOR_SALE if is_new_supplier else InventoryStatus.UNTESTED,
        grade=Grade.A if is_new_supplier else Grade.UNKNOWN,
        inspection_confidence=90 if is_new_supplier else 0,
        health_score=96 if is_new_supplier else None,
        performance_score=product.base_performance_score if is_new_supplier else None,
        thermal_score=max(20, 100 - product.base_heat_score) if is_new_supplier else None,
        fan_score=94 if is_new_supplier else None,
        vram_score=95 if is_new_supplier and product.category.value == "GPU" else None,
        stability_score=95 if is_new_supplier else None,
        warranty_risk="LOW" if is_new_supplier else None,
    )
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return get_inventory_unit(db, save_game_id, unit.id)


def update_inventory_unit(
    db: Session, save_game_id: int, inventory_unit_id: int, payload: InventoryUnitUpdate
) -> InventoryUnit:
    unit = get_inventory_unit(db, save_game_id, inventory_unit_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(unit, field, value)
    db.commit()
    db.refresh(unit)
    return get_inventory_unit(db, save_game_id, unit.id)
