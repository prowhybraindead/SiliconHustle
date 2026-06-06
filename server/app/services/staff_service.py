from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import bad_request, not_found
from app.models.entities import (
    InventoryUnit,
    Order,
    PurchaseOrder,
    ResaleListing,
    SaveGame,
    StaffAssignmentLog,
    StaffMember,
)
from app.models.enums import InventoryStatus, StaffRole, StaffStatus, StaffTaskType, StaffTrait
from app.services import progression_service
from app.services.save_game_service import get_save_game


FIRST_NAMES = [
    "Alex",
    "Ava",
    "Ben",
    "Cleo",
    "Dylan",
    "Elsa",
    "Finn",
    "Gia",
    "Hana",
    "Ivan",
    "Jade",
    "Kai",
    "Lina",
    "Milo",
    "Nora",
    "Owen",
    "Pia",
    "Quinn",
    "Rin",
    "Theo",
]

LAST_NAMES = [
    "Adler",
    "Baker",
    "Chen",
    "Dao",
    "Everett",
    "Frost",
    "Grant",
    "Hale",
    "Ishida",
    "Jensen",
    "Keller",
    "Le",
    "Miller",
    "Nguyen",
    "Ortiz",
    "Park",
    "Quang",
    "Rossi",
    "Stone",
    "Tran",
]

ROLE_BASE_SALARY = {
    StaffRole.SALES: 240_000,
    StaffRole.MARKETING: 260_000,
    StaffRole.TECHNICIAN: 320_000,
    StaffRole.REPAIR_SPECIALIST: 450_000,
    StaffRole.PROCUREMENT: 300_000,
    StaffRole.WARRANTY_SUPPORT: 280_000,
    StaffRole.MARKET_ANALYST: 320_000,
    StaffRole.OPERATIONS: 260_000,
}

ROLE_TRAITS = {
    StaffRole.SALES: [StaffTrait.SMOOTH_TALKER, StaffTrait.HONEST_ADVISOR, StaffTrait.OVERCONFIDENT],
    StaffRole.MARKETING: [StaffTrait.SMOOTH_TALKER, StaffTrait.RGB_ADDICT, StaffTrait.MARKET_SENSE],
    StaffRole.TECHNICIAN: [StaffTrait.CAREFUL_TESTER, StaffTrait.METICULOUS, StaffTrait.FAST_HANDS],
    StaffRole.REPAIR_SPECIALIST: [StaffTrait.METICULOUS, StaffTrait.DAMAGE_CONTROL, StaffTrait.CAREFUL_TESTER],
    StaffRole.PROCUREMENT: [StaffTrait.BARGAIN_HUNTER, StaffTrait.HONEST_ADVISOR, StaffTrait.MARKET_SENSE],
    StaffRole.WARRANTY_SUPPORT: [StaffTrait.DAMAGE_CONTROL, StaffTrait.HONEST_ADVISOR, StaffTrait.METICULOUS],
    StaffRole.MARKET_ANALYST: [StaffTrait.MARKET_SENSE, StaffTrait.CAREFUL_TESTER, StaffTrait.HONEST_ADVISOR],
    StaffRole.OPERATIONS: [StaffTrait.METICULOUS, StaffTrait.FAST_HANDS, StaffTrait.HONEST_ADVISOR],
}

TASK_ROLE_WEIGHTS: dict[StaffTaskType, dict[StaffRole, int]] = {
    StaffTaskType.CUSTOMER_CONSULT: {
        StaffRole.SALES: 6,
        StaffRole.MARKETING: 5,
        StaffRole.OPERATIONS: 2,
    },
    StaffTaskType.TEST_BENCH: {
        StaffRole.TECHNICIAN: 6,
        StaffRole.REPAIR_SPECIALIST: 5,
        StaffRole.OPERATIONS: 2,
    },
    StaffTaskType.REFURBISH: {
        StaffRole.REPAIR_SPECIALIST: 6,
        StaffRole.TECHNICIAN: 5,
        StaffRole.OPERATIONS: 2,
    },
    StaffTaskType.RESALE: {
        StaffRole.SALES: 6,
        StaffRole.MARKETING: 5,
        StaffRole.MARKET_ANALYST: 3,
    },
    StaffTaskType.WARRANTY: {
        StaffRole.WARRANTY_SUPPORT: 6,
        StaffRole.SALES: 3,
        StaffRole.OPERATIONS: 2,
    },
    StaffTaskType.PROCUREMENT: {
        StaffRole.PROCUREMENT: 6,
        StaffRole.OPERATIONS: 3,
        StaffRole.MARKET_ANALYST: 2,
    },
    StaffTaskType.MARKET_ANALYSIS: {
        StaffRole.MARKET_ANALYST: 6,
        StaffRole.MARKETING: 3,
        StaffRole.OPERATIONS: 2,
    },
    StaffTaskType.OPERATIONS: {
        StaffRole.OPERATIONS: 6,
        StaffRole.TECHNICIAN: 3,
        StaffRole.WARRANTY_SUPPORT: 2,
    },
}


