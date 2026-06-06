from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import bad_request, not_found
from app.models.entities import (
    Brand,
    HardwareProduct,
    InventoryUnit,
    Order,
    OrderItem,
    ResaleListing,
    WarrantyClaim,
    WarrantyClaimItem,
    WarrantyEvent,
)
from app.models.enums import (
    ConditionType,
    Grade,
    InventoryStatus,
    OrderStatus,
    ResaleListingStatus,
    WarrantyClaimReason,
    WarrantyClaimStatus,
    WarrantyClaimType,
    WarrantyResolutionType,
    WarrantyEventType,
)
from app.schemas.game import (
    WarrantyClaimCreate,
    WarrantyClaimGenerateRequest,
    WarrantyClaimResolveRequest,
    WarrantyClaimReviewRequest,
    WarrantyDiagnosisRequest,
    WarrantyRejectRequest,
    WarrantyResolutionRequest,
)
from app.services import progression_service
from app.services.save_game_service import get_save_game


CLOSED_STATUSES = {
    WarrantyClaimStatus.CLOSED,
    WarrantyClaimStatus.REJECTED,
    WarrantyClaimStatus.RESOLVED,
    WarrantyClaimStatus.CANCELLED,
    WarrantyClaimStatus.REPLACED,
    WarrantyClaimStatus.REFUNDED,
    WarrantyClaimStatus.RMA_COMPLETED,
}


def list_warranty_claims(db: Session, save_game_id: int, status: WarrantyClaimStatus | None = None) -> list[WarrantyClaim]:
    get_save_game(db, save_game_id)
    query = _claim_query().where(WarrantyClaim.save_game_id == save_game_id)
    if status is not None:
        query = query.where(WarrantyClaim.status == status)
    return list(
        db.scalars(
            query.order_by(WarrantyClaim.updated_at.desc())
        )
    )


def get_warranty_claim(db: Session, save_game_id: int, claim_id: int) -> WarrantyClaim:
    claim = db.scalar(_claim_query().where(WarrantyClaim.save_game_id == save_game_id, WarrantyClaim.id == claim_id))
    if not claim:
        raise not_found("Warranty claim not found")
    claim.events.sort(key=lambda event: event.created_at)
    return claim


def create_warranty_claim(db: Session, save_game_id: int, order_id: int, payload: WarrantyClaimCreate) -> WarrantyClaim:
    return create_warranty_claim_from_order(db, save_game_id, order_id, payload)


def start_diagnosis(db: Session, save_game_id: int, claim_id: int) -> WarrantyClaim:
    claim = _mutable_claim(db, save_game_id, claim_id)
    if claim.status != WarrantyClaimStatus.OPEN:
        raise bad_request("Only open warranty claims can start diagnosis")
    claim.status = WarrantyClaimStatus.DIAGNOSING
    _touch_order_warranty(claim, "DIAGNOSING")
    _add_event(db, claim, WarrantyEventType.DIAGNOSIS_STARTED, "Diagnosis started on returned issue report.", None)
    db.commit()
    return get_warranty_claim(db, save_game_id, claim_id)


def complete_diagnosis(
    db: Session,
    save_game_id: int,
    claim_id: int,
    payload: WarrantyDiagnosisRequest | None = None,
) -> WarrantyClaim:
    claim = _mutable_claim(db, save_game_id, claim_id)
    if claim.status != WarrantyClaimStatus.DIAGNOSING:
        raise bad_request("Claim must be diagnosing before diagnosis can complete")
    diagnosis = _diagnose_claim(db, claim)
    claim.status = WarrantyClaimStatus.AWAITING_DECISION
    claim.diagnostic_summary = diagnosis["summary"]
    claim.diagnosed_at = datetime.now(timezone.utc)
    claim.warranty_valid = bool(diagnosis["warranty_valid"])
    if payload and payload.notes:
        claim.internal_notes = _append_note(claim.internal_notes, payload.notes)
    for item in claim.items:
        item.diagnosis_result = diagnosis["item_result"]
    _touch_order_warranty(claim, "AWAITING_DECISION")
    _add_event(db, claim, WarrantyEventType.DIAGNOSIS_COMPLETED, claim.diagnostic_summary, diagnosis)
    db.commit()
    return get_warranty_claim(db, save_game_id, claim_id)


def approve_claim(db: Session, save_game_id: int, claim_id: int) -> WarrantyClaim:
    claim = _mutable_claim(db, save_game_id, claim_id)
    if claim.status != WarrantyClaimStatus.AWAITING_DECISION:
        raise bad_request("Claim must await decision before approval")
    claim.status = WarrantyClaimStatus.APPROVED
    _touch_order_warranty(claim, "APPROVED")
    _add_event(db, claim, WarrantyEventType.APPROVED, "Warranty claim approved for service resolution.", None)
    db.commit()
    return get_warranty_claim(db, save_game_id, claim_id)


def reject_claim(
    db: Session,
    save_game_id: int,
    claim_id: int,
    payload: WarrantyRejectRequest | None = None,
) -> WarrantyClaim:
    claim = _mutable_claim(db, save_game_id, claim_id)
    if claim.status not in {WarrantyClaimStatus.OPEN, WarrantyClaimStatus.DIAGNOSING, WarrantyClaimStatus.AWAITING_DECISION}:
        raise bad_request("Claim cannot be rejected from its current status")
    reason = payload.reason if payload and payload.reason else "Claim rejected after review."
    delta = 0 if not claim.warranty_valid else -4
    claim.status = WarrantyClaimStatus.REJECTED
    claim.resolution_type = WarrantyResolutionType.REJECT
    claim.resolution_summary = reason
    claim.final_cost_vnd = 0
    claim.resolved_on_day = claim.order.save_game.game_day if claim.order else None
    claim.resolved_at = datetime.now(timezone.utc)
    claim.reputation_delta = delta
    _apply_reputation(claim, delta)
    _touch_order_warranty(claim, "REJECTED")
    _add_event(db, claim, WarrantyEventType.REJECTED, reason, {"reputation_delta": delta})
    db.commit()
    return get_warranty_claim(db, save_game_id, claim_id)


def resolve_claim_repair(
    db: Session,
    save_game_id: int,
    claim_id: int,
    payload: WarrantyResolutionRequest | None = None,
) -> WarrantyClaim:
    claim = _approved_claim(db, save_game_id, claim_id)
    cost = _repair_cost(claim)
    if claim.order.save_game.cash < cost:
        raise bad_request("Insufficient cash to perform this repair")
    claim.status = WarrantyClaimStatus.IN_REPAIR
    claim.repair_cost_vnd = cost
    claim.final_cost_vnd = cost
    claim.resolution_type = WarrantyResolutionType.REPAIR
    _add_event(db, claim, WarrantyEventType.REPAIR_STARTED, "Repair started for approved warranty claim.", {"repair_cost_vnd": cost})
    claim.status = WarrantyClaimStatus.CLOSED
    claim.resolved_at = datetime.now(timezone.utc)
    claim.resolved_on_day = claim.order.save_game.game_day
    claim.resolution_summary = payload.notes if payload and payload.notes else f"Repaired affected components for {cost:,} VND."
    claim.reputation_delta = 2 if claim.warranty_valid else 0
    for item in claim.items:
        item.action_taken = "REPAIRED"
    _apply_cash(claim, -cost)
    _apply_reputation(claim, claim.reputation_delta)
    _touch_order_warranty(claim, "REPAIRED")
    _add_event(db, claim, WarrantyEventType.REPAIR_COMPLETED, claim.resolution_summary, {"cash_delta": -cost})
    _add_event(db, claim, WarrantyEventType.CLAIM_CLOSED, "Warranty claim closed after repair.", None)
    db.commit()
    return get_warranty_claim(db, save_game_id, claim_id)


