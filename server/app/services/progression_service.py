from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import bad_request, not_found
from app.models.entities import InventoryUnit, PurchasedShopUpgrade, SaveGame
from app.models.enums import ShopUpgradeCategory, ShopUpgradeStatus
from app.services.save_game_service import get_save_game


UPGRADE_DEFINITIONS: list[dict[str, Any]] = [
    {
        "key": "STORAGE_RACK_I",
        "title": "Storage Rack I",
        "description": "Expand the showroom back room with better shelving for more inventory.",
        "category": ShopUpgradeCategory.STORAGE,
        "level": 1,
        "max_level": 1,
        "cost_vnd": 2_000_000,
        "required_shop_level": 1,
        "required_upgrade_keys": [],
        "effects_json": {"inventory_capacity_bonus": 20},
        "icon": "boxes",
    },
    {
        "key": "STORAGE_RACK_II",
        "title": "Storage Rack II",
        "description": "A heavier-duty rack layout for serious inventory scaling.",
        "category": ShopUpgradeCategory.STORAGE,
        "level": 2,
        "max_level": 1,
        "cost_vnd": 6_000_000,
        "required_shop_level": 2,
        "required_upgrade_keys": ["STORAGE_RACK_I"],
        "effects_json": {"inventory_capacity_bonus": 40},
        "icon": "warehouse",
    },
    {
        "key": "BASIC_DIAGNOSTIC_KIT",
        "title": "Basic Diagnostic Kit",
        "description": "Improve the baseline confidence of your test bench inspections.",
        "category": ShopUpgradeCategory.TEST_BENCH,
        "level": 1,
        "max_level": 1,
        "cost_vnd": 1_500_000,
        "required_shop_level": 1,
        "required_upgrade_keys": [],
        "effects_json": {"test_confidence_bonus": 10},
        "icon": "microscope",
    },
    {
        "key": "ADVANCED_TEST_BENCH",
        "title": "Advanced Test Bench",
        "description": "Unlock stronger diagnostics and better hidden defect detection.",
        "category": ShopUpgradeCategory.TEST_BENCH,
        "level": 2,
        "max_level": 1,
        "cost_vnd": 8_000_000,
        "required_shop_level": 2,
        "required_upgrade_keys": ["BASIC_DIAGNOSTIC_KIT"],
        "effects_json": {"test_confidence_bonus": 20, "hidden_defect_reveal_bonus": 10},
        "icon": "scanner",
    },
    {
        "key": "REFURBISH_TOOLKIT_I",
        "title": "Refurbish Toolkit I",
        "description": "Cut down basic repair spend with a better workbench layout.",
        "category": ShopUpgradeCategory.REFURBISH,
        "level": 1,
        "max_level": 1,
        "cost_vnd": 2_500_000,
        "required_shop_level": 1,
        "required_upgrade_keys": [],
        "effects_json": {"refurbish_cost_reduction_percent": 5},
        "icon": "wrench",
    },
    {
        "key": "REFURBISH_TOOLKIT_II",
        "title": "Refurbish Toolkit II",
        "description": "Higher-grade refurbish gear for stronger results and lower waste.",
        "category": ShopUpgradeCategory.REFURBISH,
        "level": 2,
        "max_level": 1,
        "cost_vnd": 7_500_000,
        "required_shop_level": 2,
        "required_upgrade_keys": ["REFURBISH_TOOLKIT_I"],
        "effects_json": {"refurbish_cost_reduction_percent": 10, "refurbish_success_bonus": 5},
        "icon": "toolcase",
    },
    {
        "key": "SUPPLIER_RELATIONSHIP_I",
        "title": "Supplier Relationship I",
        "description": "A small relationship program that nudges import fees down.",
        "category": ShopUpgradeCategory.SUPPLIER,
        "level": 1,
        "max_level": 1,
        "cost_vnd": 3_000_000,
        "required_shop_level": 1,
        "required_upgrade_keys": [],
        "effects_json": {"supplier_import_fee_reduction_percent": 3},
        "icon": "handshake",
    },
    {
        "key": "SUPPLIER_RELATIONSHIP_II",
        "title": "Supplier Relationship II",
        "description": "Better vendor trust trims shipping delays and import overhead.",
        "category": ShopUpgradeCategory.SUPPLIER,
        "level": 2,
        "max_level": 1,
        "cost_vnd": 9_000_000,
        "required_shop_level": 2,
        "required_upgrade_keys": ["SUPPLIER_RELATIONSHIP_I"],
        "effects_json": {"supplier_import_fee_reduction_percent": 6, "delivery_days_reduction": 1},
        "icon": "truck",
    },
    {
        "key": "RESELLER_MARKETING_I",
        "title": "Reseller Marketing I",
        "description": "Basic listing promotion to make buyers pay a little more attention.",
        "category": ShopUpgradeCategory.RESALE,
        "level": 1,
        "max_level": 1,
        "cost_vnd": 2_000_000,
        "required_shop_level": 1,
        "required_upgrade_keys": [],
        "effects_json": {"resale_buyer_interest_bonus": 10},
        "icon": "megaphone",
    },
    {
        "key": "RESELLER_MARKETING_II",
        "title": "Reseller Marketing II",
        "description": "Sharper copy and more visible listings improve buyer offers.",
        "category": ShopUpgradeCategory.RESALE,
        "level": 2,
        "max_level": 1,
        "cost_vnd": 7_000_000,
        "required_shop_level": 2,
        "required_upgrade_keys": ["RESELLER_MARKETING_I"],
        "effects_json": {"resale_buyer_interest_bonus": 20, "offer_price_bonus_percent": 3},
        "icon": "badge-dollar-sign",
    },
    {
        "key": "WARRANTY_QA_CHECKLIST",
        "title": "Warranty QA Checklist",
        "description": "A tighter review checklist lowers warranty exposure on outbound builds.",
        "category": ShopUpgradeCategory.WARRANTY,
        "level": 1,
        "max_level": 1,
        "cost_vnd": 2_500_000,
        "required_shop_level": 1,
        "required_upgrade_keys": [],
        "effects_json": {"warranty_risk_reduction_percent": 5},
        "icon": "shield-check",
    },
    {
        "key": "WARRANTY_STRESS_PROTOCOL",
        "title": "Warranty Stress Protocol",
        "description": "Deeper QA procedures help cut warranty risk further.",
        "category": ShopUpgradeCategory.WARRANTY,
        "level": 2,
        "max_level": 1,
        "cost_vnd": 8_500_000,
        "required_shop_level": 2,
        "required_upgrade_keys": ["WARRANTY_QA_CHECKLIST"],
        "effects_json": {"warranty_risk_reduction_percent": 10},
        "icon": "shield",
    },
    {
        "key": "STAFF_TRAINING_PROGRAM_I",
        "title": "Staff Training Program I",
        "description": "Basic team training improves learning speed and reduces burnout.",
        "category": ShopUpgradeCategory.STAFF,
        "level": 1,
        "max_level": 1,
        "cost_vnd": 3_500_000,
        "required_shop_level": 1,
        "required_upgrade_keys": [],
        "effects_json": {"staff_xp_bonus_percent": 10, "staff_fatigue_reduction_percent": 5},
        "icon": "graduation-cap",
    },
    {
        "key": "STAFF_TRAINING_PROGRAM_II",
        "title": "Staff Training Program II",
        "description": "Advanced onboarding and coaching raise staff performance further.",
        "category": ShopUpgradeCategory.STAFF,
        "level": 2,
        "max_level": 1,
        "cost_vnd": 10_000_000,
        "required_shop_level": 2,
        "required_upgrade_keys": ["STAFF_TRAINING_PROGRAM_I"],
        "effects_json": {"staff_xp_bonus_percent": 20, "staff_fatigue_reduction_percent": 10},
        "icon": "person-standing",
    },
    {
        "key": "CUSTOMER_SHOWROOM_DECOR",
        "title": "Customer Showroom Decor",
        "description": "Improve the showroom vibe so customers arrive with slightly bigger budgets.",
        "category": ShopUpgradeCategory.CUSTOMER,
        "level": 1,
        "max_level": 1,
        "cost_vnd": 4_000_000,
        "required_shop_level": 1,
        "required_upgrade_keys": [],
        "effects_json": {"customer_budget_bonus_percent": 3, "reputation_gain_bonus": 1},
        "icon": "sparkles",
    },
    {
        "key": "MARKET_ANALYTICS_TERMINAL",
        "title": "Market Analytics Terminal",
        "description": "Surface market pressure and price trends with a cleaner ops dashboard.",
        "category": ShopUpgradeCategory.MARKET,
        "level": 2,
        "max_level": 1,
        "cost_vnd": 5_000_000,
        "required_shop_level": 2,
        "required_upgrade_keys": [],
        "effects_json": {"market_event_visibility_bonus": 1, "price_estimate_accuracy_bonus": 10},
        "icon": "chart-column",
    },
    {
        "key": "OPERATIONS_BOARD",
        "title": "Operations Board",
        "description": "A dashboard board that makes the whole shop easier to scan at a glance.",
        "category": ShopUpgradeCategory.OPERATIONS,
        "level": 1,
        "max_level": 1,
        "cost_vnd": 1_500_000,
        "required_shop_level": 1,
        "required_upgrade_keys": [],
        "effects_json": {"dashboard_summary_bonus": True},
        "icon": "clipboard-list",
    },
    {
        "key": "SHOP_LEVEL_2_LICENSE",
        "title": "Shop Level 2 License",
        "description": "Unlock the next tier of showroom upgrades and shop growth.",
        "category": ShopUpgradeCategory.OPERATIONS,
        "level": 2,
        "max_level": 1,
        "cost_vnd": 10_000_000,
        "required_shop_level": 1,
        "required_upgrade_keys": [],
        "effects_json": {"unlock_shop_level": 2},
        "icon": "badge",
    },
]

