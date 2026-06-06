from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import bad_request
from app.models.entities import InventoryUnit, Order, OrderFulfillmentEvent, OrderItem
from app.models.enums import ConditionType, CustomerRequestStatus, Grade, InventoryStatus, OrderFulfillmentEventType, OrderStatus
from app.services import compatibility_service
from app.services.order_service import get_order
from app.services.save_game_service import get_save_game


def start_order_build(db: Session, save_game_id: int, order_id: int) -> Order:
    order = get_order(db, save_game_id, order_id)
    if order.status != OrderStatus.ACCEPTED:
        raise bad_request("Only accepted orders can start build")
    if not order.items:
        raise bad_request("Order has no items to build")

    now = datetime.now(timezone.utc)
    order.status = OrderStatus.IN_PROGRESS
    order.started_at = order.started_at or now
    for item in order.items:
        if item.inventory_unit:
            item.inventory_unit.status = InventoryStatus.INSTALLED_IN_BUILD
    _add_event(
        db,
        order.id,
        OrderFulfillmentEventType.BUILD_STARTED,
        "Build started. Linked inventory units are staged on the bench.",
        {"item_count": len(order.items)},
    )
    db.commit()
    db.expire_all()
    return get_order(db, save_game_id, order_id)


def run_order_build_test(db: Session, save_game_id: int, order_id: int) -> Order:
    order = get_order(db, save_game_id, order_id)
    if order.status not in {OrderStatus.IN_PROGRESS, OrderStatus.TESTING}:
        raise bad_request("Build test can only run on in-progress or testing orders")
    if not order.items:
        raise bad_request("Order has no items to test")

    compatibility_result = getattr(order, "compatibility_result", None) or compatibility_service.evaluate_order_compatibility(db, order)
    quality = calculate_build_quality(order)
    quality = _clamp(round((quality + compatibility_result["build_quality_score_estimate"]) / 2))
    final_test = calculate_final_test_score(order, quality, compatibility_result)
    warranty_risk = calculate_order_warranty_risk(order, final_test, compatibility_result)
    now = datetime.now(timezone.utc)
    order.status = OrderStatus.TESTING
    order.testing_started_at = order.testing_started_at or now
    order.build_quality_score = quality
    order.final_test_score = final_test
    order.final_warranty_risk = warranty_risk
    summary = f"Build test completed with quality {quality}, final score {final_test}, warranty risk {warranty_risk}."
    _add_event(
        db,
        order.id,
        OrderFulfillmentEventType.BUILD_TESTED,
        summary,
        {
            "build_quality_score": quality,
            "final_test_score": final_test,
            "final_warranty_risk": warranty_risk,
            "compatibility_score": compatibility_result["compatibility_score"],
            "risk_notes": _risk_notes(order),
        },
    )
    db.commit()
    db.expire_all()
    return get_order(db, save_game_id, order_id)


