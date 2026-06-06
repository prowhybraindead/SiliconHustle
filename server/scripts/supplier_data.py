from __future__ import annotations

import json
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Any

# Add project server/ directory to python path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.entities import Brand, HardwareProduct
from app.models.enums import HardwareCategory, SupplierTier
from app.services import fx_service

SUPPLIER_JSON_NAME = "suppliers.json"
OFFER_JSON_NAME = "supplier_offers.sample.json"

ALLOWED_TIERS = {tier.value for tier in SupplierTier}
ALLOWED_CATEGORIES = {cat.value for cat in HardwareCategory}

def get_db_path() -> str:
    settings = get_settings()
    db_url = settings.database_url
    if db_url.startswith("sqlite"):
        db_path = db_url.replace("sqlite:///", "")
        if db_path.startswith("./"):
            db_path = db_path[2:]
        return str(Path(db_path).resolve())
    return db_url

# Print database path upon import/load to be explicitly clear
db_path = get_db_path()
print(f"Active SQLite DB resolved path: {db_path}", file=sys.stderr)

@dataclass
class ValidationReport:
    suppliers: list[dict[str, Any]]
    offers: list[dict[str, Any]]
    warnings: list[str]
    errors: list[str]

def imports_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "imports"

def validate_suppliers_and_offers() -> ValidationReport:
    warnings: list[str] = []
    errors: list[str] = []
    
    # Resolve active DB path
    db_path = get_db_path()
    print(f"Active database path for validation: {db_path}")

    # Load databases
    with SessionLocal() as db:
        known_brand_slugs = {brand.slug for brand in db.query(Brand).all()}
        known_product_slugs = {product.slug for product in db.query(HardwareProduct).filter(HardwareProduct.slug.is_not(None)).all()}
        supported_currencies = {curr["code"] for curr in fx_service.get_supported_currencies()}

    # Load suppliers
    suppliers_path = imports_dir() / SUPPLIER_JSON_NAME
    suppliers_data: list[dict[str, Any]] = []
    if not suppliers_path.exists():
        errors.append(f"Missing suppliers JSON file at: {suppliers_path}")
    else:
        try:
            raw = json.loads(suppliers_path.read_text(encoding="utf-8-sig"))
            if not isinstance(raw, dict) or not isinstance(raw.get("suppliers"), list):
                errors.append("Top-level suppliers JSON must contain a 'suppliers' array.")
            else:
                suppliers_data = raw["suppliers"]
        except Exception as e:
            errors.append(f"Failed to read suppliers JSON: {e}")

    # Validate suppliers
    supplier_slugs: set[str] = set()
    for index, supplier in enumerate(suppliers_data, start=1):
        label = supplier.get("slug") or supplier.get("name") or f"supplier row {index}"
        
        slug = supplier.get("slug")
        if not slug:
            errors.append(f"{label}: missing slug")
        else:
            if slug in supplier_slugs:
                errors.append(f"Duplicate supplier slug: {slug}")
            supplier_slugs.add(slug)

        name = supplier.get("name")
        if not name:
            errors.append(f"{label}: missing name")

        tier = supplier.get("supplier_tier")
        if tier and tier not in ALLOWED_TIERS:
            errors.append(f"{label}: invalid supplier_tier {tier}")

        invoice_currency = supplier.get("invoice_currency", "VND")
        if invoice_currency not in supported_currencies:
            errors.append(f"{label}: unsupported invoice_currency {invoice_currency}")

        country_code = supplier.get("country_code")
        if country_code and len(country_code) not in (2, 3):
            errors.append(f"{label}: country_code must be 2 or 3 characters")

        for score_field in ("trust_score", "relationship_score"):
            score = supplier.get(score_field)
            if score is None:
                errors.append(f"{label}: missing {score_field}")
            elif not isinstance(score, int) or not (0 <= score <= 100):
                errors.append(f"{label}: {score_field} must be an integer between 0 and 100")

        delivery_days = supplier.get("default_delivery_days") or supplier.get("delivery_days")
        if delivery_days is None:
            errors.append(f"{label}: missing default_delivery_days or delivery_days")
        elif not isinstance(delivery_days, int) or delivery_days < 0:
            errors.append(f"{label}: delivery days must be a non-negative integer")

        for fee_field in ("fx_spread_percent", "import_fee_percent", "payment_fee_flat_vnd"):
            val = supplier.get(fee_field)
            if val is not None and (not isinstance(val, (int, float)) or val < 0):
                errors.append(f"{label}: {fee_field} must be a non-negative number")

        # Validate brands/categories lists
        brands = supplier.get("supported_brand_slugs")
        if brands is not None:
            if not isinstance(brands, list):
                errors.append(f"{label}: supported_brand_slugs must be a list")
            else:
                for brand in brands:
                    if brand not in known_brand_slugs:
                        errors.append(f"{label}: unknown supported brand_slug '{brand}'")
        else:
            warnings.append(f"{label}: no supported brands list provided")

        categories = supplier.get("supported_categories")
        if categories is not None:
            if not isinstance(categories, list):
                errors.append(f"{label}: supported_categories must be a list")
            else:
                for cat in categories:
                    if cat not in ALLOWED_CATEGORIES:
                        errors.append(f"{label}: unknown supported category '{cat}'")
        else:
            warnings.append(f"{label}: no supported categories list provided")

    # Load offers
    offers_path = imports_dir() / OFFER_JSON_NAME
    offers_data: list[dict[str, Any]] = []
    if not offers_path.exists():
        errors.append(f"Missing offers JSON file at: {offers_path}")
    else:
        try:
            raw = json.loads(offers_path.read_text(encoding="utf-8-sig"))
            if not isinstance(raw, dict) or not isinstance(raw.get("offers"), list):
                errors.append("Top-level offers JSON must contain an 'offers' array.")
            else:
                offers_data = raw["offers"]
        except Exception as e:
            errors.append(f"Failed to read offers JSON: {e}")

    # Validate offers
    for index, offer in enumerate(offers_data, start=1):
        label = f"offer row {index} (Supplier: {offer.get('supplier_slug')}, Product: {offer.get('product_slug')})"
        
        supplier_slug = offer.get("supplier_slug")
        if not supplier_slug:
            errors.append(f"offer row {index}: missing supplier_slug")
        elif supplier_slug not in supplier_slugs:
            errors.append(f"offer row {index}: unknown supplier_slug '{supplier_slug}'")

        product_slug = offer.get("product_slug")
        if not product_slug:
            errors.append(f"offer row {index}: missing product_slug")
        elif product_slug not in known_product_slugs:
            errors.append(f"offer row {index}: unknown product_slug '{product_slug}'")

        # Validate pricing
        foreign_unit_price = offer.get("foreign_unit_price")
        foreign_currency = offer.get("foreign_currency")
        unit_price_vnd = offer.get("unit_price_vnd")

        if foreign_unit_price is not None:
            if foreign_currency is None:
                errors.append(f"{label}: foreign_unit_price requires foreign_currency")
            elif foreign_currency not in supported_currencies:
                errors.append(f"{label}: unsupported foreign_currency '{foreign_currency}'")
            if not isinstance(foreign_unit_price, (int, float)) or foreign_unit_price < 0:
                errors.append(f"{label}: foreign_unit_price must be a non-negative number")
        
        if unit_price_vnd is not None:
            if not isinstance(unit_price_vnd, int) or unit_price_vnd < 0:
                errors.append(f"{label}: unit_price_vnd must be a non-negative integer")

        if foreign_unit_price is None and unit_price_vnd is None:
            warnings.append(f"{label}: must specify at least one price (foreign_unit_price + foreign_currency OR unit_price_vnd)")
            errors.append(f"{label}: missing price field")

        # Quantities
        moq = offer.get("min_order_quantity", 1)
        if not isinstance(moq, int) or moq <= 0:
            errors.append(f"{label}: min_order_quantity must be a positive integer")

        avail = offer.get("available_quantity", 1)
        if not isinstance(avail, int) or avail <= 0:
            errors.append(f"{label}: available_quantity must be a positive integer")

        warranty = offer.get("warranty_months")
        if warranty is not None:
            if not isinstance(warranty, int) or warranty < 0:
                errors.append(f"{label}: warranty_months must be a non-negative integer")
        else:
            warnings.append(f"{label}: missing warranty months")

        qrm = offer.get("quality_risk_modifier")
        if qrm is not None and (not isinstance(qrm, (int, float)) or not (0.0 <= qrm <= 1.0)):
            errors.append(f"{label}: quality_risk_modifier must be a number between 0.0 and 1.0")

        exp = offer.get("expires_on_day")
        if exp is not None:
            if not isinstance(exp, int) or exp <= 0:
                errors.append(f"{label}: expires_on_day must be a positive integer")
        else:
            warnings.append(f"{label}: missing expires_on_day")

    return ValidationReport(
        suppliers=suppliers_data,
        offers=offers_data,
        warnings=warnings,
        errors=errors,
    )
