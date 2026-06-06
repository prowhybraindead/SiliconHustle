import random
from datetime import datetime, timezone
from typing import Any, List, Optional, Dict, Tuple
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import not_found, bad_request
from app.models.entities import InventoryUnit, InventoryRefurbishEvent, SaveGame
from app.models.enums import (
    HardwareCategory,
    Grade,
    InventoryStatus,
    RefurbishActionType,
    RefurbishResultStatus,
    StaffStatus,
    StaffTaskType,
)
from app.services import progression_service, staff_service


APPLICABILITY = {
    RefurbishActionType.CLEAN_DUST: [
        HardwareCategory.CPU, HardwareCategory.GPU, HardwareCategory.RAM, HardwareCategory.SSD,
        HardwareCategory.STORAGE, HardwareCategory.PSU, HardwareCategory.MOTHERBOARD, HardwareCategory.CASE,
        HardwareCategory.COOLER, HardwareCategory.WATER_COOLING, HardwareCategory.MONITOR, HardwareCategory.OTHER
    ],
    RefurbishActionType.COSMETIC_CLEANUP: [
        HardwareCategory.GPU, HardwareCategory.CASE, HardwareCategory.COOLER, HardwareCategory.RAM,
        HardwareCategory.MOTHERBOARD, HardwareCategory.PSU
    ],
    RefurbishActionType.REPASTE: [
        HardwareCategory.CPU, HardwareCategory.GPU, HardwareCategory.COOLER
    ],
    RefurbishActionType.REPLACE_FAN: [
        HardwareCategory.GPU, HardwareCategory.PSU, HardwareCategory.CASE, HardwareCategory.COOLER
    ],
    RefurbishActionType.REPLACE_THERMAL_PADS: [
        HardwareCategory.GPU, HardwareCategory.SSD, HardwareCategory.STORAGE, HardwareCategory.COOLER
    ],
    RefurbishActionType.FIRMWARE_FLASH: [
        HardwareCategory.GPU, HardwareCategory.SSD, HardwareCategory.STORAGE, HardwareCategory.MOTHERBOARD
    ],
    RefurbishActionType.BASIC_REPAIR: [
        HardwareCategory.CPU, HardwareCategory.GPU, HardwareCategory.RAM, HardwareCategory.SSD,
        HardwareCategory.STORAGE, HardwareCategory.PSU, HardwareCategory.MOTHERBOARD, HardwareCategory.CASE,
        HardwareCategory.COOLER, HardwareCategory.WATER_COOLING, HardwareCategory.MONITOR, HardwareCategory.OTHER
    ],
    RefurbishActionType.DEEP_DIAGNOSTIC: [
        HardwareCategory.CPU, HardwareCategory.GPU, HardwareCategory.RAM, HardwareCategory.SSD,
        HardwareCategory.STORAGE, HardwareCategory.PSU, HardwareCategory.MOTHERBOARD, HardwareCategory.CASE,
        HardwareCategory.COOLER, HardwareCategory.WATER_COOLING, HardwareCategory.MONITOR, HardwareCategory.OTHER
    ],
    RefurbishActionType.STRESS_VALIDATION: [
        HardwareCategory.CPU, HardwareCategory.GPU, HardwareCategory.RAM, HardwareCategory.SSD,
        HardwareCategory.STORAGE, HardwareCategory.PSU, HardwareCategory.MOTHERBOARD
    ]
}


ACTION_DETAILS = {
    RefurbishActionType.CLEAN_DUST: {"cost": 50_000, "duration": 0},
    RefurbishActionType.COSMETIC_CLEANUP: {"cost": 100_000, "duration": 0},
    RefurbishActionType.REPASTE: {"cost": 150_000, "duration": 0},
    RefurbishActionType.REPLACE_FAN: {"cost": 300_000, "duration": 1},
    RefurbishActionType.REPLACE_THERMAL_PADS: {"cost": 250_000, "duration": 1},
    RefurbishActionType.FIRMWARE_FLASH: {"cost": 100_000, "duration": 0},
    RefurbishActionType.BASIC_REPAIR: {"cost": 800_000, "duration": 1},
    RefurbishActionType.DEEP_DIAGNOSTIC: {"cost": 200_000, "duration": 0},
    RefurbishActionType.STRESS_VALIDATION: {"cost": 150_000, "duration": 0},
}


