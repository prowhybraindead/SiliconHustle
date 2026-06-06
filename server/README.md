# Silicon Hustle Backend

FastAPI backend for the Silicon Hustle MVP foundation.

## Setup

```bash
cd game/server
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

## Environment Variables

- `DATABASE_URL`: SQLite by default, `sqlite:///./silicon_hustle.db`.
- `FRONTEND_ORIGIN`: CORS origin for local or deployed frontend.
- `NESTYAI_BASE_URL`: future NestyAI base URL.
- `NESTYAI_API_KEY`: future server-only API key.
- `NESTYAI_MODEL_DEFAULT`: future default model name.
- `FX_ENABLED`: Enable/disable currency and FX services (defaults to `true`).
- `FX_EXTERNAL_CALLS_ENABLED`: Set to `false` in offline mode/tests to bypass remote provider requests (defaults to `true`).
- `FX_PRIMARY_PROVIDER`: Primary external rate source (`frankfurter` by default).
- `FX_FALLBACK_PROVIDER`: Fallback external rate source (`exchangerate_api_open_access` by default).
- `FX_CACHE_TTL_SECONDS`: Cache duration for external rates in seconds (6 hours/`21600` by default).
- `FX_STATIC_FALLBACK_ENABLED`: Enable/disable local static rates fallback when offline (defaults to `true`).
- `FX_SPREAD_PERCENT_DEFAULT`: Default exchange markup spread percent (defaults to `1.5`).
- `FX_ATTRIBUTION_TEXT`: Attribution disclaimer text for foreign exchange rates.


## Database

Local SQLite DB file defaults to:

```text
game/server/silicon_hustle.db
```

Tables are created on startup. Seed data is idempotent and includes hardware products, suppliers, and supplier offers.

## API Overview

