from __future__ import annotations

import argparse
import sys
from pathlib import Path
from sqlalchemy import select, update

# Add project server/ and scripts/ directories to python path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.database import SessionLocal, init_db
from app.core.config import get_settings
from app.models.entities import HardwareProduct, ProductPriceSnapshot
from app.services import fx_service
from price_data import validate_prices
from supplier_data import get_db_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Import product price snapshots from CSV file")
    parser.add_argument("--file", type=str, default=None, help="Path to product prices CSV file")
    args = parser.parse_args()

    init_db()
    db_path = get_db_path()
    settings = get_settings()

    report = validate_prices(path=args.file)

    print("==================================================")
    print(f"DATABASE_URL: {settings.database_url}")
    print(f"ACTIVE DATABASE: {db_path}")
    print(f"RESOLVED PRICE FILE: {report.path or 'None'}")
    print("==================================================")

    if report.file_missing:
        print(f"No price import performed: product_prices.csv does not exist yet at: {report.path or 'default path'}.")
        return 0

    if report.errors:
        print("Import cancelled due to validation errors:")
        for error in report.errors:
            print(f"  ERROR: {error}")
        return 1

    created_count = 0
    skipped_count = 0
    updated_current_count = 0

    # Sort prices by observed_at ascending to process in chronological order
    sorted_prices = sorted(report.prices, key=lambda x: x["observed_at"])

    with SessionLocal() as db:
        for p_data in sorted_prices:
            slug = p_data["product_slug"]
            price_type = p_data["price_type"]
            currency = p_data["currency"]
            amount = p_data["amount"]
            region = p_data["region"]
            source_name = p_data["source_name"]
            source_url = p_data["source_url"]
            observed_at = p_data["observed_at"]
            confidence = p_data["confidence"]
            notes = p_data["notes"]

            # 1. Fetch product
            product = db.query(HardwareProduct).filter(HardwareProduct.slug == slug).first()
            if not product:
                # Should not happen since validation passed, but safety first
                print(f"Skipping row: product slug '{slug}' not found in database.")
                skipped_count += 1
                continue

            # 2. Check if identical snapshot already exists (Idempotency check)
            existing_exact = db.query(ProductPriceSnapshot).filter(
                ProductPriceSnapshot.product_slug == slug,
                ProductPriceSnapshot.price_type == price_type,
                ProductPriceSnapshot.region == region,
                ProductPriceSnapshot.source_name == source_name,
                ProductPriceSnapshot.observed_at == observed_at,
                ProductPriceSnapshot.currency == currency,
                ProductPriceSnapshot.amount == amount
            ).first()

            if existing_exact:
                skipped_count += 1
                continue

            # 3. Perform FX conversion
            if currency == "VND":
                amount_vnd = round(amount)
                rate = None
                provider = None
                fetched_at = None
                is_fallback = False
            else:
                rate, provider, source, fetched_at, is_fallback, _ = fx_service.get_rate_to_vnd(db, currency)
                amount_vnd = round(amount * rate)

            # 4. Check if there is an existing current snapshot for this group
            existing_current = db.query(ProductPriceSnapshot).filter(
                ProductPriceSnapshot.product_slug == slug,
                ProductPriceSnapshot.price_type == price_type,
                ProductPriceSnapshot.region == region,
                ProductPriceSnapshot.source_name == source_name,
                ProductPriceSnapshot.is_current == True
            ).first()

            is_new_current = True
            if existing_current:
                if observed_at >= existing_current.observed_at:
                    # New snapshot is newer or same time; deprecate previous
                    existing_current.is_current = False
                else:
                    # New snapshot is older than the current one in DB; it is not current
                    is_new_current = False

            # 5. Insert new snapshot
            snapshot = ProductPriceSnapshot(
                product_id=product.id,
                product_slug=slug,
                price_type=price_type,
                currency=currency,
                amount=amount,
                amount_vnd=amount_vnd,
                fx_rate_to_vnd=rate,
                fx_provider=provider,
                fx_fetched_at=fetched_at,
                fx_is_fallback=is_fallback,
                region=region,
                source_name=source_name,
                source_url=source_url,
                confidence=confidence,
                observed_at=observed_at,
                is_current=is_new_current,
                notes=notes
            )
            db.add(snapshot)
            created_count += 1

            # 6. Update cache fields on HardwareProduct if this snapshot is current
            if is_new_current:
                db.flush()
                # Find the newest current snapshot for this product and price_type
                newest_current = db.query(ProductPriceSnapshot).filter(
                    ProductPriceSnapshot.product_id == product.id,
                    ProductPriceSnapshot.price_type == price_type,
                    ProductPriceSnapshot.is_current == True
                ).order_by(ProductPriceSnapshot.observed_at.desc()).first()

                if newest_current:
                    if price_type == "LOCAL_RETAIL":
                        product.latest_local_retail_vnd = newest_current.amount_vnd
                    elif price_type == "USED_MARKET":
                        product.latest_used_market_vnd = newest_current.amount_vnd
                    elif price_type == "SUPPLIER_COST":
                        product.latest_supplier_cost_vnd = newest_current.amount_vnd
                    elif price_type == "MSRP":
                        product.latest_msrp_vnd = newest_current.amount_vnd

                # Also update latest_price_updated_at to the max observed_at of all current snapshots
                newest_overall = db.query(ProductPriceSnapshot).filter(
                    ProductPriceSnapshot.product_id == product.id,
                    ProductPriceSnapshot.is_current == True
                ).order_by(ProductPriceSnapshot.observed_at.desc()).first()
                if newest_overall:
                    product.latest_price_updated_at = newest_overall.observed_at
                
                updated_current_count += 1

        db.commit()

    print("\nProduct Price Import Summary:")
    print(f"- snapshots created: {created_count}")
    print(f"- snapshots skipped: {skipped_count}")
    print(f"- snapshots updated/current-changed: {updated_current_count}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
