from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.models import entities  # noqa: F401

    try:
        Base.metadata.create_all(bind=engine)
        _apply_sqlite_dev_migrations()
    except OperationalError as exc:
        if "readonly database" not in str(exc).lower():
            raise


def _apply_sqlite_dev_migrations() -> None:
    if not settings.database_url.startswith("sqlite"):
        return

    order_columns = {
        "started_at": "DATETIME",
        "testing_started_at": "DATETIME",
        "delivered_at": "DATETIME",
        "build_quality_score": "INTEGER",
        "final_test_score": "INTEGER",
        "final_warranty_risk": "VARCHAR(40)",
        "reputation_delta": "INTEGER",
        "delivery_summary": "TEXT",
        "warranty_eligible": "BOOLEAN DEFAULT 0",
        "warranty_expires_at": "DATETIME",
        "warranty_claim_count": "INTEGER DEFAULT 0",
        "warranty_status": "VARCHAR(80)",
        "last_warranty_event_at": "DATETIME",
    }
    hardware_columns = {
        "slug": "VARCHAR(180)",
        "brand_id": "INTEGER",
        "chip_vendor_brand_id": "INTEGER",
        "origin_name_vi": "VARCHAR(120)",
        "origin_code": "VARCHAR(12)",
        "source_name": "VARCHAR(120)",
        "source_url": "VARCHAR(300)",
        "data_confidence": "VARCHAR(40)",
        "real_specs_json": "JSON",
        "game_balance_json": "JSON",
        "base_local_price_vnd": "INTEGER",
        "base_used_price_vnd": "INTEGER",
        "supplier_cost_vnd": "INTEGER",
        "notes": "TEXT",
        "latest_local_retail_vnd": "INTEGER",
        "latest_used_market_vnd": "INTEGER",
        "latest_supplier_cost_vnd": "INTEGER",
        "latest_msrp_vnd": "INTEGER",
        "latest_price_updated_at": "DATETIME",
    }
    supplier_columns = {
        "slug": "VARCHAR(120)",
        "supplier_tier": "VARCHAR(40)",
        "supported_brand_slugs_json": "JSON",
        "supported_category_json": "JSON",
        "default_delivery_days": "INTEGER",
    }
    offer_columns = {
        "foreign_unit_price": "FLOAT",
        "foreign_currency": "VARCHAR(10)",
        "quality_risk_modifier": "FLOAT",
        "expires_on_day": "INTEGER",
        "offer_type": "VARCHAR(40)",
    }
    purchase_order_columns = {
        "market_multiplier_snapshot": "FLOAT",
        "market_event_titles_snapshot": "TEXT",
    }
    save_game_columns = {
        "shop_level": "INTEGER DEFAULT 1",
        "shop_xp": "INTEGER DEFAULT 0",
        "shop_name": "VARCHAR(120)",
        "progression_notes": "TEXT",
        "player_profile_id": "INTEGER REFERENCES player_profiles(id)",
        "pin_required": "BOOLEAN DEFAULT 0",
        "last_accessed_at": "DATETIME",
    }
    inventory_columns = {
        "hidden_condition_json": "JSON",
        "refurbish_count": "INTEGER DEFAULT 0",
        "last_refurbished_at": "DATETIME",
        "refurbish_notes": "TEXT",
        "repair_risk_score": "INTEGER",
        "resale_value_estimate_vnd": "INTEGER",
        "ready_for_resale": "BOOLEAN DEFAULT 0",
    }
    customer_columns = {
        "persona_type": "VARCHAR(40)",
        "preference_json": "JSON",
        "preferred_brand_slugs_json": "JSON",
        "disliked_brand_slugs_json": "JSON",
        "accepts_used_parts": "BOOLEAN",
        "warranty_sensitivity": "INTEGER",
        "price_sensitivity": "INTEGER",
        "performance_priority": "INTEGER",
        "aesthetics_priority": "INTEGER",
        "reliability_priority": "INTEGER",
    }
    customer_request_columns = {
        "persona_type": "VARCHAR(40)",
        "preference_json": "JSON",
        "priority_tags_json": "JSON",
        "accepts_used_parts": "BOOLEAN",
        "min_compatibility_score": "INTEGER",
        "min_build_quality_score": "INTEGER",
        "used_part_tolerance": "INTEGER",
        "warranty_expectation_days": "INTEGER",
        "conversation_id": "INTEGER",
        "conversation_status": "VARCHAR(40)",
    }
    quote_columns = {
        "persona_match_score": "INTEGER",
        "price_fit_score": "INTEGER",
        "performance_fit_score": "INTEGER",
        "reliability_fit_score": "INTEGER",
        "aesthetics_fit_score": "INTEGER",
        "used_part_fit_score": "INTEGER",
        "quote_acceptance_chance": "INTEGER",
        "customer_feedback_summary": "TEXT",
        "persona_warnings_json": "JSON",
    }
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    with engine.begin() as connection:
        if "save_games" in table_names:
            existing = {column["name"] for column in inspector.get_columns("save_games")}
            for column, ddl in save_game_columns.items():
                if column not in existing:
                    connection.execute(text(f"ALTER TABLE save_games ADD COLUMN {column} {ddl}"))
        if "inventory_units" in table_names:
            existing = {column["name"] for column in inspector.get_columns("inventory_units")}
            for column, ddl in inventory_columns.items():
                if column not in existing:
                    connection.execute(text(f"ALTER TABLE inventory_units ADD COLUMN {column} {ddl}"))
        if "customers" in table_names:
            existing = {column["name"] for column in inspector.get_columns("customers")}
            for column, ddl in customer_columns.items():
                if column not in existing:
                    connection.execute(text(f"ALTER TABLE customers ADD COLUMN {column} {ddl}"))
        if "customer_requests" in table_names:
            existing = {column["name"] for column in inspector.get_columns("customer_requests")}
            for column, ddl in customer_request_columns.items():
                if column not in existing:
                    connection.execute(text(f"ALTER TABLE customer_requests ADD COLUMN {column} {ddl}"))
        if "quotes" in table_names:
            existing = {column["name"] for column in inspector.get_columns("quotes")}
            for column, ddl in quote_columns.items():
                if column not in existing:
                    connection.execute(text(f"ALTER TABLE quotes ADD COLUMN {column} {ddl}"))
        if "orders" in table_names:
            existing = {column["name"] for column in inspector.get_columns("orders")}
            for column, ddl in order_columns.items():
                if column not in existing:
                    connection.execute(text(f"ALTER TABLE orders ADD COLUMN {column} {ddl}"))
        if "hardware_products" in table_names:
            existing = {column["name"] for column in inspector.get_columns("hardware_products")}
            for column, ddl in hardware_columns.items():
                if column not in existing:
                    connection.execute(text(f"ALTER TABLE hardware_products ADD COLUMN {column} {ddl}"))
        if "suppliers" in table_names:
            existing = {column["name"] for column in inspector.get_columns("suppliers")}
            for column, ddl in supplier_columns.items():
                if column not in existing:
                    connection.execute(text(f"ALTER TABLE suppliers ADD COLUMN {column} {ddl}"))
        if "supplier_offers" in table_names:
            existing = {column["name"] for column in inspector.get_columns("supplier_offers")}
            for column, ddl in offer_columns.items():
                if column not in existing:
                    connection.execute(text(f"ALTER TABLE supplier_offers ADD COLUMN {column} {ddl}"))
        if "purchase_orders" in table_names:
            existing = {column["name"] for column in inspector.get_columns("purchase_orders")}
            for column, ddl in purchase_order_columns.items():
                if column not in existing:
                    connection.execute(text(f"ALTER TABLE purchase_orders ADD COLUMN {column} {ddl}"))
        if "warranty_claims" in table_names:
            existing_columns = {column["name"]: column for column in inspector.get_columns("warranty_claims")}
            rebuild_warranty_claims = (
                "resale_listing_id" not in existing_columns
                or "inventory_unit_id" not in existing_columns
                or "claim_type" not in existing_columns
                or "title" not in existing_columns
                or "description" not in existing_columns
                or "severity" not in existing_columns
                or "claimed_on_day" not in existing_columns
                or "due_on_day" not in existing_columns
                or "resolved_on_day" not in existing_columns
                or "customer_message" not in existing_columns
                or "internal_risk_score" not in existing_columns
                or "estimated_cost_vnd" not in existing_columns
                or "final_cost_vnd" not in existing_columns
                or "resolution_type" not in existing_columns
                or "notes" not in existing_columns
                or existing_columns.get("order_id", {}).get("nullable") is False
                or existing_columns.get("customer_id", {}).get("nullable") is False
            )
            if rebuild_warranty_claims:
                connection.execute(text("PRAGMA foreign_keys=OFF"))
                connection.execute(
                    text(
                        """
                        CREATE TABLE warranty_claims_new (
                            id INTEGER NOT NULL PRIMARY KEY,
                            save_game_id INTEGER NOT NULL,
                            order_id INTEGER,
                            resale_listing_id INTEGER,
                            inventory_unit_id INTEGER,
                            customer_id INTEGER,
                            claim_type VARCHAR(40) NOT NULL DEFAULT 'OTHER',
                            status VARCHAR(40) NOT NULL DEFAULT 'OPEN',
                            claim_reason VARCHAR(40) NOT NULL DEFAULT 'OTHER',
                            title VARCHAR(160) NOT NULL DEFAULT '',
                            complaint_summary TEXT NOT NULL,
                            description TEXT,
                            severity INTEGER NOT NULL DEFAULT 1,
                            claimed_on_day INTEGER NOT NULL DEFAULT 0,
                            due_on_day INTEGER,
                            resolved_on_day INTEGER,
                            customer_message TEXT,
                            internal_risk_score INTEGER NOT NULL DEFAULT 0,
                            estimated_cost_vnd INTEGER NOT NULL DEFAULT 0,
                            final_cost_vnd INTEGER,
                            diagnostic_summary TEXT,
                            resolution_summary TEXT,
                            resolution_type VARCHAR(40),
                            notes TEXT,
                            claimed_at DATETIME NOT NULL,
                            updated_at DATETIME NOT NULL,
                            diagnosed_at DATETIME,
                            resolved_at DATETIME,
                            reimbursement_vnd INTEGER NOT NULL DEFAULT 0,
                            repair_cost_vnd INTEGER NOT NULL DEFAULT 0,
                            replacement_cost_vnd INTEGER NOT NULL DEFAULT 0,
                            rma_shipping_cost_vnd INTEGER NOT NULL DEFAULT 0,
                            reputation_delta INTEGER,
                            warranty_valid BOOLEAN NOT NULL DEFAULT 1,
                            internal_notes TEXT,
                            FOREIGN KEY(save_game_id) REFERENCES save_games(id),
                            FOREIGN KEY(order_id) REFERENCES orders(id),
                            FOREIGN KEY(resale_listing_id) REFERENCES resale_listings(id),
                            FOREIGN KEY(inventory_unit_id) REFERENCES inventory_units(id),
                            FOREIGN KEY(customer_id) REFERENCES customers(id)
                        )
                        """
                    )
                )
                copy_columns = [
                    "id",
                    "save_game_id",
                    "order_id",
                    "resale_listing_id",
                    "inventory_unit_id",
                    "customer_id",
                    "claim_type",
                    "status",
                    "claim_reason",
                    "title",
                    "complaint_summary",
                    "description",
                    "severity",
                    "claimed_on_day",
                    "due_on_day",
                    "resolved_on_day",
                    "customer_message",
                    "internal_risk_score",
                    "estimated_cost_vnd",
                    "final_cost_vnd",
                    "diagnostic_summary",
                    "resolution_summary",
                    "resolution_type",
                    "notes",
                    "claimed_at",
                    "updated_at",
                    "diagnosed_at",
                    "resolved_at",
                    "reimbursement_vnd",
                    "repair_cost_vnd",
                    "replacement_cost_vnd",
                    "rma_shipping_cost_vnd",
                    "reputation_delta",
                    "warranty_valid",
                    "internal_notes",
                ]
                def _claim_column(name: str, fallback: str) -> str:
                    return name if name in existing_columns else f"{fallback} AS {name}"

                select_columns = [
                    _claim_column("id", "NULL"),
                    _claim_column("save_game_id", "NULL"),
                    _claim_column("order_id", "NULL"),
                    _claim_column("resale_listing_id", "NULL"),
                    _claim_column("inventory_unit_id", "NULL"),
                    _claim_column("customer_id", "NULL"),
                    _claim_column("claim_type", "'OTHER'"),
                    _claim_column("status", "'OPEN'"),
                    _claim_column("claim_reason", "'OTHER'"),
                    _claim_column("title", "''"),
                    _claim_column("complaint_summary", "''"),
                    _claim_column("description", "NULL"),
                    _claim_column("severity", "1"),
                    _claim_column("claimed_on_day", "0"),
                    _claim_column("due_on_day", "NULL"),
                    _claim_column("resolved_on_day", "NULL"),
                    _claim_column("customer_message", "NULL"),
                    _claim_column("internal_risk_score", "0"),
                    _claim_column("estimated_cost_vnd", "0"),
                    _claim_column("final_cost_vnd", "NULL"),
                    _claim_column("diagnostic_summary", "NULL"),
                    _claim_column("resolution_summary", "NULL"),
                    _claim_column("resolution_type", "NULL"),
                    _claim_column("notes", "NULL"),
                    _claim_column("claimed_at", "CURRENT_TIMESTAMP"),
                    _claim_column("updated_at", "CURRENT_TIMESTAMP"),
                    _claim_column("diagnosed_at", "NULL"),
                    _claim_column("resolved_at", "NULL"),
                    _claim_column("reimbursement_vnd", "0"),
                    _claim_column("repair_cost_vnd", "0"),
                    _claim_column("replacement_cost_vnd", "0"),
                    _claim_column("rma_shipping_cost_vnd", "0"),
                    _claim_column("reputation_delta", "NULL"),
                    _claim_column("warranty_valid", "1"),
                    _claim_column("internal_notes", "NULL"),
                ]
                column_list = ", ".join(copy_columns)
                select_list = ", ".join(select_columns)
                connection.execute(text(f"INSERT INTO warranty_claims_new ({column_list}) SELECT {select_list} FROM warranty_claims"))
                connection.execute(text("DROP TABLE warranty_claims"))
                connection.execute(text("ALTER TABLE warranty_claims_new RENAME TO warranty_claims"))
                connection.execute(text("CREATE INDEX IF NOT EXISTS ix_warranty_claims_save_game_id ON warranty_claims (save_game_id)"))
                connection.execute(text("CREATE INDEX IF NOT EXISTS ix_warranty_claims_order_id ON warranty_claims (order_id)"))
                connection.execute(text("CREATE INDEX IF NOT EXISTS ix_warranty_claims_resale_listing_id ON warranty_claims (resale_listing_id)"))
                connection.execute(text("CREATE INDEX IF NOT EXISTS ix_warranty_claims_inventory_unit_id ON warranty_claims (inventory_unit_id)"))
                connection.execute(text("CREATE INDEX IF NOT EXISTS ix_warranty_claims_customer_id ON warranty_claims (customer_id)"))
                connection.execute(text("CREATE INDEX IF NOT EXISTS ix_warranty_claims_claim_type ON warranty_claims (claim_type)"))
                connection.execute(text("CREATE INDEX IF NOT EXISTS ix_warranty_claims_status ON warranty_claims (status)"))
                connection.execute(text("CREATE INDEX IF NOT EXISTS ix_warranty_claims_due_on_day ON warranty_claims (due_on_day)"))
                connection.execute(text("PRAGMA foreign_keys=ON"))
            columns = {column["name"]: column for column in inspector.get_columns("hardware_products")}
            if columns.get("msrp_vnd", {}).get("nullable") is False:
                connection.execute(text("PRAGMA foreign_keys=OFF"))
                connection.execute(
                    text(
                        """
                        CREATE TABLE hardware_products_new (
                            id INTEGER NOT NULL PRIMARY KEY,
                            slug VARCHAR(180),
                            name VARCHAR(160) NOT NULL,
                            brand VARCHAR(80) NOT NULL,
                            category VARCHAR(40) NOT NULL,
                            release_year INTEGER,
                            origin_name_vi VARCHAR(120),
                            origin_code VARCHAR(12),
                            base_performance_score INTEGER NOT NULL,
                            base_power_watts INTEGER NOT NULL,
                            base_heat_score INTEGER NOT NULL,
                            base_reliability_score INTEGER NOT NULL,
                            msrp_vnd INTEGER,
                            used_demand_score INTEGER NOT NULL,
                            mining_popularity_score INTEGER NOT NULL,
                            depreciation_rate INTEGER NOT NULL,
                            specs_json JSON,
                            image_url VARCHAR(300),
                            brand_logo_url VARCHAR(300),
                            brand_id INTEGER,
                            chip_vendor_brand_id INTEGER,
                            source_name VARCHAR(120),
                            source_url VARCHAR(300),
                            data_confidence VARCHAR(40),
                            real_specs_json JSON,
                            game_balance_json JSON,
                            base_local_price_vnd INTEGER,
                            base_used_price_vnd INTEGER,
                            supplier_cost_vnd INTEGER,
                            notes TEXT,
                            latest_local_retail_vnd INTEGER,
                            latest_used_market_vnd INTEGER,
                            latest_supplier_cost_vnd INTEGER,
                            latest_msrp_vnd INTEGER,
                            latest_price_updated_at DATETIME,
                            created_at DATETIME NOT NULL,
                            updated_at DATETIME NOT NULL
                        )
                        """
                    )
                )
                copy_columns = [
                    "id",
                    "slug",
                    "name",
                    "brand",
                    "category",
                    "release_year",
                    "origin_name_vi",
                    "origin_code",
                    "base_performance_score",
                    "base_power_watts",
                    "base_heat_score",
                    "base_reliability_score",
                    "msrp_vnd",
                    "used_demand_score",
                    "mining_popularity_score",
                    "depreciation_rate",
                    "specs_json",
                    "image_url",
                    "brand_logo_url",
                    "brand_id",
                    "chip_vendor_brand_id",
                    "source_name",
                    "source_url",
                    "data_confidence",
                    "real_specs_json",
                    "game_balance_json",
                    "base_local_price_vnd",
                    "base_used_price_vnd",
                    "supplier_cost_vnd",
                    "notes",
                    "latest_local_retail_vnd",
                    "latest_used_market_vnd",
                    "latest_supplier_cost_vnd",
                    "latest_msrp_vnd",
                    "latest_price_updated_at",
                    "created_at",
                    "updated_at",
                ]
                column_list = ", ".join(copy_columns)
                connection.execute(text(f"INSERT INTO hardware_products_new ({column_list}) SELECT {column_list} FROM hardware_products"))
                connection.execute(text("DROP TABLE hardware_products"))
                connection.execute(text("ALTER TABLE hardware_products_new RENAME TO hardware_products"))
                connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_hardware_products_name ON hardware_products (name)"))
                connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_hardware_products_slug ON hardware_products (slug)"))
                connection.execute(text("CREATE INDEX IF NOT EXISTS ix_hardware_products_category ON hardware_products (category)"))
                connection.execute(text("PRAGMA foreign_keys=ON"))