- `GET /health`
- `GET /api/health`
- `GET|POST /api/save-games`
- `GET /api/save-games/{save_game_id}/state`
- `POST /api/save-games/{save_game_id}/autosave`
- `GET /api/brands`
- `GET /api/brands/{brand_id}`
- `GET /api/hardware-products`
- `GET /api/hardware-products/{product_id}`
- `GET|POST /api/save-games/{save_game_id}/inventory`
- `POST /api/save-games/{save_game_id}/inventory/{inventory_unit_id}/tests/basic-check`
- `POST /api/save-games/{save_game_id}/inventory/{inventory_unit_id}/tests/benchmark`
- `POST /api/save-games/{save_game_id}/inventory/{inventory_unit_id}/tests/stress-test`
- `POST /api/save-games/{save_game_id}/inventory/{inventory_unit_id}/tests/full-inspection`
- `GET /api/save-games/{save_game_id}/progression`
- `GET /api/save-games/{save_game_id}/progression/upgrades`
- `POST /api/save-games/{save_game_id}/progression/upgrades/{upgrade_key}/purchase`
- `GET|POST /api/save-games/{save_game_id}/staff`
- `GET /api/save-games/{save_game_id}/staff/summary`
- `GET /api/save-games/{save_game_id}/staff/assignments`
- `POST /api/save-games/{save_game_id}/staff/{staff_id}/assign`
- `POST /api/save-games/{save_game_id}/staff/candidates/generate`
- `GET /api/suppliers`
- `GET /api/supplier-offers`
- `GET|POST /api/save-games/{save_game_id}/purchase-orders`
- `POST /api/save-games/{save_game_id}/purchase-orders/{purchase_order_id}/receive`
- `POST /api/save-games/{save_game_id}/customers/generate-sample`
- `GET /api/save-games/{save_game_id}/customers`
- `GET /api/save-games/{save_game_id}/customer-requests`
- `GET /api/save-games/{save_game_id}/customer-conversations`
- `POST /api/save-games/{save_game_id}/customer-requests/{request_id}/conversation`
- `GET /api/save-games/{save_game_id}/customer-conversations/{conversation_id}`
- `GET /api/save-games/{save_game_id}/customer-conversations/{conversation_id}/messages`
- `POST /api/save-games/{save_game_id}/customer-conversations/{conversation_id}/messages`
- `POST /api/save-games/{save_game_id}/customer-conversations/{conversation_id}/quick-reply`
- `POST /api/save-games/{save_game_id}/customer-conversations/{conversation_id}/assign-staff`
- `POST /api/save-games/{save_game_id}/customer-conversations/{conversation_id}/send-quote/{quote_id}`
- `POST /api/save-games/{save_game_id}/customer-conversations/{conversation_id}/ready-to-order`
- `POST /api/save-games/{save_game_id}/customer-conversations/{conversation_id}/close`
- `GET /api/customer-personas`
- `GET /api/customer-personas/{persona_type}`
- `POST /api/save-games/{save_game_id}/customers/{customer_id}/persona`
- `POST /api/save-games/{save_game_id}/customer-requests/{request_id}/evaluate-quotes`
- `GET|POST /api/save-games/{save_game_id}/quotes`
- `GET|PATCH /api/save-games/{save_game_id}/quotes/{quote_id}`
- `POST /api/save-games/{save_game_id}/customer-requests/{request_id}/generate-quote`
- `POST /api/save-games/{save_game_id}/quotes/{quote_id}/reserve`
- `POST /api/save-games/{save_game_id}/quotes/{quote_id}/release`
- `POST /api/save-games/{save_game_id}/quotes/{quote_id}/accept`
- `GET|POST /api/save-games/{save_game_id}/orders`
- `GET /api/save-games/{save_game_id}/orders/{order_id}`
- `GET /api/save-games/{save_game_id}/quotes/{quote_id}/compatibility`
- `GET /api/save-games/{save_game_id}/orders/{order_id}/compatibility`
- `POST /api/compatibility/evaluate`
- `POST /api/save-games/{save_game_id}/orders/{order_id}/start-build`
- `POST /api/save-games/{save_game_id}/orders/{order_id}/run-build-test`
- `POST /api/save-games/{save_game_id}/orders/{order_id}/deliver`
- `GET /api/save-games/{save_game_id}/orders/{order_id}/fulfillment-events`
- `POST /api/save-games/{save_game_id}/orders/{order_id}/cancel`
- `GET /api/save-games/{save_game_id}/warranty-claims`
- `POST /api/save-games/{save_game_id}/orders/{order_id}/warranty-claims`
- `GET /api/save-games/{save_game_id}/warranty-claims/{claim_id}`
- `POST /api/save-games/{save_game_id}/warranty-claims/{claim_id}/start-diagnosis`
- `POST /api/save-games/{save_game_id}/warranty-claims/{claim_id}/complete-diagnosis`
- `POST /api/save-games/{save_game_id}/warranty-claims/{claim_id}/approve`
- `POST /api/save-games/{save_game_id}/warranty-claims/{claim_id}/reject`
- `POST /api/save-games/{save_game_id}/warranty-claims/{claim_id}/resolve/repair`
- `POST /api/save-games/{save_game_id}/warranty-claims/{claim_id}/resolve/replace`
- `POST /api/save-games/{save_game_id}/warranty-claims/{claim_id}/resolve/refund`
- `POST /api/save-games/{save_game_id}/warranty-claims/{claim_id}/resolve/rma`
- `POST /api/save-games/{save_game_id}/warranty-claims/{claim_id}/close`
- `GET /api/save-games/{save_game_id}/warranty-claims/{claim_id}/events`
- `GET /api/save-games/{save_game_id}/reviews`
- `GET /api/save-games/{save_game_id}/reviews/{review_id}`
- `POST /api/save-games/{save_game_id}/reviews/generate`
- `POST /api/save-games/{save_game_id}/orders/{order_id}/generate-review`
- `POST /api/save-games/{save_game_id}/resale/listings/{listing_id}/generate-review`
- `POST /api/save-games/{save_game_id}/warranty/claims/{claim_id}/generate-review`
- `GET /api/save-games/{save_game_id}/reputation/summary`
- `GET /api/fx/supported-currencies`
- `GET /api/fx/rates`
- `POST /api/fx/rates/refresh`
- `GET /api/fx/convert`
- `GET /api/fx/attribution`


## Currency / FX Rates Workflow

VND is the game's base accounting currency. All game-wide cash tracking, inventory values, and shop finances are calculated in VND.