UPGRADE_BY_KEY = {definition["key"]: definition for definition in UPGRADE_DEFINITIONS}
EFFECT_KEYS = (
    "inventory_capacity_bonus",
    "test_confidence_bonus",
    "hidden_defect_reveal_bonus",
    "refurbish_cost_reduction_percent",
    "refurbish_success_bonus",
    "supplier_import_fee_reduction_percent",
    "delivery_days_reduction",
    "resale_buyer_interest_bonus",
    "offer_price_bonus_percent",
    "warranty_risk_reduction_percent",
    "staff_xp_bonus_percent",
    "staff_fatigue_reduction_percent",
    "customer_budget_bonus_percent",
    "reputation_gain_bonus",
    "market_event_visibility_bonus",
    "price_estimate_accuracy_bonus",
    "dashboard_summary_bonus",
    "unlock_shop_level",
)


def list_upgrade_definitions() -> list[dict[str, Any]]:
    return [_definition_payload(definition, status=ShopUpgradeStatus.AVAILABLE) for definition in UPGRADE_DEFINITIONS]


def list_save_upgrades(db: Session, save_game_id: int) -> list[PurchasedShopUpgrade]:
    get_save_game(db, save_game_id)
    return list(
        db.scalars(
            select(PurchasedShopUpgrade)
            .where(PurchasedShopUpgrade.save_game_id == save_game_id)
            .order_by(PurchasedShopUpgrade.created_at.desc())
        )
    )