def _grade_from_health(health: int) -> Grade:
    if health >= 95:
        return Grade.A_PLUS
    if health >= 85:
        return Grade.A
    if health >= 70:
        return Grade.B
    if health >= 55:
        return Grade.C
    if health >= 40:
        return Grade.D
    return Grade.F


def build_public_condition_snapshot(unit: InventoryUnit) -> Dict[str, Any]:
    return {
        "grade": unit.grade.value if unit.grade else None,
        "status": unit.status.value if unit.status else None,
        "inspection_confidence": unit.inspection_confidence,
        "health_score": unit.health_score,
        "thermal_score": unit.thermal_score,
        "fan_score": unit.fan_score,
        "vram_score": unit.vram_score,
        "stability_score": unit.stability_score,
        "repair_risk_score": unit.repair_risk_score,
        "resale_value_estimate_vnd": unit.resale_value_estimate_vnd,
        "ready_for_resale": unit.ready_for_resale,
        "refurbish_count": unit.refurbish_count,
    }


def recompute_inventory_grade(unit: InventoryUnit) -> Grade:
    if unit.health_score is not None:
        unit.grade = _grade_from_health(unit.health_score)
    return unit.grade


def recompute_resale_value(db: Session, save_game_id: int, unit: InventoryUnit) -> int:
    product = unit.product
    
    # 1. Base price resolution
    if product.latest_used_market_vnd is not None and product.latest_used_market_vnd > 0:
        base_price = product.latest_used_market_vnd
    elif product.latest_local_retail_vnd is not None and product.latest_local_retail_vnd > 0:
        base_price = int(product.latest_local_retail_vnd * 0.70)
    elif product.latest_supplier_cost_vnd is not None and product.latest_supplier_cost_vnd > 0:
        base_price = int(product.latest_supplier_cost_vnd * 0.75)
    elif product.msrp_vnd is not None and product.msrp_vnd > 0:
        base_price = int(product.msrp_vnd * 0.65)
    else:
        perf = product.base_performance_score or 50
        base_price = perf * 150_000

    # 2. Market multiplier (Requirements 8)
    from app.services.market_service import get_effective_product_multiplier
    mult = get_effective_product_multiplier(db, save_game_id, product)
    market_adjusted = base_price * mult

    # 3. Quality/Grade factor
    grade_factor = 0.5
    if unit.grade:
        if unit.grade == Grade.A_PLUS:
            grade_factor = 1.1
        elif unit.grade == Grade.A:
            grade_factor = 1.0
        elif unit.grade == Grade.B:
            grade_factor = 0.85
        elif unit.grade == Grade.C:
            grade_factor = 0.7
        elif unit.grade == Grade.D:
            grade_factor = 0.5
        elif unit.grade == Grade.F:
            grade_factor = 0.2

    # Scale by health_score if present
    health_scale = 1.0
    if unit.health_score is not None:
        health_scale = 0.5 + 0.5 * (unit.health_score / 100.0)

    resale_val = int(market_adjusted * grade_factor * health_scale)
    return max(0, resale_val)


def is_action_applicable(unit: InventoryUnit, action_type: RefurbishActionType) -> Tuple[bool, str]:
    category = unit.product.category
    allowed_categories = APPLICABILITY.get(action_type, [])
    if category not in allowed_categories:
        return False, f"Action {action_type.value} is not applicable to product category {category.value}."
    return True, ""


def list_refurbish_events(db: Session, save_game_id: int, inventory_unit_id: Optional[int] = None) -> List[InventoryRefurbishEvent]:
    stmt = select(InventoryRefurbishEvent).where(InventoryRefurbishEvent.save_game_id == save_game_id)
    if inventory_unit_id is not None:
        stmt = stmt.where(InventoryRefurbishEvent.inventory_unit_id == inventory_unit_id)
    return list(db.scalars(stmt.order_by(InventoryRefurbishEvent.created_at.desc())))


def get_refurbish_event(db: Session, save_game_id: int, event_id: int) -> InventoryRefurbishEvent:
    event = db.scalar(
        select(InventoryRefurbishEvent).where(
            InventoryRefurbishEvent.save_game_id == save_game_id,
            InventoryRefurbishEvent.id == event_id
        )
    )
    if not event:
        raise not_found("Refurbish event not found")
    return event


