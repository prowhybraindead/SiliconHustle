from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal, init_db  # noqa: E402
from app.models.entities import Brand, BrandCategory, HardwareProduct  # noqa: E402
from app.models.enums import BrandCategoryName, BrandType, HardwareCategory, MarketTier  # noqa: E402
from brand_data import normalize_slug, parse_brand_csv, validate_report  # noqa: E402


def main() -> int:
    report = parse_brand_csv()
    warnings, errors = validate_report(report)
    print(f"Brands CSV: {report.brands_path or 'missing'}")
    print(f"Categories CSV: {report.categories_path or 'missing'}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print_summary(0, 0, 0, 0, len(warnings), len(errors))
        return 1

    init_db()
    from app.core.config import get_settings
    from supplier_data import get_db_path
    db_path = get_db_path()
    settings = get_settings()

    print("==================================================")
    print(f"DATABASE_URL: {settings.database_url}")
    print(f"ACTIVE DATABASE: {db_path}")
    print(f"RESOLVED BRANDS FILE: {report.brands_path or 'None'}")
    print(f"RESOLVED CATEGORIES FILE: {report.categories_path or 'None'}")
    print("==================================================")
    with SessionLocal() as db:
        existing = {brand.slug: brand for brand in db.query(Brand).all()}
        brands_created = 0
        brands_updated = 0
        for parsed in report.brands:
            brand = existing.get(parsed.slug)
            if not brand:
                brand = Brand(slug=parsed.slug, name=parsed.name)
                db.add(brand)
                existing[parsed.slug] = brand
                brands_created += 1
            if update_brand(brand, parsed):
                if parsed.slug in existing and brand.id is not None:
                    brands_updated += 1
        db.flush()

        categories_linked, categories_skipped = link_categories(db, existing, report.categories)
        link_warnings = link_existing_hardware_products_to_brands(db, existing)
        warnings.extend(link_warnings)
        db.commit()

    for warning in warnings:
        print(f"WARNING: {warning}")
    print_summary(brands_created, brands_updated, categories_linked, categories_skipped, len(warnings), 0)
    return 0


def update_brand(brand: Brand, parsed) -> bool:
    updates = {
        "name": parsed.name,
        "origin_name_vi": parsed.origin_name_vi,
        "origin_code": parsed.origin_code,
        "logo_url": parsed.logo_url,
        "website_url": parsed.website_url,
        "brand_type": BrandType(parsed.brand_type),
        "market_tier": MarketTier(parsed.market_tier),
        "base_trust_score": parsed.base_trust_score,
        "used_market_risk_modifier": parsed.used_market_risk_modifier,
        "notes": parsed.notes,
    }
    changed = False
    for field, value in updates.items():
        if getattr(brand, field) != value:
            setattr(brand, field, value)
            changed = True
    return changed


def link_categories(db, brands_by_slug: dict[str, Brand], categories) -> tuple[int, int]:
    existing_links = {
        (category.brand_id, category.category.value if hasattr(category.category, "value") else category.category)
        for category in db.query(BrandCategory).all()
    }
    linked = 0
    skipped = 0
    for parsed in categories:
        brand = brands_by_slug.get(parsed.brand_slug)
        if not brand:
            continue
        key = (brand.id, parsed.category)
        if key in existing_links:
            skipped += 1
            continue
        db.add(BrandCategory(brand_id=brand.id, category=BrandCategoryName(parsed.category)))
        existing_links.add(key)
        linked += 1
    return linked, skipped


def link_existing_hardware_products_to_brands(db, brands_by_slug: dict[str, Brand]) -> list[str]:
    warnings: list[str] = []
    chip_vendors = {slug: brands_by_slug.get(slug) for slug in ("intel", "amd", "nvidia")}
    for product in db.query(HardwareProduct).all():
        brand_slug = normalize_slug(product.brand)
        brand = brands_by_slug.get(brand_slug)
        if brand:
            product.brand_id = brand.id
        else:
            warnings.append(f"Unmatched hardware product brand: {product.brand} ({product.name})")

        vendor = infer_chip_vendor(product, chip_vendors)
        if vendor:
            product.chip_vendor_brand_id = vendor.id
    return warnings


def infer_chip_vendor(product: HardwareProduct, chip_vendors: dict[str, Brand | None]) -> Brand | None:
    brand_slug = normalize_slug(product.brand)
    name_slug = normalize_slug(product.name)
    if product.category == HardwareCategory.CPU:
        if "intel" in {brand_slug, name_slug.split("-")[0]} or "core" in name_slug:
            return chip_vendors.get("intel")
        if brand_slug == "amd" or "ryzen" in name_slug:
            return chip_vendors.get("amd")
    if product.category == HardwareCategory.GPU:
        if brand_slug == "nvidia" or "geforce" in name_slug or "rtx" in name_slug or "gtx" in name_slug:
            return chip_vendors.get("nvidia")
        if brand_slug == "amd" or "radeon" in name_slug or "rx" in name_slug:
            return chip_vendors.get("amd")
    if brand_slug in chip_vendors:
        return chip_vendors.get(brand_slug)
    return None


def print_summary(created: int, updated: int, linked: int, skipped: int, warnings_count: int, errors_count: int) -> None:
    print("Brand import summary")
    print(f"- brands created: {created}")
    print(f"- brands updated: {updated}")
    print(f"- categories linked: {linked}")
    print(f"- category links skipped: {skipped}")
    print(f"- warnings count: {warnings_count}")
    print(f"- hard errors count: {errors_count}")


if __name__ == "__main__":
    raise SystemExit(main())