1. **Exchange Rates Definition**: Rates represent `1 foreign_currency = X VND` (`rate_to_vnd`). For example, 1 USD = 25,400 VND. Stored in DB as `base_currency = foreign_currency` and `quote_currency = VND`.
2. **Provider Hierarchy**: Rates are queried from Frankfurter API first, falling back to ExchangeRate-API Open Access. If both fail or external calls are disabled, the system reads the latest cached DB rate (valid for 6 hours). If no cached rate is found, it falls back to hardcoded static rates.
3. **Transaction Snapshots**: Quotes, Orders, and Purchase Orders capture an immutable snapshot of exchange rates (`fx_rate_to_vnd`, `fx_provider`, `fx_fetched_at`, `fx_is_fallback`) at creation. Converted prices are stored statically on the entities to ensure past transaction values remain accurate and are never recalculated when current live rates update.
4. **Fees and Spread**:
   - Foreign Suppliers: Purchase orders in foreign currencies (e.g. USD/CNY) increase the VND cash deduction by the supplier's spread and flat/percentage fees.
   - Customers: Foreign customer budgets are converted using the current rate adjusted by the spread. Customers have a ~10-15% chance to prefer a foreign currency.

## Customer Persona / Build Preference Workflow

Customer persona scoring is heuristic gameplay logic. It makes requests feel different by emphasizing price sensitivity, used-part tolerance, reliability, aesthetics, and brand preference. Quotes are scored with fit metadata and an acceptance chance so the UI can show why a buyer is likely to say yes or no.

This is not AI customer chat, not real sales advice, and not a psychological profile system.

## Customer Conversation / Sales Chat Workflow

Customer conversations are rule-based and scripted, not AI-generated. Opening a conversation for a request seeds a safe showroom thread with customer intent, budget/use-case hints, and intent metadata. Players or staff can use quick replies to ask about budget, use case, used parts, warranty tradeoffs, or quote readiness, and then attach a generated quote inside the same conversation.

Conversation messages store gameplay-safe text, sender labels, action tags, and quote references only. No PIN/token data or hidden condition data is exposed. The flow is intentionally lightweight so future AI text generation can plug in later without changing the business rules that govern quote generation, acceptance, or order conversion.

## Dynamic Market Events Workflow

Simulated dynamic market shifts (e.g. Crypto Mining Boom, Wafer Shortage) are save-game scoped and affect product retail, used, and supplier prices.

1. **Stacking and Clamping**: Market events match components null-safely by category, brand (via `brand_ref.slug` or slugified `brand` name), origin code, currency, or specific product ID. Active event multipliers stack multiplicatively. The final combined multiplier is clamped between `[0.35 - 3.5]`. MSRP pricing (`latest_msrp_vnd`) acts as a static reference and is **never** adjusted.
2. **Day Advancement and Limits**: Advancing the day via `/api/save-games/{id}/advance-day` expires old active events (where `ends_on_day < game_day`) first. A new random event can auto-generate with a `20%` chance, but only if the current active event count is below `market_max_active_events` (5). If at or above the limit, auto-generation is skipped.
3. **Purchase Order Snapshots**: Purchase orders capture and snapshot the final market-adjusted VND unit price at the time of creation. Subtotal and final totals are computed from these snapshotted prices and remain immutable. Future market changes do not modify existing purchase order totals. Active market event titles are stored in the database as a JSON string list.
4. **AI Debug Data Safety**: AI-assisted generation stores only a small safe summary in `ai_prompt_context_json` (`game_day` and `active_events_count`). Stored `ai_raw_proposal_json` is sanitized, allowing only a whitelist of expected keys and truncating string lengths to 500 characters. No secrets, DB dumps, or full customer/inventory records are ever stored.
5. **Optional Save Game Pricing**: Both the `/api/hardware-products` and `/api/supplier-offers` endpoints accept an optional `save_game_id`. If omitted, they return baseline prices with a multiplier of 1.0, empty active event titles, and no adjustments.


## Quote Workflow Rule

Generated quotes prefer `READY_FOR_SALE` inventory and fall back to catalog placeholder items when stock is missing. Reserving a quote moves linked inventory units to `RESERVED`. Releasing returns them to `READY_FOR_SALE`. Accepting a quote creates an `ACCEPTED` order, sets the quote to `CONVERTED_TO_ORDER`, marks the customer request `ACCEPTED`, and moves linked inventory units to `INSTALLED_IN_BUILD`.

## Build / Delivery Workflow

