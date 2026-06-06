from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

# Add project server/ and scripts/ directories to python path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from supplier_data import imports_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Export product price CSV template")
    parser.add_argument("--force", action="store_true", help="Overwrite template file if it already exists")
    args = parser.parse_args()

    output_path = imports_dir() / "product_prices.template.csv"
    if output_path.exists() and not args.force:
        print(f"Template file already exists at: {output_path}. Use --force to overwrite.")
        return 0

    headers = [
        "product_slug",
        "price_type",
        "currency",
        "amount",
        "region",
        "source_name",
        "source_url",
        "observed_at",
        "confidence",
        "notes"
    ]

    sample_rows = [
        {
            "product_slug": "intel-core-i5-14400",
            "price_type": "MSRP",
            "currency": "USD",
            "amount": "185.00",
            "region": "US",
            "source_name": "Intel Ark",
            "source_url": "https://ark.intel.com/content/www/us/en/ark.html",
            "observed_at": "2026-06-04 12:00:00",
            "confidence": "OFFICIAL",
            "notes": "Launch MSRP"
        },
        {
            "product_slug": "intel-core-i5-14400",
            "price_type": "LOCAL_RETAIL",
            "currency": "VND",
            "amount": "4699000",
            "region": "VN",
            "source_name": "Nguyen Kim",
            "source_url": "https://nguyenkim.com",
            "observed_at": "2026-06-04 12:00:00",
            "confidence": "RETAILER",
            "notes": "Retail box price"
        }
    ]

    try:
        with output_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(sample_rows)
        print(f"Successfully exported product prices template to: {output_path}")
    except Exception as e:
        print(f"Error exporting template: {e}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