def list_staff(db: Session, save_game_id: int, role: StaffRole | None = None, status: StaffStatus | None = None) -> list[StaffMember]:
    get_save_game(db, save_game_id)
    query = select(StaffMember).where(StaffMember.save_game_id == save_game_id)
    if role is not None:
        query = query.where(StaffMember.role == role)
    if status is not None:
        query = query.where(StaffMember.status == status)
    query = query.order_by(StaffMember.status.asc(), StaffMember.role.asc(), StaffMember.level.desc(), StaffMember.name.asc())
    return list(db.scalars(query))


def get_staff_member(db: Session, save_game_id: int, staff_id: int) -> StaffMember:
    staff_member = db.scalar(
        select(StaffMember).where(StaffMember.save_game_id == save_game_id, StaffMember.id == staff_id)
    )
    if not staff_member:
        raise not_found("Staff member not found")
    return staff_member


def hire_staff_member(db: Session, save_game_id: int, payload: Any) -> StaffMember:
    save_game = get_save_game(db, save_game_id)
    staff_member = _build_staff_member(save_game_id, payload, save_game.game_day)
    db.add(staff_member)
    db.commit()
    db.refresh(staff_member)
    return staff_member


def fire_staff_member(db: Session, save_game_id: int, staff_id: int) -> StaffMember:
    staff_member = get_staff_member(db, save_game_id, staff_id)
    staff_member.status = StaffStatus.INACTIVE
    db.commit()
    db.refresh(staff_member)
    return staff_member


def generate_staff_candidate(db: Session, save_game_id: int, role: StaffRole | None = None, seed_offset: int = 0) -> dict[str, Any]:
    save_game = get_save_game(db, save_game_id)
    existing_names = {member.name for member in list_staff(db, save_game_id)}
    chosen_role = role or _choose_role(save_game_id)
    rng = random.Random(f"{save_game_id}:{chosen_role.value}:{len(existing_names)}:{save_game.game_day}:{seed_offset}")
    candidate = _candidate_payload(rng, save_game, chosen_role, len(existing_names))
    candidate["preview_effects"] = compute_staff_effects(_build_preview_staff(save_game_id, candidate), StaffTaskType[_task_from_role(chosen_role)])
    return candidate


def generate_staff_candidates(db: Session, save_game_id: int, count: int = 3, role: StaffRole | None = None) -> list[dict[str, Any]]:
    count = max(1, min(10, count))
    return [generate_staff_candidate(db, save_game_id, role=role, seed_offset=index) for index in range(count)]


def assign_staff_to_task(
    db: Session,
    save_game_id: int,
    staff_id: int,
    task_type: StaffTaskType,
    target_type: str | None = None,
    target_id: int | None = None,
) -> StaffAssignmentLog:
    save_game = get_save_game(db, save_game_id)
    staff_member = get_staff_member(db, save_game_id, staff_id)
    if staff_member.status == StaffStatus.INACTIVE:
        raise bad_request("Inactive staff cannot be assigned")
    if staff_member.status not in {StaffStatus.AVAILABLE, StaffStatus.RESTING}:
        raise bad_request("Staff member is not available for assignment")

    _validate_assignment_target(db, save_game_id, task_type, target_type, target_id)
    effects = compute_staff_effects(staff_member, task_type)
    result_summary = _build_result_summary(staff_member, task_type, effects, target_type, target_id)
    log = StaffAssignmentLog(
        save_game_id=save_game_id,
        staff_member_id=staff_member.id,
        task_type=task_type,
        target_type=target_type,
        target_id=target_id,
        result_summary=result_summary,
        xp_gained=effects["xp_gained"],
        fatigue_gained=effects["fatigue_gained"],
        effect_json=effects,
        assigned_on_day=save_game.game_day,
    )
    db.add(log)
    apply_staff_task_result(db, staff_member, task_type, result_summary)
    db.commit()
    db.refresh(log)
    return log


def apply_staff_task_result(db: Session, staff_member: StaffMember, task_type: StaffTaskType, effect_summary: str) -> StaffMember:
    if staff_member.status == StaffStatus.INACTIVE:
        raise bad_request("Inactive staff cannot receive task results")
    effects = compute_staff_effects(staff_member, task_type)
    gain_staff_xp(db, staff_member, int(effects["xp_gained"]))
    add_staff_fatigue(db, staff_member, int(effects["fatigue_gained"]))
    staff_member.last_assigned_on_day = staff_member.save_game.game_day if staff_member.save_game else staff_member.last_assigned_on_day
    staff_member.status = StaffStatus.AVAILABLE
    if effect_summary:
        staff_member.notes = _append_note(staff_member.notes, effect_summary)
    return staff_member