def resolve_claim_replace(
    db: Session,
    save_game_id: int,
    claim_id: int,
    payload: WarrantyResolutionRequest | None = None,
) -> WarrantyClaim:
    claim = _approved_claim(db, save_game_id, claim_id)
    replacement = _find_replacement_unit(db, claim)
    replacement_cost = replacement.purchase_price_vnd if replacement else _fallback_replacement_cost(claim)
    if claim.order.save_game.cash < replacement_cost:
        raise bad_request("Insufficient cash to perform this replacement")
    claim.status = WarrantyClaimStatus.REPLACED
    claim.replacement_cost_vnd = replacement_cost
    claim.final_cost_vnd = replacement_cost
    claim.resolution_type = WarrantyResolutionType.REPLACE
    claim.resolved_at = datetime.now(timezone.utc)
    claim.resolved_on_day = claim.order.save_game.game_day
    claim.resolution_summary = payload.notes if payload and payload.notes else "Replacement issued for approved warranty claim."
    claim.reputation_delta = 3 if claim.warranty_valid else 1
    if replacement:
        replacement.status = InventoryStatus.SOLD
        claim.items[0].replacement_inventory_unit_id = replacement.id
    for item in claim.items:
        item.action_taken = "REPLACED"
    _apply_cash(claim, -replacement_cost)
    _apply_reputation(claim, claim.reputation_delta)
    _touch_order_warranty(claim, "REPLACED")
    _add_event(
        db,
        claim,
        WarrantyEventType.REPLACEMENT_ISSUED,
        claim.resolution_summary,
        {"replacement_inventory_unit_id": replacement.id if replacement else None, "cash_delta": -replacement_cost},
    )
    _add_event(db, claim, WarrantyEventType.CLAIM_CLOSED, "Warranty claim closed after replacement.", None)
    db.commit()
    return get_warranty_claim(db, save_game_id, claim_id)


def resolve_claim_refund(
    db: Session,
    save_game_id: int,
    claim_id: int,
    payload: WarrantyResolutionRequest | None = None,
) -> WarrantyClaim:
    claim = _approved_claim(db, save_game_id, claim_id)
    refund = claim.order.quoted_price_vnd if claim.warranty_valid else claim.order.quoted_price_vnd // 4
    if claim.order.save_game.cash < refund:
        raise bad_request("Insufficient cash to issue this refund")
    claim.status = WarrantyClaimStatus.REFUNDED
    claim.reimbursement_vnd = refund
    claim.final_cost_vnd = refund
    claim.resolution_type = WarrantyResolutionType.REFUND
    claim.resolved_at = datetime.now(timezone.utc)
    claim.resolved_on_day = claim.order.save_game.game_day
    claim.resolution_summary = payload.notes if payload and payload.notes else f"Refund issued for {refund:,} VND."
    claim.reputation_delta = 4 if claim.warranty_valid else 1
    for item in claim.items:
        item.action_taken = "REFUNDED"
    _apply_cash(claim, -refund)
    _apply_reputation(claim, claim.reputation_delta)
    _touch_order_warranty(claim, "REFUNDED")
    _add_event(db, claim, WarrantyEventType.REFUND_ISSUED, claim.resolution_summary, {"cash_delta": -refund})
    _add_event(db, claim, WarrantyEventType.CLAIM_CLOSED, "Warranty claim closed after refund.", None)
    db.commit()
    return get_warranty_claim(db, save_game_id, claim_id)


