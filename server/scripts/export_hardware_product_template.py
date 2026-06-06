from __future__ import annotations

import argparse
from pathlib import Path

from brand_data import imports_dir

JSON_TEMPLATE = """{
  "products": [
    {
      "slug": "example-gpu",
      "name": "Example GPU",
      "brand_slug": "example-brand",
      "chip_vendor_slug": null,
      "category": "GPU",
      "release_year": null,
      "origin_name_vi": null,
      "origin_code": null,
      "source_name": "Manual curated sheet",
      "source_url": null,
      "data_confidence": "MANUAL",
      "real_specs": {
        "raw_key_specs": "Example key specs",
        "socket_slot": null,
        "power_watts": 120
      },
      "pricing": {
        "msrp_vnd": null,
        "base_local_price_vnd": null,
        "base_used_price_vnd": null,
        "supplier_cost_vnd": null
      },
      "game_balance": {
        "base_performance_score": 50,
        "base_power_watts": 120,
        "base_heat_score": 50,
        "base_reliability_score": 70,
        "used_demand_score": 50,
        "mining_popularity_score": 0,
        "depreciation_rate": 20
      },
      "image_url": null,
      "notes": null
    }
  ]
}
"""

CSV_TEMPLATE = "category,brand,name,key_specs,notes\nGPU,Example Brand,Example GPU,Example key specs,\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Export hardware product import templates.")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    base = imports_dir()
    base.mkdir(parents=True, exist_ok=True)
    write(base / "hardware_products.template.json", JSON_TEMPLATE, args.force)
    write(base / "hardware_products_raw.template.csv", CSV_TEMPLATE, args.force)
    return 0


def write(path: Path, content: str, force: bool) -> None:
    if path.exists() and not force:
        print(f"Skipped existing file: {path}")
        return
    path.write_text(content, encoding="utf-8")
    print(f"Wrote: {path}")


if __name__ == "__main__":
    raise SystemExit(main())
