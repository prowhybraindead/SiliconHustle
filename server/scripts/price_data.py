from __future__ import annotations

import csv
import sys
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import Any

# Add project server/ and scripts/ directories to python path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.database import SessionLocal, init_db
from app.models.entities import HardwareProduct
from app.models.enums import ProductPriceType, ProductPriceConfidence
from app.services import fx_service
from supplier_data import get_db_path, imports_dir

PRICE_CSV_NAME = "product_prices.csv"
PRICE_TEMPLATE_NAME = "product_prices.template.csv"

ALLOWED_PRICE_TYPES = {t.value for t in ProductPriceType}
ALLOWED_CONFIDENCE_VALUES = {c.value for c in ProductPriceConfidence}


@dataclass
class PriceValidationReport:
    prices: list[dict[str, Any]]
    path: Path | None
    warnings: list[str]
    errors: list[str]
    file_missing: bool = False


def validate_prices(path: str | Path | None = None) -> PriceValidationReport:
    warnings: list[str] = []
    errors: list[str] = []
    
    resolved_path: Path | None = None
    if path:
        p = Path(path)
        if p.exists():
            resolved_path = p.resolve()
        else:
            p_imports = imports_dir() / path
            if p_imports.exists():
                resolved_path = p_imports.resolve()
            else:
                p_server = Path(__file__).resolve().parents[1] / path
                if p_server.exists():
                    resolved_path = p_server.resolve()
    else:
        # Check in imports directory
        default_path = imports_dir() / PRICE_CSV_NAME
        if default_path.exists():
            resolved_path = default_path.resolve()
        else:
            # Also search server/ directory
            resolved_path = default_path

    if not resolved_path or not resolved_path.exists():
        return PriceValidationReport([], resolved_path, [], [], file_missing=True)

    # Make sure the local SQLite schema exists before touching the catalog table.
    # This keeps the validator usable as a standalone script and avoids test
    # failures when the database has not been initialized yet.
    init_db()

    # Load slugs and currencies from database
    with SessionLocal() as db:
        known_slugs = {p.slug for p in db.query(HardwareProduct).filter(HardwareProduct.slug.is_not(None)).all()}
        supported_currencies = {curr["code"] for curr in fx_service.get_supported_currencies()}

    prices: list[dict[str, Any]] = []
    try:
        with resolved_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            expected_fields = {
                "product_slug", "price_type", "currency", "amount", 
                "region", "source_name", "source_url", "observed_at", "confidence", "notes"
            }
            if reader.fieldnames:
                missing_fields = expected_fields - set(reader.fieldnames)
                if missing_fields:
                    errors.append(f"CSV header is missing expected fields: {', '.join(sorted(missing_fields))}")
                    return PriceValidationReport([], resolved_path, warnings, errors)
            else:
                errors.append("CSV file is empty or has no header.")
                return PriceValidationReport([], resolved_path, warnings, errors)

            for row_num, row in enumerate(reader, start=2):
                label = f"row {row_num} (slug: {row.get('product_slug')})"
                
                slug = (row.get("product_slug") or "").strip()
                if not slug:
                    errors.append(f"Row {row_num}: missing product_slug")
                elif slug not in known_slugs:
                    errors.append(f"{label}: unknown product_slug '{slug}'")

                price_type = (row.get("price_type") or "").strip().upper()
                if not price_type:
                    errors.append(f"{label}: missing price_type")
                elif price_type not in ALLOWED_PRICE_TYPES:
                    errors.append(f"{label}: invalid price_type '{price_type}'")

                currency = (row.get("currency") or "").strip().upper()
                if not currency:
                    errors.append(f"{label}: missing currency")
                elif currency not in supported_currencies:
                    errors.append(f"{label}: unsupported currency '{currency}'")

                amount_str = (row.get("amount") or "").strip()
                amount: float | None = None
                if not amount_str:
                    errors.append(f"{label}: missing amount")
                else:
                    try:
                        amount = float(amount_str)
                        if amount <= 0:
                            errors.append(f"{label}: amount must be positive (got {amount})")
                    except ValueError:
                        errors.append(f"{label}: invalid amount '{amount_str}' (must be a number)")

                confidence = (row.get("confidence") or "").strip().upper()
                if not confidence:
                    errors.append(f"{label}: missing confidence")
                elif confidence not in ALLOWED_CONFIDENCE_VALUES:
                    errors.append(f"{label}: invalid confidence '{confidence}'")

                observed_at_str = (row.get("observed_at") or "").strip()
                observed_at: datetime | None = None
                if not observed_at_str:
                    errors.append(f"{label}: missing observed_at")
                else:
                    parsed = False
                    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
                        try:
                            observed_at = datetime.strptime(observed_at_str, fmt)
                            parsed = True
                            break
                        except ValueError:
                            pass
                    if not parsed:
                        try:
                            observed_at = datetime.fromisoformat(observed_at_str)
                            parsed = True
                        except ValueError:
                            pass
                    if not parsed:
                        errors.append(f"{label}: invalid observed_at '{observed_at_str}' (must be a valid datetime)")

                # Warnings
                source_name = (row.get("source_name") or "").strip() or None
                if not source_name:
                    warnings.append(f"{label}: source_name missing")

                source_url = (row.get("source_url") or "").strip() or None
                if not source_url:
                    warnings.append(f"{label}: source_url missing")

                notes = (row.get("notes") or "").strip() or None
                if not notes:
                    warnings.append(f"{label}: notes empty")

                region = (row.get("region") or "").strip() or None

                prices.append({
                    "product_slug": slug,
                    "price_type": price_type,
                    "currency": currency,
                    "amount": amount,
                    "region": region,
                    "source_name": source_name,
                    "source_url": source_url,
                    "observed_at": observed_at,
                    "confidence": confidence,
                    "notes": notes
                })
    except Exception as e:
        errors.append(f"Failed to read CSV file: {e}")

    return PriceValidationReport(prices, resolved_path, warnings, errors)
