from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project server/ and scripts/ directories to python path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.database import SessionLocal, init_db  # noqa: E402
from app.models.entities import Brand, HardwareProduct  # noqa: E402
from app.models.enums import HardwareCategory  # noqa: E402
from product_data import orm_payload, validate_products  # noqa: E402
from supplier_data import get_db_path  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Import hardware products from JSON catalog")
    parser.add_argument("--file", type=str, default=None, help="Path to hardware products JSON file")
    args = parser.parse_args()

    init_db()
    db_path = get_db_path()
    from app.core.config import get_settings
    settings = get_settings()

    with SessionLocal() as db:
        brands = {brand.slug: brand for brand in db.query(Brand).all()}
        result = validate_products(set(brands), path=args.file)

        print("==================================================")
        print(f"DATABASE_URL: {settings.database_url}")
        print(f"ACTIVE DATABASE: {db_path}")
        print(f"RESOLVED IMPORT FILE: {result.path or 'None'}")
        print("==================================================")

        if result.errors:
            for error in result.errors:
                print(f"ERROR: {error}")
            print_summary(0, 0, 0, len(result.warnings), len(result.errors))
            return 1

        existing = {product.slug: product for product in db.query(HardwareProduct).filter(HardwareProduct.slug.is_not(None)).all()}
        created = 0
        updated = 0
        skipped = 0
        for source in result.products:
            brand = brands[source["brand_slug"]]
            chip_vendor = brands.get(source.get("chip_vendor_slug"))
            payload = orm_payload(source, brand, chip_vendor)
            product = existing.get(payload["slug"])
            if not product:
                product = HardwareProduct()
                db.add(product)
                created += 1
            elif not apply_payload(product, payload):
                skipped += 1
                continue
            else:
                updated += 1
            apply_payload(product, payload)
            product.category = HardwareCategory(payload["category"])
        db.commit()
    print_summary(created, updated, skipped, len(result.warnings), 0)
    return 0


def apply_payload(product: HardwareProduct, payload: dict) -> bool:
    changed = False
    for field, value in payload.items():
        if field == "category":
            value = HardwareCategory(value)
        if getattr(product, field, None) != value:
            setattr(product, field, value)
            changed = True
    return changed


def print_summary(created: int, updated: int, skipped: int, warnings: int, errors: int) -> None:
    print("Hardware product import summary")
    print(f"- products created: {created}")
    print(f"- products updated: {updated}")
    print(f"- products skipped: {skipped}")
    print(f"- warnings: {warnings}")
    print(f"- errors: {errors}")


if __name__ == "__main__":
    raise SystemExit(main())