def gain_staff_xp(db: Session, staff_member: StaffMember, amount: int) -> StaffMember:
    if amount <= 0:
        return staff_member
    xp_bonus_percent = int(progression_service.get_effect_value(db, staff_member.save_game_id, "staff_xp_bonus_percent", 0) or 0)
    if xp_bonus_percent > 0:
        amount = int(round(amount * (1 + xp_bonus_percent / 100)))
    staff_member.xp += amount
    while staff_member.xp >= staff_member.level * 100:
        staff_member.xp -= staff_member.level * 100
        staff_member.level += 1
        _apply_level_up_bonus(staff_member)
    return staff_member


def add_staff_fatigue(db: Session, staff_member: StaffMember, amount: int) -> StaffMember:
    if amount <= 0:
        return staff_member
    reduction_percent = int(
        progression_service.get_effect_value(db, staff_member.save_game_id, "staff_fatigue_reduction_percent", 0) or 0
    )
    if reduction_percent > 0:
        amount = int(round(amount * max(0.0, 1 - (reduction_percent / 100))))
    staff_member.fatigue = max(0, min(100, staff_member.fatigue + amount))
    return staff_member


def compute_staff_effects(staff_member: StaffMember, task_type: StaffTaskType | str) -> dict[str, Any]:
    task = _coerce_task_type(task_type)
    relevant_skill = _relevant_skill(staff_member, task)
    role_bias = _role_bias(staff_member.role, task)
    fatigue_factor = _fatigue_factor(staff_member.fatigue)
    trait_bonus = _trait_bonus(staff_member, task)

    base_strength = (relevant_skill * 0.10) + (staff_member.level * 1.3) + (staff_member.morale * 0.03)
    base_strength = (base_strength * fatigue_factor) + role_bias + trait_bonus
    base_strength = max(2.0, min(15.0, base_strength))

    effect: dict[str, Any] = {
        "task_type": task.value,
        "staff_role": staff_member.role.value,
        "relevant_skill": relevant_skill,
        "effect_strength_percent": round(base_strength, 1),
        "xp_gained": int(round(12 + base_strength * 2)),
        "fatigue_gained": int(round(5 + base_strength * 0.9)),
        "morale_factor": staff_member.morale,
        "fatigue_factor": round(fatigue_factor, 2),
        "traits": list(staff_member.traits_json or []),
    }

    if task == StaffTaskType.CUSTOMER_CONSULT:
        effect.update(
            {
                "customer_fit_bonus": _bounded_int(base_strength + (trait_bonus * 2), 2, 15),
                "quote_acceptance_bonus": _bounded_int(base_strength / 2 + trait_bonus, 1, 10),
                "reputation_bonus": 1 if StaffTrait.HONEST_ADVISOR.value in (staff_member.traits_json or []) else 0,
            }
        )
    elif task == StaffTaskType.TEST_BENCH:
        effect.update(
            {
                "confidence_bonus": _bounded_int(base_strength + _carefulness_bonus(staff_member), 2, 20),
                "reveal_bonus": _bounded_int(base_strength + _trait_bonus_for_trait(staff_member, StaffTrait.CAREFUL_TESTER), 2, 20),
                "quality_bonus": _bounded_int(base_strength / 2, 1, 8),
            }
        )
    elif task == StaffTaskType.REFURBISH:
        effect.update(
            {
                "cost_reduction_percent": _bounded_int(base_strength + _trait_bonus_for_trait(staff_member, StaffTrait.BARGAIN_HUNTER), 1, 15),
                "health_bonus": _bounded_int(base_strength / 3, 1, 8),
                "thermal_bonus": _bounded_int(base_strength / 2, 1, 12),
                "fan_bonus": _bounded_int(base_strength / 3, 1, 8),
                "vram_bonus": _bounded_int(base_strength / 3, 1, 8),
                "stability_bonus": _bounded_int(base_strength / 3, 1, 8),
                "confidence_bonus": _bounded_int(base_strength / 2, 1, 10),
            }
        )
    elif task == StaffTaskType.RESALE:
        effect.update(
            {
                "buyer_interest_bonus": _bounded_int(base_strength + _trait_bonus_for_trait(staff_member, StaffTrait.SMOOTH_TALKER), 1, 15),
                "offer_price_bonus_percent": _bounded_int(base_strength / 2 + _trait_bonus_for_trait(staff_member, StaffTrait.MARKET_SENSE), 1, 10),
                "reputation_bonus": 1 if StaffTrait.HONEST_ADVISOR.value in (staff_member.traits_json or []) else 0,
            }
        )
    elif task == StaffTaskType.WARRANTY:
        effect.update(
            {
                "reputation_protection_bonus": _bounded_int(base_strength + _trait_bonus_for_trait(staff_member, StaffTrait.DAMAGE_CONTROL), 1, 12),
                "cost_reduction_percent": _bounded_int(base_strength / 2, 1, 10),
                "support_bonus": _bounded_int(base_strength / 2 + _trait_bonus_for_trait(staff_member, StaffTrait.HONEST_ADVISOR), 1, 12),
            }
        )
    elif task == StaffTaskType.PROCUREMENT:
        effect.update(
            {
                "supplier_cost_reduction_percent": _bounded_int(base_strength + _trait_bonus_for_trait(staff_member, StaffTrait.BARGAIN_HUNTER), 1, 15),
                "import_fee_reduction_percent": _bounded_int(base_strength / 2, 0, 10),
                "procurement_bonus": _bounded_int(base_strength / 2, 1, 10),
            }
        )
    elif task == StaffTaskType.MARKET_ANALYSIS:
        effect.update(
            {
                "market_insight_bonus": _bounded_int(base_strength + _trait_bonus_for_trait(staff_member, StaffTrait.MARKET_SENSE), 1, 15),
                "price_accuracy_bonus": _bounded_int(base_strength / 2, 1, 10),
            }
        )
    else:
        effect.update(
            {
                "efficiency_bonus": _bounded_int(base_strength / 2, 1, 10),
            }
        )

    effect["summary_hint"] = _summary_hint(staff_member, task, effect)
    return effect


