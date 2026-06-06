from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from brand_data import ALLOWED_ORIGIN_CODES, imports_dir
except ModuleNotFoundError:
    from scripts.brand_data import ALLOWED_ORIGIN_CODES, imports_dir

PRODUCT_JSON_CANDIDATES = (
    "hardware_products.normalized.json",
    "silicon_hustle_hardware_products_normalized.json",
    "hardware_products_v2_normalized.json",
    "silicon_hustle_hardware_products_v2_normalized.json",
)
PRODUCT_CSV_CANDIDATES = ("hardware_products.normalized.csv", "silicon_hustle_hardware_products_normalized.csv")

ALLOWED_CATEGORIES = {"CPU", "GPU", "MOTHERBOARD", "RAM", "STORAGE", "SSD", "PSU", "CASE", "COOLER", "WATER_COOLING", "MONITOR", "OTHER"}
ALLOWED_DATA_CONFIDENCE = {"OFFICIAL", "RETAILER", "COMMUNITY_DATABASE", "MANUAL", "ESTIMATED"}
GAME_BALANCE_KEYS = {
    "base_performance_score",
    "base_power_watts",
    "base_heat_score",
    "base_reliability_score",
    "used_demand_score",
    "mining_popularity_score",
    "depreciation_rate",
}
PRICING_KEYS = {"msrp_vnd", "base_local_price_vnd", "base_used_price_vnd", "supplier_cost_vnd"}


@dataclass
class ProductValidationResult:
    products: list[dict[str, Any]]
    path: Path | None
    warnings: list[str]
    errors: list[str]
    categories: Counter[str]


def resolve_product_json() -> Path | None:
    base = imports_dir()
    for name in PRODUCT_JSON_CANDIDATES:
        path = base / name
        if path.exists():
            return path
    return None


