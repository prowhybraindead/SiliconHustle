from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project server/ and scripts/ directories to python path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.database import SessionLocal, init_db  # noqa: E402
from app.models.entities import Brand  # noqa: E402
from product_data import validate_products  # noqa: E402
from supplier_data import get_db_path  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate hardware products JSON catalog")
    parser.add_argument("--file", type=str, default=None, help="Path to hardware products JSON file")
    args = parser.parse_args()

    init_db()
    db_path = get_db_path()
    
    with SessionLocal() as db:
        brand_slugs = {slug for (slug,) in db.query(Brand.slug).all()}
    
    result = validate_products(brand_slugs, path=args.file)

    print("==================================================")
    print(f"ACTIVE DATABASE: {db_path}")
    print(f"RESOLVED IMPORT FILE: {result.path or 'None'}")
    print("==================================================")

    print("Hardware product validation report")
    print(f"- source JSON: {result.path or 'missing'}")
    print(f"- products checked: {len(result.products)}")
    print(f"- categories count: {dict(result.categories)}")
    print(f"- warning count: {len(result.warnings)}")
    print(f"- hard error count: {len(result.errors)}")
    for warning in result.warnings[:80]:
        print(f"WARNING: {warning}")
    if len(result.warnings) > 80:
        print(f"WARNING: ... {len(result.warnings) - 80} more warnings omitted")
    for error in result.errors:
        print(f"ERROR: {error}")
    return 1 if result.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