def summarize_staff_state(db: Session, save_game_id: int) -> dict[str, Any]:
    get_save_game(db, save_game_id)
    staff = list_staff(db, save_game_id)
    staff_count = len(staff)
    available_count = sum(1 for member in staff if member.status == StaffStatus.AVAILABLE)
    inactive_count = sum(1 for member in staff if member.status == StaffStatus.INACTIVE)
    salary_total = sum(member.salary_per_day_vnd for member in staff if member.status != StaffStatus.INACTIVE)
    average_morale = round(sum(member.morale for member in staff) / staff_count, 1) if staff_count else 0.0
    average_fatigue = round(sum(member.fatigue for member in staff) / staff_count, 1) if staff_count else 0.0
    role_counts: dict[str, int] = {}
    role_strengths: dict[str, float] = {}
    for member in staff:
        role_counts[member.role.value] = role_counts.get(member.role.value, 0) + 1
        role_strengths[member.role.value] = role_strengths.get(member.role.value, 0.0) + _relevant_skill(member, _task_from_role_enum(member.role))
    strongest_roles = [
        role
        for role, _ in sorted(
            role_strengths.items(),
            key=lambda item: (item[1] / max(1, role_counts[item[0]]), role_counts[item[0]]),
            reverse=True,
        )[:3]
    ]
    recent_assignments = list(
        db.scalars(
            select(StaffAssignmentLog)
            .options(selectinload(StaffAssignmentLog.staff_member))
            .where(StaffAssignmentLog.save_game_id == save_game_id)
            .order_by(StaffAssignmentLog.created_at.desc())
            .limit(8)
        )
    )
    return {
        "save_game_id": save_game_id,
        "staff_count": staff_count,
        "available_staff_count": available_count,
        "inactive_staff_count": inactive_count,
        "daily_salary_total_vnd": salary_total,
        "average_morale": average_morale,
        "average_fatigue": average_fatigue,
        "role_counts": role_counts,
        "strongest_roles": strongest_roles,
        "recent_assignments": recent_assignments,
    }


def get_best_staff_for_task(db: Session, save_game_id: int, task_type: StaffTaskType) -> StaffMember | None:
    candidates = [
        member
        for member in list_staff(db, save_game_id, status=StaffStatus.AVAILABLE)
        if member.status == StaffStatus.AVAILABLE
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda member: _effect_score(member, task_type))


def list_staff_assignments(db: Session, save_game_id: int, limit: int = 20) -> list[StaffAssignmentLog]:
    get_save_game(db, save_game_id)
    query = (
        select(StaffAssignmentLog)
        .options(selectinload(StaffAssignmentLog.staff_member))
        .where(StaffAssignmentLog.save_game_id == save_game_id)
        .order_by(StaffAssignmentLog.created_at.desc())
        .limit(max(1, min(50, limit)))
    )
    return list(db.scalars(query))