def load_product_json(path: str | Path | None = None) -> tuple[list[dict[str, Any]], Path | None, list[str]]:
    errors: list[str] = []
    resolved_path: Path | None = None

    if path:
        p = Path(path)
        # Try direct path
        if p.exists():
            resolved_path = p.resolve()
        else:
            # Try relative to imports_dir()
            p_imports = imports_dir() / path
            if p_imports.exists():
                resolved_path = p_imports.resolve()
            else:
                # Try relative to server directory
                p_server = Path(__file__).resolve().parents[1] / path
                if p_server.exists():
                    resolved_path = p_server.resolve()
    else:
        resolved_path = resolve_product_json()

    if not resolved_path or not resolved_path.exists():
        return [], None, [f"Missing hardware product JSON at: {path or 'default candidates'}"]

    try:
        data = json.loads(resolved_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        return [], resolved_path, [f"Invalid JSON: {exc}"]
    if not isinstance(data, dict) or not isinstance(data.get("products"), list):
        return [], resolved_path, ["Top-level JSON must contain a products array."]
    products = [item for item in data["products"] if isinstance(item, dict)]
    if len(products) != len(data["products"]):
        errors.append("Products array contains non-object rows.")
    return products, resolved_path, errors


def validate_products(known_brand_slugs: set[str], path: str | Path | None = None) -> ProductValidationResult:
    products, resolved_path, errors = load_product_json(path)
    warnings: list[str] = []
    categories: Counter[str] = Counter()
    slugs: list[str] = []
    for index, product in enumerate(products, start=1):
        label = product.get("slug") or f"row {index}"
        slug = clean(product.get("slug"))
        if not slug:
            errors.append(f"{label}: missing slug")
        else:
            slugs.append(slug)
        for field in ("name", "brand_slug", "category", "real_specs", "game_balance"):
            if product.get(field) in (None, "", {}):
                errors.append(f"{label}: missing required field {field}")
        brand_slug = clean(product.get("brand_slug"))
        if brand_slug and brand_slug not in known_brand_slugs:
            errors.append(f"{label}: unknown brand_slug {brand_slug}")
        chip_vendor_slug = clean(product.get("chip_vendor_slug"))
        if chip_vendor_slug and chip_vendor_slug not in known_brand_slugs:
            errors.append(f"{label}: unknown chip_vendor_slug {chip_vendor_slug}")
        category = normalize_category(product.get("category"))
        if category not in ALLOWED_CATEGORIES:
            errors.append(f"{label}: invalid category {product.get('category')}")
        else:
            categories[category] += 1
        origin_code = clean(product.get("origin_code"))
        if origin_code and origin_code.upper() not in ALLOWED_ORIGIN_CODES:
            errors.append(f"{label}: unknown origin_code {origin_code}")
        confidence = clean(product.get("data_confidence"))
        if confidence and confidence.upper() not in ALLOWED_DATA_CONFIDENCE:
            errors.append(f"{label}: invalid data_confidence {confidence}")
        validate_game_balance(product.get("game_balance"), label, errors)
        validate_pricing(product.get("pricing") or {}, label, errors, warnings)
        real_specs = product.get("real_specs") or {}
        if int_or_none(real_specs.get("power_watts")) is not None and int(real_specs["power_watts"]) < 0:
            errors.append(f"{label}: real_specs.power_watts must be non-negative")
        image_url = clean(product.get("image_url"))
        if image_url and (image_url.startswith("http://") or image_url.startswith("https://")):
            errors.append(f"{label}: image_url must be null or local path")
        if not image_url:
            warnings.append(f"{label}: image_url missing")
        if not clean(product.get("source_url")):
            warnings.append(f"{label}: source_url missing")
        if product.get("release_year") is None:
            warnings.append(f"{label}: release_year missing")
        if confidence and confidence.upper() == "MANUAL":
            warnings.append(f"{label}: manually curated row")
    duplicates = sorted({slug for slug in slugs if slugs.count(slug) > 1})
    for slug in duplicates:
        errors.append(f"Duplicate product slug: {slug}")
    return ProductValidationResult(products=products, path=resolved_path, warnings=warnings, errors=errors, categories=categories)


def validate_game_balance(value: Any, label: str, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{label}: game_balance must be an object")
        return
    missing = GAME_BALANCE_KEYS - set(value)
    for key in sorted(missing):
        errors.append(f"{label}: game_balance missing {key}")
    for key in GAME_BALANCE_KEYS:
        number = int_or_none(value.get(key))
        if number is None:
            errors.append(f"{label}: game_balance.{key} must be an integer")
        elif number < 0 or (key != "base_power_watts" and number > 100):
            errors.append(f"{label}: game_balance.{key} out of range")


def validate_pricing(value: dict[str, Any], label: str, errors: list[str], warnings: list[str]) -> None:
    all_null = True
    for key in PRICING_KEYS:
        item = value.get(key)
        if item is not None:
            all_null = False
            if int_or_none(item) is None or int(item) < 0:
                errors.append(f"{label}: pricing.{key} must be null or non-negative integer")
    if all_null:
        warnings.append(f"{label}: all pricing fields are null")


def orm_payload(product: dict[str, Any], brand, chip_vendor) -> dict[str, Any]:
    pricing = product.get("pricing") or {}
    balance = product.get("game_balance") or {}
    real_specs = product.get("real_specs") or {}
    return {
        "slug": clean(product.get("slug")),
        "name": clean(product.get("name")),
        "brand": brand.name,
        "brand_id": brand.id,
        "chip_vendor_brand_id": chip_vendor.id if chip_vendor else None,
        "category": normalize_category(product.get("category")),
        "release_year": int_or_none(product.get("release_year")),
        "origin_name_vi": clean(product.get("origin_name_vi")),
        "origin_code": clean(product.get("origin_code")).upper() if clean(product.get("origin_code")) else None,
        "source_name": clean(product.get("source_name")),
        "source_url": clean(product.get("source_url")),
        "data_confidence": clean(product.get("data_confidence")).upper() if clean(product.get("data_confidence")) else None,
        "real_specs_json": real_specs,
        "game_balance_json": balance,
        "specs_json": real_specs,
        "image_url": clean(product.get("image_url")),
        "brand_logo_url": brand.logo_url,
        "notes": clean(product.get("notes")),
        "msrp_vnd": int_or_none(pricing.get("msrp_vnd")),
        "base_local_price_vnd": int_or_none(pricing.get("base_local_price_vnd")),
        "base_used_price_vnd": int_or_none(pricing.get("base_used_price_vnd")),
        "supplier_cost_vnd": int_or_none(pricing.get("supplier_cost_vnd")),
        "base_performance_score": int(balance["base_performance_score"]),
        "base_power_watts": int(balance["base_power_watts"]),
        "base_heat_score": int(balance["base_heat_score"]),
        "base_reliability_score": int(balance["base_reliability_score"]),
        "used_demand_score": int(balance["used_demand_score"]),
        "mining_popularity_score": int(balance["mining_popularity_score"]),
        "depreciation_rate": int(balance["depreciation_rate"]),
    }


def normalize_category(value: Any) -> str:
    return str(value or "").strip().upper().replace(" ", "_")


def clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