Accepted orders move through `ACCEPTED -> IN_PROGRESS -> TESTING -> DELIVERED`. Starting a build creates a `BUILD_STARTED` fulfillment event. Running a build test calculates build quality, final test score, warranty risk, and creates a `BUILD_TESTED` event. Delivery creates a `DELIVERED` event, adds customer payment to save cash, updates reputation, marks linked inventory units `SOLD`, and completes the linked customer request.

Economy rule: supplier purchase orders deduct cash when ordered. Delivery adds customer revenue. Delivery does not deduct inventory costs again.

## Compatibility / Build Quality Workflow

Compatibility is a lightweight gameplay heuristic, not a PCPartPicker-style validator or external benchmark system. The service checks socket and memory fit, PSU headroom, thermal sufficiency, bottleneck balance, case form-factor fit, and used/refurbished part risk. Quote and order reads surface the snapshot, and build testing uses the score to gently influence quality and warranty risk without blocking the normal flow.

Hidden condition data remains server-side only. Compatibility warnings are gameplay-facing summaries and do not expose `hidden_condition_json`.

## Warranty / RMA Workflow

Delivery marks an order warranty-eligible and sets a 30-day warranty expiry. Warranty claims can only be opened against delivered orders. Claim diagnosis uses order test scores, warranty risk, inventory condition, grade, and inspection confidence to create a simplified diagnostic summary and recommended resolution.

Resolution actions are gameplay actions: repair deducts repair cost, replacement consumes matching `READY_FOR_SALE` stock when available, refund deducts reimbursement, and RMA deducts shipping before later closure. Claim events form the warranty timeline, and save-game state exposes warranty queue counts and recent warranty events for the dashboard.

QA invariants: hidden condition data never appears in public responses, mutating save actions must use `X-Profile-Unlock-Token` when a PIN-locked profile is attached, and historical transactions keep their snapshot VND values rather than being recomputed from current FX or market state.

## Review / Reputation Workflow

The backend stores lightweight customer feedback records after three outcomes:

- `ORDER_DELIVERY`
- `RESALE_SALE`
- `WARRANTY_RMA`

Reviews are generated by rule-based templates, not AI text generation. Each review stores a 1-5 rating, a sentiment label, safe source snapshots, and a clamped reputation delta. Duplicate generation for the same source is idempotent and does not double-apply reputation. Hidden inventory condition data is never exposed through review APIs.

## Staff Assignment Foundation

Staff members are save-game scoped and include role, availability, morale, fatigue, salary, traits, and skill ratings. Players can generate candidates, hire or fire staff, inspect summary/assignment logs, and send optional staff support into safe refurbish and resale flows without changing the base gameplay loop.

## Progression / Shop Upgrade Foundation

Shop upgrades are defined in a static registry and purchased per save game. Purchased upgrades persist in `purchased_shop_upgrades`, while the full catalog is derived from code so balancing stays simple. Upgrades currently cover storage, test bench, refurbish, supplier, resale, warranty, staff, customer, market, and operations improvements. Effects aggregate additively, with boolean effects turning on when any purchased upgrade provides them.

## Brand Master Data

Brand master data uses two normalized tables:

- `brands`: one row per brand with slug, origin metadata, logo path, website, brand type, market tier, base trust, used-market risk modifier, and notes.
- `brand_categories`: many-to-many category mappings with a unique `(brand_id, category)` constraint.

Hardware products keep the legacy `brand` string and can optionally link to `brand_id` and `chip_vendor_brand_id`. Product responses include `brand_ref`, `chip_vendor_brand`, and `effective_logo_url` while preserving the old `brand` field.

Validate CSV files:

```bash
cd game/server
python scripts/validate_brands.py
```

Import CSV files:

```bash
cd game/server
python scripts/import_brands.py
```

The scripts read standard names (`brands_normalized.csv`, `brand_categories.csv`) and the current prefixed files (`silicon_hustle_brands_normalized.csv`, `silicon_hustle_brand_categories.csv`). Import is idempotent, does not overwrite CSVs, does not scrape/download logos, and treats missing logo files as warnings.

Template export:

```bash
cd game/server
python scripts/export_brand_template.py
python scripts/export_brand_template.py --force
```

Brand API filters for `GET /api/brands`: `category`, `q`, `market_tier`, `brand_type`, and `origin_code`.