def deliver_order(db: Session, save_game_id: int, order_id: int, force: bool = False) -> dict[str, Any]:
    save_game = get_save_game(db, save_game_id)
    order = get_order(db, save_game_id, order_id)
    if order.status == OrderStatus.DELIVERED:
        raise bad_request("Order has already been delivered")
    if order.status != OrderStatus.TESTING:
        raise bad_request("Order must be tested before delivery")
    if (order.final_test_score is None or order.final_warranty_risk is None) and not force:
        raise bad_request("Order needs a build test before delivery")
    if not force and (order.final_warranty_risk == "CRITICAL" or (order.final_test_score or 0) < 45):
        raise bad_request("Delivery blocked by critical build test result. Retry after fixing the build or force delivery.")

    now = datetime.now(timezone.utc)
    order.status = OrderStatus.DELIVERED
    order.delivered_at = now
    order.warranty_eligible = True
    order.warranty_expires_at = now + timedelta(days=30)
    order.warranty_status = "ELIGIBLE"
    order.profit_vnd = order.quoted_price_vnd - order.cost_vnd
    final_test_label = order.final_test_score if order.final_test_score is not None else "unknown"
    order.delivery_summary = (
        f"Delivered for {order.quoted_price_vnd:,} VND. "
        f"Final test {final_test_label}; warranty risk {order.final_warranty_risk or 'UNKNOWN'}."
    )
    for item in order.items:
        if item.inventory_unit:
            item.inventory_unit.status = InventoryStatus.SOLD
    if order.request:
        order.request.status = CustomerRequestStatus.COMPLETED
    save_game.cash += order.quoted_price_vnd
    _add_event(
        db,
        order.id,
        OrderFulfillmentEventType.DELIVERED,
        order.delivery_summary,
        {
            "cash_delta": order.quoted_price_vnd,
            "force": force,
        },
    )
    db.flush()
    from app.services import review_service

    review = review_service.generate_review_from_order(db, save_game_id, order.id)
    return {
        "order": get_order(db, save_game_id, order_id),
        "cash_delta": order.quoted_price_vnd,
        "reputation_delta": review.reputation_delta,
    }


def cancel_order(db: Session, save_game_id: int, order_id: int) -> Order:
    order = get_order(db, save_game_id, order_id)
    if order.status == OrderStatus.DELIVERED:
        raise bad_request("Delivered orders cannot be cancelled")
    order.status = OrderStatus.CANCELLED
    for item in order.items:
        if item.inventory_unit and item.inventory_unit.status == InventoryStatus.INSTALLED_IN_BUILD:
            item.inventory_unit.status = InventoryStatus.READY_FOR_SALE
    _add_event(db, order.id, OrderFulfillmentEventType.CANCELLED, "Order cancelled and staged inventory released.", None)
    db.commit()
    return get_order(db, save_game_id, order_id)