def get_available_refurbish_actions(db: Session, save_game_id: int, inventory_unit_id: int) -> List[Dict[str, Any]]:
    unit = db.scalar(
        select(InventoryUnit).where(
            InventoryUnit.save_game_id == save_game_id,
            InventoryUnit.id == inventory_unit_id
        )
    )
    if not unit:
        raise not_found("Inventory unit not found")
        
    actions = []
    for action_type in RefurbishActionType:
        applicable, reason = is_action_applicable(unit, action_type)
        details = ACTION_DETAILS[action_type]
        
        # Check availability constraints
        is_blocked = False
        blocked_reason = ""
        if unit.status in [InventoryStatus.SOLD, InventoryStatus.INSTALLED_IN_BUILD, InventoryStatus.RESERVED, InventoryStatus.READY_FOR_SALE]:
            is_blocked = True
            blocked_reason = f"Item is currently {unit.status.value}"
            
        actions.append({
            "action_type": action_type.value,
            "cost_vnd": details["cost"],
            "duration_days": details["duration"],
            "applicable": applicable,
            "unavailable_reason": blocked_reason or (reason if not applicable else ""),
        })
    return actions


def estimate_refurbish_action(db: Session, save_game_id: int, inventory_unit_id: int, action_type: RefurbishActionType) -> Dict[str, Any]:
    unit = db.scalar(
        select(InventoryUnit).where(
            InventoryUnit.save_game_id == save_game_id,
            InventoryUnit.id == inventory_unit_id
        )
    )
    if not unit:
        raise not_found("Inventory unit not found")
        
    applicable, reason = is_action_applicable(unit, action_type)
    details = ACTION_DETAILS[action_type]
    
    # Check availability constraints
    is_blocked = False
    blocked_reason = ""
    if unit.status in [InventoryStatus.SOLD, InventoryStatus.INSTALLED_IN_BUILD, InventoryStatus.RESERVED, InventoryStatus.READY_FOR_SALE]:
        is_blocked = True
        blocked_reason = f"Item is currently {unit.status.value}"
        
    return {
        "action_type": action_type.value,
        "cost_vnd": details["cost"],
        "duration_days": details["duration"],
        "applicable": applicable and not is_blocked,
        "unavailable_reason": blocked_reason or (reason if not applicable else ""),
    }


