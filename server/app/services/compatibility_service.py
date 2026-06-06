from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.models.entities import HardwareProduct, InventoryUnit, Order, OrderItem, Quote, QuoteItem
from app.models.enums import ConditionType, Grade, HardwareCategory


WARNING_PENALTIES = {
    "INFO": 3,
    "WARNING": 12,
    "CRITICAL": 35,
}

MOTHERBOARD_ALIASES = {"MOTHERBOARD", "MAINBOARD"}
COOLING_ALIASES = {"COOLER", "WATER_COOLING"}
RAM_MEMORY_RE = re.compile(r"\bDDR(?:3|4|5)\b", re.IGNORECASE)
CPU_SOCKET_RE = re.compile(r"\b(AM5|AM4|LGA2011-3|LGA1851|LGA1700|LGA1200|LGA1151|LGA1150|LGA1155)\b", re.IGNORECASE)
FORM_FACTOR_RE = re.compile(r"\b(E-ATX|EATX|ATX|M-ATX|MICRO-ATX|MATX|MINI-ITX|ITX)\b", re.IGNORECASE)
STORAGE_INTERFACE_RE = re.compile(r"\b(NVME|NVMe|M\.2|M2|SATA)\b", re.IGNORECASE)


@dataclass
class ComponentSummary:
    product_id: int | None
    inventory_unit_id: int | None
    name: str
    category: str
    quantity: int
    condition_type: str | None
    grade: str | None
    inspection_confidence: int | None
    power_watts: int
    performance_score: int
    heat_score: int
    socket_slot: str | None
    memory_type: str | None
    form_factor: str | None
    cooler_type: str | None
    psu_watts: int | None
    source: str
    ready_for_resale: bool | None
    repair_risk_score: int | None


@dataclass
class CompatibilityWarning:
    severity: str
    code: str
    message: str
    affected_categories: list[str]


def evaluate_build_compatibility(db: Session, items_or_products: Iterable[Any]) -> dict[str, Any]:
    components = extract_component_summary(items_or_products)
    warnings, suggestions = _build_warnings_and_suggestions(components)
    compatibility_score = _compatibility_score(components, warnings)
    power_headroom_score = compute_power_score(components)
    thermal_score = compute_thermal_score(components)
    bottleneck_score = compute_bottleneck_score(components)
    used_risk_score = _used_risk_score(components)
    build_quality_score_estimate = _build_quality_score(
        compatibility_score=compatibility_score,
        power_headroom_score=power_headroom_score,
        thermal_score=thermal_score,
        bottleneck_score=bottleneck_score,
        used_risk_score=used_risk_score,
    )
    warranty_risk_delta = compute_warranty_risk_delta(components, warnings)
    result = {
        "compatibility_score": compatibility_score,
        "power_headroom_score": power_headroom_score,
        "thermal_score": thermal_score,
        "bottleneck_score": bottleneck_score,
        "build_quality_score_estimate": build_quality_score_estimate,
        "warranty_risk_delta": warranty_risk_delta,
        "blocking_issues": [warning for warning in warnings if warning["severity"] == "CRITICAL"],
        "warnings": warnings,
        "suggestions": suggestions,
        "component_summary": components,
    }
    return serialize_compatibility_result(result)


def evaluate_quote_compatibility(db: Session, quote: Quote) -> dict[str, Any]:
    result = evaluate_build_compatibility(db, quote.items)
    apply_compatibility_snapshot(quote, result)
    return result


def evaluate_order_compatibility(db: Session, order: Order) -> dict[str, Any]:
    result = evaluate_build_compatibility(db, order.items)
    apply_compatibility_snapshot(order, result)
    return result


def extract_component_summary(items_or_products: Iterable[Any]) -> list[dict[str, Any]]:
    components: list[ComponentSummary] = []
    for item in items_or_products or []:
        components.append(_normalize_component(item))
    return [asdict(component) for component in components]


