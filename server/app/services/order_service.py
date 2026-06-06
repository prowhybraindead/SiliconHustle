from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import not_found
from app.models.entities import Brand, Customer, HardwareProduct, InventoryUnit, Order, OrderFulfillmentEvent, OrderItem
from app.schemas.game import OrderCreate
from app.services import compatibility_service
from app.services.save_game_service import get_save_game


def list_orders(db: Session, save_game_id: int) -> list[Order]:
    get_save_game(db, save_game_id)
    orders = list(
        db.scalars(
            select(Order)
            .options(
                selectinload(Order.customer),
                selectinload(Order.request),
                selectinload(Order.items).selectinload(OrderItem.product).selectinload(HardwareProduct.brand_record).selectinload(Brand.categories),
                selectinload(Order.items).selectinload(OrderItem.product).selectinload(HardwareProduct.chip_vendor_brand).selectinload(Brand.categories),
                selectinload(Order.items)
                .selectinload(OrderItem.inventory_unit)
                .selectinload(InventoryUnit.product)
                .selectinload(HardwareProduct.brand_record)
                .selectinload(Brand.categories),
                selectinload(Order.items)
                .selectinload(OrderItem.inventory_unit)
                .selectinload(InventoryUnit.product)
                .selectinload(HardwareProduct.chip_vendor_brand)
                .selectinload(Brand.categories),
            )
            .where(Order.save_game_id == save_game_id)
            .order_by(Order.created_at.desc())
        )
    )
    for order in orders:
        compatibility_service.evaluate_order_compatibility(db, order)
    return orders


def create_order(db: Session, save_game_id: int, payload: OrderCreate) -> Order:
    get_save_game(db, save_game_id)
    customer = db.get(Customer, payload.customer_id)
    if not customer or customer.save_game_id != save_game_id:
        raise not_found("Customer not found")

    order = Order(
        save_game_id=save_game_id,
        customer_id=payload.customer_id,
        request_id=payload.request_id,
        quoted_price_vnd=payload.quoted_price_vnd,
        cost_vnd=payload.cost_vnd,
        profit_vnd=payload.quoted_price_vnd - payload.cost_vnd,
        customer_fit_score=70,
        notes=payload.notes,
        items=[
            OrderItem(
                product_id=item.product_id,
                inventory_unit_id=item.inventory_unit_id,
                quantity=item.quantity,
                unit_price_vnd=item.unit_price_vnd,
                cost_vnd=item.cost_vnd,
            )
            for item in payload.items
        ],
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    created_order = db.scalar(
        select(Order)
        .options(
            selectinload(Order.customer),
            selectinload(Order.items).selectinload(OrderItem.product).selectinload(HardwareProduct.brand_record).selectinload(Brand.categories),
            selectinload(Order.items).selectinload(OrderItem.product).selectinload(HardwareProduct.chip_vendor_brand).selectinload(Brand.categories),
            selectinload(Order.items).selectinload(OrderItem.inventory_unit).selectinload(InventoryUnit.product).selectinload(HardwareProduct.brand_record).selectinload(Brand.categories),
            selectinload(Order.items).selectinload(OrderItem.inventory_unit).selectinload(InventoryUnit.product).selectinload(HardwareProduct.chip_vendor_brand).selectinload(Brand.categories),
        )
        .where(Order.id == order.id)
    )
    compatibility_service.evaluate_order_compatibility(db, created_order)
    return created_order


def get_order(db: Session, save_game_id: int, order_id: int) -> Order:
    order = db.scalar(
        select(Order)
        .options(
            selectinload(Order.customer),
            selectinload(Order.request),
            selectinload(Order.items).selectinload(OrderItem.product).selectinload(HardwareProduct.brand_record).selectinload(Brand.categories),
            selectinload(Order.items).selectinload(OrderItem.product).selectinload(HardwareProduct.chip_vendor_brand).selectinload(Brand.categories),
            selectinload(Order.items)
            .selectinload(OrderItem.inventory_unit)
            .selectinload(InventoryUnit.product)
            .selectinload(HardwareProduct.brand_record)
            .selectinload(Brand.categories),
            selectinload(Order.items)
            .selectinload(OrderItem.inventory_unit)
            .selectinload(InventoryUnit.product)
            .selectinload(HardwareProduct.chip_vendor_brand)
            .selectinload(Brand.categories),
            selectinload(Order.fulfillment_events),
        )
        .where(Order.save_game_id == save_game_id, Order.id == order_id)
        .execution_options(populate_existing=True)
    )
    if not order:
        raise not_found("Order not found")
    order.fulfillment_events.sort(key=lambda event: event.created_at)
    compatibility_service.evaluate_order_compatibility(db, order)
    return order


def list_fulfillment_events(db: Session, save_game_id: int, order_id: int) -> list[OrderFulfillmentEvent]:
    order = get_order(db, save_game_id, order_id)
    return order.fulfillment_events
