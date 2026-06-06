from __future__ import annotations

import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add project server/ and scripts/ directories to python path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.database import SessionLocal, init_db
from app.models.entities import Brand, HardwareProduct, Supplier, SupplierOffer
from app.models.enums import SupplierType, SupplierTier, HardwareCategory
from app.services import fx_service
from supplier_data import validate_suppliers_and_offers, get_db_path

def map_tier_to_type(tier: str | None) -> SupplierType:
    if not tier:
        return SupplierType.OTHER
    if tier == "OFFICIAL_DISTRIBUTOR":
        return SupplierType.OFFICIAL_DISTRIBUTOR
    elif tier == "WHOLESALE":
        return SupplierType.WHOLESALE
    elif tier == "IMPORTER":
        return SupplierType.WHOLESALE
    elif tier == "USED_MARKET":
        return SupplierType.USED_MARKET
    else:
        return SupplierType.OTHER

def main() -> int:
    init_db()
    db_path = get_db_path()
    from app.core.config import get_settings
    from supplier_data import imports_dir, SUPPLIER_JSON_NAME, OFFER_JSON_NAME
    settings = get_settings()
    suppliers_path = imports_dir() / SUPPLIER_JSON_NAME
    offers_path = imports_dir() / OFFER_JSON_NAME

    print("==================================================")
    print(f"DATABASE_URL: {settings.database_url}")
    print(f"ACTIVE DATABASE: {db_path}")
    print(f"RESOLVED SUPPLIERS FILE: {suppliers_path.resolve() if suppliers_path.exists() else 'None'}")
    print(f"RESOLVED OFFERS FILE: {offers_path.resolve() if offers_path.exists() else 'None'}")
    print("==================================================")

    report = validate_suppliers_and_offers()
    if report.errors:
        print("Import cancelled due to validation errors:")
        for error in report.errors:
            print(f"  ERROR: {error}")
        return 1

    with SessionLocal() as db:
        # Load lookups
        existing_suppliers = {s.slug: s for s in db.query(Supplier).all() if s.slug}
        existing_suppliers_by_name = {s.name: s for s in db.query(Supplier).all()}
        
        products = {p.slug: p for p in db.query(HardwareProduct).filter(HardwareProduct.slug.is_not(None)).all()}

        created_suppliers = 0
        updated_suppliers = 0
        
        # Upsert Suppliers
        supplier_id_map = {}
        for s_data in report.suppliers:
            slug = s_data["slug"]
            name = s_data["name"]
            
            supplier = existing_suppliers.get(slug) or existing_suppliers_by_name.get(name)
            if not supplier:
                supplier = Supplier()
                db.add(supplier)
                created_suppliers += 1
            else:
                updated_suppliers += 1
                
            supplier.name = name
            supplier.slug = slug
            supplier.type = map_tier_to_type(s_data.get("supplier_tier"))
            supplier.supplier_tier = SupplierTier(s_data.get("supplier_tier") or "OTHER")
            supplier.trust_score = s_data["trust_score"]
            supplier.relationship_score = s_data["relationship_score"]
            supplier.delivery_days = s_data.get("default_delivery_days") or s_data.get("delivery_days", 2)
            supplier.default_delivery_days = s_data.get("default_delivery_days")
            supplier.notes = s_data.get("notes")
            
            supplier.country_code = s_data.get("country_code")
            supplier.invoice_currency = s_data.get("invoice_currency", "VND")
            supplier.fx_spread_percent = s_data.get("fx_spread_percent")
            supplier.import_fee_percent = s_data.get("import_fee_percent")
            supplier.payment_fee_flat_vnd = s_data.get("payment_fee_flat_vnd")
            supplier.supported_brand_slugs_json = s_data.get("supported_brand_slugs")
            supplier.supported_category_json = s_data.get("supported_categories")
            
            db.flush()
            supplier_id_map[slug] = supplier.id

        db.commit()
        print(f"Suppliers upserted: {created_suppliers} created, {updated_suppliers} updated.")

        # Upsert Supplier Offers
        created_offers = 0
        updated_offers = 0
        
        for o_data in report.offers:
            s_slug = o_data["supplier_slug"]
            p_slug = o_data["product_slug"]
            
            supplier_id = supplier_id_map[s_slug]
            product = products.get(p_slug)
            if not product:
                continue
                
            product_id = product.id
            
            offer = db.query(SupplierOffer).filter(
                SupplierOffer.supplier_id == supplier_id,
                SupplierOffer.product_id == product_id
            ).first()
            
            if not offer:
                offer = SupplierOffer(
                    supplier_id=supplier_id,
                    product_id=product_id
                )
                db.add(offer)
                created_offers += 1
            else:
                updated_offers += 1

            # Handle FX conversion if foreign price is used
            foreign_unit_price = o_data.get("foreign_unit_price")
            foreign_currency = o_data.get("foreign_currency")
            
            if foreign_unit_price is not None and foreign_currency is not None:
                rate, provider, _, _, is_fallback, _ = fx_service.get_rate_to_vnd(db, foreign_currency)
                unit_price_vnd = round(foreign_unit_price * rate)
                
                offer.foreign_unit_price = foreign_unit_price
                offer.foreign_currency = foreign_currency
                offer.unit_price_vnd = unit_price_vnd
            else:
                offer.foreign_unit_price = None
                offer.foreign_currency = None
                offer.unit_price_vnd = o_data["unit_price_vnd"]

            offer.min_order_quantity = o_data.get("min_order_quantity", 1)
            offer.available_quantity = o_data.get("available_quantity", 1)
            offer.warranty_months = o_data.get("warranty_months", 12)
            offer.quality_risk_modifier = o_data.get("quality_risk_modifier")
            
            exp_day = o_data.get("expires_on_day")
            offer.expires_on_day = exp_day
            if exp_day:
                offer.expires_at = datetime.now(timezone.utc) + timedelta(days=exp_day)
            else:
                offer.expires_at = None
                
            offer.offer_type = o_data.get("offer_type")
            
        db.commit()
        print(f"Supplier offers upserted: {created_offers} created, {updated_offers} updated.")
        
    print("Import completed successfully.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