def _normalize_traits(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        value = [value]
    traits: list[str] = []
    for item in value:
        if isinstance(item, StaffTrait):
            normalized = item.value
        else:
            normalized = str(item).strip().upper()
        if normalized and normalized not in traits:
            traits.append(normalized)
    return traits


def _build_staff_member(save_game_id: int, payload: Any, hired_on_day: int) -> StaffMember:
    role = payload.role if isinstance(payload.role, StaffRole) else StaffRole(payload.role)
    traits = _normalize_traits(getattr(payload, "traits_json", None))
    sales_skill = _clamp_int(getattr(payload, "sales_skill", 30))
    marketing_skill = _clamp_int(getattr(payload, "marketing_skill", 30))
    diagnostic_skill = _clamp_int(getattr(payload, "diagnostic_skill", 30))
    repair_skill = _clamp_int(getattr(payload, "repair_skill", 30))
    procurement_skill = _clamp_int(getattr(payload, "procurement_skill", 30))
    support_skill = _clamp_int(getattr(payload, "support_skill", 30))
    market_skill = _clamp_int(getattr(payload, "market_skill", 30))
    speed = _clamp_int(getattr(payload, "speed", 50))
    carefulness = _clamp_int(getattr(payload, "carefulness", 50))
    level = max(1, int(getattr(payload, "level", 1) or 1))
    morale = _clamp_int(getattr(payload, "morale", 70))
    fatigue = _clamp_int(getattr(payload, "fatigue", 0))
    main_skill = _main_skill_for_role(role, sales_skill, marketing_skill, diagnostic_skill, repair_skill, procurement_skill, support_skill, market_skill)
    salary = getattr(payload, "salary_per_day_vnd", 0) or _salary_for_staff(role, main_skill, level)

    return StaffMember(
        save_game_id=save_game_id,
        name=getattr(payload, "name"),
        role=role,
        status=StaffStatus.AVAILABLE,
        level=level,
        xp=max(0, int(getattr(payload, "xp", 0) or 0)),
        salary_per_day_vnd=int(salary),
        morale=morale,
        fatigue=fatigue,
        traits_json=traits,
        sales_skill=sales_skill,
        marketing_skill=marketing_skill,
        diagnostic_skill=diagnostic_skill,
        repair_skill=repair_skill,
        procurement_skill=procurement_skill,
        support_skill=support_skill,
        market_skill=market_skill,
        speed=speed,
        carefulness=carefulness,
        hired_on_day=hired_on_day,
        last_assigned_on_day=getattr(payload, "last_assigned_on_day", None),
        notes=getattr(payload, "notes", None),
    )


def _candidate_payload(rng: random.Random, save_game: SaveGame, role: StaffRole, offset: int) -> dict[str, Any]:
    base_skill = rng.randint(35, 75)
    secondary_skill = rng.randint(10, 50)
    tertiary_skill = rng.randint(10, 45)
    skill_profile = _candidate_skill_profile(role, base_skill, secondary_skill, tertiary_skill)
    level = rng.choice([1, 1, 1, 2])
    morale = rng.randint(60, 90)
    fatigue = 0
    speed = rng.randint(20, 80)
    carefulness = rng.randint(20, 80)
    traits = _pick_traits(role, rng)
    salary = _salary_for_staff(role, base_skill, level)
    name = _generate_name(rng, offset)
    payload = {
        "id": None,
        "save_game_id": None,
        "name": name,
        "role": role,
        "status": StaffStatus.AVAILABLE,
        "level": level,
        "xp": 0,
        "salary_per_day_vnd": salary,
        "morale": morale,
        "fatigue": fatigue,
        "traits_json": traits,
        "sales_skill": skill_profile["sales_skill"],
        "marketing_skill": skill_profile["marketing_skill"],
        "diagnostic_skill": skill_profile["diagnostic_skill"],
        "repair_skill": skill_profile["repair_skill"],
        "procurement_skill": skill_profile["procurement_skill"],
        "support_skill": skill_profile["support_skill"],
        "market_skill": skill_profile["market_skill"],
        "speed": speed,
        "carefulness": carefulness,
        "hired_on_day": None,
        "last_assigned_on_day": None,
        "notes": f"Generated for Day {save_game.game_day}.",
        "created_at": None,
        "updated_at": None,
    }
    return payload


def _build_preview_staff(save_game_id: int, payload: dict[str, Any]) -> StaffMember:
    return StaffMember(
        save_game_id=save_game_id,
        name=payload["name"],
        role=payload["role"],
        status=payload["status"],
        level=payload["level"],
        xp=payload["xp"],
        salary_per_day_vnd=payload["salary_per_day_vnd"],
        morale=payload["morale"],
        fatigue=payload["fatigue"],
        traits_json=payload["traits_json"],
        sales_skill=payload["sales_skill"],
        marketing_skill=payload["marketing_skill"],
        diagnostic_skill=payload["diagnostic_skill"],
        repair_skill=payload["repair_skill"],
        procurement_skill=payload["procurement_skill"],
        support_skill=payload["support_skill"],
        market_skill=payload["market_skill"],
        speed=payload["speed"],
        carefulness=payload["carefulness"],
        hired_on_day=None,
        last_assigned_on_day=None,
        notes=payload["notes"],
    )


def _choose_role(save_game_id: int) -> StaffRole:
    rng = random.Random(f"{save_game_id}:staff-role")
    roles = list(StaffRole)
    weights = [5, 4, 4, 4, 3, 3, 3, 4]
    return rng.choices(roles, weights=weights, k=1)[0]


def _task_from_role(role: StaffRole) -> str:
    mapping = {
        StaffRole.SALES: "CUSTOMER_CONSULT",
        StaffRole.MARKETING: "RESALE",
        StaffRole.TECHNICIAN: "TEST_BENCH",
        StaffRole.REPAIR_SPECIALIST: "REFURBISH",
        StaffRole.PROCUREMENT: "PROCUREMENT",
        StaffRole.WARRANTY_SUPPORT: "WARRANTY",
        StaffRole.MARKET_ANALYST: "MARKET_ANALYSIS",
        StaffRole.OPERATIONS: "OPERATIONS",
    }
    return mapping[role]


def _task_from_role_enum(role: StaffRole) -> StaffTaskType:
    return StaffTaskType[_task_from_role(role)]


def _candidate_skill_profile(role: StaffRole, main_skill: int, secondary_skill: int, tertiary_skill: int) -> dict[str, int]:
    profile = {
        "sales_skill": secondary_skill,
        "marketing_skill": secondary_skill,
        "diagnostic_skill": secondary_skill,
        "repair_skill": secondary_skill,
        "procurement_skill": secondary_skill,
        "support_skill": secondary_skill,
        "market_skill": secondary_skill,
    }
    if role == StaffRole.SALES:
        profile["sales_skill"] = main_skill
        profile["marketing_skill"] = tertiary_skill
        profile["support_skill"] = tertiary_skill
    elif role == StaffRole.MARKETING:
        profile["marketing_skill"] = main_skill
        profile["market_skill"] = tertiary_skill
        profile["sales_skill"] = tertiary_skill
    elif role == StaffRole.TECHNICIAN:
        profile["diagnostic_skill"] = main_skill
        profile["repair_skill"] = secondary_skill + 5
        profile["market_skill"] = tertiary_skill
    elif role == StaffRole.REPAIR_SPECIALIST:
        profile["repair_skill"] = main_skill
        profile["diagnostic_skill"] = secondary_skill + 5
        profile["support_skill"] = tertiary_skill
    elif role == StaffRole.PROCUREMENT:
        profile["procurement_skill"] = main_skill
        profile["market_skill"] = secondary_skill + 5
        profile["sales_skill"] = tertiary_skill
    elif role == StaffRole.WARRANTY_SUPPORT:
        profile["support_skill"] = main_skill
        profile["diagnostic_skill"] = secondary_skill + 5
        profile["sales_skill"] = tertiary_skill
    elif role == StaffRole.MARKET_ANALYST:
        profile["market_skill"] = main_skill
        profile["procurement_skill"] = secondary_skill + 5
        profile["marketing_skill"] = tertiary_skill
    else:
        profile["sales_skill"] = secondary_skill + 5
        profile["marketing_skill"] = secondary_skill + 5
        profile["support_skill"] = secondary_skill + 5
    return {key: _clamp_int(value) for key, value in profile.items()}


def _pick_traits(role: StaffRole, rng: random.Random) -> list[str]:
    pool = list(ROLE_TRAITS[role])
    pool.extend([trait for trait in StaffTrait if trait not in pool])
    count = rng.choice([1, 1, 2])
    traits = []
    while pool and len(traits) < count:
        choice = rng.choice(pool)
        if choice.value not in traits:
            traits.append(choice.value)
        pool = [trait for trait in pool if trait != choice]
    return traits


def _generate_name(rng: random.Random, offset: int) -> str:
    first = FIRST_NAMES[(rng.randint(0, len(FIRST_NAMES) - 1) + offset) % len(FIRST_NAMES)]
    last = LAST_NAMES[(rng.randint(0, len(LAST_NAMES) - 1) + offset * 2) % len(LAST_NAMES)]
    return f"{first} {last}"


def _salary_for_staff(role: StaffRole, main_skill: int, level: int) -> int:
    base = ROLE_BASE_SALARY[role]
    salary = base + (main_skill * 2_500) + ((level - 1) * 60_000)
    return max(150_000, min(1_200_000, int(salary)))


def _main_skill_for_role(
    role: StaffRole,
    sales_skill: int,
    marketing_skill: int,
    diagnostic_skill: int,
    repair_skill: int,
    procurement_skill: int,
    support_skill: int,
    market_skill: int,
) -> int:
    mapping = {
        StaffRole.SALES: sales_skill,
        StaffRole.MARKETING: marketing_skill,
        StaffRole.TECHNICIAN: diagnostic_skill,
        StaffRole.REPAIR_SPECIALIST: repair_skill,
        StaffRole.PROCUREMENT: procurement_skill,
        StaffRole.WARRANTY_SUPPORT: support_skill,
        StaffRole.MARKET_ANALYST: market_skill,
        StaffRole.OPERATIONS: max(sales_skill, marketing_skill, diagnostic_skill, repair_skill, procurement_skill, support_skill, market_skill),
    }
    return _clamp_int(mapping[role])


def _relevant_skill(staff_member: StaffMember, task_type: StaffTaskType) -> int:
    mapping = {
        StaffTaskType.CUSTOMER_CONSULT: staff_member.sales_skill,
        StaffTaskType.TEST_BENCH: max(staff_member.diagnostic_skill, staff_member.repair_skill),
        StaffTaskType.REFURBISH: staff_member.repair_skill,
        StaffTaskType.RESALE: max(staff_member.sales_skill, staff_member.marketing_skill, staff_member.market_skill),
        StaffTaskType.WARRANTY: staff_member.support_skill,
        StaffTaskType.PROCUREMENT: staff_member.procurement_skill,
        StaffTaskType.MARKET_ANALYSIS: staff_member.market_skill,
        StaffTaskType.OPERATIONS: max(
            staff_member.sales_skill,
            staff_member.marketing_skill,
            staff_member.diagnostic_skill,
            staff_member.repair_skill,
            staff_member.procurement_skill,
            staff_member.support_skill,
            staff_member.market_skill,
        ),
    }
    return _clamp_int(mapping[task_type])


def _role_bias(role: StaffRole, task_type: StaffTaskType) -> float:
    return TASK_ROLE_WEIGHTS.get(task_type, {}).get(role, 0) * 0.55


def _fatigue_factor(fatigue: int) -> float:
    if fatigue <= 40:
        return 1.0
    if fatigue <= 70:
        return 0.88
    return 0.72


def _trait_bonus(staff_member: StaffMember, task_type: StaffTaskType) -> float:
    total = 0.0
    traits = set(staff_member.traits_json or [])
    if StaffTrait.METICULOUS.value in traits:
        total += 1.0 if task_type in {StaffTaskType.TEST_BENCH, StaffTaskType.REFURBISH, StaffTaskType.WARRANTY} else 0.4
    if StaffTrait.FAST_HANDS.value in traits:
        total += 0.8
    if StaffTrait.SMOOTH_TALKER.value in traits and task_type in {StaffTaskType.CUSTOMER_CONSULT, StaffTaskType.RESALE}:
        total += 1.6
    if StaffTrait.BARGAIN_HUNTER.value in traits and task_type in {StaffTaskType.PROCUREMENT, StaffTaskType.REFURBISH}:
        total += 1.8
    if StaffTrait.HONEST_ADVISOR.value in traits and task_type in {StaffTaskType.CUSTOMER_CONSULT, StaffTaskType.WARRANTY, StaffTaskType.RESALE}:
        total += 1.0
    if StaffTrait.OVERCONFIDENT.value in traits:
        total -= 0.6
    if StaffTrait.CAREFUL_TESTER.value in traits and task_type in {StaffTaskType.TEST_BENCH, StaffTaskType.MARKET_ANALYSIS}:
        total += 1.4
    if StaffTrait.RGB_ADDICT.value in traits and task_type in {StaffTaskType.RESALE, StaffTaskType.CUSTOMER_CONSULT}:
        total += 0.6
    if StaffTrait.DAMAGE_CONTROL.value in traits and task_type == StaffTaskType.WARRANTY:
        total += 1.8
    if StaffTrait.MARKET_SENSE.value in traits and task_type in {StaffTaskType.RESALE, StaffTaskType.MARKET_ANALYSIS, StaffTaskType.PROCUREMENT}:
        total += 1.5
    return total


def _trait_bonus_for_trait(staff_member: StaffMember, trait: StaffTrait) -> float:
    return 1.4 if trait.value in (staff_member.traits_json or []) else 0.0


def _carefulness_bonus(staff_member: StaffMember) -> float:
    return staff_member.carefulness / 20.0


def _summary_hint(staff_member: StaffMember, task: StaffTaskType, effect: dict[str, Any]) -> str:
    if task == StaffTaskType.REFURBISH:
        return f"{staff_member.name} improved refurbish efficiency by {effect.get('effect_strength_percent', 0)}%."
    if task == StaffTaskType.RESALE:
        return f"{staff_member.name} boosted resale momentum by {effect.get('effect_strength_percent', 0)}%."
    if task == StaffTaskType.TEST_BENCH:
        return f"{staff_member.name} sharpened diagnostics by {effect.get('effect_strength_percent', 0)}%."
    if task == StaffTaskType.WARRANTY:
        return f"{staff_member.name} reduced warranty friction by {effect.get('effect_strength_percent', 0)}%."
    return f"{staff_member.name} handled {task.value.lower().replace('_', ' ')} with steady focus."


def _build_result_summary(
    staff_member: StaffMember,
    task_type: StaffTaskType,
    effects: dict[str, Any],
    target_type: str | None,
    target_id: int | None,
) -> str:
    target_text = f" on {target_type}#{target_id}" if target_type and target_id is not None else ""
    if task_type == StaffTaskType.REFURBISH:
        return (
            f"{staff_member.name} completed refurbish support{target_text} "
            f"(cost -{effects.get('cost_reduction_percent', 0)}%, confidence +{effects.get('confidence_bonus', 0)})."
        )
    if task_type == StaffTaskType.RESALE:
        return (
            f"{staff_member.name} supported resale{target_text} "
            f"(interest +{effects.get('buyer_interest_bonus', 0)}, offer +{effects.get('offer_price_bonus_percent', 0)}%)."
        )
    if task_type == StaffTaskType.TEST_BENCH:
        return (
            f"{staff_member.name} assisted test bench{target_text} "
            f"(confidence +{effects.get('confidence_bonus', 0)}, reveal +{effects.get('reveal_bonus', 0)})."
        )
    if task_type == StaffTaskType.WARRANTY:
        return (
            f"{staff_member.name} assisted warranty review{target_text} "
            f"(support +{effects.get('support_bonus', 0)}, reputation protection +{effects.get('reputation_protection_bonus', 0)})."
        )
    if task_type == StaffTaskType.PROCUREMENT:
        return (
            f"{staff_member.name} helped procurement{target_text} "
            f"(supplier cost -{effects.get('supplier_cost_reduction_percent', 0)}%)."
        )
    if task_type == StaffTaskType.MARKET_ANALYSIS:
        return f"{staff_member.name} delivered market analysis{target_text} (insight +{effects.get('market_insight_bonus', 0)})."
    if task_type == StaffTaskType.CUSTOMER_CONSULT:
        return f"{staff_member.name} led customer consult{target_text} (fit +{effects.get('customer_fit_bonus', 0)})."
    return f"{staff_member.name} completed {task_type.value.lower().replace('_', ' ')}{target_text}."


def _effect_score(staff_member: StaffMember, task_type: StaffTaskType) -> float:
    effects = compute_staff_effects(staff_member, task_type)
    return float(effects.get("effect_strength_percent", 0)) + float(effects.get("xp_gained", 0)) / 10.0


def _validate_assignment_target(
    db: Session,
    save_game_id: int,
    task_type: StaffTaskType,
    target_type: str | None,
    target_id: int | None,
) -> None:
    if not target_type or target_id is None:
        return
    normalized = target_type.strip().lower()
    if normalized == "inventory_unit":
        target = db.scalar(select(InventoryUnit).where(InventoryUnit.save_game_id == save_game_id, InventoryUnit.id == target_id))
        if not target:
            raise not_found("Inventory unit not found")
        return
    if normalized == "resale_listing":
        target = db.scalar(select(ResaleListing).where(ResaleListing.save_game_id == save_game_id, ResaleListing.id == target_id))
        if not target:
            raise not_found("Resale listing not found")
        return
    if normalized == "order":
        target = db.scalar(select(Order).where(Order.save_game_id == save_game_id, Order.id == target_id))
        if not target:
            raise not_found("Order not found")
        return
    if normalized == "purchase_order":
        target = db.scalar(select(PurchaseOrder).where(PurchaseOrder.save_game_id == save_game_id, PurchaseOrder.id == target_id))
        if not target:
            raise not_found("Purchase order not found")


def _append_note(existing: str | None, addition: str) -> str:
    if not existing:
        return addition
    return f"{existing}\n{addition}"


def _apply_level_up_bonus(staff_member: StaffMember) -> None:
    if staff_member.role == StaffRole.SALES:
        staff_member.sales_skill = _clamp_int(staff_member.sales_skill + 1)
        staff_member.speed = _clamp_int(staff_member.speed + 1)
    elif staff_member.role == StaffRole.MARKETING:
        staff_member.marketing_skill = _clamp_int(staff_member.marketing_skill + 1)
        staff_member.market_skill = _clamp_int(staff_member.market_skill + 1)
    elif staff_member.role == StaffRole.TECHNICIAN:
        staff_member.diagnostic_skill = _clamp_int(staff_member.diagnostic_skill + 1)
        staff_member.carefulness = _clamp_int(staff_member.carefulness + 1)
    elif staff_member.role == StaffRole.REPAIR_SPECIALIST:
        staff_member.repair_skill = _clamp_int(staff_member.repair_skill + 1)
        staff_member.diagnostic_skill = _clamp_int(staff_member.diagnostic_skill + 1)
    elif staff_member.role == StaffRole.PROCUREMENT:
        staff_member.procurement_skill = _clamp_int(staff_member.procurement_skill + 1)
        staff_member.market_skill = _clamp_int(staff_member.market_skill + 1)
    elif staff_member.role == StaffRole.WARRANTY_SUPPORT:
        staff_member.support_skill = _clamp_int(staff_member.support_skill + 1)
        staff_member.carefulness = _clamp_int(staff_member.carefulness + 1)
    elif staff_member.role == StaffRole.MARKET_ANALYST:
        staff_member.market_skill = _clamp_int(staff_member.market_skill + 1)
        staff_member.carefulness = _clamp_int(staff_member.carefulness + 1)
    else:
        staff_member.speed = _clamp_int(staff_member.speed + 1)
        staff_member.carefulness = _clamp_int(staff_member.carefulness + 1)
    staff_member.morale = _clamp_int(staff_member.morale + 1, low=0, high=100)


def _clamp_int(value: int | float, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, int(round(value))))


def _bounded_int(value: int | float, low: int = 0, high: int = 100) -> int:
    return _clamp_int(value, low, high)


def _coerce_task_type(task_type: StaffTaskType | str) -> StaffTaskType:
    if isinstance(task_type, StaffTaskType):
        return task_type
    return StaffTaskType[str(task_type)]