def run_refurbish_action(
    db: Session,
    save_game_id: int,
    inventory_unit_id: int,
    action_type: RefurbishActionType,
    staff_id: int | None = None,
) -> InventoryRefurbishEvent:
    save_game = db.get(SaveGame, save_game_id)
    if not save_game:
        raise not_found("Save game not found")
        
    unit = db.scalar(
        select(InventoryUnit).where(
            InventoryUnit.save_game_id == save_game_id,
            InventoryUnit.id == inventory_unit_id
        )
    )
    if not unit:
        raise not_found("Inventory unit not found")
        
    # Check availability constraints (Requirement 4)
    if unit.status in [InventoryStatus.SOLD, InventoryStatus.INSTALLED_IN_BUILD, InventoryStatus.RESERVED, InventoryStatus.READY_FOR_SALE]:
        raise bad_request(f"Cannot refurbish inventory unit with status {unit.status.value}")
        
    # Check applicability (Requirement 3)
    applicable, reason = is_action_applicable(unit, action_type)
    if not applicable:
        raise bad_request(f"Action {action_type.value} is not applicable: {reason}")

    staff_member = None
    staff_effects: dict[str, Any] | None = None
    if staff_id is not None:
        staff_member = staff_service.get_staff_member(db, save_game_id, staff_id)
        if staff_member.status not in {StaffStatus.AVAILABLE, StaffStatus.RESTING}:
            raise bad_request("Selected staff member is not available")
        staff_effects = staff_service.compute_staff_effects(staff_member, StaffTaskType.REFURBISH)

    # Check cash (Requirement 6)
    details = ACTION_DETAILS[action_type]
    cost = details["cost"]
    duration = details["duration"]
    if staff_effects:
        cost_reduction_percent = int(staff_effects.get("cost_reduction_percent", 0) or 0)
        if cost_reduction_percent > 0:
            cost = max(0, round(cost * (1 - cost_reduction_percent / 100.0)))

    if save_game.cash < cost:
        raise bad_request("Insufficient cash to perform this refurbish action")
        
    # Deduct cash exactly once
    save_game.cash -= cost
    
    # Capture before snapshots (excluding hidden_condition_json!) (Requirement 2)
    before_grade = unit.grade
    before_snapshot = build_public_condition_snapshot(unit)
    
    # Extract hidden conditions
    hc = unit.hidden_condition_json or {}
    true_health = hc.get("true_health", unit.health_score or 70)
    true_performance = hc.get("true_performance", unit.performance_score or 70)
    true_thermal = hc.get("true_thermal", unit.thermal_score or 70)
    true_fan = hc.get("true_fan", unit.fan_score or 70)
    true_stability = hc.get("true_stability", unit.stability_score or 70)
    true_vram = hc.get("true_vram", unit.vram_score or 70)
    hidden_defect = hc.get("hidden_defect", "NONE")
    dust_level = hc.get("dust_level", 50)
    previous_usage = hc.get("previous_usage", "UNKNOWN")
    
    status = RefurbishResultStatus.COMPLETED
    summary = ""
    
    health_delta = 0
    thermal_delta = 0
    fan_delta = 0
    vram_delta = 0
    stability_delta = 0
    cosmetic_delta = 0
    risk_delta = 0
    resale_value_delta = 0
    thermal_bonus = int(staff_effects.get("thermal_bonus", 0) or 0) if staff_effects else 0
    fan_bonus = int(staff_effects.get("fan_bonus", 0) or 0) if staff_effects else 0
    vram_bonus = int(staff_effects.get("vram_bonus", 0) or 0) if staff_effects else 0
    stability_bonus = int(staff_effects.get("stability_bonus", 0) or 0) if staff_effects else 0
    confidence_bonus = int(staff_effects.get("confidence_bonus", 0) or 0) if staff_effects else 0
    health_bonus = int(staff_effects.get("health_bonus", 0) or 0) if staff_effects else 0
    
    if action_type == RefurbishActionType.CLEAN_DUST:
        old_dust = dust_level
        dust_level = 0
        thermal_gain = random.randint(5, 12) + thermal_bonus
        fan_gain = random.randint(5, 12) + fan_bonus
        
        true_thermal = min(100, true_thermal + thermal_gain)
        true_fan = min(100, true_fan + fan_gain)
        
        if unit.thermal_score is not None:
            unit.thermal_score = min(100, unit.thermal_score + thermal_gain)
            thermal_delta = thermal_gain
        if unit.fan_score is not None:
            unit.fan_score = min(100, unit.fan_score + fan_gain)
            fan_delta = fan_gain
            
        summary = f"Thổi bụi linh kiện (giảm bụi từ {old_dust}% về 0%). Nhiệt độ và quạt hoạt động ổn định hơn."
        
    elif action_type == RefurbishActionType.COSMETIC_CLEANUP:
        health_gain = random.randint(3, 8) + health_bonus
        true_health = min(100, true_health + health_gain)
        if unit.health_score is not None:
            unit.health_score = min(100, unit.health_score + health_gain)
            health_delta = health_gain
            
        cosmetic_delta = random.randint(5, 15)
        summary = "Vệ sinh ngoại hình linh kiện. Ngoại hình trông sáng sủa và mới hơn."
        
    elif action_type == RefurbishActionType.REPASTE:
        thermal_gain = random.randint(15, 25) + thermal_bonus
        true_thermal = min(100, true_thermal + thermal_gain)
        if unit.thermal_score is not None:
            unit.thermal_score = min(100, unit.thermal_score + thermal_gain)
            thermal_delta = thermal_gain
            
        summary = "Tra lại keo tản nhiệt mới hiệu năng cao. Giảm nhiệt độ hoạt động đáng kể."
        
    elif action_type == RefurbishActionType.REPLACE_FAN:
        true_fan = min(100, random.randint(95, 100) + fan_bonus)
        if unit.fan_score is not None:
            fan_delta = true_fan - unit.fan_score
            unit.fan_score = true_fan
            
        if hidden_defect == "FAN_WEAR":
            hidden_defect = "NONE"
            summary = "Thay thế quạt tản nhiệt bị mòn/hỏng bằng quạt mới. Khắc phục hoàn toàn lỗi quạt kêu to/kẹt."
        else:
            summary = "Thay thế quạt tản nhiệt mới. Tối ưu hóa lưu lượng gió."
            
    elif action_type == RefurbishActionType.REPLACE_THERMAL_PADS:
        thermal_gain = random.randint(10, 20) + thermal_bonus
        vram_gain = random.randint(10, 20) + vram_bonus
        
        true_thermal = min(100, true_thermal + thermal_gain)
        true_vram = min(100, true_vram + vram_gain)
        
        if unit.thermal_score is not None:
            unit.thermal_score = min(100, unit.thermal_score + thermal_gain)
            thermal_delta = thermal_gain
        if unit.vram_score is not None:
            unit.vram_score = min(100, unit.vram_score + vram_gain)
            vram_delta = vram_gain
            
        summary = "Thay thế các tấm dẫn nhiệt (thermal pads) trên VRAM và VRM."
        
    elif action_type == RefurbishActionType.FIRMWARE_FLASH:
        stability_change = random.randint(-8, 12) + stability_bonus
        true_stability = max(10, min(100, true_stability + stability_change))
        if unit.stability_score is not None:
            unit.stability_score = max(10, min(100, unit.stability_score + stability_change))
            stability_delta = stability_change
            
        summary = "Nạp lại/Cập nhật BIOS/Firmware cho linh kiện."
        if stability_change < 0:
            status = RefurbishResultStatus.PARTIAL_SUCCESS
            summary += " Quá trình nạp thành công nhưng độ ổn định giảm sút."
        else:
            summary += " Tăng tính tương thích và độ ổn định."
            
    elif action_type == RefurbishActionType.BASIC_REPAIR:
        success = random.random() < min(0.90, 0.60 + (confidence_bonus / 100.0))
        if success:
            if hidden_defect != "NONE":
                old_defect = hidden_defect
                hidden_defect = "NONE"
                health_gain = random.randint(15, 25) + health_bonus
                true_health = min(100, true_health + health_gain)
                if unit.health_score is not None:
                    unit.health_score = min(100, unit.health_score + health_gain)
                    health_delta = health_gain
                summary = f"Sửa chữa phần cứng cơ bản thành công. Khắc phục lỗi {old_defect}."
            else:
                summary = "Sửa chữa phần cứng cơ bản thành công. Gia cố mạch nguồn linh kiện."
            status = RefurbishResultStatus.COMPLETED
        else:
            status = RefurbishResultStatus.FAILED
            summary = "Sửa chữa phần cứng cơ bản thất bại. Không khắc phục được lỗi hiện tại."
            
    elif action_type == RefurbishActionType.DEEP_DIAGNOSTIC:
        conf_gain = random.randint(20, 30) + confidence_bonus
        unit.inspection_confidence = min(100, unit.inspection_confidence + conf_gain)
        
        if hidden_defect != "NONE" and not unit.hidden_defect_revealed:
            if random.random() < 0.85:
                unit.hidden_defect_revealed = True
                summary = f"Chẩn đoán chuyên sâu thành công. Phát hiện lỗi ẩn: {hidden_defect}."
            else:
                summary = "Chẩn đoán chuyên sâu hoàn tất. Không phát hiện lỗi bất thường nào mới."
        else:
            summary = "Chẩn đoán chuyên sâu hoàn tất. Xác nhận tình trạng linh kiện hiện tại."
            
    elif action_type == RefurbishActionType.STRESS_VALIDATION:
        conf_gain = random.randint(10, 15) + confidence_bonus
        unit.inspection_confidence = min(100, unit.inspection_confidence + conf_gain)
        
        stability_gain = random.randint(5, 15) + stability_bonus
        true_stability = min(100, true_stability + stability_gain)
        if unit.stability_score is not None:
            unit.stability_score = min(100, unit.stability_score + stability_gain)
            stability_delta = stability_gain
            
        summary = "Chạy kiểm tra tải cao (Stress test) để đánh giá độ ổn định của linh kiện."

    # Update hidden condition
    if unit.hidden_condition_json:
        unit.hidden_condition_json = {
            "true_health": true_health,
            "true_performance": true_performance,
            "true_thermal": true_thermal,
            "true_fan": true_fan,
            "true_stability": true_stability,
            "true_vram": true_vram,
            "previous_usage": previous_usage,
            "hidden_defect": hidden_defect,
            "dust_level": dust_level,
            "warranty_risk": hc.get("warranty_risk", "MEDIUM"),
            "repair_history": hc.get("repair_history", "NONE")
        }

    # Recompute grade
    if unit.health_score is not None:
        unit.grade = _grade_from_health(unit.health_score)

    # Recompute risk
    if hidden_defect != "NONE":
        unit.repair_risk_score = random.randint(60, 95)
    else:
        unit.repair_risk_score = max(5, min(95, 100 - true_stability))

    # Recompute resale value
    old_resale_value = unit.resale_value_estimate_vnd or 0
    new_resale_value = recompute_resale_value(db, save_game_id, unit)
    unit.resale_value_estimate_vnd = new_resale_value
    resale_value_delta = new_resale_value - old_resale_value

    # Update metadata
    unit.refurbish_count += 1
    unit.last_refurbished_at = datetime.now(timezone.utc)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    note_line = f"[{date_str}] {action_type.value}: {summary}"
    if unit.refurbish_notes:
        unit.refurbish_notes += f"\n{note_line}"
    else:
        unit.refurbish_notes = note_line

    if unit.status not in [InventoryStatus.DEFECTIVE, InventoryStatus.READY_FOR_SALE]:
        unit.status = InventoryStatus.REFURBISHED
    if unit.hidden_defect_revealed:
        unit.status = InventoryStatus.DEFECTIVE

    after_grade = unit.grade
    after_snapshot = build_public_condition_snapshot(unit)

    event = InventoryRefurbishEvent(
        save_game_id=save_game_id,
        inventory_unit_id=unit.id,
        action_type=action_type,
        status=status,
        cost_vnd=cost,
        duration_days=duration,
        started_on_day=save_game.game_day,
        completed_on_day=save_game.game_day,
        before_grade=before_grade,
        after_grade=after_grade,
        before_condition_json=before_snapshot,
        after_condition_json=after_snapshot,
        health_delta=health_delta,
        thermal_delta=thermal_delta,
        fan_delta=fan_delta,
        vram_delta=vram_delta,
        stability_delta=stability_delta,
        cosmetic_delta=cosmetic_delta,
        risk_delta=risk_delta,
        resale_value_delta_vnd=resale_value_delta,
        summary=summary,
        notes=None
    )
    
    db.add(event)
    if staff_member is not None:
        staff_service.assign_staff_to_task(db, save_game_id, staff_member.id, StaffTaskType.REFURBISH, "inventory_unit", unit.id)
    db.commit()
    db.refresh(event)
    return event