def resolve_claim_rma(
    db: Session,
    save_game_id: int,
    claim_id: int,
    payload: WarrantyResolutionRequest | None = None,
) -> WarrantyClaim:
    claim = _approved_claim(db, save_game_id, claim_id)
    shipping = max(120_000, min(650_000, claim.order.quoted_price_vnd // 80))
    if claim.order.save_game.cash < shipping:
        raise bad_request("Insufficient cash to submit manufacturer RMA")
    claim.status = WarrantyClaimStatus.RMA_SUBMITTED
    claim.rma_shipping_cost_vnd = shipping
    claim.resolution_summary = payload.notes if payload and payload.notes else "Manufacturer RMA submitted; awaiting completion."
    claim.final_cost_vnd = shipping
    for item in claim.items:
        item.action_taken = "RMA_SUBMITTED"
    _apply_cash(claim, -shipping)
    _touch_order_warranty(claim, "RMA_SUBMITTED")
    _add_event(db, claim, WarrantyEventType.RMA_SUBMITTED, claim.resolution_summary, {"cash_delta": -shipping})
    db.commit()
    return get_warranty_claim(db, save_game_id, claim_id)


def close_claim(db: Session, save_game_id: int, claim_id: int) -> WarrantyClaim:
    claim = _mutable_claim(db, save_game_id, claim_id, allow_rma=True)
    if claim.status == WarrantyClaimStatus.RMA_SUBMITTED:
        claim.status = WarrantyClaimStatus.RMA_COMPLETED
        claim.resolution_summary = "Manufacturer RMA completed and customer notified."
        claim.reputation_delta = 2
        _apply_reputation(claim, claim.reputation_delta)
        _add_event(db, claim, WarrantyEventType.RMA_COMPLETED, claim.resolution_summary, {"reputation_delta": claim.reputation_delta})
    elif claim.status not in {WarrantyClaimStatus.REJECTED, WarrantyClaimStatus.REPLACED, WarrantyClaimStatus.REFUNDED, WarrantyClaimStatus.RESOLVED}:
        raise bad_request("Only rejected, resolved, or RMA-submitted claims can be closed")
    claim.status = WarrantyClaimStatus.CLOSED
    claim.resolved_at = claim.resolved_at or datetime.now(timezone.utc)
    _touch_order_warranty(claim, "CLOSED")
    _add_event(db, claim, WarrantyEventType.CLAIM_CLOSED, "Warranty claim closed.", None)
    db.commit()
    return get_warranty_claim(db, save_game_id, claim_id)


def list_events(db: Session, save_game_id: int, claim_id: int) -> list[WarrantyEvent]:
    claim = get_warranty_claim(db, save_game_id, claim_id)
    return claim.events


def _claim_query():
    return select(WarrantyClaim).options(
        selectinload(WarrantyClaim.customer),
        selectinload(WarrantyClaim.order),
        selectinload(WarrantyClaim.order).selectinload(Order.customer),
        selectinload(WarrantyClaim.order).selectinload(Order.items).selectinload(OrderItem.product).selectinload(HardwareProduct.brand_record).selectinload(Brand.categories),
        selectinload(WarrantyClaim.order)
        .selectinload(Order.items)
        .selectinload(OrderItem.product)
        .selectinload(HardwareProduct.chip_vendor_brand)
        .selectinload(Brand.categories),
        selectinload(WarrantyClaim.order)
        .selectinload(Order.items)
        .selectinload(OrderItem.inventory_unit)
        .selectinload(InventoryUnit.product)
        .selectinload(HardwareProduct.brand_record)
        .selectinload(Brand.categories),
        selectinload(WarrantyClaim.order)
        .selectinload(Order.items)
        .selectinload(OrderItem.inventory_unit)
        .selectinload(InventoryUnit.product)
        .selectinload(HardwareProduct.chip_vendor_brand)
        .selectinload(Brand.categories),
        selectinload(WarrantyClaim.resale_listing).selectinload(ResaleListing.inventory_unit).selectinload(InventoryUnit.product).selectinload(HardwareProduct.brand_record).selectinload(Brand.categories),
        selectinload(WarrantyClaim.resale_listing).selectinload(ResaleListing.inventory_unit).selectinload(InventoryUnit.product).selectinload(HardwareProduct.chip_vendor_brand).selectinload(Brand.categories),
        selectinload(WarrantyClaim.inventory_unit).selectinload(InventoryUnit.product).selectinload(HardwareProduct.brand_record).selectinload(Brand.categories),
        selectinload(WarrantyClaim.inventory_unit).selectinload(InventoryUnit.product).selectinload(HardwareProduct.chip_vendor_brand).selectinload(Brand.categories),
        selectinload(WarrantyClaim.items).selectinload(WarrantyClaimItem.product).selectinload(HardwareProduct.brand_record).selectinload(Brand.categories),
        selectinload(WarrantyClaim.items).selectinload(WarrantyClaimItem.product).selectinload(HardwareProduct.chip_vendor_brand).selectinload(Brand.categories),
        selectinload(WarrantyClaim.items)
        .selectinload(WarrantyClaimItem.inventory_unit)
        .selectinload(InventoryUnit.product)
        .selectinload(HardwareProduct.brand_record)
        .selectinload(Brand.categories),
        selectinload(WarrantyClaim.items)
        .selectinload(WarrantyClaimItem.inventory_unit)
        .selectinload(InventoryUnit.product)
        .selectinload(HardwareProduct.chip_vendor_brand)
        .selectinload(Brand.categories),
        selectinload(WarrantyClaim.items)
        .selectinload(WarrantyClaimItem.replacement_inventory_unit)
        .selectinload(InventoryUnit.product)
        .selectinload(HardwareProduct.brand_record)
        .selectinload(Brand.categories),
        selectinload(WarrantyClaim.items)
        .selectinload(WarrantyClaimItem.replacement_inventory_unit)
        .selectinload(InventoryUnit.product)
        .selectinload(HardwareProduct.chip_vendor_brand)
        .selectinload(Brand.categories),
        selectinload(WarrantyClaim.events),
    ).execution_options(populate_existing=True)


def _get_order_for_warranty(db: Session, save_game_id: int, order_id: int) -> Order:
    order = db.scalar(
        select(Order)
        .options(
            selectinload(Order.customer),
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
        .where(Order.save_game_id == save_game_id, Order.id == order_id)
    )
    if not order:
        raise not_found("Order not found")
    return order


def _mutable_claim(db: Session, save_game_id: int, claim_id: int, allow_rma: bool = False) -> WarrantyClaim:
    claim = get_warranty_claim(db, save_game_id, claim_id)
    if claim.status == WarrantyClaimStatus.CLOSED or (claim.status in CLOSED_STATUSES and not allow_rma):
        raise bad_request("Warranty claim is already closed or resolved")
    return claim


def _approved_claim(db: Session, save_game_id: int, claim_id: int) -> WarrantyClaim:
    claim = _mutable_claim(db, save_game_id, claim_id)
    if claim.status != WarrantyClaimStatus.APPROVED:
        raise bad_request("Claim must be approved before resolution")
    return claim


def _diagnose_claim(db: Session, claim: WarrantyClaim) -> dict[str, Any]:
    risk_points = 0
    order = claim.order
    if order.final_warranty_risk == "CRITICAL":
        risk_points += 6
    elif order.final_warranty_risk == "HIGH":
        risk_points += 4
    elif order.final_warranty_risk == "MEDIUM":
        risk_points += 2
    if order.final_test_score is not None and order.final_test_score < 65:
        risk_points += 2
    if order.build_quality_score is not None and order.build_quality_score < 65:
        risk_points += 2
    for item in order.items:
        unit = item.inventory_unit
        if not unit:
            risk_points += 1
            continue
        if unit.condition_type == ConditionType.USED:
            risk_points += 2
        if unit.condition_type in {ConditionType.DEFECTIVE, ConditionType.FOR_PARTS}:
            risk_points += 6
        if unit.grade in {Grade.D, Grade.F, Grade.UNKNOWN}:
            risk_points += 2
        if unit.inspection_confidence < 45:
            risk_points += 2
    risk_reduction = int(progression_service.get_effect_value(db, claim.save_game_id, "warranty_risk_reduction_percent", 0) or 0)
    risk_points = max(0, risk_points - risk_reduction // 2)
    if not claim.warranty_valid:
        summary = "Warranty period appears expired. Fault can be reviewed, but claim is likely invalid."
        item_result = "Warranty expired; manual review recommended."
        recommended_resolution = "REJECT"
    elif risk_points >= 8:
        summary = _summary_for_reason(claim.claim_reason, severe=True)
        item_result = "Likely valid fault tied to sold build or component risk."
        recommended_resolution = "REPLACE_OR_REFUND"
    elif risk_points >= 4:
        summary = _summary_for_reason(claim.claim_reason, severe=False)
        item_result = "Likely serviceable fault; repair or manufacturer RMA recommended."
        recommended_resolution = "REPAIR_OR_RMA"
    else:
        summary = "No reproducible fault found in simplified diagnosis. Monitor customer report before major payout."
        item_result = "No reproducible fault found."
        recommended_resolution = "REJECT_OR_MONITOR"
    return {
        "summary": summary,
        "severity_score": min(100, risk_points * 10),
        "recommended_resolution": recommended_resolution,
        "warranty_valid": claim.warranty_valid,
        "item_result": item_result,
    }


def _summary_for_reason(reason: WarrantyClaimReason, severe: bool) -> str:
    if reason == WarrantyClaimReason.NOISY_FAN:
        return "Likely fan wear causing noise and thermal spikes." if severe else "Fan noise reproduced under load; repair recommended."
    if reason == WarrantyClaimReason.ARTIFACTING:
        return "Possible GPU instability under sustained load."
    if reason == WarrantyClaimReason.OVERHEATING:
        return "Thermal issue reproduced; cooling or paste service recommended."
    if reason in {WarrantyClaimReason.CRASHING, WarrantyClaimReason.RANDOM_SHUTDOWN, WarrantyClaimReason.DOA}:
        return "System instability reproduced during warranty diagnosis."
    return "Issue likely caused by low-grade or stressed component in the delivered build." if severe else "Customer issue partially reproduced; service decision required."


def _suspected_issue(reason: WarrantyClaimReason, item: OrderItem) -> str:
    if reason in {WarrantyClaimReason.ARTIFACTING, WarrantyClaimReason.CRASHING} and item.product.category.value == "GPU":
        return "GPU instability suspected."
    if reason == WarrantyClaimReason.OVERHEATING and item.product.category.value in {"CPU", "GPU", "COOLER"}:
        return "Thermal path suspected."
    if reason == WarrantyClaimReason.NOISY_FAN and item.product.category.value in {"GPU", "PSU", "COOLER", "CASE"}:
        return "Fan noise suspected."
    return "Included for warranty review."


def _repair_cost(claim: WarrantyClaim) -> int:
    base = max(150_000, claim.order.quoted_price_vnd // 35)
    risk_multiplier = 2 if claim.order.final_warranty_risk in {"HIGH", "CRITICAL"} else 1
    return min(2_500_000, base * risk_multiplier)


def _fallback_replacement_cost(claim: WarrantyClaim) -> int:
    costs = [item.order_item.cost_vnd for item in claim.items if item.order_item]
    return max(costs) if costs else claim.order.cost_vnd // 3


def _find_replacement_unit(db: Session, claim: WarrantyClaim) -> InventoryUnit | None:
    product_ids = [item.product_id for item in claim.items if item.product_id]
    if not product_ids:
        return None
    exact = db.scalar(
        select(InventoryUnit)
        .where(
            InventoryUnit.save_game_id == claim.save_game_id,
            InventoryUnit.product_id.in_(product_ids),
            InventoryUnit.status == InventoryStatus.READY_FOR_SALE,
        )
        .order_by(InventoryUnit.grade, InventoryUnit.inspection_confidence.desc())
        .limit(1)
    )
    if exact:
        return exact
    categories = [item.product.category for item in claim.items if item.product]
    if not categories:
        return None
    return db.scalar(
        select(InventoryUnit)
        .join(InventoryUnit.product)
        .where(
            InventoryUnit.save_game_id == claim.save_game_id,
            HardwareProduct.category.in_(categories),
            InventoryUnit.status == InventoryStatus.READY_FOR_SALE,
        )
        .order_by(InventoryUnit.inspection_confidence.desc())
        .limit(1)
    )


def _apply_cash(claim: WarrantyClaim, delta: int) -> None:
    claim.order.save_game.cash += delta


def _apply_reputation(claim: WarrantyClaim, delta: int) -> None:
    claim.order.save_game.reputation = max(0, min(100, claim.order.save_game.reputation + delta))


def _touch_order_warranty(claim: WarrantyClaim, status: str) -> None:
    now = datetime.now(timezone.utc)
    claim.order.warranty_status = status
    claim.order.last_warranty_event_at = now


def _add_event(
    db: Session,
    claim: WarrantyClaim,
    event_type: WarrantyEventType,
    summary: str,
    raw_result_json: dict[str, Any] | None,
) -> None:
    db.add(WarrantyEvent(warranty_claim=claim, event_type=event_type, summary=summary, raw_result_json=raw_result_json))


def _append_note(current: str | None, note: str) -> str:
    return f"{current}\n{note}" if current else note


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def estimate_claim_risk_for_order(db: Session, order: Order) -> int:
    risk = 8
    if order.final_warranty_risk == "CRITICAL":
        risk += 32
    elif order.final_warranty_risk == "HIGH":
        risk += 22
    elif order.final_warranty_risk == "MEDIUM":
        risk += 12
    elif order.final_warranty_risk == "LOW":
        risk += 4

    if order.final_test_score is not None:
        risk += max(0, 28 - order.final_test_score // 2)
    if order.build_quality_score is not None:
        risk += max(0, 24 - order.build_quality_score // 2)
    if order.warranty_eligible:
        risk -= 3
    if order.warranty_expires_at and _as_utc(order.warranty_expires_at) < datetime.now(timezone.utc):
        risk += 15

    for item in order.items:
        unit = item.inventory_unit
        if not unit:
            risk += 4
            continue
        risk += estimate_claim_risk_for_inventory_unit(db, unit) // 3
        if unit.condition_type == ConditionType.NEW:
            risk -= 2
        elif unit.condition_type == ConditionType.OPEN_BOX:
            risk += 1
        elif unit.condition_type == ConditionType.USED:
            risk += 6
        elif unit.condition_type == ConditionType.REFURBISHED:
            risk += 4
        elif unit.condition_type in {ConditionType.DEFECTIVE, ConditionType.FOR_PARTS}:
            risk += 16
        if unit.source.value in {"USED_MARKET", "TRADE_IN"}:
            risk += 4

    risk_reduction = int(progression_service.get_effect_value(db, order.save_game_id, "warranty_risk_reduction_percent", 0) or 0)
    return max(0, min(100, risk - risk_reduction))


def estimate_claim_risk_for_inventory_unit(db: Session, inventory_unit: InventoryUnit) -> int:
    risk = 10
    if inventory_unit.condition_type == ConditionType.NEW:
        risk -= 6
    elif inventory_unit.condition_type == ConditionType.OPEN_BOX:
        risk += 2
    elif inventory_unit.condition_type == ConditionType.USED:
        risk += 12
    elif inventory_unit.condition_type == ConditionType.REFURBISHED:
        risk += 8
    elif inventory_unit.condition_type in {ConditionType.DEFECTIVE, ConditionType.FOR_PARTS}:
        risk += 25

    if inventory_unit.status == InventoryStatus.SOLD:
        risk += 6
    if inventory_unit.grade in {Grade.D, Grade.F, Grade.UNKNOWN}:
        risk += 16
    elif inventory_unit.grade == Grade.C:
        risk += 8
    elif inventory_unit.grade == Grade.B:
        risk += 3
    elif inventory_unit.grade in {Grade.A, Grade.A_PLUS}:
        risk -= 2

    risk += max(0, 50 - inventory_unit.inspection_confidence) // 2
    if inventory_unit.ready_for_resale:
        risk -= 5
    if inventory_unit.refurbish_count:
        risk -= min(8, inventory_unit.refurbish_count * 2)
    if inventory_unit.repair_risk_score is not None:
        risk += max(0, inventory_unit.repair_risk_score // 6)
    if inventory_unit.resale_value_estimate_vnd:
        risk += 2 if inventory_unit.resale_value_estimate_vnd < inventory_unit.purchase_price_vnd else 0

    hidden = inventory_unit.hidden_condition_json or {}
    risk += _hidden_condition_risk(hidden)
    risk_reduction = int(progression_service.get_effect_value(db, inventory_unit.save_game_id, "warranty_risk_reduction_percent", 0) or 0)
    return max(0, min(100, risk - risk_reduction))


def estimate_resolution_cost(claim: WarrantyClaim, resolution_type: WarrantyResolutionType) -> int:
    base_sale_value = 0
    if claim.order:
        base_sale_value = claim.order.quoted_price_vnd
    elif claim.resale_listing:
        base_sale_value = claim.resale_listing.final_sale_price_vnd or claim.resale_listing.asking_price_vnd
    elif claim.inventory_unit:
        base_sale_value = claim.inventory_unit.resale_value_estimate_vnd or claim.inventory_unit.purchase_price_vnd

    baseline = max(100_000, claim.estimated_cost_vnd or 0, base_sale_value // 5 if base_sale_value else 0)
    if resolution_type == WarrantyResolutionType.REPAIR:
        return min(2_500_000, max(120_000, baseline))
    if resolution_type == WarrantyResolutionType.REPLACE:
        return min(5_000_000, max(baseline * 2, base_sale_value // 2 if base_sale_value else baseline * 2))
    if resolution_type == WarrantyResolutionType.REFUND:
        return max(0, base_sale_value or baseline * 2)
    if resolution_type == WarrantyResolutionType.GOODWILL_CREDIT:
        return min(1_250_000, max(75_000, baseline // 2))
    return 0


def summarize_warranty_state(db: Session, save_game_id: int) -> dict[str, int]:
    save_game = get_save_game(db, save_game_id)
    open_claims = db.scalar(
        select(func.count())
        .select_from(WarrantyClaim)
        .where(WarrantyClaim.save_game_id == save_game_id, WarrantyClaim.status == WarrantyClaimStatus.OPEN)
    ) or 0
    in_review_claims = db.scalar(
        select(func.count())
        .select_from(WarrantyClaim)
        .where(WarrantyClaim.save_game_id == save_game_id, WarrantyClaim.status == WarrantyClaimStatus.IN_REVIEW)
    ) or 0
    approved_claims = db.scalar(
        select(func.count())
        .select_from(WarrantyClaim)
        .where(WarrantyClaim.save_game_id == save_game_id, WarrantyClaim.status == WarrantyClaimStatus.APPROVED)
    ) or 0
    resolved_claims = db.scalar(
        select(func.count())
        .select_from(WarrantyClaim)
        .where(WarrantyClaim.save_game_id == save_game_id, WarrantyClaim.status.in_([WarrantyClaimStatus.RESOLVED, WarrantyClaimStatus.CLOSED]))
    ) or 0
    rejected_claims = db.scalar(
        select(func.count())
        .select_from(WarrantyClaim)
        .where(WarrantyClaim.save_game_id == save_game_id, WarrantyClaim.status == WarrantyClaimStatus.REJECTED)
    ) or 0
    due_soon_claims = db.scalar(
        select(func.count())
        .select_from(WarrantyClaim)
        .where(
            WarrantyClaim.save_game_id == save_game_id,
            WarrantyClaim.status.not_in(list(CLOSED_STATUSES)),
            WarrantyClaim.due_on_day.is_not(None),
            WarrantyClaim.due_on_day <= save_game.game_day + 2,
        )
    ) or 0
    overdue_claims = db.scalar(
        select(func.count())
        .select_from(WarrantyClaim)
        .where(
            WarrantyClaim.save_game_id == save_game_id,
            WarrantyClaim.status.not_in(list(CLOSED_STATUSES)),
            WarrantyClaim.due_on_day.is_not(None),
            WarrantyClaim.due_on_day < save_game.game_day,
        )
    ) or 0
    estimated_exposure = db.scalar(
        select(func.coalesce(func.sum(WarrantyClaim.estimated_cost_vnd), 0))
        .where(
            WarrantyClaim.save_game_id == save_game_id,
            WarrantyClaim.status.not_in(list(CLOSED_STATUSES)),
        )
    ) or 0
    unresolved_risk_score = min(100, open_claims * 8 + in_review_claims * 10 + approved_claims * 12 + due_soon_claims * 15 + overdue_claims * 20)
    total_claims = db.scalar(
        select(func.count()).select_from(WarrantyClaim).where(WarrantyClaim.save_game_id == save_game_id)
    ) or 0
    return {
        "save_game_id": save_game_id,
        "total_claims": total_claims,
        "open_claims_count": open_claims,
        "in_review_claims_count": in_review_claims,
        "approved_claims_count": approved_claims,
        "resolved_claims_count": resolved_claims,
        "rejected_claims_count": rejected_claims,
        "due_soon_claims_count": due_soon_claims,
        "overdue_claims_count": overdue_claims,
        "estimated_exposure_vnd": estimated_exposure,
        "unresolved_risk_score": unresolved_risk_score,
    }


def generate_warranty_claim(
    db: Session,
    save_game_id: int,
    source_type: str | None = None,
    order_id: int | None = None,
    resale_listing_id: int | None = None,
    inventory_unit_id: int | None = None,
) -> WarrantyClaim:
    if order_id is not None:
        return create_warranty_claim_from_order(db, save_game_id, order_id)
    if resale_listing_id is not None:
        return create_warranty_claim_from_resale(db, save_game_id, resale_listing_id)
    if inventory_unit_id is not None:
        return create_warranty_claim_from_inventory_unit(db, save_game_id, inventory_unit_id)

    source = (source_type or "").lower().strip()
    if source == "order":
        order = db.scalar(
            select(Order)
            .where(Order.save_game_id == save_game_id, Order.status == OrderStatus.DELIVERED)
            .order_by(Order.delivered_at.desc().nullslast(), Order.updated_at.desc())
            .limit(1)
        )
        if order:
            return create_warranty_claim_from_order(db, save_game_id, order.id)
        raise bad_request("No delivered order is available for warranty generation")
    if source == "resale":
        listing = db.scalar(
            select(ResaleListing)
            .where(ResaleListing.save_game_id == save_game_id, ResaleListing.status == ResaleListingStatus.SOLD)
            .order_by(ResaleListing.sold_on_day.desc().nullslast(), ResaleListing.updated_at.desc())
            .limit(1)
        )
        if listing:
            return create_warranty_claim_from_resale(db, save_game_id, listing.id)
    elif source == "inventory":
        unit = db.scalar(
            select(InventoryUnit)
            .where(InventoryUnit.save_game_id == save_game_id)
            .order_by(InventoryUnit.updated_at.desc())
            .limit(1)
        )
        if unit:
            return create_warranty_claim_from_inventory_unit(db, save_game_id, unit.id)
    else:
        order = db.scalar(
            select(Order)
            .where(Order.save_game_id == save_game_id, Order.status == OrderStatus.DELIVERED)
            .order_by(Order.delivered_at.desc().nullslast(), Order.updated_at.desc())
            .limit(1)
        )
        if order:
            return create_warranty_claim_from_order(db, save_game_id, order.id)
        listing = db.scalar(
            select(ResaleListing)
            .where(ResaleListing.save_game_id == save_game_id, ResaleListing.status == ResaleListingStatus.SOLD)
            .order_by(ResaleListing.sold_on_day.desc().nullslast(), ResaleListing.updated_at.desc())
            .limit(1)
        )
        if listing:
            return create_warranty_claim_from_resale(db, save_game_id, listing.id)

    raise bad_request("No eligible warranty claim could be generated")


def generate_random_warranty_claim(db: Session, save_game_id: int) -> WarrantyClaim:
    order = db.scalar(
        select(Order)
        .where(Order.save_game_id == save_game_id, Order.status == OrderStatus.DELIVERED)
        .order_by(Order.delivered_at.desc().nullslast(), Order.updated_at.desc())
        .limit(1)
    )
    if order:
        risk = estimate_claim_risk_for_order(db, order)
        if risk >= 20:
            return create_warranty_claim_from_order(db, save_game_id, order.id)

    listing = db.scalar(
        select(ResaleListing)
        .where(ResaleListing.save_game_id == save_game_id, ResaleListing.status == ResaleListingStatus.SOLD)
        .order_by(ResaleListing.sold_on_day.desc().nullslast(), ResaleListing.updated_at.desc())
        .limit(1)
    )
    if listing:
        risk = estimate_claim_risk_for_inventory_unit(db, listing.inventory_unit) if listing.inventory_unit else 25
        if risk >= 20:
            return create_warranty_claim_from_resale(db, save_game_id, listing.id)

    unit = db.scalar(
        select(InventoryUnit)
        .where(InventoryUnit.save_game_id == save_game_id, InventoryUnit.status == InventoryStatus.SOLD)
        .order_by(InventoryUnit.updated_at.desc())
        .limit(1)
    )
    if unit:
        risk = estimate_claim_risk_for_inventory_unit(db, unit)
        if risk >= 20:
            return create_warranty_claim_from_inventory_unit(db, save_game_id, unit.id)

    raise bad_request("No eligible warranty claim could be generated from the current sales history")


def create_warranty_claim_from_order(
    db: Session,
    save_game_id: int,
    order_id: int,
    payload: WarrantyClaimCreate | None = None,
) -> WarrantyClaim:
    order = _get_order_for_warranty(db, save_game_id, order_id)
    if order.status != OrderStatus.DELIVERED:
        raise bad_request("Only delivered orders can receive warranty claims")

    save_game = get_save_game(db, save_game_id)
    now = datetime.now(timezone.utc)
    warranty_valid = bool(order.warranty_eligible)
    if order.warranty_expires_at and _as_utc(order.warranty_expires_at) < now:
        warranty_valid = False

    risk_score = estimate_claim_risk_for_order(db, order)
    claim_reason = payload.claim_reason if payload else WarrantyClaimReason.OTHER
    claim_type = _claim_type_from_reason(claim_reason)
    severity = _severity_from_risk(risk_score)
    risky_unit = _most_risky_order_unit(order)
    claim = WarrantyClaim(
        save_game_id=save_game_id,
        order_id=order.id,
        customer_id=order.customer_id,
        inventory_unit_id=risky_unit.id if risky_unit else None,
        claim_type=claim_type,
        claim_reason=claim_reason,
        status=WarrantyClaimStatus.OPEN,
        title=_claim_title(claim_type, source_label=f"Order #{order.id}"),
        complaint_summary=payload.complaint_summary if payload else "Customer reported a post-delivery issue.",
        description=_claim_description(order=order, claim_type=claim_type),
        severity=severity,
        claimed_on_day=save_game.game_day,
        due_on_day=save_game.game_day + _due_days_from_risk(risk_score),
        customer_message=payload.complaint_summary if payload else "Customer reported a warranty issue after delivery.",
        internal_risk_score=risk_score,
        estimated_cost_vnd=estimate_resolution_cost(_seed_claim_placeholder(order=order, claim_type=claim_type, risk_score=risk_score), WarrantyResolutionType.REPAIR),
        warranty_valid=warranty_valid,
        internal_notes=payload.internal_notes if payload else None,
        items=[
            WarrantyClaimItem(
                order_item_id=item.id,
                inventory_unit_id=item.inventory_unit_id,
                product_id=item.product_id,
                suspected_issue=_suspected_issue(claim_reason, item),
            )
            for item in order.items
        ],
    )
    db.add(claim)
    db.flush()
    order.warranty_claim_count = (order.warranty_claim_count or 0) + 1
    order.warranty_status = "CLAIM_OPEN"
    order.last_warranty_event_at = now
    _add_event(
        db,
        claim,
        WarrantyEventType.CLAIM_OPENED,
        f"Warranty claim opened for order #{order.id}: {claim_reason.value}.",
        {"warranty_valid": warranty_valid, "complaint_summary": claim.complaint_summary, "risk_score": risk_score},
    )
    db.commit()
    db.expire_all()
    return get_warranty_claim(db, save_game_id, claim.id)


def create_warranty_claim_from_resale(
    db: Session,
    save_game_id: int,
    resale_listing_id: int,
    payload: WarrantyClaimCreate | None = None,
) -> WarrantyClaim:
    listing = db.scalar(
        select(ResaleListing)
        .options(selectinload(ResaleListing.inventory_unit).selectinload(InventoryUnit.product))
        .where(ResaleListing.save_game_id == save_game_id, ResaleListing.id == resale_listing_id)
    )
    if not listing:
        raise not_found("Resale listing not found")
    if listing.status != ResaleListingStatus.SOLD:
        raise bad_request("Only sold resale listings can receive warranty claims")

    save_game = get_save_game(db, save_game_id)
    unit = listing.inventory_unit
    risk_score = estimate_claim_risk_for_inventory_unit(db, unit) if unit else 25
    claim_type = _claim_type_from_inventory(unit, listing)
    claim_reason = _reason_for_claim_type(claim_type)
    severity = _severity_from_risk(risk_score)
    claim = WarrantyClaim(
        save_game_id=save_game_id,
        resale_listing_id=listing.id,
        inventory_unit_id=unit.id if unit else None,
        claim_type=claim_type,
        claim_reason=claim_reason,
        status=WarrantyClaimStatus.OPEN,
        title=_claim_title(claim_type, source_label=f"Resale #{listing.id}"),
        complaint_summary=payload.complaint_summary if payload else listing.title,
        description=_claim_description(resale_listing=listing, claim_type=claim_type),
        severity=severity,
        claimed_on_day=save_game.game_day,
        due_on_day=save_game.game_day + _due_days_from_risk(risk_score),
        customer_message=payload.complaint_summary if payload else listing.description,
        internal_risk_score=risk_score,
        estimated_cost_vnd=estimate_resolution_cost(_seed_claim_placeholder(resale_listing=listing, claim_type=claim_type, risk_score=risk_score), WarrantyResolutionType.REPAIR),
        warranty_valid=bool(listing.warranty_days_offered > 0),
        internal_notes=payload.internal_notes if payload else None,
        items=[
            WarrantyClaimItem(
                inventory_unit_id=unit.id if unit else None,
                product_id=unit.product_id if unit else None,
                suspected_issue=_suspected_issue_from_claim_type(claim_type, unit.product if unit else None),
            )
        ],
    )
    db.add(claim)
    db.flush()
    _add_event(
        db,
        claim,
        WarrantyEventType.CLAIM_OPENED,
        f"Warranty claim opened for resale listing #{listing.id}: {claim_reason.value}.",
        {"warranty_valid": claim.warranty_valid, "risk_score": risk_score},
    )
    db.commit()
    db.expire_all()
    return get_warranty_claim(db, save_game_id, claim.id)


def create_warranty_claim_from_inventory_unit(
    db: Session,
    save_game_id: int,
    inventory_unit_id: int,
    payload: WarrantyClaimCreate | None = None,
) -> WarrantyClaim:
    unit = db.scalar(
        select(InventoryUnit)
        .options(selectinload(InventoryUnit.product))
        .where(InventoryUnit.save_game_id == save_game_id, InventoryUnit.id == inventory_unit_id)
    )
    if not unit:
        raise not_found("Inventory unit not found")

    save_game = get_save_game(db, save_game_id)
    risk_score = estimate_claim_risk_for_inventory_unit(db, unit)
    claim_type = _claim_type_from_inventory(unit)
    claim_reason = _reason_for_claim_type(claim_type)
    severity = _severity_from_risk(risk_score)
    claim = WarrantyClaim(
        save_game_id=save_game_id,
        inventory_unit_id=unit.id,
        claim_type=claim_type,
        claim_reason=claim_reason,
        status=WarrantyClaimStatus.OPEN,
        title=_claim_title(claim_type, source_label=f"Inventory #{unit.id}"),
        complaint_summary=payload.complaint_summary if payload else f"Warranty concern on inventory unit #{unit.id}",
        description=_claim_description(inventory_unit=unit, claim_type=claim_type),
        severity=severity,
        claimed_on_day=save_game.game_day,
        due_on_day=save_game.game_day + _due_days_from_risk(risk_score),
        customer_message=payload.complaint_summary if payload else "Post-sale issue was reported against a unit in stock.",
        internal_risk_score=risk_score,
        estimated_cost_vnd=estimate_resolution_cost(_seed_claim_placeholder(inventory_unit=unit, claim_type=claim_type, risk_score=risk_score), WarrantyResolutionType.REPAIR),
        warranty_valid=unit.warranty_months_remaining > 0 or unit.ready_for_resale,
        internal_notes=payload.internal_notes if payload else None,
        items=[
            WarrantyClaimItem(
                inventory_unit_id=unit.id,
                product_id=unit.product_id,
                suspected_issue=_suspected_issue_from_claim_type(claim_type, unit.product),
            )
        ],
    )
    db.add(claim)
    db.flush()
    _add_event(
        db,
        claim,
        WarrantyEventType.CLAIM_OPENED,
        f"Warranty claim opened for inventory unit #{unit.id}: {claim_reason.value}.",
        {"warranty_valid": claim.warranty_valid, "risk_score": risk_score},
    )
    db.commit()
    db.expire_all()
    return get_warranty_claim(db, save_game_id, claim.id)


def review_warranty_claim(
    db: Session,
    save_game_id: int,
    claim_id: int,
    payload: WarrantyClaimReviewRequest | None = None,
) -> WarrantyClaim:
    claim = _mutable_claim(db, save_game_id, claim_id)
    if claim.status in CLOSED_STATUSES:
        raise bad_request("Warranty claim is already resolved")

    if not claim.internal_risk_score:
        claim.internal_risk_score = _estimate_current_claim_risk(claim)
    if payload and payload.notes:
        claim.internal_notes = _append_note(claim.internal_notes, payload.notes)

    if claim.internal_risk_score >= 55 or claim.severity >= 4:
        claim.status = WarrantyClaimStatus.APPROVED
        claim.resolution_summary = claim.resolution_summary or "Claim reviewed and approved for resolution."
        _add_event(db, claim, WarrantyEventType.APPROVED, claim.resolution_summary, {"risk_score": claim.internal_risk_score})
    else:
        claim.status = WarrantyClaimStatus.IN_REVIEW
        _add_event(db, claim, WarrantyEventType.DIAGNOSIS_STARTED, "Warranty claim moved into review.", {"risk_score": claim.internal_risk_score})
    if claim.order:
        _touch_order_warranty(claim, claim.status.value)
    db.commit()
    return get_warranty_claim(db, save_game_id, claim_id)


def resolve_warranty_claim(
    db: Session,
    save_game_id: int,
    claim_id: int,
    resolution_type: WarrantyResolutionType,
    notes: str | None = None,
) -> WarrantyClaim:
    claim = _mutable_claim(db, save_game_id, claim_id, allow_rma=True)
    if claim.status in {WarrantyClaimStatus.CLOSED, WarrantyClaimStatus.RESOLVED, WarrantyClaimStatus.CANCELLED}:
        raise bad_request("Warranty claim is already resolved")

    if notes:
        claim.notes = _append_note(claim.notes, notes)

    final_cost = estimate_resolution_cost(claim, resolution_type)
    save_game = claim.order.save_game if claim.order else (claim.resale_listing.save_game if claim.resale_listing else get_save_game(db, save_game_id))
    if resolution_type != WarrantyResolutionType.REJECT and save_game.cash < final_cost:
        raise bad_request("Insufficient cash to resolve this warranty claim")

    reputation_delta = _reputation_delta_for_resolution(claim, resolution_type)
    if resolution_type != WarrantyResolutionType.REJECT:
        save_game.cash -= final_cost

    claim.final_cost_vnd = final_cost
    claim.reputation_delta = reputation_delta
    claim.resolution_type = resolution_type
    claim.resolved_on_day = save_game.game_day
    claim.resolved_at = datetime.now(timezone.utc)
    claim.resolution_summary = notes or _resolution_summary(claim, resolution_type, final_cost)
    claim.status = WarrantyClaimStatus.REJECTED if resolution_type == WarrantyResolutionType.REJECT else WarrantyClaimStatus.RESOLVED
    if claim.order:
        _touch_order_warranty(claim, claim.status.value)
    for item in claim.items:
        item.action_taken = resolution_type.value if resolution_type != WarrantyResolutionType.REJECT else "REJECTED"

    event_type = _resolution_event_type(resolution_type)
    _add_event(db, claim, event_type, claim.resolution_summary, {"cash_delta": -final_cost, "reputation_delta": reputation_delta})
    _add_event(db, claim, WarrantyEventType.CLAIM_CLOSED, "Warranty claim closed after resolution.", None)
    db.flush()
    from app.services import review_service

    review_service.generate_review_from_warranty(db, save_game_id, claim.id)
    return get_warranty_claim(db, save_game_id, claim_id)


def _claim_type_from_reason(reason: WarrantyClaimReason) -> WarrantyClaimType:
    mapping = {
        WarrantyClaimReason.DOA: WarrantyClaimType.DOA,
        WarrantyClaimReason.OVERHEATING: WarrantyClaimType.OVERHEATING,
        WarrantyClaimReason.CRASHING: WarrantyClaimType.RANDOM_CRASH,
        WarrantyClaimReason.RANDOM_SHUTDOWN: WarrantyClaimType.POWER_ISSUE,
        WarrantyClaimReason.ARTIFACTING: WarrantyClaimType.ARTIFACTING,
        WarrantyClaimReason.NOISY_FAN: WarrantyClaimType.FAN_NOISE,
        WarrantyClaimReason.PERFORMANCE_ISSUE: WarrantyClaimType.PERFORMANCE_ISSUE,
        WarrantyClaimReason.NO_DISPLAY: WarrantyClaimType.POWER_ISSUE,
        WarrantyClaimReason.OTHER: WarrantyClaimType.OTHER,
    }
    return mapping.get(reason, WarrantyClaimType.OTHER)


def _reason_for_claim_type(claim_type: WarrantyClaimType) -> WarrantyClaimReason:
    mapping = {
        WarrantyClaimType.DOA: WarrantyClaimReason.DOA,
        WarrantyClaimType.OVERHEATING: WarrantyClaimReason.OVERHEATING,
        WarrantyClaimType.RANDOM_CRASH: WarrantyClaimReason.CRASHING,
        WarrantyClaimType.PERFORMANCE_ISSUE: WarrantyClaimReason.PERFORMANCE_ISSUE,
        WarrantyClaimType.FAN_NOISE: WarrantyClaimReason.NOISY_FAN,
        WarrantyClaimType.STORAGE_FAILURE: WarrantyClaimReason.OTHER,
        WarrantyClaimType.ARTIFACTING: WarrantyClaimReason.ARTIFACTING,
        WarrantyClaimType.POWER_ISSUE: WarrantyClaimReason.RANDOM_SHUTDOWN,
        WarrantyClaimType.CUSTOMER_DAMAGE: WarrantyClaimReason.OTHER,
        WarrantyClaimType.COSMETIC_COMPLAINT: WarrantyClaimReason.OTHER,
        WarrantyClaimType.OTHER: WarrantyClaimReason.OTHER,
    }
    return mapping.get(claim_type, WarrantyClaimReason.OTHER)


def _claim_type_from_inventory(inventory_unit: InventoryUnit | None, resale_listing: ResaleListing | None = None) -> WarrantyClaimType:
    hidden_text = ""
    if inventory_unit and inventory_unit.hidden_condition_json is not None:
        hidden_text = str(inventory_unit.hidden_condition_json).lower()
    elif resale_listing and resale_listing.inventory_unit and resale_listing.inventory_unit.hidden_condition_json is not None:
        hidden_text = str(resale_listing.inventory_unit.hidden_condition_json).lower()

    if "customer_damage" in hidden_text or "physical_damage" in hidden_text:
        return WarrantyClaimType.CUSTOMER_DAMAGE
    if "liquid" in hidden_text or "power_issue" in hidden_text:
        return WarrantyClaimType.POWER_ISSUE
    if "storage" in hidden_text or "bad_sector" in hidden_text or "sector" in hidden_text:
        return WarrantyClaimType.STORAGE_FAILURE
    if "artifact" in hidden_text or "vram" in hidden_text or "gpu" in hidden_text:
        return WarrantyClaimType.ARTIFACTING
    if "crash" in hidden_text or "stability" in hidden_text or "random" in hidden_text:
        return WarrantyClaimType.RANDOM_CRASH
    if "overheat" in hidden_text or "thermal" in hidden_text:
        return WarrantyClaimType.OVERHEATING
    if "fan_noise" in hidden_text or "fan" in hidden_text:
        return WarrantyClaimType.FAN_NOISE

    category = inventory_unit.product.category.value if inventory_unit and inventory_unit.product else None
    if category == "GPU":
        return WarrantyClaimType.ARTIFACTING
    if category in {"CPU", "COOLER"}:
        return WarrantyClaimType.OVERHEATING
    if category in {"SSD", "STORAGE"}:
        return WarrantyClaimType.STORAGE_FAILURE
    if category in {"PSU", "CASE"}:
        return WarrantyClaimType.POWER_ISSUE
    return WarrantyClaimType.OTHER


def _severity_from_risk(risk_score: int) -> int:
    return max(1, min(5, 1 + risk_score // 20))


def _due_days_from_risk(risk_score: int) -> int:
    return max(3, min(10, 3 + risk_score // 15))


def _claim_title(claim_type: WarrantyClaimType, source_label: str) -> str:
    labels = {
        WarrantyClaimType.DOA: "Dead on Arrival",
        WarrantyClaimType.OVERHEATING: "Overheating Claim",
        WarrantyClaimType.RANDOM_CRASH: "Random Crash Claim",
        WarrantyClaimType.PERFORMANCE_ISSUE: "Performance Complaint",
        WarrantyClaimType.FAN_NOISE: "Fan Noise Claim",
        WarrantyClaimType.STORAGE_FAILURE: "Storage Failure Claim",
        WarrantyClaimType.ARTIFACTING: "Artifacting Claim",
        WarrantyClaimType.POWER_ISSUE: "Power Issue Claim",
        WarrantyClaimType.CUSTOMER_DAMAGE: "Customer Damage Review",
        WarrantyClaimType.COSMETIC_COMPLAINT: "Cosmetic Complaint",
        WarrantyClaimType.OTHER: "Warranty Claim",
    }
    return f"{labels.get(claim_type, 'Warranty Claim')} - {source_label}"


def _claim_description(
    order: Order | None = None,
    resale_listing: ResaleListing | None = None,
    inventory_unit: InventoryUnit | None = None,
    claim_type: WarrantyClaimType = WarrantyClaimType.OTHER,
) -> str:
    if order:
        return f"Post-delivery claim for order #{order.id}. Internal risk type: {claim_type.value}."
    if resale_listing:
        return f"Post-sale claim for resale listing #{resale_listing.id}. Internal risk type: {claim_type.value}."
    if inventory_unit:
        return f"Item-level warranty review for inventory unit #{inventory_unit.id}. Internal risk type: {claim_type.value}."
    return f"Warranty claim under review. Internal risk type: {claim_type.value}."


def _suspected_issue_from_claim_type(claim_type: WarrantyClaimType, product: HardwareProduct | None) -> str:
    category = product.category.value if product else "OTHER"
    if claim_type == WarrantyClaimType.OVERHEATING or category in {"CPU", "GPU", "COOLER"}:
        return "Thermal issue suspected."
    if claim_type == WarrantyClaimType.FAN_NOISE:
        return "Fan noise suspected."
    if claim_type == WarrantyClaimType.ARTIFACTING:
        return "Display artifacting or GPU instability suspected."
    if claim_type == WarrantyClaimType.STORAGE_FAILURE:
        return "Storage fault suspected."
    if claim_type == WarrantyClaimType.POWER_ISSUE:
        return "Power delivery issue suspected."
    if claim_type == WarrantyClaimType.RANDOM_CRASH:
        return "System stability issue suspected."
    if claim_type == WarrantyClaimType.DOA:
        return "Dead-on-arrival issue suspected."
    if claim_type == WarrantyClaimType.CUSTOMER_DAMAGE:
        return "Possible customer-caused damage under review."
    return "Included for warranty review."


def _hidden_condition_risk(hidden_condition: Any) -> int:
    if not hidden_condition:
        return 0
    text = str(hidden_condition).lower()
    points = 0
    for keyword, value in {
        "vram_instability": 16,
        "random_crash": 14,
        "artifact": 14,
        "bad_sector": 14,
        "storage_failure": 18,
        "overheat": 12,
        "fan_noise": 10,
        "power_issue": 12,
        "customer_damage": 20,
        "cosmetic": 4,
        "liquid": 18,
    }.items():
        if keyword in text:
            points += value
    return points


def _most_risky_order_unit(order: Order) -> InventoryUnit | None:
    best_unit: InventoryUnit | None = None
    best_score = -1
    for item in order.items:
        unit = item.inventory_unit
        if not unit:
            continue
        score = estimate_claim_risk_for_inventory_unit(None, unit)
        if score > best_score:
            best_score = score
            best_unit = unit
    return best_unit


def _estimate_current_claim_risk(claim: WarrantyClaim) -> int:
    if claim.order:
        return estimate_claim_risk_for_order(None, claim.order)
    if claim.inventory_unit:
        return estimate_claim_risk_for_inventory_unit(None, claim.inventory_unit)
    if claim.resale_listing and claim.resale_listing.inventory_unit:
        return estimate_claim_risk_for_inventory_unit(None, claim.resale_listing.inventory_unit)
    return claim.internal_risk_score or 0


def _resolution_event_type(resolution_type: WarrantyResolutionType) -> WarrantyEventType:
    return {
        WarrantyResolutionType.REPAIR: WarrantyEventType.REPAIR_COMPLETED,
        WarrantyResolutionType.REPLACE: WarrantyEventType.REPLACEMENT_ISSUED,
        WarrantyResolutionType.REFUND: WarrantyEventType.REFUND_ISSUED,
        WarrantyResolutionType.REJECT: WarrantyEventType.REJECTED,
        WarrantyResolutionType.GOODWILL_CREDIT: WarrantyEventType.CLAIM_CLOSED,
    }[resolution_type]


def _resolution_summary(claim: WarrantyClaim, resolution_type: WarrantyResolutionType, final_cost: int) -> str:
    if resolution_type == WarrantyResolutionType.REPAIR:
        return f"Repair completed for {final_cost:,} VND."
    if resolution_type == WarrantyResolutionType.REPLACE:
        return f"Replacement issued for {final_cost:,} VND."
    if resolution_type == WarrantyResolutionType.REFUND:
        return f"Refund issued for {final_cost:,} VND."
    if resolution_type == WarrantyResolutionType.GOODWILL_CREDIT:
        return f"Goodwill credit issued for {final_cost:,} VND."
    if claim.claim_type == WarrantyClaimType.CUSTOMER_DAMAGE:
        return "Claim rejected after confirming customer-caused damage."
    return "Claim rejected after review."


def _reputation_delta_for_resolution(claim: WarrantyClaim, resolution_type: WarrantyResolutionType) -> int:
    if resolution_type == WarrantyResolutionType.REPAIR:
        return 2 if claim.warranty_valid else 1
    if resolution_type == WarrantyResolutionType.REPLACE:
        return 3 if claim.warranty_valid else 1
    if resolution_type == WarrantyResolutionType.REFUND:
        return 4 if claim.warranty_valid else 1
    if resolution_type == WarrantyResolutionType.GOODWILL_CREDIT:
        return 2
    if claim.claim_type == WarrantyClaimType.CUSTOMER_DAMAGE:
        return 0
    return -4 if claim.warranty_valid else -2


def _seed_claim_placeholder(
    order: Order | None = None,
    resale_listing: ResaleListing | None = None,
    inventory_unit: InventoryUnit | None = None,
    claim_type: WarrantyClaimType = WarrantyClaimType.OTHER,
    risk_score: int = 0,
) -> WarrantyClaim:
    return WarrantyClaim(
        save_game_id=order.save_game_id if order else (resale_listing.save_game_id if resale_listing else inventory_unit.save_game_id),
        order_id=order.id if order else None,
        resale_listing_id=resale_listing.id if resale_listing else None,
        inventory_unit_id=inventory_unit.id if inventory_unit else None,
        customer_id=order.customer_id if order else None,
        claim_type=claim_type,
        claim_reason=_reason_for_claim_type(claim_type),
        status=WarrantyClaimStatus.OPEN,
        title="",
        complaint_summary="",
        description=None,
        severity=_severity_from_risk(risk_score),
        claimed_on_day=0,
        due_on_day=None,
        resolved_on_day=None,
        customer_message=None,
        internal_risk_score=risk_score,
        estimated_cost_vnd=0,
        final_cost_vnd=None,
        warranty_valid=True,
    )
