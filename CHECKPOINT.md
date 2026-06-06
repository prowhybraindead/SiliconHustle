# Silicon Hustle Checkpoint

Date: 2026-06-04

Current state:

- Frontend: Vite + React + TypeScript dashboard game.
- Backend: FastAPI + SQLAlchemy + SQLite.
- Main loops implemented:
  - Save game management.
  - Hardware catalog and inventory.
  - Supplier purchase orders.
  - Customer generation and quote/build proposals.
  - Order build, test, and delivery workflow.
  - Warranty/RMA claim workflow after delivery.
  - Brand master data import/API/frontend display.
  - Product catalog import/API/frontend catalog display.
- Quote flow:
  - Customer request -> Generate Quote -> Reserve -> Accept -> Order.
- Order flow:
  - Accepted order -> Start Build -> Run Build Test -> Deliver.
- Warranty flow:
  - Delivered order -> Open Claim -> Diagnose -> Approve/Reject -> Repair/Replace/Refund/RMA -> Close.
- Brand master flow:
  - Validate local CSV -> Import idempotently -> Link seeded hardware products -> Browse/filter `/brands`.
- Product catalog flow:
  - Validate normalized JSON -> Import idempotently -> Link Brand/chip vendor -> Browse/filter `/catalog`.

Important rules:

- Purchase orders deduct cash when created.
- Delivery adds customer payment to save-game cash.
- Linked inventory units move to `INSTALLED_IN_BUILD` on quote accept and to `SOLD` on delivery.
- Delivered orders become warranty-eligible for a simplified 30-day period.
- Warranty repair/replacement/refund/RMA can deduct cash and update reputation.
- Replacement tries to consume matching `READY_FOR_SALE` inventory.
- Brand CSV files currently use `silicon_hustle_*.csv` names; scripts support both those and the standard prompt names.
- Product JSON/CSV files currently use `silicon_hustle_hardware_products_*` names; scripts support both those and the standard prompt names.
- Missing brand logos are warnings only. UI falls back to initials.
- Product pricing stays null when missing; no prices are invented.
- `real_specs_json` and `game_balance_json` are stored separately.
- No deep PC compatibility scoring yet.
- No market pricing simulation yet.
- NestyAI is still placeholder-only.

Useful commands:

```bash
cd game/server
pytest
uvicorn app.main:app --reload
```

```bash
cd game
npm.cmd run dev
npm.cmd run build
```

Open items for next session:

- Deeper compatibility and build validation.
- Deeper warranty balance: supplier-specific policies, customer happiness, fault attribution, and time delays.
- Market pricing simulation and supplier offers from imported catalog data.
- AI-assisted summaries and negotiation later.

Validation completed this checkpoint:

- Brand validation: `python scripts/validate_brands.py` -> 143 brands, 212 mappings, 0 hard errors, warnings for missing websites/logos.
- Brand import: `python scripts/import_brands.py` -> first run created 143 brands and linked 212 mappings; second run created 0 and skipped 212 existing links.
- Product validation: `python scripts/validate_hardware_products.py` -> 169 products, 0 hard errors, warnings for null pricing/missing images/source URLs/release years.
- Product import: `python scripts/import_hardware_products.py` -> first run created 169 products; second run skipped 169 existing products.
- Backend: `pytest` -> 25 passed.
- Frontend: `npm.cmd run build` -> passed.

Portable note:

- `node_modules`, `server/.venv`, and `dist` were recreated to validate the new work. They can be deleted again before copying if anh wants a lighter folder.