def list_progression_upgrades(db: Session, save_game_id: int) -> list[dict[str, Any]]:
    save_game = get_save_game(db, save_game_id)
    purchased_by_key = _purchased_records(db, save_game_id)
    return [
        _definition_payload(definition, *_upgrade_status(save_game, definition, purchased_by_key))
        for definition in UPGRADE_DEFINITIONS
    ]


def get_progression_state(db: Session, save_game_id: int) -> dict[str, Any]:
    save_game = get_save_game(db, save_game_id)
    purchased = list_save_upgrades(db, save_game_id)
    purchased_by_key = {record.upgrade_key: record for record in purchased}
    effects = get_upgrade_effects(db, save_game_id)
    inventory_capacity_summary = _inventory_capacity_summary(db, save_game_id, effects)

    available_upgrades: list[dict[str, Any]] = []
    locked_upgrades: list[dict[str, Any]] = []
    purchased_upgrades: list[dict[str, Any]] = []
    for definition in UPGRADE_DEFINITIONS:
        status, locked_reason = _upgrade_status(save_game, definition, purchased_by_key)
        payload = _definition_payload(definition, status=status, locked_reason=locked_reason)
        if status == ShopUpgradeStatus.LOCKED:
            locked_upgrades.append(payload)
        elif status == ShopUpgradeStatus.PURCHASED:
            purchased_upgrades.append(payload)
        else:
            available_upgrades.append(payload)

    summary = summarize_progression(db, save_game_id)
    return {
        "shop_level": save_game.shop_level,
        "shop_xp": save_game.shop_xp,
        "cash": save_game.cash,
        "purchased_upgrades": purchased,
        "available_upgrades": available_upgrades,
        "locked_upgrades": locked_upgrades,
        "upgrade_effect_summary": effects,
        "summary": summary,
        "inventory_capacity_summary": inventory_capacity_summary,
    }