## Product Catalog Import

Product catalog import reads normalized local JSON, supporting v1 and v2 files (such as `silicon_hustle_hardware_products_v2_normalized.json` or standard `hardware_products_v2_normalized.json`). Raw/debug CSVs stay untouched for traceability.

A `--file` argument is supported to specify the source of truth catalog JSON file:

```bash
cd game/server
# Validate v2 catalog
python scripts/validate_hardware_products.py --file data/imports/silicon_hustle_hardware_products_v2_normalized.json
# Import v2 catalog
python scripts/import_hardware_products.py --file data/imports/silicon_hustle_hardware_products_v2_normalized.json
# Export product template
python scripts/export_hardware_product_template.py
```

Validation requires `brand_slug` and optional `chip_vendor_slug` to exist in Brand master data, accepts `STORAGE` and `WATER_COOLING`, checks gameplay score ranges, keeps pricing null when absent, and warns for missing source URLs/images/release years. Import upserts by product `slug`, stores `real_specs_json` and `game_balance_json` separately, maps game balance into legacy score columns, and preserves existing gameplay fields.

Hardware API filters for `GET /api/hardware-products`: `category`, `brand_id`, `brand_slug`, `chip_vendor_slug`, `q`, `data_confidence`, `origin_code`, `min_performance_score`, and `max_power_watts`.

## Product Prices Baseline & Snapshots

Product prices baseline history is managed through a snapshot-based database table `product_price_snapshots`, with the latest current prices cached as denormalized fields on the `HardwareProduct` model (`latest_local_retail_vnd`, `latest_used_market_vnd`, `latest_supplier_cost_vnd`, `latest_msrp_vnd`, `latest_price_updated_at`) for UI/API performance.

### Exporter & Template
To export a CSV template with the expected headers:
```bash
python scripts/export_product_price_template.py
```
This generates `server/data/imports/product_prices.template.csv`.

### Validation
To validate a prices CSV file (`product_prices.csv` by default, or another file specified by `--file`):
```bash
python scripts/validate_product_prices.py [--file path/to/file] [--strict]
```
If the price CSV is missing, it exits gracefully with code 0 unless the `--strict` flag is specified (which fails with exit code 1).

### Import
To import prices from the CSV file:
```bash
python scripts/import_product_prices.py [--file path/to/file]
```
The script performs the following actions:
1. Prints the active `DATABASE_URL`, resolved SQLite DB path, and import file path before writing.
2. Checks for identical snapshot records (`product_slug`, `price_type`, `region`, `source_name`, `observed_at`, `currency`, `amount`) for idempotency.
3. Automatically converts foreign currency amounts using the FX Rate foundation and stores the conversion rates and metadata.
4. Updates `is_current` grouping logic on `(product_slug, price_type, region, source_name)` by marking previous snapshots as `is_current=false` if a newer snapshot is imported.
5. Updates the corresponding cached columns on `HardwareProduct` with the newest active baseline prices.

### API Endpoint
The REST endpoint `GET /api/product-prices` allows querying the baseline history.
Query parameters: `product_slug`, `product_id`, `price_type`, `region`, `current_only`, `currency`, `confidence`.
By default, `current_only` is `true` to avoid fetching unnecessary historical rows.

### Duplicates Diagnostic Script
To search the database for duplicate products by slug or name similarities:
```bash
python scripts/find_duplicate_products.py
```

## Tests

```bash
cd game/server
pytest
```

Covered flows include save creation, catalog seed, brand normalization helpers, Brand API listing/filtering, hardware product brand references, product JSON validation helpers, `STORAGE`/`WATER_COOLING` category validation, unknown brand/chip vendor validation, unknown used inventory metrics, test bench reveal, purchase order receiving, sample customer generation, quote generation, quote reservations, release, acceptance, double-accept prevention, untested-used warranty risk, build start, build test, delivery economy/reputation update, inventory sold marking, request completion, double-delivery prevention, warranty claim intake, diagnosis, approval, rejection, repair, refund, replacement, RMA, claim event tracking, and FX services (supported currencies, Frankfurter/ExchangeRate-API provider layers, 6-hour caching, offline/testing static fallback rates, customer foreign budget generation, supplier PO cash conversions, quote/order snapshotting, and manual refresh endpoints).
