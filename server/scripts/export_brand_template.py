from __future__ import annotations

import argparse
from pathlib import Path

from brand_data import imports_dir

BRANDS_TEMPLATE = """name,slug,origin_name_vi,origin_code,logo_url,website_url,brand_type,market_tier,base_trust_score,used_market_risk_modifier,categories,notes
Example Brand,example-brand,Việt Nam,VN,/assets/brands/example-brand.svg,,OTHER,UNKNOWN,50,0,OTHER,
"""

CATEGORIES_TEMPLATE = """brand_slug,brand_name,category
example-brand,Example Brand,OTHER
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Export Silicon Hustle brand CSV templates.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing template files.")
    args = parser.parse_args()
    base = imports_dir()
    base.mkdir(parents=True, exist_ok=True)
    write_template(base / "brands_template.csv", BRANDS_TEMPLATE, args.force)
    write_template(base / "brand_categories_template.csv", CATEGORIES_TEMPLATE, args.force)
    return 0


def write_template(path: Path, content: str, force: bool) -> None:
    if path.exists() and not force:
        print(f"Skipped existing file: {path}")
        return
    path.write_text(content, encoding="utf-8")
    print(f"Wrote: {path}")


if __name__ == "__main__":
    raise SystemExit(main())