def purchase_upgrade(db: Session, save_game_id: int, upgrade_key: str) -> dict[str, Any]:
    save_game = get_save_game(db, save_game_id)
    definition = UPGRADE_BY_KEY.get(upgrade_key)
    if not definition:
        raise not_found("Upgrade definition not found")

    purchased = db.scalar(
        select(PurchasedShopUpgrade).where(
            PurchasedShopUpgrade.save_game_id == save_game_id,
            PurchasedShopUpgrade.upgrade_key == upgrade_key,
        )
    )
    current_level = purchased.level if purchased else 0
    if current_level >= definition["max_level"]:
        raise bad_request("Upgrade is already fully purchased")

    _, locked_reason = _upgrade_status(save_game, definition, _purchased_records(db, save_game_id))
    if locked_reason:
        raise bad_request(locked_reason)

    cost = int(definition["cost_vnd"])
    if save_game.cash < cost:
        raise bad_request("Not enough cash to purchase this upgrade")

    save_game.cash -= cost
    now = datetime.now(timezone.utc)
    if purchased:
        purchased.level += 1
        purchased.cost_paid_vnd += cost
        purchased.updated_at = now
    else:
        purchased = PurchasedShopUpgrade(
            save_game_id=save_game_id,
            upgrade_key=upgrade_key,
            level=1,
            purchased_on_day=save_game.game_day,
            cost_paid_vnd=cost,
        )
        db.add(purchased)

    unlock_level = int(definition["effects_json"].get("unlock_shop_level", 0) or 0)
    if unlock_level:
        save_game.shop_level = max(save_game.shop_level, unlock_level)

    db.commit()
    db.refresh(save_game)
    db.refresh(purchased)
    return {
        "cash_delta": -cost,
        "upgrade": purchased,
        "progression": get_progression_state(db, save_game_id),
    }


def has_upgrade(db: Session, save_game_id: int, upgrade_key: str) -> bool:
    return (
        db.scalar(
            select(func.count())
            .select_from(PurchasedShopUpgrade)
            .where(PurchasedShopUpgrade.save_game_id == save_game_id, PurchasedShopUpgrade.upgrade_key == upgrade_key)
        )
        or 0
    ) > 0


def get_upgrade_effects(db: Session, save_game_id: int) -> dict[str, Any]:
    if db is None:
        return {effect_key: False if effect_key == "dashboard_summary_bonus" else 0 for effect_key in EFFECT_KEYS}
    get_save_game(db, save_game_id)
    purchased = list_save_upgrades(db, save_game_id)
    effects: dict[str, Any] = {effect_key: False if effect_key == "dashboard_summary_bonus" else 0 for effect_key in EFFECT_KEYS}
    for record in purchased:
        definition = UPGRADE_BY_KEY.get(record.upgrade_key)
        if not definition:
            continue
        for effect_key, effect_value in definition["effects_json"].items():
            if isinstance(effect_value, bool):
                effects[effect_key] = bool(effects.get(effect_key, False) or effect_value)
            else:
                effects[effect_key] = int(effects.get(effect_key, 0) or 0) + int(effect_value)
    return effects


def get_effect_value(db: Session, save_game_id: int, effect_key: str, default: Any = 0) -> Any:
    if db is None:
        return default
    return get_upgrade_effects(db, save_game_id).get(effect_key, default)


