from __future__ import annotations

import sys
from pathlib import Path
from collections import defaultdict

# Add project server/ and scripts/ directories to python path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.database import SessionLocal, init_db
from app.models.entities import HardwareProduct
from supplier_data import get_db_path


def normalize_name(name: str) -> str:
    # Lowercase, remove spaces, dashes, special characters
    return "".join(c for c in name.lower() if c.isalnum())


def main() -> int:
    init_db()
    db_path = get_db_path()

    print("==================================================")
    print(f"ACTIVE DATABASE: {db_path}")
    print("==================================================")

    with SessionLocal() as db:
        products = db.query(HardwareProduct).all()

    print(f"Loaded {len(products)} products from database.")

    # 1. Exact name matches
    exact_names = defaultdict(list)
    # 2. Normalized name matches (near duplicates)
    norm_names = defaultdict(list)
    # 3. Slug matches (should not occur in DB due to unique constraints, but checks just in case)
    exact_slugs = defaultdict(list)

    for p in products:
        if p.name:
            exact_names[p.name.strip().lower()].append(p)
            norm_names[normalize_name(p.name)].append(p)
        if p.slug:
            exact_slugs[p.slug.strip().lower()].append(p)

    # Filter out non-duplicates
    dup_names = {k: v for k, v in exact_names.items() if len(v) > 1}
    dup_norm = {k: v for k, v in norm_names.items() if len(v) > 1 and len({p.name for p in v}) > 1}
    dup_slugs = {k: v for k, v in exact_slugs.items() if len(v) > 1}

    print("\n--- Duplicate slugs (exact) ---")
    if not dup_slugs:
        print("No duplicate slugs found.")
    else:
        for slug, plist in dup_slugs.items():
            print(f"Slug: '{slug}' referenced by:")
            for p in plist:
                print(f"  - ID: {p.id}, Name: '{p.name}', Brand: '{p.brand}'")

    print("\n--- Duplicate names (exact) ---")
    if not dup_names:
        print("No duplicate exact names found.")
    else:
        for name, plist in dup_names.items():
            print(f"Name: '{plist[0].name}' referenced by:")
            for p in plist:
                print(f"  - ID: {p.id}, Slug: '{p.slug}', Brand: '{p.brand}'")

    print("\n--- Near-duplicates (normalized name matches) ---")
    if not dup_norm:
        print("No near-duplicate products found.")
    else:
        for norm, plist in dup_norm.items():
            print(f"Normalized: '{norm}' matches these distinct names:")
            for p in plist:
                print(f"  - ID: {p.id}, Name: '{p.name}', Slug: '{p.slug}', Brand: '{p.brand}'")

    print("\nDiagnostics complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
