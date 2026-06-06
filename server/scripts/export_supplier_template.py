from __future__ import annotations

import argparse
from pathlib import Path
from supplier_data import imports_dir, get_db_path

SUPPLIERS_TEMPLATE = """{
  "suppliers": [
    {
      "slug": "example-supplier-slug",
      "name": "Example Supplier Name",
      "country_code": "VN",
      "invoice_currency": "VND",
      "supplier_tier": "WHOLESALE",
      "trust_score": 80,
      "relationship_score": 50,
      "default_delivery_days": 3,
      "fx_spread_percent": 1.5,
      "import_fee_percent": 2.0,
      "payment_fee_flat_vnd": 50000,
      "supported_brand_slugs": ["brand-a-slug", "brand-b-slug"],
      "supported_categories": ["CPU", "GPU"],
      "notes": "Example notes"
    }
  ]
}
"""

OFFERS_TEMPLATE = """{
  "offers": [
    {
      "supplier_slug": "example-supplier-slug",
      "product_slug": "intel-core-i5-14400",
      "foreign_unit_price": 185.0,
      "foreign_currency": "USD",
      "unit_price_vnd": 4700000,
      "min_order_quantity": 5,
      "available_quantity": 100,
      "warranty_months": 12,
      "quality_risk_modifier": 0.05,
      "expires_on_day": 14,
      "offer_type": "OFFICIAL",
      "notes": "Example offer notes"
    }
  ]
}
"""

def main() -> int:
    parser = argparse.ArgumentParser(description="Export supplier and offer import templates.")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    
    base = imports_dir()
    base.mkdir(parents=True, exist_ok=True)
    
    db_path = get_db_path()
    print("==================================================")
    print(f"ACTIVE DATABASE: {db_path}")
    print("==================================================")
    
    write(base / "suppliers.template.json", SUPPLIERS_TEMPLATE, args.force)
    write(base / "supplier_offers.template.json", OFFERS_TEMPLATE, args.force)
    return 0

def write(path: Path, content: str, force: bool) -> None:
    if path.exists() and not force:
        print(f"Skipped existing file: {path}")
        return
    path.write_text(content, encoding="utf-8")
    print(f"Wrote: {path}")

if __name__ == "__main__":
    raise SystemExit(main())