def summarize_progression(db: Session, save_game_id: int) -> dict[str, Any]:
    save_game = get_save_game(db, save_game_id)
    effects = get_upgrade_effects(db, save_game_id)
    inventory_count = db.scalar(
        select(func.count())
        .select_from(InventoryUnit)
        .where(InventoryUnit.save_game_id == save_game_id)
    ) or 0
    inventory_capacity = 50 + int(effects.get("inventory_capacity_bonus", 0) or 0)
    purchased_count = db.scalar(
        select(func.count())
        .select_from(PurchasedShopUpgrade)
        .where(PurchasedShopUpgrade.save_game_id == save_game_id)
    ) or 0
    available = []
    locked = []
    for definition in UPGRADE_DEFINITIONS:
        status, locked_reason = _upgrade_status(save_game, definition, _purchased_records(db, save_game_id))
        if status == ShopUpgradeStatus.LOCKED:
            locked.append(definition)
        elif status == ShopUpgradeStatus.AVAILABLE:
            available.append(definition)
    next_recommended = min(available, key=lambda item: item["cost_vnd"], default=None)
    return {
        "shop_level": save_game.shop_level,
        "shop_xp": save_game.shop_xp,
        "cash": save_game.cash,
        "purchased_upgrades_count": int(purchased_count),
        "available_upgrades_count": len(available),
        "locked_upgrades_count": len(locked),
        "inventory_count": int(inventory_count),
        "inventory_capacity": int(inventory_capacity),
        "inventory_headroom": max(0, int(inventory_capacity) - int(inventory_count)),
        "next_recommended_upgrade": next_recommended["key"] if next_recommended else None,
        "next_recommended_upgrade_title": next_recommended["title"] if next_recommended else None,
        "dashboard_summary_bonus": bool(effects.get("dashboard_summary_bonus", False)),
    }


def _purchased_records(db: Session, save_game_id: int) -> dict[str, PurchasedShopUpgrade]:
    return {
        record.upgrade_key: record
        for record in list_save_upgrades(db, save_game_id)
    }


def _upgrade_status(
    save_game: SaveGame,
    definition: dict[str, Any],
    purchased_by_key: dict[str, PurchasedShopUpgrade],
) -> tuple[ShopUpgradeStatus, str | None]:
    purchased = purchased_by_key.get(definition["key"])
    current_level = purchased.level if purchased else 0
    if current_level >= definition["max_level"]:
        return ShopUpgradeStatus.PURCHASED, None

    if save_game.shop_level < int(definition["required_shop_level"] or 1):
        return ShopUpgradeStatus.LOCKED, f"Requires shop level {definition['required_shop_level']}."

    missing_requirements = [key for key in definition["required_upgrade_keys"] if key not in purchased_by_key]
    if missing_requirements:
        missing_titles = [UPGRADE_BY_KEY[key]["title"] if key in UPGRADE_BY_KEY else key for key in missing_requirements]
        return ShopUpgradeStatus.LOCKED, "Requires " + ", ".join(missing_titles) + "."

    return ShopUpgradeStatus.AVAILABLE, None


def _definition_payload(
    definition: dict[str, Any],
    status: ShopUpgradeStatus,
    locked_reason: str | None = None,
) -> dict[str, Any]:
    requirements = []
    if definition["required_shop_level"] > 1:
        requirements.append(f"Shop level {definition['required_shop_level']}")
    for key in definition["required_upgrade_keys"]:
        requirements.append(UPGRADE_BY_KEY[key]["title"] if key in UPGRADE_BY_KEY else key)
    return {
        "key": definition["key"],
        "title": definition["title"],
        "description": definition["description"],
        "category": definition["category"],
        "level": definition["level"],
        "max_level": definition["max_level"],
        "cost_vnd": definition["cost_vnd"],
        "required_shop_level": definition["required_shop_level"],
        "required_upgrade_keys": list(definition["required_upgrade_keys"]),
        "requirements": requirements,
        "status": status,
        "locked_reason": locked_reason,
        "effects_json": dict(definition["effects_json"]),
        "icon": definition.get("icon"),
    }


def _inventory_capacity_summary(db: Session, save_game_id: int, effects: dict[str, Any]) -> dict[str, int]:
    inventory_count = db.scalar(
        select(func.count())
        .select_from(InventoryUnit)
        .where(InventoryUnit.save_game_id == save_game_id)
    ) or 0
    capacity = 50 + int(effects.get("inventory_capacity_bonus", 0) or 0)
    return {
        "base_capacity": 50,
        "bonus_capacity": int(effects.get("inventory_capacity_bonus", 0) or 0),
        "total_capacity": capacity,
        "current_inventory": int(inventory_count),
        "remaining_capacity": max(0, capacity - int(inventory_count)),
    }
