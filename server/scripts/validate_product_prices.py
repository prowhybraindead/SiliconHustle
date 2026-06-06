from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project server/ and scripts/ directories to python path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.database import init_db
from price_data import validate_prices
from supplier_data import get_db_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate product price baseline CSV file")
    parser.add_argument("--file", type=str, default=None, help="Path to product prices CSV file")
    parser.add_argument("--strict", action="store_true", help="Fail with non-zero code if file is missing")
    args = parser.parse_args()

    init_db()
    db_path = get_db_path()

    report = validate_prices(path=args.file)

    print("==================================================")
    print(f"ACTIVE DATABASE: {db_path}")
    print(f"RESOLVED PRICE FILE: {report.path or 'None'}")
    print("==================================================")

    if report.file_missing:
        print(f"No price validation performed: product_prices.csv does not exist yet at: {report.path or 'default path'}.")
        if args.strict:
            print("Strict mode enabled: failing because file is missing.")
            return 1
        return 0

    print("\nProduct Price Validation Report:")
    print(f"- prices checked: {len(report.prices)}")
    print(f"- warnings: {len(report.warnings)}")
    print(f"- errors: {len(report.errors)}")

    if report.warnings:
        print("\nWarnings:")
        for warning in report.warnings[:80]:
            print(f"  WARNING: {warning}")
        if len(report.warnings) > 80:
            print(f"  WARNING: ... {len(report.warnings) - 80} more warnings omitted")

    if report.errors:
        print("\nErrors:")
        for error in report.errors:
            print(f"  ERROR: {error}")
        return 1

    print("\nValidation PASSED successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
