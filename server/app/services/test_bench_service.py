import random
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.entities import InventoryUnit, TestResult
from app.models.enums import ConditionType, Grade, InventoryStatus, TestType
from app.services import progression_service
from app.services.inventory_service import get_inventory_unit


def _clamp(value: int, low: int = 1, high: int = 100) -> int:
    return max(low, min(high, value))


def _rng(unit: InventoryUnit, test_type: TestType) -> random.Random:
    seed = f"{unit.id}:{unit.product_id}:{unit.condition_type.value}:{test_type.value}:{unit.created_at.isoformat()}"
    return random.Random(seed)


def _condition_offset(condition: ConditionType) -> int:
    return {
        ConditionType.NEW: 8,
        ConditionType.OPEN_BOX: 2,
        ConditionType.USED: -10,
        ConditionType.REFURBISHED: -2,
        ConditionType.DEFECTIVE: -35,
        ConditionType.FOR_PARTS: -55,
    }[condition]


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


def _base_scores(unit: InventoryUnit, test_type: TestType) -> dict[str, int | str | bool]:
    product = unit.product
    rng = _rng(unit, test_type)
    offset = _condition_offset(unit.condition_type)
    heat_penalty = max(0, product.base_heat_score - 55) // 4
    mining_penalty = max(0, product.mining_popularity_score - 65) // 5
    random_swing = rng.randint(-6, 7)

    health = _clamp(product.base_reliability_score + offset - mining_penalty + random_swing)
    performance = _clamp(product.base_performance_score + offset // 3 + rng.randint(-4, 5))
    thermal = _clamp(100 - product.base_heat_score + product.base_reliability_score // 8 + offset // 2 + rng.randint(-5, 7))
    fan = _clamp(88 + offset // 2 - heat_penalty + rng.randint(-8, 6))
    stability = _clamp((health + thermal + product.base_reliability_score) // 3 + rng.randint(-4, 5))
    vram = _clamp(90 + offset // 2 - mining_penalty + rng.randint(-7, 7))
    defect = health < 45 or rng.random() < (0.03 if unit.condition_type == ConditionType.USED else 0.01)
    warranty_risk = "LOW" if stability >= 82 and health >= 80 else "MEDIUM" if stability >= 58 else "HIGH"

    # Override with hidden condition json if present (Used Market / Trade-in)
    if unit.hidden_condition_json:
        hc = unit.hidden_condition_json
        health = hc.get("true_health", health)
        performance = hc.get("true_performance", performance)
        thermal = hc.get("true_thermal", thermal)
        fan = hc.get("true_fan", fan)
        stability = hc.get("true_stability", stability)
        vram = hc.get("true_vram", vram)
        defect = hc.get("hidden_defect", "NONE") != "NONE"
        warranty_risk = hc.get("warranty_risk", warranty_risk)

    return {
        "health_score": health,
        "performance_score": performance,
        "thermal_score": thermal,
        "fan_score": fan,
        "stability_score": stability,
        "vram_score": vram,
        "warranty_risk": warranty_risk,
        "hidden_defect_revealed": defect,
    }


def run_test(db: Session, save_game_id: int, inventory_unit_id: int, test_type: TestType) -> tuple[InventoryUnit, TestResult]:
    unit = get_inventory_unit(db, save_game_id, inventory_unit_id)
    scores = _base_scores(unit, test_type)
    rng = _rng(unit, test_type)
    confidence_bonus = int(progression_service.get_effect_value(db, save_game_id, "test_confidence_bonus", 0) or 0)
    reveal_bonus = int(progression_service.get_effect_value(db, save_game_id, "hidden_defect_reveal_bonus", 0) or 0)

    if test_type == TestType.BASIC_CHECK:
        unit.inspection_confidence = max(unit.inspection_confidence, rng.randint(20, 30))
        unit.inspection_confidence = min(100, unit.inspection_confidence + confidence_bonus)
        unit.health_score = scores["health_score"]
        unit.status = InventoryStatus.BASIC_CHECKED
        summary = "Basic check completed. Cosmetic and boot-level health are now visible."
    elif test_type == TestType.BENCHMARK:
        unit.inspection_confidence = max(unit.inspection_confidence, rng.randint(45, 60))
        unit.inspection_confidence = min(100, unit.inspection_confidence + confidence_bonus)
        unit.health_score = unit.health_score or scores["health_score"]
        unit.performance_score = scores["performance_score"]
        unit.thermal_score = scores["thermal_score"]
        unit.fan_score = scores["fan_score"]
        unit.status = InventoryStatus.BENCHMARKED
        summary = "Benchmark completed. Performance, thermal, and fan behavior are now visible."
    elif test_type == TestType.STRESS_TEST:
        unit.inspection_confidence = max(unit.inspection_confidence, rng.randint(70, 80))
        unit.inspection_confidence = min(100, unit.inspection_confidence + confidence_bonus)
        unit.thermal_score = scores["thermal_score"]
        unit.stability_score = scores["stability_score"]
        unit.warranty_risk = str(scores["warranty_risk"])
        unit.hidden_defect_revealed = bool(scores["hidden_defect_revealed"])
        if reveal_bonus > 0 and unit.hidden_condition_json and not unit.hidden_defect_revealed:
            unit.hidden_defect_revealed = rng.randint(1, 100) <= reveal_bonus
        unit.status = InventoryStatus.STRESS_TESTED
        summary = "Stress test completed. Stability and warranty risk are now visible."
    else:
        unit.inspection_confidence = max(unit.inspection_confidence, rng.randint(90, 95))
        unit.inspection_confidence = min(100, unit.inspection_confidence + confidence_bonus)
        unit.health_score = scores["health_score"]
        unit.performance_score = scores["performance_score"]
        unit.thermal_score = scores["thermal_score"]
        unit.fan_score = scores["fan_score"]
        unit.vram_score = scores["vram_score"]
        unit.stability_score = scores["stability_score"]
        unit.warranty_risk = str(scores["warranty_risk"])
        unit.hidden_defect_revealed = bool(scores["hidden_defect_revealed"])
        if reveal_bonus > 0 and unit.hidden_condition_json and not unit.hidden_defect_revealed:
            unit.hidden_defect_revealed = rng.randint(1, 100) <= reveal_bonus
        unit.grade = _grade_from_health(int(scores["health_score"]))
        unit.status = InventoryStatus.DEFECTIVE if unit.hidden_defect_revealed else InventoryStatus.READY_FOR_SALE
        summary = "Full inspection completed. Most hidden risk and resale metrics are now visible."

    unit.updated_at = datetime.now(timezone.utc)
    result = TestResult(
        inventory_unit_id=unit.id,
        test_type=test_type,
        summary=summary,
        raw_result_json=scores,
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    refreshed = get_inventory_unit(db, save_game_id, inventory_unit_id)
    return refreshed, result


def list_tests(db: Session, save_game_id: int, inventory_unit_id: int) -> list[TestResult]:
    get_inventory_unit(db, save_game_id, inventory_unit_id)
    return list(
        db.scalars(
            select(TestResult)
            .where(TestResult.inventory_unit_id == inventory_unit_id)
            .options(selectinload(TestResult.inventory_unit))
            .order_by(TestResult.created_at.desc())
        )
    )
