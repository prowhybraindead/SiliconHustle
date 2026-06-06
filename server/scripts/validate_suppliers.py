from __future__ import annotations

import sys
from pathlib import Path

# Add project server/ and scripts/ directories to python path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.database import init_db
from supplier_data import validate_suppliers_and_offers, get_db_path

def main() -> int:
    init_db()
    db_path = get_db_path()
    print("==================================================")
    print(f"ACTIVE DATABASE: {db_path}")
    print("==================================================")
    
    report = validate_suppliers_and_offers()
    print("\nSupplier Import Validation Report:")
    print(f"- suppliers checked: {len(report.suppliers)}")
    print(f"- offers checked: {len(report.offers)}")
    print(f"- warnings: {len(report.warnings)}")
    print(f"- errors: {len(report.errors)}")
    
    if report.warnings:
        print("\nWarnings:")
        for warning in report.warnings:
            print(f"  WARNING: {warning}")
            
    if report.errors:
        print("\nErrors:")
        for error in report.errors:
            print(f"  ERROR: {error}")
        return 1
        
    print("\nValidation PASSED successfully.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