def calculate_build_quality(order: Order) -> int:
    scores = [_item_quality_score(item) for item in order.items]
    if not scores:
        return 0
    fit_bonus = min(8, (order.customer_fit_score or 50) // 12)
    return _clamp(int(mean(scores)) + fit_bonus)


def calculate_final_test_score(
    order: Order,
    build_quality: int | None = None,
    compatibility_result: dict[str, Any] | None = None,
) -> int:
    quality = build_quality if build_quality is not None else calculate_build_quality(order)
    heat_penalty = int(mean([item.product.base_heat_score for item in order.items])) // 8 if order.items else 0
    unknown_penalty = sum(6 for item in order.items if item.inventory_unit and item.inventory_unit.inspection_confidence < 35)
    defective_penalty = sum(35 for item in order.items if item.inventory_unit and item.inventory_unit.condition_type in {ConditionType.DEFECTIVE, ConditionType.FOR_PARTS})
    compatibility_penalty = 0
    if compatibility_result:
        compatibility_penalty += max(0, 70 - int(compatibility_result.get("compatibility_score", 70))) // 4
        compatibility_penalty += max(0, 70 - int(compatibility_result.get("power_headroom_score", 70))) // 6
        compatibility_penalty += max(0, 70 - int(compatibility_result.get("thermal_score", 70))) // 6
        compatibility_penalty += max(0, 70 - int(compatibility_result.get("bottleneck_score", 70))) // 8
    return _clamp(quality - heat_penalty - unknown_penalty - defective_penalty - compatibility_penalty)


def calculate_order_warranty_risk(
    order: Order,
    final_test_score: int | None = None,
    compatibility_result: dict[str, Any] | None = None,
) -> str:
    score = final_test_score if final_test_score is not None else calculate_final_test_score(order)
    risk_points = 0
    for item in order.items:
        unit = item.inventory_unit
        if not unit:
            risk_points += 2
            continue
        if unit.condition_type == ConditionType.USED:
            risk_points += 2
        if unit.condition_type in {ConditionType.DEFECTIVE, ConditionType.FOR_PARTS}:
            risk_points += 6
        if unit.grade in {Grade.D, Grade.F, Grade.UNKNOWN}:
            risk_points += 2
        if unit.inspection_confidence < 35:
            risk_points += 3
        if unit.health_score is not None and unit.health_score < 55:
            risk_points += 2
        if unit.stability_score is not None and unit.stability_score < 55:
            risk_points += 2
    if compatibility_result:
        risk_points += max(0, int(compatibility_result.get("warranty_risk_delta", 0)))
        if int(compatibility_result.get("compatibility_score", 100)) < 60:
            risk_points += 2
        if int(compatibility_result.get("thermal_score", 100)) < 60:
            risk_points += 2
        if int(compatibility_result.get("power_headroom_score", 100)) < 60:
            risk_points += 2
    if score < 35 or risk_points >= 10:
        return "CRITICAL"
    if score < 55 or risk_points >= 6:
        return "HIGH"
    if score < 75 or risk_points >= 3:
        return "MEDIUM"
    return "LOW"


def calculate_reputation_delta(order: Order) -> int:
    final_score = order.final_test_score or 50
    quality = order.build_quality_score or 50
    fit = order.customer_fit_score or 50
    risk = order.final_warranty_risk or "MEDIUM"
    delta = 0
    if final_score >= 85 and quality >= 80:
        delta += 5
    elif final_score >= 70:
        delta += 2
    elif final_score < 50:
        delta -= 4
    if fit >= 80:
        delta += 2
    if risk == "HIGH":
        delta -= 2
    elif risk == "CRITICAL":
        delta -= 6
    return max(-10, min(10, delta))


def _item_quality_score(item: OrderItem) -> int:
    product = item.product
    unit = item.inventory_unit
    score = product.base_reliability_score
    score -= max(0, product.base_heat_score - 55) // 3
    if not unit:
        return _clamp(score - 12)
    score += {
        ConditionType.NEW: 10,
        ConditionType.OPEN_BOX: 4,
        ConditionType.USED: -12,
        ConditionType.REFURBISHED: 2,
        ConditionType.DEFECTIVE: -55,
        ConditionType.FOR_PARTS: -70,
    }[unit.condition_type]
    score += {
        Grade.A_PLUS: 10,
        Grade.A: 8,
        Grade.B: 2,
        Grade.C: -4,
        Grade.D: -14,
        Grade.F: -35,
        Grade.UNKNOWN: -12,
    }[unit.grade]
    score += min(10, unit.inspection_confidence // 10)
    if unit.health_score is not None:
        score = (score + unit.health_score) // 2
    if unit.thermal_score is not None:
        score += (unit.thermal_score - 60) // 8
    if unit.stability_score is not None:
        score += (unit.stability_score - 60) // 6
    return _clamp(score)


def _risk_notes(order: Order) -> list[str]:
    notes = []
    compatibility_result = getattr(order, "compatibility_result", None)
    if compatibility_result:
        for warning in compatibility_result.get("blocking_issues", []):
            notes.append(warning["message"])
    for item in order.items:
        unit = item.inventory_unit
        if not unit:
            notes.append(f"{item.product.name}: catalog placeholder has unknown fulfillment risk")
        elif unit.condition_type == ConditionType.USED and unit.inspection_confidence < 35:
            notes.append(f"{item.product.name}: untested used unit")
        elif unit.condition_type in {ConditionType.DEFECTIVE, ConditionType.FOR_PARTS}:
            notes.append(f"{item.product.name}: defective/for-parts unit")
    return notes


def _add_event(
    db: Session,
    order_id: int,
    event_type: OrderFulfillmentEventType,
    summary: str,
    raw_result_json: dict[str, Any] | None,
) -> None:
    db.add(
        OrderFulfillmentEvent(
            order_id=order_id,
            event_type=event_type,
            summary=summary,
            raw_result_json=raw_result_json,
        )
    )


def _clamp(value: int, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, value))