def compute_socket_memory_score(components: list[dict[str, Any]]) -> int:
    context = _build_context(components)
    score = 100

    cpu = context["cpu"]
    motherboard = context["motherboard"]
    if cpu and motherboard:
        cpu_socket = _normalize_socket(cpu.get("socket_slot"))
        board_socket = _normalize_socket(motherboard.get("socket_slot"))
        if cpu_socket and board_socket:
            if not _socket_matches(cpu_socket, board_socket):
                score -= 48
        elif cpu_socket or board_socket:
            score -= 4

    ram_modules = context["ram_modules"]
    if ram_modules and motherboard:
        board_memory = _normalize_memory_type(motherboard.get("memory_type"), motherboard.get("socket_slot"))
        for ram in ram_modules:
            ram_memory = _normalize_memory_type(ram.get("memory_type"), ram.get("socket_slot"), ram.get("name"))
            if ram_memory and board_memory:
                if ram_memory != board_memory:
                    score -= 45
                    break
            elif ram_memory or board_memory:
                score -= 4
                break

    if context["storage_modules"] and motherboard:
        motherboard_storage = _board_storage_support(motherboard)
        for storage in context["storage_modules"]:
            interface = _storage_interface(storage)
            if interface and motherboard_storage and interface not in motherboard_storage:
                score -= 10
                break

    if context["case"] and motherboard:
        case_rank = _form_factor_rank(_case_support_form_factor(context["case"]))
        board_rank = _form_factor_rank(_board_form_factor(motherboard))
        if case_rank and board_rank and board_rank > case_rank:
            score -= 20

    return _clamp(score)


def compute_power_score(components: list[dict[str, Any]]) -> int:
    context = _build_context(components)
    load_watts = context["estimated_load_watts"]
    psu_watts = context["psu_watts"]
    recommended_psu = context["recommended_psu_watts"]

    if load_watts <= 0:
        return 100

    if psu_watts is None:
        return 45

    if psu_watts < load_watts:
        ratio = psu_watts / max(load_watts, 1)
        return _clamp(20 + round(ratio * 30))

    if psu_watts < recommended_psu:
        span = max(recommended_psu - load_watts, 1)
        ratio = (psu_watts - load_watts) / span
        return _clamp(60 + round(ratio * 20))

    headroom_ratio = (psu_watts - recommended_psu) / max(recommended_psu, 1)
    return _clamp(88 + min(12, round(headroom_ratio * 10)))