def mark_ready_for_resale(db: Session, save_game_id: int, inventory_unit_id: int) -> InventoryUnit:
    unit = db.scalar(
        select(InventoryUnit).where(
            InventoryUnit.save_game_id == save_game_id,
            InventoryUnit.id == inventory_unit_id
        )
    )
    if not unit:
        raise not_found("Inventory unit not found")
        
    if unit.status in [InventoryStatus.SOLD, InventoryStatus.INSTALLED_IN_BUILD, InventoryStatus.RESERVED]:
        raise bad_request(f"Cannot mark ready for resale: Item is {unit.status.value}")
        
    if unit.inspection_confidence < 60:
        raise bad_request(f"Cannot mark ready for resale: Inspection confidence is too low ({unit.inspection_confidence}%)")
        
    if unit.grade in [Grade.UNKNOWN, Grade.F]:
        raise bad_request(f"Cannot mark ready for resale: Item grade is {unit.grade.value if unit.grade else 'UNKNOWN'}")
        
    unit.ready_for_resale = True
    unit.status = InventoryStatus.READY_FOR_SALE
    db.commit()
    db.refresh(unit)
    return unit


def unmark_ready_for_resale(db: Session, save_game_id: int, inventory_unit_id: int) -> InventoryUnit:
    unit = db.scalar(
        select(InventoryUnit).where(
            InventoryUnit.save_game_id == save_game_id,
            InventoryUnit.id == inventory_unit_id
        )
    )
    if not unit:
        raise not_found("Inventory unit not found")
        
    if unit.status in [InventoryStatus.SOLD, InventoryStatus.INSTALLED_IN_BUILD, InventoryStatus.RESERVED]:
        raise bad_request(f"Cannot unmark ready for resale: Item is {unit.status.value}")
        
    unit.ready_for_resale = False
    
    if unit.refurbish_count > 0:
        unit.status = InventoryStatus.REFURBISHED
    elif unit.inspection_confidence >= 90:
        unit.status = InventoryStatus.FULLY_INSPECTED
    elif unit.inspection_confidence >= 70:
        unit.status = InventoryStatus.STRESS_TESTED
    elif unit.inspection_confidence >= 45:
        unit.status = InventoryStatus.BENCHMARKED
    elif unit.inspection_confidence >= 20:
        unit.status = InventoryStatus.BASIC_CHECKED
    else:
        unit.status = InventoryStatus.UNTESTED
        
    db.commit()
    db.refresh(unit)
    return unit
