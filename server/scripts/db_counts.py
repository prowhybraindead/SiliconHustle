from __future__ import annotations

import sys
from pathlib import Path

# Add project server/ directory to python path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.entities import (
    Brand,
    BrandCategory,
    HardwareProduct,
    Supplier,
    SupplierOffer,
    ExchangeRate,
    SaveGame,
    InventoryUnit,
    Quote,
    Order,
    PurchaseOrder,
)
from sqlalchemy import select, func

def main() -> int:
    settings = get_settings()
    db_url = settings.database_url
    print(f"Active DATABASE_URL: {db_url}")
    
    if db_url.startswith("sqlite"):
        db_path = db_url.replace("sqlite:///", "")
        # Remove any leading dot or slash for proper resolution
        if db_path.startswith("./"):
            db_path = db_path[2:]
        resolved_path = Path(db_path).resolve()
        print(f"Resolved SQLite DB file path: {resolved_path}")
        if not resolved_path.exists():
            print("WARNING: SQLite DB file does not exist yet at this location.")
    else:
        print("Using non-SQLite database.")
        
    try:
        with SessionLocal() as db:
            counts = {
                "brands": db.scalar(select(func.count(Brand.id))),
                "brand_categories": db.scalar(select(func.count(BrandCategory.id))),
                "hardware_products": db.scalar(select(func.count(HardwareProduct.id))),
                "suppliers": db.scalar(select(func.count(Supplier.id))),
                "supplier_offers": db.scalar(select(func.count(SupplierOffer.id))),
                "exchange_rates": db.scalar(select(func.count(ExchangeRate.id))),
                "save_games": db.scalar(select(func.count(SaveGame.id))),
                "inventory_units": db.scalar(select(func.count(InventoryUnit.id))),
                "quotes": db.scalar(select(func.count(Quote.id))),
                "orders": db.scalar(select(func.count(Order.id))),
                "purchase_orders": db.scalar(select(func.count(PurchaseOrder.id))),
            }
            print("\nTable Counts:")
            for table, count in counts.items():
                print(f"  {table}: {count}")
    except Exception as e:
        print(f"Error querying table counts: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