def compute_thermal_score(components: list[dict[str, Any]]) -> int:
    context = _build_context(components)
    heat = context["estimated_heat_score"]
    cooling = context["cooling_capacity"]
    cpu = context["cpu"]
    gpu = context["gpu"]
    score = 100

    pressure = max(0, heat - cooling - 150)
    score -= min(55, pressure // 2)

    if cooling <= 0 and (cpu or gpu):
        score -= 18

    if cpu and cpu.get("power_watts", 0) >= 105 and cooling < 25:
        score -= 10
    if gpu and gpu.get("power_watts", 0) >= 220 and cooling < 30:
        score -= 10

    if any(component.get("cooler_type") == "WATER" for component in context["coolers"]):
        score += 8
    elif cooling >= 35:
        score += 5
    elif cooling >= 20:
        score += 2

    return _clamp(score)


def compute_bottleneck_score(components: list[dict[str, Any]]) -> int:
    context = _build_context(components)
    cpu_perf = context["cpu_performance"]
    gpu_perf = context["gpu_performance"]

    if cpu_perf is None and gpu_perf is None:
        return 100
    if cpu_perf is None or gpu_perf is None:
        return 85

    strongest = max(cpu_perf, gpu_perf, 1)
    weakest = min(cpu_perf, gpu_perf)
    ratio = weakest / strongest

    if ratio >= 0.85:
        return 100
    if ratio >= 0.70:
        return 90
    if ratio >= 0.55:
        return 80
    if ratio >= 0.40:
        return 65
    if ratio >= 0.28:
        return 52
    return 40


def compute_warranty_risk_delta(components: list[dict[str, Any]], warnings: list[dict[str, Any]]) -> int:
    context = _build_context(components)
    risk = 0
    for warning in warnings:
        severity = warning.get("severity", "INFO")
        risk += {"CRITICAL": 12, "WARNING": 5, "INFO": 1}.get(severity, 1)

    risk += context["used_risk_points"]

    compatibility_score = _compatibility_score(components, warnings)
    power_score = compute_power_score(components)
    thermal_score = compute_thermal_score(components)
    bottleneck_score = compute_bottleneck_score(components)
    build_quality = _build_quality_score(
        compatibility_score=compatibility_score,
        power_headroom_score=power_score,
        thermal_score=thermal_score,
        bottleneck_score=bottleneck_score,
        used_risk_score=_used_risk_score(components),
    )

    if build_quality >= 90:
        risk -= 2
    elif build_quality >= 80:
        risk -= 1

    return int(max(-8, min(60, risk)))


def serialize_compatibility_result(result: dict[str, Any]) -> dict[str, Any]:
    return _serialize_any(result)


def apply_compatibility_snapshot(target: Any, result: dict[str, Any]) -> Any:
    setattr(target, "compatibility_score", result.get("compatibility_score"))
    setattr(target, "power_headroom_score", result.get("power_headroom_score"))
    setattr(target, "thermal_score", result.get("thermal_score"))
    setattr(target, "bottleneck_score", result.get("bottleneck_score"))
    setattr(target, "build_quality_score_estimate", result.get("build_quality_score_estimate"))
    setattr(target, "warranty_risk_delta", result.get("warranty_risk_delta"))
    setattr(target, "compatibility_warnings_json", result.get("warnings", []))
    setattr(target, "compatibility_result", result)
    return target


def _normalize_component(item: Any) -> ComponentSummary:
    product, inventory_unit, quantity = _extract_product_and_unit(item)
    specs = product.specs_json or {}
    real_specs = product.real_specs_json or {}
    game_balance = product.game_balance_json or {}
    category = _normalize_category(product.category.value if hasattr(product.category, "value") else str(product.category))
    socket_slot = _clean_text(_spec_value_from_sources(product, ("socket_slot", "socket")))
    if not socket_slot:
        socket_slot = _socket_hint_from_text(product.name)
    memory_type = _normalize_memory_type(
        _spec_value_from_sources(product, ("memory_type", "ram_type")),
        socket_slot,
        product.name,
    )
    form_factor = _normalize_form_factor(
        _spec_value_from_sources(product, ("form_factor", "form_factor_support", "size")),
        product.name,
        socket_slot,
    )
    cooler_type = _normalize_cooler_type(
        _spec_value_from_sources(product, ("cooler_type", "cooling_type")),
        product.name,
    )
    psu_watts = _parse_int(
        _spec_value_from_sources(product, ("power_watts", "watts", "wattage")),
    )
    if psu_watts is None and category == "PSU":
        psu_watts = product.base_power_watts

    component = ComponentSummary(
        product_id=product.id,
        inventory_unit_id=inventory_unit.id if inventory_unit else None,
        name=product.name,
        category=category,
        quantity=max(1, quantity),
        condition_type=inventory_unit.condition_type.value if inventory_unit and hasattr(inventory_unit.condition_type, "value") else (inventory_unit.condition_type if inventory_unit else None),
        grade=inventory_unit.grade.value if inventory_unit and hasattr(inventory_unit.grade, "value") else (inventory_unit.grade if inventory_unit else None),
        inspection_confidence=inventory_unit.inspection_confidence if inventory_unit else None,
        power_watts=_component_power_watts(product, category),
        performance_score=_component_performance_score(product),
        heat_score=_component_heat_score(product),
        socket_slot=socket_slot,
        memory_type=memory_type,
        form_factor=form_factor,
        cooler_type=cooler_type,
        psu_watts=psu_watts,
        source=_component_source(product, inventory_unit),
        ready_for_resale=inventory_unit.ready_for_resale if inventory_unit else None,
        repair_risk_score=inventory_unit.repair_risk_score if inventory_unit else None,
    )
    return component


def _extract_product_and_unit(item: Any) -> tuple[HardwareProduct, InventoryUnit | None, int]:
    if isinstance(item, QuoteItem) or isinstance(item, OrderItem):
        return item.product, item.inventory_unit, item.quantity
    if isinstance(item, InventoryUnit):
        return item.product, item, 1
    if isinstance(item, HardwareProduct):
        return item, None, 1
    if isinstance(item, dict):
        product = item.get("product")
        inventory_unit = item.get("inventory_unit")
        quantity = int(item.get("quantity", 1) or 1)
        if isinstance(product, HardwareProduct):
            return product, inventory_unit if isinstance(inventory_unit, InventoryUnit) else None, quantity
    raise TypeError(f"Unsupported component payload: {type(item)!r}")


def _component_power_watts(product: HardwareProduct, category: str) -> int:
    power = _parse_int(_spec_value_from_sources(product, ("power_watts", "watts", "wattage", "tdp")))
    if power is not None:
        return max(0, power)
    defaults = {
        "CPU": 95,
        "GPU": 220,
        "RAM": 5,
        "STORAGE": 5,
        "PSU": product.base_power_watts,
        "MOTHERBOARD": 40,
        "CASE": 5,
        "COOLER": 10,
        "WATER_COOLING": 12,
    }
    return defaults.get(category, max(0, product.base_power_watts))


def _component_performance_score(product: HardwareProduct) -> int:
    score = _parse_int(_spec_value_from_sources(product, ("performance_score", "perf_score")))
    return score if score is not None else product.base_performance_score


def _component_heat_score(product: HardwareProduct) -> int:
    score = _parse_int(_spec_value_from_sources(product, ("heat_score",)))
    return score if score is not None else product.base_heat_score


def _component_source(product: HardwareProduct, inventory_unit: InventoryUnit | None) -> str:
    if inventory_unit:
        return f"inventory:{inventory_unit.condition_type.value if hasattr(inventory_unit.condition_type, 'value') else inventory_unit.condition_type}"
    return "catalog"


def _build_context(components: list[dict[str, Any]]) -> dict[str, Any]:
    grouped = {
        "cpu": None,
        "gpu": None,
        "motherboard": None,
        "psu": None,
        "case": None,
        "ram_modules": [],
        "coolers": [],
        "storage_modules": [],
    }
    estimated_load_watts = 0
    estimated_heat_score = 0
    cooling_capacity = 0
    psu_watts = None
    cpu_performance = None
    gpu_performance = None
    total_used_risk = 0

    for component in components:
        category = component.get("category")
        quantity = max(1, int(component.get("quantity") or 1))
        if category == "CPU" and grouped["cpu"] is None:
            grouped["cpu"] = component
        elif category == "GPU" and grouped["gpu"] is None:
            grouped["gpu"] = component
        elif category == "MOTHERBOARD" and grouped["motherboard"] is None:
            grouped["motherboard"] = component
        elif category == "PSU" and grouped["psu"] is None:
            grouped["psu"] = component
        elif category == "CASE" and grouped["case"] is None:
            grouped["case"] = component
        elif category == "RAM":
            grouped["ram_modules"].append(component)
        elif category in COOLING_ALIASES:
            grouped["coolers"].append(component)
        elif category in {"SSD", "STORAGE"}:
            grouped["storage_modules"].append(component)

        if category != "PSU":
            estimated_load_watts += int(component.get("power_watts") or 0) * quantity
            estimated_heat_score += int(component.get("heat_score") or 0) * quantity

        if category in COOLING_ALIASES:
            cooling_capacity += _cooling_capacity(component) * quantity
        elif category == "CASE":
            cooling_capacity += 5

        if category == "PSU":
            psu_watts = _parse_int(component.get("psu_watts")) or _parse_int(component.get("power_watts"))

        if category == "CPU" and cpu_performance is None:
            cpu_performance = int(component.get("performance_score") or 0)
        if category == "GPU" and gpu_performance is None:
            gpu_performance = int(component.get("performance_score") or 0)

        total_used_risk += _inventory_risk_points(component)

    recommended_psu_watts = int(estimated_load_watts * 1.35 + 100) if estimated_load_watts > 0 else 0
    return {
        "components": components,
        "cpu": grouped["cpu"],
        "gpu": grouped["gpu"],
        "motherboard": grouped["motherboard"],
        "psu": grouped["psu"],
        "case": grouped["case"],
        "ram_modules": grouped["ram_modules"],
        "coolers": grouped["coolers"],
        "storage_modules": grouped["storage_modules"],
        "estimated_load_watts": estimated_load_watts,
        "estimated_heat_score": estimated_heat_score,
        "cooling_capacity": cooling_capacity,
        "recommended_psu_watts": recommended_psu_watts,
        "psu_watts": psu_watts,
        "cpu_performance": cpu_performance,
        "gpu_performance": gpu_performance,
        "used_risk_points": total_used_risk,
    }


def _build_warnings_and_suggestions(components: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    context = _build_context(components)
    warnings: list[CompatibilityWarning] = []
    suggestions: list[str] = []

    cpu = context["cpu"]
    motherboard = context["motherboard"]
    ram_modules = context["ram_modules"]
    psu = context["psu"]
    case = context["case"]
    cpu_perf = context["cpu_performance"]
    gpu_perf = context["gpu_performance"]
    load_watts = context["estimated_load_watts"]
    recommended_psu = context["recommended_psu_watts"]
    psu_watts = context["psu_watts"]
    cooling_capacity = context["cooling_capacity"]
    heat = context["estimated_heat_score"]

    if not any(component["category"] == "CPU" for component in components):
        _add_warning(warnings, "INFO", "CPU_MISSING", "No CPU was supplied, so the compatibility check is incomplete.", ["CPU"])
    if not motherboard:
        _add_warning(warnings, "INFO", "MOTHERBOARD_MISSING", "No motherboard was supplied, so socket and memory checks are incomplete.", ["MOTHERBOARD"])

    if cpu and motherboard:
        cpu_socket = _normalize_socket(cpu.get("socket_slot"))
        board_socket = _normalize_socket(motherboard.get("socket_slot"))
        if cpu_socket and board_socket:
            if not _socket_matches(cpu_socket, board_socket):
                _add_warning(
                    warnings,
                    "CRITICAL",
                    "CPU_BOARD_SOCKET_MISMATCH",
                    f"CPU socket {cpu_socket} does not match motherboard socket {board_socket}.",
                    ["CPU", "MOTHERBOARD"],
                )
                suggestions.append("Swap the motherboard or CPU so both parts share a matching socket.")
        else:
            _add_warning(
                warnings,
                "INFO",
                "CPU_BOARD_SOCKET_UNKNOWN",
                "CPU or motherboard socket information is missing, so the socket check is only partial.",
                ["CPU", "MOTHERBOARD"],
            )

    if ram_modules and motherboard:
        board_memory = _normalize_memory_type(motherboard.get("memory_type"), motherboard.get("socket_slot"), motherboard.get("name"))
        for ram in ram_modules:
            ram_memory = _normalize_memory_type(ram.get("memory_type"), ram.get("socket_slot"), ram.get("name"))
            if ram_memory and board_memory:
                if ram_memory != board_memory:
                    _add_warning(
                        warnings,
                        "CRITICAL",
                        "RAM_BOARD_MEMORY_MISMATCH",
                        f"RAM type {ram_memory} does not match motherboard memory type {board_memory}.",
                        ["RAM", "MOTHERBOARD"],
                    )
                    suggestions.append("Choose RAM and a motherboard that both use the same DDR generation.")
                    break
            else:
                _add_warning(
                    warnings,
                    "INFO",
                    "RAM_BOARD_MEMORY_UNKNOWN",
                    "RAM or motherboard memory type is missing, so the memory check is partial.",
                    ["RAM", "MOTHERBOARD"],
                )
                break

    if psu_watts is None:
        if load_watts > 0:
            _add_warning(
                warnings,
                "WARNING",
                "PSU_MISSING",
                "No PSU was supplied for a powered build.",
                ["PSU"],
            )
            suggestions.append("Add a PSU that clears the estimated system load with comfortable headroom.")
    elif load_watts > 0:
        if psu_watts < load_watts:
            _add_warning(
                warnings,
                "CRITICAL",
                "PSU_INSUFFICIENT",
                f"PSU capacity {psu_watts}W is below the estimated load of {load_watts}W.",
                ["PSU", "CPU", "GPU"],
            )
            suggestions.append("Upgrade to a higher-wattage PSU before building this system.")
        elif psu_watts < recommended_psu:
            _add_warning(
                warnings,
                "WARNING",
                "PSU_HEADROOM_LOW",
                f"PSU capacity {psu_watts}W is below the recommended {recommended_psu}W headroom target.",
                ["PSU", "CPU", "GPU"],
            )
            suggestions.append("A slightly stronger PSU would make this build feel safer and more stable.")

    gpu = context["gpu"]
    if (cpu or gpu) and cooling_capacity <= 0 and heat > 120:
        _add_warning(
            warnings,
            "WARNING",
            "COOLING_MISSING",
            "The build has meaningful heat output but no obvious cooler to absorb it.",
            ["CPU", "GPU", "COOLER"],
        )
        suggestions.append("Add a stronger air cooler or an AIO if you want lower thermal risk.")
    elif heat > 0 and cooling_capacity < max(18, heat // 8):
        severity = "CRITICAL" if heat >= 240 and cooling_capacity < 15 else "WARNING"
        _add_warning(
            warnings,
            severity,
            "THERMAL_INSUFFICIENT",
            "Cooling capacity looks light for the overall heat load.",
            ["CPU", "GPU", "COOLER"],
        )
        suggestions.append("Use a stronger cooler or a case with better airflow.")

    if cpu_perf is not None and gpu_perf is not None:
        strongest = max(cpu_perf, gpu_perf, 1)
        weakest = min(cpu_perf, gpu_perf)
        ratio = weakest / strongest
        if ratio < 0.4:
            _add_warning(
                warnings,
                "WARNING",
                "BOTTLE_NECK_SEVERE",
                "CPU and GPU performance are far apart, so one side will likely bottleneck the other.",
                ["CPU", "GPU"],
            )
            if cpu_perf < gpu_perf:
                suggestions.append("A stronger CPU would balance the GPU better.")
            else:
                suggestions.append("A stronger GPU would keep the CPU from overfeeding the frame rate.")
        elif ratio < 0.65:
            _add_warning(
                warnings,
                "INFO",
                "BOTTLE_NECK_MODERATE",
                "CPU and GPU performance are a little uneven, but the build is still workable.",
                ["CPU", "GPU"],
            )

    if case and motherboard:
        board_form = _form_factor_rank(_board_form_factor(motherboard))
        case_form = _form_factor_rank(_case_support_form_factor(case))
        if board_form and case_form and board_form > case_form:
            _add_warning(
                warnings,
                "WARNING",
                "CASE_FORM_FACTOR_MISMATCH",
                "The motherboard form factor looks larger than the case support.",
                ["CASE", "MOTHERBOARD"],
            )
            suggestions.append("Pick a larger case or a smaller motherboard form factor.")

    for storage in context["storage_modules"]:
        interface = _storage_interface(storage)
        if interface and motherboard:
            board_support = _board_storage_support(motherboard)
            if board_support and interface not in board_support:
                _add_warning(
                    warnings,
                    "INFO",
                    "STORAGE_INTERFACE_LIMITED",
                    f"Storage interface {interface} may not be fully supported by the motherboard.",
                    ["STORAGE", "MOTHERBOARD"],
                )
                suggestions.append("Check the motherboard's storage interface support before finalizing the build.")
                break

    used_risk_points = context["used_risk_points"]
    if used_risk_points > 0:
        severity = "WARNING" if used_risk_points >= 8 else "INFO"
        risky_names = ", ".join(component["name"] for component in components if _inventory_risk_points(component) > 0)
        _add_warning(
            warnings,
            severity,
            "USED_PART_RISK",
            f"Used or refurbished parts increase warranty risk: {risky_names}.",
            [component["category"] for component in components if _inventory_risk_points(component) > 0][:3] or ["INVENTORY"],
        )
        suggestions.append("If this is a customer-facing build, prefer cleaner or better-tested inventory units.")

    if not warnings:
        _add_warning(
            warnings,
            "INFO",
            "BUILD_OK",
            "No obvious compatibility issues were detected.",
            [component["category"] for component in components[:1]] if components else [],
        )

    return [asdict(warning) for warning in warnings], _dedupe_preserve_order(suggestions)


def _compatibility_score(components: list[dict[str, Any]], warnings: list[dict[str, Any]]) -> int:
    socket_memory_score = compute_socket_memory_score(components)
    warning_score = 100
    for warning in warnings:
        warning_score -= WARNING_PENALTIES.get(warning.get("severity", "INFO"), 3)
    return _clamp(round((socket_memory_score + warning_score) / 2))


def _build_quality_score(
    *,
    compatibility_score: int,
    power_headroom_score: int,
    thermal_score: int,
    bottleneck_score: int,
    used_risk_score: int,
) -> int:
    return _clamp(
        round(
            compatibility_score * 0.40
            + power_headroom_score * 0.20
            + thermal_score * 0.20
            + bottleneck_score * 0.10
            + used_risk_score * 0.10
        )
    )


def _used_risk_score(components: list[dict[str, Any]]) -> int:
    risk = 0
    for component in components:
        risk += _inventory_risk_points(component)
    return _clamp(100 - min(75, risk * 4))


def _inventory_risk_points(component: dict[str, Any]) -> int:
    points = 0
    condition = component.get("condition_type")
    grade = component.get("grade")
    confidence = component.get("inspection_confidence")
    repair_risk = component.get("repair_risk_score")
    ready = component.get("ready_for_resale")

    if condition == ConditionType.USED.value:
        points += 4
    elif condition == ConditionType.REFURBISHED.value:
        points += 2
    elif condition in {ConditionType.DEFECTIVE.value, ConditionType.FOR_PARTS.value}:
        points += 12

    if grade in {Grade.D.value, Grade.F.value, Grade.UNKNOWN.value}:
        points += 3 if grade == Grade.D.value else 5

    if confidence is not None:
        if confidence < 20:
            points += 8
        elif confidence < 40:
            points += 4

    if repair_risk is not None:
        if repair_risk >= 85:
            points += 8
        elif repair_risk >= 70:
            points += 4

    return points


def _cooling_capacity(component: dict[str, Any]) -> int:
    cooler_type = (component.get("cooler_type") or "").upper()
    name = (component.get("name") or "").upper()
    heat = int(component.get("heat_score") or 0)
    power = int(component.get("power_watts") or 0)
    radiator_match = re.search(r"(\d{2,3})\s*MM", name)
    radiator_mm = int(radiator_match.group(1)) if radiator_match else 0

    if "WATER" in cooler_type or "AIO" in name or radiator_mm >= 240:
        return 45 + (10 if radiator_mm >= 240 else 0)
    if "AIR" in cooler_type:
        return 30 + max(0, 12 - heat // 6)
    if "WATER" in name or "LIQUID" in name:
        return 42
    if power <= 6 and heat <= 40:
        return 26
    return 20


def _clamp(value: int, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, int(value)))


def _normalize_category(value: str) -> str:
    normalized = value.upper().replace(" ", "_")
    if normalized in MOTHERBOARD_ALIASES:
        return "MOTHERBOARD"
    if normalized == "SSD":
        return "STORAGE"
    if normalized in COOLING_ALIASES:
        return normalized
    return normalized


def _normalize_socket(value: Any) -> str | None:
    text = _clean_text(value)
    if not text:
        return None
    match = CPU_SOCKET_RE.search(text)
    if match:
        return match.group(1).upper()
    if "X99" in text or "2011-3" in text:
        return "LGA2011-3"
    return text


def _normalize_memory_type(value: Any, socket_slot: Any = None, name: Any = None) -> str | None:
    for source in (value, socket_slot, name):
        text = _clean_text(source)
        if not text:
            continue
        match = RAM_MEMORY_RE.search(text)
        if match:
            return match.group(0).upper()
    return None


def _normalize_form_factor(value: Any, name: Any = None, socket_slot: Any = None) -> str | None:
    for source in (value, name, socket_slot):
        text = _clean_text(source)
        if not text:
            continue
        match = FORM_FACTOR_RE.search(text)
        if match:
            token = match.group(1).upper()
            return "M-ATX" if token in {"M-ATX", "MATX", "MICRO-ATX"} else ("E-ATX" if token in {"E-ATX", "EATX"} else token)
    return None


def _normalize_cooler_type(value: Any, name: Any = None) -> str | None:
    text = _clean_text(value) or _clean_text(name)
    if not text:
        return None
    if "AIO" in text or "WATER" in text or "LIQUID" in text:
        return "WATER"
    if "AIR" in text:
        return "AIR"
    return None


def _board_form_factor(component: dict[str, Any]) -> str | None:
    return _normalize_form_factor(component.get("form_factor"), component.get("name"), component.get("socket_slot"))


def _case_support_form_factor(component: dict[str, Any]) -> str | None:
    return _normalize_form_factor(component.get("form_factor"), component.get("name"), component.get("socket_slot"))


def _board_storage_support(component: dict[str, Any]) -> set[str]:
    support: set[str] = set()
    text = " ".join(
        _clean_text(value) or ""
        for value in (
            component.get("socket_slot"),
            component.get("name"),
            component.get("form_factor"),
        )
    ).upper()
    if "M.2" in text or "M2" in text or "NVME" in text:
        support.add("NVME")
        support.add("M.2")
    if "SATA" in text:
        support.add("SATA")
    return support


def _storage_interface(component: dict[str, Any]) -> str | None:
    for source in (component.get("socket_slot"), component.get("name"), component.get("form_factor")):
        text = _clean_text(source)
        if not text:
            continue
        match = STORAGE_INTERFACE_RE.search(text)
        if match:
            return match.group(1).upper().replace(".", "")
    return None


def _form_factor_rank(value: str | None) -> int:
    if not value:
        return 0
    normalized = value.upper().replace(" ", "")
    return {
        "MINI-ITX": 1,
        "ITX": 1,
        "M-ATX": 2,
        "MATX": 2,
        "MICRO-ATX": 2,
        "ATX": 3,
        "E-ATX": 4,
        "EATX": 4,
    }.get(normalized, 0)


def _socket_matches(cpu_socket: str, board_socket: str) -> bool:
    cpu_socket = cpu_socket.upper()
    board_socket = board_socket.upper()
    if cpu_socket == board_socket:
        return True
    if cpu_socket.startswith("LGA") and cpu_socket in board_socket:
        return True
    if board_socket.startswith("LGA") and board_socket in cpu_socket:
        return True
    if cpu_socket in {"AM4", "AM5"} and cpu_socket in board_socket:
        return True
    if cpu_socket == "LGA2011-3" and ("X99" in board_socket or "2011-3" in board_socket):
        return True
    return False


def _spec_value_from_sources(product: HardwareProduct, keys: tuple[str, ...]) -> Any:
    for source in (product.real_specs_json, product.specs_json, product.game_balance_json):
        if not isinstance(source, dict):
            continue
        for key in keys:
            value = source.get(key)
            if value not in (None, "", [], {}):
                return value
    return None


def _parse_int(value: Any) -> int | None:
    if value in (None, "", False):
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    match = re.search(r"-?\d+", text.replace(",", ""))
    if not match:
        return None
    return int(match.group(0))


def _first_text(*values: Any) -> str | None:
    for value in values:
        text = _clean_text(value)
        if text:
            return text
    return None


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return str(value).strip() or None


def _socket_hint_from_text(value: Any) -> str | None:
    text = _clean_text(value)
    if not text:
        return None
    match = CPU_SOCKET_RE.search(text)
    if match:
        return match.group(1).upper()
    if "X99" in text.upper() or "2011-3" in text:
        return "LGA2011-3"
    return None


def _add_warning(warnings: list[CompatibilityWarning], severity: str, code: str, message: str, affected_categories: list[str]) -> None:
    warning = CompatibilityWarning(
        severity=severity,
        code=code,
        message=message,
        affected_categories=[category for category in _dedupe_preserve_order(affected_categories) if category],
    )
    if any(existing.code == warning.code and existing.message == warning.message for existing in warnings):
        return
    warnings.append(warning)


def _dedupe_preserve_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen or value is None:
            continue
        seen.add(value)
        result.append(value)
    return result


def _serialize_any(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _serialize_any(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_serialize_any(item) for item in value]
    if isinstance(value, tuple):
        return [_serialize_any(item) for item in value]
    if hasattr(value, "__dataclass_fields__"):
        return _serialize_any(asdict(value))
    if hasattr(value, "value") and not isinstance(value, (str, bytes)):
        return value.value
    return value
