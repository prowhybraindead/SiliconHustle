from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import (
    BrandCategoryName,
    BrandType,
    ConditionType,
    CustomerArchetype,
    CustomerConversationStage,
    CustomerConversationStatus,
    CustomerRequestStatus,
    ConversationActionType,
    ConversationMessageSender,
    ConversationMessageType,
    Grade,
    HardwareCategory,
    InventorySource,
    InventoryStatus,
    KnowledgeLevel,
    MarketTier,
    OrderStatus,
    OrderFulfillmentEventType,
    PurchaseOrderStatus,
    QuoteItemSource,
    QuoteStatus,
    RequestType,
    RiskTolerance,
    SupplierType,
    SupplierTier,
    TestType,
    WarrantyClaimReason,
    WarrantyClaimStatus,
    WarrantyClaimType,
    WarrantyResolutionType,
    WarrantyEventType,
    ProductPriceType,
    ProductPriceConfidence,
    MarketEventType,
    MarketEventGenerationSource,
    ShopUpgradeCategory,
    UsedPartListingStatus,
    UsedPartNegotiationStatus,
    NegotiationSender,
    RefurbishActionType,
    RefurbishResultStatus,
    ResaleListingStatus,
    ResaleBuyerOfferStatus,
    StaffRole,
    StaffStatus,
    StaffTaskType,
    StaffTrait,
)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)


class ExchangeRate(Base, TimestampMixin):
    __tablename__ = "exchange_rates"

    id: Mapped[int] = mapped_column(primary_key=True)
    base_currency: Mapped[str] = mapped_column(String(10), index=True)
    quote_currency: Mapped[str] = mapped_column(String(10), index=True)
    rate: Mapped[float] = mapped_column(Float)
    provider: Mapped[str] = mapped_column(String(80))
    source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    valid_for_day: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_fallback: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class SaveGame(Base, TimestampMixin):
    __tablename__ = "save_games"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    shop_level: Mapped[int] = mapped_column(Integer, default=1)
    shop_xp: Mapped[int] = mapped_column(Integer, default=0)
    shop_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    progression_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    game_day: Mapped[int] = mapped_column(Integer, default=1)
    cash: Mapped[int] = mapped_column(Integer, default=150_000_000)
    reputation: Mapped[int] = mapped_column(Integer, default=50)
    last_autosave_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    client_state_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    
    player_profile_id: Mapped[int | None] = mapped_column(ForeignKey("player_profiles.id"), nullable=True)
    pin_required: Mapped[bool] = mapped_column(Boolean, default=False)
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    inventory_units: Mapped[list["InventoryUnit"]] = relationship(back_populates="save_game")
    purchase_orders: Mapped[list["PurchaseOrder"]] = relationship(back_populates="save_game")
    customers: Mapped[list["Customer"]] = relationship(back_populates="save_game")
    customer_conversations: Mapped[list["CustomerConversation"]] = relationship(back_populates="save_game", cascade="all, delete-orphan")
    orders: Mapped[list["Order"]] = relationship(back_populates="save_game")
    reviews: Mapped[list["CustomerReview"]] = relationship(back_populates="save_game", cascade="all, delete-orphan")
    quotes: Mapped[list["Quote"]] = relationship(back_populates="save_game")
    market_events: Mapped[list["MarketEvent"]] = relationship(back_populates="save_game")
    player_profile: Mapped["PlayerProfile | None"] = relationship(back_populates="save_games")
    used_part_listings: Mapped[list["UsedPartListing"]] = relationship(back_populates="save_game")
    used_part_negotiations: Mapped[list["UsedPartNegotiation"]] = relationship(back_populates="save_game")
    refurbish_events: Mapped[list["InventoryRefurbishEvent"]] = relationship(back_populates="save_game")
    resale_listings: Mapped[list["ResaleListing"]] = relationship(back_populates="save_game", cascade="all, delete-orphan")
    resale_buyer_offers: Mapped[list["ResaleBuyerOffer"]] = relationship(back_populates="save_game", cascade="all, delete-orphan")
    purchased_shop_upgrades: Mapped[list["PurchasedShopUpgrade"]] = relationship(back_populates="save_game", cascade="all, delete-orphan")
    staff_members: Mapped[list["StaffMember"]] = relationship(back_populates="save_game", cascade="all, delete-orphan")
    staff_assignment_logs: Mapped[list["StaffAssignmentLog"]] = relationship(back_populates="save_game", cascade="all, delete-orphan")

    @property
    def profile_display_name(self) -> str | None:
        return self.player_profile.display_name if self.player_profile else None

    @property
    def is_locked(self) -> bool:
        return bool(self.player_profile.pin_enabled) if self.player_profile else False


class CustomerReview(Base, TimestampMixin):
    __tablename__ = "customer_reviews"
    __table_args__ = (UniqueConstraint("save_game_id", "source_key", name="uq_customer_reviews_save_game_source_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    save_game_id: Mapped[int] = mapped_column(ForeignKey("save_games.id"), index=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), nullable=True, index=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), nullable=True, index=True)
    resale_listing_id: Mapped[int | None] = mapped_column(ForeignKey("resale_listings.id"), nullable=True, index=True)
    warranty_claim_id: Mapped[int | None] = mapped_column(ForeignKey("warranty_claims.id"), nullable=True, index=True)
    source_type: Mapped[str] = mapped_column(String(40), index=True)
    source_key: Mapped[str] = mapped_column(String(120), index=True)
    sentiment: Mapped[str] = mapped_column(String(20), index=True)
    rating: Mapped[int] = mapped_column(Integer, default=3)
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(Text)
    tags_json: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    persona_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    source_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    quote_fit_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    compatibility_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    build_quality_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    warranty_risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    final_price_vnd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reputation_delta: Mapped[int] = mapped_column(Integer, default=0)
    generated_on_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    save_game: Mapped[SaveGame] = relationship(back_populates="reviews")
    customer: Mapped["Customer | None"] = relationship(back_populates="reviews")
    order: Mapped["Order | None"] = relationship(back_populates="reviews")
    resale_listing: Mapped["ResaleListing | None"] = relationship(back_populates="reviews")
    warranty_claim: Mapped["WarrantyClaim | None"] = relationship(back_populates="reviews")


class PurchasedShopUpgrade(Base, TimestampMixin):
    __tablename__ = "purchased_shop_upgrades"
    __table_args__ = (UniqueConstraint("save_game_id", "upgrade_key", name="uq_purchased_shop_upgrades_save_upgrade"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    save_game_id: Mapped[int] = mapped_column(ForeignKey("save_games.id"), index=True)
    upgrade_key: Mapped[str] = mapped_column(String(120), index=True)
    level: Mapped[int] = mapped_column(Integer, default=1)
    purchased_on_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_paid_vnd: Mapped[int] = mapped_column(Integer, default=0)

    save_game: Mapped[SaveGame] = relationship(back_populates="purchased_shop_upgrades")


class Brand(Base, TimestampMixin):
    __tablename__ = "brands"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    origin_name_vi: Mapped[str | None] = mapped_column(String(120), nullable=True)
    origin_code: Mapped[str | None] = mapped_column(String(12), nullable=True, index=True)
    logo_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    website_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    brand_type: Mapped[BrandType] = mapped_column(Enum(BrandType, native_enum=False), default=BrandType.OTHER, index=True)
    market_tier: Mapped[MarketTier] = mapped_column(Enum(MarketTier, native_enum=False), default=MarketTier.UNKNOWN, index=True)
    base_trust_score: Mapped[int] = mapped_column(Integer, default=50)
    used_market_risk_modifier: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    categories: Mapped[list["BrandCategory"]] = relationship(back_populates="brand")
    hardware_products: Mapped[list["HardwareProduct"]] = relationship(back_populates="brand_record", foreign_keys="HardwareProduct.brand_id")
    chip_vendor_products: Mapped[list["HardwareProduct"]] = relationship(
        back_populates="chip_vendor_brand", foreign_keys="HardwareProduct.chip_vendor_brand_id"
    )


class BrandCategory(Base, TimestampMixin):
    __tablename__ = "brand_categories"
    __table_args__ = (UniqueConstraint("brand_id", "category", name="uq_brand_categories_brand_category"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"), index=True)
    category: Mapped[BrandCategoryName] = mapped_column(Enum(BrandCategoryName, native_enum=False), index=True)

    brand: Mapped[Brand] = relationship(back_populates="categories")


class HardwareProduct(Base, TimestampMixin):
    __tablename__ = "hardware_products"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str | None] = mapped_column(String(180), unique=True, index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    brand: Mapped[str] = mapped_column(String(80))
    category: Mapped[HardwareCategory] = mapped_column(Enum(HardwareCategory, native_enum=False), index=True)
    release_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    origin_name_vi: Mapped[str | None] = mapped_column(String(120), nullable=True)
    origin_code: Mapped[str | None] = mapped_column(String(12), nullable=True, index=True)
    base_performance_score: Mapped[int] = mapped_column(Integer)
    base_power_watts: Mapped[int] = mapped_column(Integer)
    base_heat_score: Mapped[int] = mapped_column(Integer)
    base_reliability_score: Mapped[int] = mapped_column(Integer)
    msrp_vnd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    used_demand_score: Mapped[int] = mapped_column(Integer)
    mining_popularity_score: Mapped[int] = mapped_column(Integer)
    depreciation_rate: Mapped[int] = mapped_column(Integer)
    specs_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    brand_logo_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    brand_id: Mapped[int | None] = mapped_column(ForeignKey("brands.id"), nullable=True, index=True)
    chip_vendor_brand_id: Mapped[int | None] = mapped_column(ForeignKey("brands.id"), nullable=True, index=True)
    source_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    data_confidence: Mapped[str | None] = mapped_column(String(40), nullable=True)
    real_specs_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    game_balance_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    base_local_price_vnd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    base_used_price_vnd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    supplier_cost_vnd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Price Baseline Cache (UI/API convenience)
    latest_local_retail_vnd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latest_used_market_vnd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latest_supplier_cost_vnd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latest_msrp_vnd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latest_price_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


    brand_record: Mapped[Brand | None] = relationship(back_populates="hardware_products", foreign_keys=[brand_id])
    chip_vendor_brand: Mapped[Brand | None] = relationship(back_populates="chip_vendor_products", foreign_keys=[chip_vendor_brand_id])

    @property
    def brand_ref(self) -> Brand | None:
        return self.brand_record

    @property
    def effective_logo_url(self) -> str | None:
        if self.brand_record and self.brand_record.logo_url:
            return self.brand_record.logo_url
        return self.brand_logo_url


class InventoryUnit(Base, TimestampMixin):
    __tablename__ = "inventory_units"

    id: Mapped[int] = mapped_column(primary_key=True)
    save_game_id: Mapped[int] = mapped_column(ForeignKey("save_games.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("hardware_products.id"), index=True)
    serial_number: Mapped[str | None] = mapped_column(String(80), nullable=True)
    condition_type: Mapped[ConditionType] = mapped_column(Enum(ConditionType, native_enum=False))
    status: Mapped[InventoryStatus] = mapped_column(Enum(InventoryStatus, native_enum=False), default=InventoryStatus.UNTESTED)
    grade: Mapped[Grade] = mapped_column(Enum(Grade, native_enum=False), default=Grade.UNKNOWN)
    inspection_confidence: Mapped[int] = mapped_column(Integer, default=0)
    purchase_price_vnd: Mapped[int] = mapped_column(Integer, default=0)
    listed_price_vnd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    warranty_months_remaining: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[InventorySource] = mapped_column(Enum(InventorySource, native_enum=False), default=InventorySource.OTHER)
    health_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    performance_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    thermal_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fan_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vram_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stability_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    warranty_risk: Mapped[str | None] = mapped_column(String(40), nullable=True)
    hidden_defect_revealed: Mapped[bool] = mapped_column(Boolean, default=False)
    hidden_condition_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    refurbish_count: Mapped[int] = mapped_column(Integer, default=0)
    last_refurbished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    refurbish_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    repair_risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resale_value_estimate_vnd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ready_for_resale: Mapped[bool] = mapped_column(Boolean, default=False)

    save_game: Mapped[SaveGame] = relationship(back_populates="inventory_units")
    product: Mapped[HardwareProduct] = relationship()
    test_results: Mapped[list["TestResult"]] = relationship(back_populates="inventory_unit")
    refurbish_events: Mapped[list["InventoryRefurbishEvent"]] = relationship(back_populates="inventory_unit", cascade="all, delete-orphan")
    resale_listings: Mapped[list["ResaleListing"]] = relationship(back_populates="inventory_unit", cascade="all, delete-orphan")


class TestResult(Base):
    __tablename__ = "test_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    inventory_unit_id: Mapped[int] = mapped_column(ForeignKey("inventory_units.id"), index=True)
    test_type: Mapped[TestType] = mapped_column(Enum(TestType, native_enum=False), index=True)
    summary: Mapped[str] = mapped_column(String(240))
    raw_result_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    inventory_unit: Mapped[InventoryUnit] = relationship(back_populates="test_results")


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    slug: Mapped[str | None] = mapped_column(String(120), unique=True, index=True, nullable=True)
    type: Mapped[SupplierType] = mapped_column(Enum(SupplierType, native_enum=False))
    supplier_tier: Mapped[SupplierTier | None] = mapped_column(Enum(SupplierTier, native_enum=False), default=SupplierTier.OTHER, nullable=True)
    trust_score: Mapped[int] = mapped_column(Integer)
    relationship_score: Mapped[int] = mapped_column(Integer)
    delivery_days: Mapped[int] = mapped_column(Integer)
    default_delivery_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # FX Extensions
    country_code: Mapped[str | None] = mapped_column(String(3), nullable=True)
    invoice_currency: Mapped[str] = mapped_column(String(10), default="VND")
    fx_spread_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    import_fee_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    payment_fee_flat_vnd: Mapped[int | None] = mapped_column(Integer, nullable=True)

    supported_brand_slugs_json: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    supported_category_json: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    offers: Mapped[list["SupplierOffer"]] = relationship(back_populates="supplier")


class SupplierOffer(Base):
    __tablename__ = "supplier_offers"

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("hardware_products.id"), index=True)
    unit_price_vnd: Mapped[int] = mapped_column(Integer)
    min_order_quantity: Mapped[int] = mapped_column(Integer, default=1)
    available_quantity: Mapped[int] = mapped_column(Integer, default=1)
    warranty_months: Mapped[int] = mapped_column(Integer, default=12)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Expanded fields
    foreign_unit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    foreign_currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    quality_risk_modifier: Mapped[float | None] = mapped_column(Float, nullable=True)
    expires_on_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    offer_type: Mapped[str | None] = mapped_column(String(40), nullable=True)

    supplier: Mapped[Supplier] = relationship(back_populates="offers")
    product: Mapped[HardwareProduct] = relationship()


class PurchaseOrder(Base, TimestampMixin):
    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    save_game_id: Mapped[int] = mapped_column(ForeignKey("save_games.id"), index=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), index=True)
    status: Mapped[PurchaseOrderStatus] = mapped_column(Enum(PurchaseOrderStatus, native_enum=False), default=PurchaseOrderStatus.ORDERED)
    subtotal_vnd: Mapped[int] = mapped_column(Integer, default=0)
    delivery_due_day: Mapped[int] = mapped_column(Integer, default=1)

    # FX snapshotted fields
    invoice_currency: Mapped[str] = mapped_column(String(10), default="VND")
    foreign_subtotal: Mapped[float | None] = mapped_column(Float, nullable=True)
    fx_rate_to_vnd: Mapped[float | None] = mapped_column(Float, nullable=True)
    fx_provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    fx_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fx_is_fallback: Mapped[bool] = mapped_column(Boolean, default=False)
    fx_spread_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    fx_fee_vnd: Mapped[int] = mapped_column(Integer, default=0)
    final_total_vnd: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Market snapshotted fields
    market_multiplier_snapshot: Mapped[float | None] = mapped_column(Float, nullable=True)
    market_event_titles_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)

    save_game: Mapped[SaveGame] = relationship(back_populates="purchase_orders")
    supplier: Mapped[Supplier] = relationship()
    items: Mapped[list["PurchaseOrderItem"]] = relationship(back_populates="purchase_order")


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    purchase_order_id: Mapped[int] = mapped_column(ForeignKey("purchase_orders.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("hardware_products.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price_vnd: Mapped[int] = mapped_column(Integer)
    warranty_months: Mapped[int] = mapped_column(Integer)

    purchase_order: Mapped[PurchaseOrder] = relationship(back_populates="items")
    product: Mapped[HardwareProduct] = relationship()


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    save_game_id: Mapped[int] = mapped_column(ForeignKey("save_games.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    archetype: Mapped[CustomerArchetype] = mapped_column(Enum(CustomerArchetype, native_enum=False))
    knowledge_level: Mapped[KnowledgeLevel] = mapped_column(Enum(KnowledgeLevel, native_enum=False))
    patience: Mapped[int] = mapped_column(Integer)
    negotiation_score: Mapped[int] = mapped_column(Integer)
    risk_tolerance: Mapped[RiskTolerance] = mapped_column(Enum(RiskTolerance, native_enum=False))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    # FX Extensions
    country_code: Mapped[str | None] = mapped_column(String(3), nullable=True)
    preferred_currency: Mapped[str] = mapped_column(String(10), default="VND")
    persona_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    preference_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    preferred_brand_slugs_json: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    disliked_brand_slugs_json: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    accepts_used_parts: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    warranty_sensitivity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price_sensitivity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    performance_priority: Mapped[int | None] = mapped_column(Integer, nullable=True)
    aesthetics_priority: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reliability_priority: Mapped[int | None] = mapped_column(Integer, nullable=True)

    save_game: Mapped[SaveGame] = relationship(back_populates="customers")
    requests: Mapped[list["CustomerRequest"]] = relationship(back_populates="customer")
    reviews: Mapped[list["CustomerReview"]] = relationship(back_populates="customer")
    conversations: Mapped[list["CustomerConversation"]] = relationship(back_populates="customer")


class CustomerRequest(Base, TimestampMixin):
    __tablename__ = "customer_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    request_type: Mapped[RequestType] = mapped_column(Enum(RequestType, native_enum=False))
    budget_vnd: Mapped[int] = mapped_column(Integer)
    use_case: Mapped[str] = mapped_column(String(160))
    target_performance_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    requirements_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    persona_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    preference_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    priority_tags_json: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    accepts_used_parts: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    min_compatibility_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_build_quality_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    used_part_tolerance: Mapped[int | None] = mapped_column(Integer, nullable=True)
    warranty_expectation_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[CustomerRequestStatus] = mapped_column(
        Enum(CustomerRequestStatus, native_enum=False), default=CustomerRequestStatus.NEW
    )

    # FX snapshotted fields
    budget_currency: Mapped[str] = mapped_column(String(10), default="VND")
    foreign_budget_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    budget_fx_rate_to_vnd: Mapped[float | None] = mapped_column(Float, nullable=True)
    conversation_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    conversation_status: Mapped[str | None] = mapped_column(String(40), nullable=True)

    customer: Mapped[Customer] = relationship(back_populates="requests")
    conversations: Mapped[list["CustomerConversation"]] = relationship(back_populates="customer_request")


class CustomerConversation(Base, TimestampMixin):
    __tablename__ = "customer_conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    save_game_id: Mapped[int] = mapped_column(ForeignKey("save_games.id"), index=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), nullable=True, index=True)
    customer_request_id: Mapped[int | None] = mapped_column(ForeignKey("customer_requests.id"), nullable=True, index=True)
    assigned_staff_id: Mapped[int | None] = mapped_column(ForeignKey("staff_members.id"), nullable=True, index=True)
    status: Mapped[CustomerConversationStatus] = mapped_column(
        Enum(CustomerConversationStatus, native_enum=False), default=CustomerConversationStatus.OPEN, index=True
    )
    stage: Mapped[CustomerConversationStage] = mapped_column(
        Enum(CustomerConversationStage, native_enum=False), default=CustomerConversationStage.NEW_REQUEST, index=True
    )
    persona_type: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    title: Mapped[str | None] = mapped_column(String(160), nullable=True)
    customer_mood: Mapped[str | None] = mapped_column(String(80), nullable=True)
    engagement_score: Mapped[int] = mapped_column(Integer, default=50)
    urgency_score: Mapped[int] = mapped_column(Integer, default=50)
    conversion_probability: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detected_budget_vnd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detected_use_case: Mapped[str | None] = mapped_column(String(200), nullable=True)
    detected_preferences_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    accepts_used_parts: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_on_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_on_day: Mapped[int | None] = mapped_column(Integer, nullable=True)

    save_game: Mapped[SaveGame] = relationship(back_populates="customer_conversations")
    customer: Mapped["Customer | None"] = relationship(back_populates="conversations")
    customer_request: Mapped["CustomerRequest | None"] = relationship(back_populates="conversations")
    assigned_staff: Mapped["StaffMember | None"] = relationship()
    messages: Mapped[list["CustomerConversationMessage"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="CustomerConversationMessage.created_at"
    )


class CustomerConversationMessage(Base):
    __tablename__ = "customer_conversation_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("customer_conversations.id"), index=True)
    save_game_id: Mapped[int] = mapped_column(ForeignKey("save_games.id"), index=True)
    sender_type: Mapped[ConversationMessageSender] = mapped_column(
        Enum(ConversationMessageSender, native_enum=False), index=True
    )
    sender_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    staff_id: Mapped[int | None] = mapped_column(ForeignKey("staff_members.id"), nullable=True, index=True)
    message_type: Mapped[ConversationMessageType] = mapped_column(
        Enum(ConversationMessageType, native_enum=False), default=ConversationMessageType.TEXT, index=True
    )
    body: Mapped[str] = mapped_column(Text)
    action_type: Mapped[ConversationActionType | None] = mapped_column(
        Enum(ConversationActionType, native_enum=False), nullable=True, index=True
    )
    quote_id: Mapped[int | None] = mapped_column(ForeignKey("quotes.id"), nullable=True, index=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_on_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    conversation: Mapped[CustomerConversation] = relationship(back_populates="messages")
    staff_member: Mapped["StaffMember | None"] = relationship()
    quote: Mapped["Quote | None"] = relationship()


class Quote(Base, TimestampMixin):
    __tablename__ = "quotes"

    id: Mapped[int] = mapped_column(primary_key=True)
    save_game_id: Mapped[int] = mapped_column(ForeignKey("save_games.id"), index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    customer_request_id: Mapped[int] = mapped_column(ForeignKey("customer_requests.id"), index=True)
    status: Mapped[QuoteStatus] = mapped_column(Enum(QuoteStatus, native_enum=False), default=QuoteStatus.DRAFT)
    title: Mapped[str] = mapped_column(String(160))
    summary: Mapped[str] = mapped_column(Text)
    quoted_price_vnd: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_vnd: Mapped[int] = mapped_column(Integer, default=0)
    estimated_profit_vnd: Mapped[int] = mapped_column(Integer, default=0)
    customer_fit_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    performance_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    value_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    thermal_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reliability_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    persona_match_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price_fit_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    performance_fit_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reliability_fit_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    aesthetics_fit_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    used_part_fit_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quote_acceptance_chance: Mapped[int | None] = mapped_column(Integer, nullable=True)
    customer_feedback_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    persona_warnings_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    warranty_risk: Mapped[str | None] = mapped_column(String(40), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # FX snapshotted fields
    quote_currency: Mapped[str] = mapped_column(String(10), default="VND")
    foreign_quoted_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    fx_rate_to_vnd: Mapped[float | None] = mapped_column(Float, nullable=True)
    fx_provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    fx_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fx_is_fallback: Mapped[bool] = mapped_column(Boolean, default=False)
    fx_spread_percent: Mapped[float | None] = mapped_column(Float, nullable=True)

    save_game: Mapped[SaveGame] = relationship(back_populates="quotes")
    customer: Mapped[Customer] = relationship()
    customer_request: Mapped[CustomerRequest] = relationship()
    items: Mapped[list["QuoteItem"]] = relationship(back_populates="quote")


class QuoteItem(Base):
    __tablename__ = "quote_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    quote_id: Mapped[int] = mapped_column(ForeignKey("quotes.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("hardware_products.id"), index=True)
    inventory_unit_id: Mapped[int | None] = mapped_column(ForeignKey("inventory_units.id"), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price_vnd: Mapped[int] = mapped_column(Integer, default=0)
    unit_cost_vnd: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[QuoteItemSource] = mapped_column(Enum(QuoteItemSource, native_enum=False), default=QuoteItemSource.CATALOG_PLACEHOLDER)
    is_reserved: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    quote: Mapped[Quote] = relationship(back_populates="items")
    product: Mapped[HardwareProduct] = relationship()
    inventory_unit: Mapped[InventoryUnit | None] = relationship()


class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    save_game_id: Mapped[int] = mapped_column(ForeignKey("save_games.id"), index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    request_id: Mapped[int | None] = mapped_column(ForeignKey("customer_requests.id"), nullable=True)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus, native_enum=False), default=OrderStatus.DRAFT)
    quoted_price_vnd: Mapped[int] = mapped_column(Integer, default=0)
    cost_vnd: Mapped[int] = mapped_column(Integer, default=0)
    profit_vnd: Mapped[int] = mapped_column(Integer, default=0)
    customer_fit_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    testing_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    build_quality_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    final_test_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    final_warranty_risk: Mapped[str | None] = mapped_column(String(40), nullable=True)
    reputation_delta: Mapped[int | None] = mapped_column(Integer, nullable=True)
    delivery_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    warranty_eligible: Mapped[bool] = mapped_column(Boolean, default=False)
    warranty_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    warranty_claim_count: Mapped[int] = mapped_column(Integer, default=0)
    warranty_status: Mapped[str | None] = mapped_column(String(80), nullable=True)
    last_warranty_event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # FX snapshotted fields
    order_currency: Mapped[str] = mapped_column(String(10), default="VND")
    foreign_order_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    fx_rate_to_vnd: Mapped[float | None] = mapped_column(Float, nullable=True)
    fx_provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    fx_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fx_is_fallback: Mapped[bool] = mapped_column(Boolean, default=False)
    fx_spread_percent: Mapped[float | None] = mapped_column(Float, nullable=True)

    save_game: Mapped[SaveGame] = relationship(back_populates="orders")
    customer: Mapped[Customer] = relationship()
    request: Mapped[CustomerRequest | None] = relationship()
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order")
    fulfillment_events: Mapped[list["OrderFulfillmentEvent"]] = relationship(back_populates="order")
    warranty_claims: Mapped[list["WarrantyClaim"]] = relationship(back_populates="order")
    reviews: Mapped[list["CustomerReview"]] = relationship(back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    inventory_unit_id: Mapped[int | None] = mapped_column(ForeignKey("inventory_units.id"), nullable=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("hardware_products.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price_vnd: Mapped[int] = mapped_column(Integer, default=0)
    cost_vnd: Mapped[int] = mapped_column(Integer, default=0)

    order: Mapped[Order] = relationship(back_populates="items")
    inventory_unit: Mapped[InventoryUnit | None] = relationship()
    product: Mapped[HardwareProduct] = relationship()


class OrderFulfillmentEvent(Base):
    __tablename__ = "order_fulfillment_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    event_type: Mapped[OrderFulfillmentEventType] = mapped_column(Enum(OrderFulfillmentEventType, native_enum=False), index=True)
    summary: Mapped[str] = mapped_column(String(260))
    raw_result_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    order: Mapped[Order] = relationship(back_populates="fulfillment_events")


class WarrantyClaim(Base):
    __tablename__ = "warranty_claims"

    id: Mapped[int] = mapped_column(primary_key=True)
    save_game_id: Mapped[int] = mapped_column(ForeignKey("save_games.id"), index=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), index=True, nullable=True)
    resale_listing_id: Mapped[int | None] = mapped_column(ForeignKey("resale_listings.id"), index=True, nullable=True)
    inventory_unit_id: Mapped[int | None] = mapped_column(ForeignKey("inventory_units.id"), index=True, nullable=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), index=True, nullable=True)
    claim_type: Mapped[WarrantyClaimType] = mapped_column(
        Enum(WarrantyClaimType, native_enum=False), default=WarrantyClaimType.OTHER, index=True
    )
    status: Mapped[WarrantyClaimStatus] = mapped_column(Enum(WarrantyClaimStatus, native_enum=False), default=WarrantyClaimStatus.OPEN)
    claim_reason: Mapped[WarrantyClaimReason] = mapped_column(Enum(WarrantyClaimReason, native_enum=False), default=WarrantyClaimReason.OTHER)
    title: Mapped[str] = mapped_column(String(160), default="")
    complaint_summary: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[int] = mapped_column(Integer, default=1)
    claimed_on_day: Mapped[int] = mapped_column(Integer, default=0)
    due_on_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resolved_on_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    customer_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    internal_risk_score: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_vnd: Mapped[int] = mapped_column(Integer, default=0)
    final_cost_vnd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    diagnostic_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution_type: Mapped[WarrantyResolutionType | None] = mapped_column(
        Enum(WarrantyResolutionType, native_enum=False), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    claimed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)
    diagnosed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reimbursement_vnd: Mapped[int] = mapped_column(Integer, default=0)
    repair_cost_vnd: Mapped[int] = mapped_column(Integer, default=0)
    replacement_cost_vnd: Mapped[int] = mapped_column(Integer, default=0)
    rma_shipping_cost_vnd: Mapped[int] = mapped_column(Integer, default=0)
    reputation_delta: Mapped[int | None] = mapped_column(Integer, nullable=True)
    warranty_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    order: Mapped[Order | None] = relationship(back_populates="warranty_claims")
    resale_listing: Mapped["ResaleListing | None"] = relationship(back_populates="warranty_claims")
    inventory_unit: Mapped[InventoryUnit | None] = relationship(foreign_keys=[inventory_unit_id])
    customer: Mapped[Customer | None] = relationship()
    items: Mapped[list["WarrantyClaimItem"]] = relationship(back_populates="warranty_claim")
    events: Mapped[list["WarrantyEvent"]] = relationship(back_populates="warranty_claim")
    reviews: Mapped[list["CustomerReview"]] = relationship(back_populates="warranty_claim")


class WarrantyClaimItem(Base, TimestampMixin):
    __tablename__ = "warranty_claim_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    warranty_claim_id: Mapped[int] = mapped_column(ForeignKey("warranty_claims.id"), index=True)
    order_item_id: Mapped[int | None] = mapped_column(ForeignKey("order_items.id"), nullable=True)
    inventory_unit_id: Mapped[int | None] = mapped_column(ForeignKey("inventory_units.id"), nullable=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("hardware_products.id"), nullable=True)
    suspected_issue: Mapped[str | None] = mapped_column(String(160), nullable=True)
    diagnosis_result: Mapped[str | None] = mapped_column(String(220), nullable=True)
    action_taken: Mapped[str | None] = mapped_column(String(120), nullable=True)
    replacement_inventory_unit_id: Mapped[int | None] = mapped_column(ForeignKey("inventory_units.id"), nullable=True)

    warranty_claim: Mapped[WarrantyClaim] = relationship(back_populates="items")
    order_item: Mapped[OrderItem | None] = relationship()
    inventory_unit: Mapped[InventoryUnit | None] = relationship(foreign_keys=[inventory_unit_id])
    replacement_inventory_unit: Mapped[InventoryUnit | None] = relationship(foreign_keys=[replacement_inventory_unit_id])
    product: Mapped[HardwareProduct | None] = relationship()


class WarrantyEvent(Base):
    __tablename__ = "warranty_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    warranty_claim_id: Mapped[int] = mapped_column(ForeignKey("warranty_claims.id"), index=True)
    event_type: Mapped[WarrantyEventType] = mapped_column(Enum(WarrantyEventType, native_enum=False), index=True)
    summary: Mapped[str] = mapped_column(String(260))
    raw_result_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    warranty_claim: Mapped[WarrantyClaim] = relationship(back_populates="events")


class ProductPriceSnapshot(Base, TimestampMixin):
    __tablename__ = "product_price_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("hardware_products.id"), index=True)
    product_slug: Mapped[str] = mapped_column(String(180), index=True)
    price_type: Mapped[str] = mapped_column(String(40), index=True)
    currency: Mapped[str] = mapped_column(String(10), default="VND")
    amount: Mapped[float] = mapped_column(Float)
    amount_vnd: Mapped[int] = mapped_column(Integer)
    fx_rate_to_vnd: Mapped[float | None] = mapped_column(Float, nullable=True)
    fx_provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    fx_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fx_is_fallback: Mapped[bool] = mapped_column(Boolean, default=False)
    region: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    confidence: Mapped[str] = mapped_column(String(40), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    product: Mapped[HardwareProduct] = relationship()


class MarketEvent(Base, TimestampMixin):
    __tablename__ = "market_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    save_game_id: Mapped[int | None] = mapped_column(ForeignKey("save_games.id"), index=True, nullable=True)
    event_type: Mapped[MarketEventType] = mapped_column(Enum(MarketEventType, native_enum=False), index=True)
    title: Mapped[str] = mapped_column(String(160))
    summary: Mapped[str] = mapped_column(Text)
    severity: Mapped[int] = mapped_column(Integer)
    affected_category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    affected_brand_slug: Mapped[str | None] = mapped_column(String(120), nullable=True)
    affected_origin_code: Mapped[str | None] = mapped_column(String(12), nullable=True)
    affected_currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    affected_product_id: Mapped[int | None] = mapped_column(ForeignKey("hardware_products.id"), index=True, nullable=True)
    price_multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    demand_delta: Mapped[int] = mapped_column(Integer, default=0)
    supply_delta: Mapped[int] = mapped_column(Integer, default=0)
    reliability_delta: Mapped[int] = mapped_column(Integer, default=0)
    quality_risk_delta: Mapped[int] = mapped_column(Integer, default=0)
    starts_on_day: Mapped[int] = mapped_column(Integer)
    ends_on_day: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    generation_source: Mapped[MarketEventGenerationSource] = mapped_column(
        Enum(MarketEventGenerationSource, native_enum=False), default=MarketEventGenerationSource.RULE, index=True
    )
    ai_prompt_context_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    ai_raw_proposal_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    raw_effect_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    save_game: Mapped[SaveGame | None] = relationship(back_populates="market_events")
    product: Mapped[HardwareProduct | None] = relationship()


class PlayerProfile(Base, TimestampMixin):
    __tablename__ = "player_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120), index=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    pin_hash: Mapped[str | None] = mapped_column(String(256), nullable=True)
    pin_salt: Mapped[str | None] = mapped_column(String(256), nullable=True)
    pin_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    last_unlocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_unlock_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failed_unlock_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    save_games: Mapped[list[SaveGame]] = relationship(back_populates="player_profile")
    unlock_sessions: Mapped[list["ProfileUnlockSession"]] = relationship(back_populates="player_profile", cascade="all, delete-orphan")


class ProfileUnlockSession(Base, TimestampMixin):
    __tablename__ = "profile_unlock_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("player_profiles.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(256), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)

    player_profile: Mapped[PlayerProfile] = relationship(back_populates="unlock_sessions")


class StaffMember(Base, TimestampMixin):
    __tablename__ = "staff_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    save_game_id: Mapped[int] = mapped_column(ForeignKey("save_games.id"), index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    role: Mapped[StaffRole] = mapped_column(Enum(StaffRole, native_enum=False), index=True)
    status: Mapped[StaffStatus] = mapped_column(Enum(StaffStatus, native_enum=False), default=StaffStatus.AVAILABLE, index=True)
    level: Mapped[int] = mapped_column(Integer, default=1)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    salary_per_day_vnd: Mapped[int] = mapped_column(Integer, default=0)
    morale: Mapped[int] = mapped_column(Integer, default=70)
    fatigue: Mapped[int] = mapped_column(Integer, default=0)
    traits_json: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    sales_skill: Mapped[int] = mapped_column(Integer, default=30)
    marketing_skill: Mapped[int] = mapped_column(Integer, default=30)
    diagnostic_skill: Mapped[int] = mapped_column(Integer, default=30)
    repair_skill: Mapped[int] = mapped_column(Integer, default=30)
    procurement_skill: Mapped[int] = mapped_column(Integer, default=30)
    support_skill: Mapped[int] = mapped_column(Integer, default=30)
    market_skill: Mapped[int] = mapped_column(Integer, default=30)
    speed: Mapped[int] = mapped_column(Integer, default=50)
    carefulness: Mapped[int] = mapped_column(Integer, default=50)
    hired_on_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_assigned_on_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    save_game: Mapped[SaveGame] = relationship(back_populates="staff_members")
    assignment_logs: Mapped[list["StaffAssignmentLog"]] = relationship(back_populates="staff_member", cascade="all, delete-orphan")


class StaffAssignmentLog(Base, TimestampMixin):
    __tablename__ = "staff_assignment_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    save_game_id: Mapped[int] = mapped_column(ForeignKey("save_games.id"), index=True)
    staff_member_id: Mapped[int] = mapped_column(ForeignKey("staff_members.id"), index=True)
    task_type: Mapped[StaffTaskType] = mapped_column(Enum(StaffTaskType, native_enum=False), index=True)
    target_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    target_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    xp_gained: Mapped[int] = mapped_column(Integer, default=0)
    fatigue_gained: Mapped[int] = mapped_column(Integer, default=0)
    effect_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    assigned_on_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    save_game: Mapped[SaveGame] = relationship(back_populates="staff_assignment_logs")
    staff_member: Mapped[StaffMember] = relationship(back_populates="assignment_logs")


class UsedPartListing(Base, TimestampMixin):
    __tablename__ = "used_part_listings"

    id: Mapped[int] = mapped_column(primary_key=True)
    save_game_id: Mapped[int] = mapped_column(ForeignKey("save_games.id"), index=True)
    seller_name: Mapped[str] = mapped_column(String(120))
    product_id: Mapped[int] = mapped_column(ForeignKey("hardware_products.id"), index=True)
    asking_price_vnd: Mapped[int] = mapped_column(Integer)
    estimated_fair_value_vnd: Mapped[int] = mapped_column(Integer)
    min_accept_price_vnd: Mapped[int] = mapped_column(Integer)
    status: Mapped[UsedPartListingStatus] = mapped_column(
        Enum(UsedPartListingStatus, native_enum=False), default=UsedPartListingStatus.AVAILABLE, index=True
    )
    seller_honesty: Mapped[int] = mapped_column(Integer, default=100)
    seller_patience: Mapped[int] = mapped_column(Integer, default=100)
    claimed_condition: Mapped[str | None] = mapped_column(String(240), nullable=True)
    claimed_usage: Mapped[str | None] = mapped_column(String(240), nullable=True)
    claimed_warranty_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    visible_condition_grade: Mapped[str | None] = mapped_column(String(12), nullable=True)
    hidden_condition_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    market_multiplier_at_creation: Mapped[float] = mapped_column(Float, default=1.0)
    created_on_day: Mapped[int] = mapped_column(Integer)
    expires_on_day: Mapped[int] = mapped_column(Integer)
    final_price_vnd: Mapped[int | None] = mapped_column(Integer, nullable=True)

    save_game: Mapped[SaveGame] = relationship(back_populates="used_part_listings")
    product: Mapped[HardwareProduct] = relationship()
    negotiations: Mapped[list["UsedPartNegotiation"]] = relationship(back_populates="listing", cascade="all, delete-orphan")


class UsedPartNegotiation(Base, TimestampMixin):
    __tablename__ = "used_part_negotiations"

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("used_part_listings.id"), index=True)
    save_game_id: Mapped[int] = mapped_column(ForeignKey("save_games.id"), index=True)
    status: Mapped[UsedPartNegotiationStatus] = mapped_column(
        Enum(UsedPartNegotiationStatus, native_enum=False), default=UsedPartNegotiationStatus.OPEN, index=True
    )
    current_offer_vnd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_seller_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    rounds_count: Mapped[int] = mapped_column(Integer, default=0)
    accepted_price_vnd: Mapped[int | None] = mapped_column(Integer, nullable=True)

    listing: Mapped[UsedPartListing] = relationship(back_populates="negotiations")
    save_game: Mapped[SaveGame] = relationship(back_populates="used_part_negotiations")
    messages: Mapped[list["NegotiationMessage"]] = relationship(back_populates="negotiation", cascade="all, delete-orphan")


class NegotiationMessage(Base, TimestampMixin):
    __tablename__ = "negotiation_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    negotiation_id: Mapped[int] = mapped_column(ForeignKey("used_part_negotiations.id"), index=True)
    sender: Mapped[NegotiationSender] = mapped_column(Enum(NegotiationSender, native_enum=False), index=True)
    message: Mapped[str] = mapped_column(Text)
    offer_vnd: Mapped[int | None] = mapped_column(Integer, nullable=True)

    negotiation: Mapped[UsedPartNegotiation] = relationship(back_populates="messages")


class InventoryRefurbishEvent(Base):
    __tablename__ = "inventory_refurbish_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    save_game_id: Mapped[int] = mapped_column(ForeignKey("save_games.id"), index=True)
    inventory_unit_id: Mapped[int] = mapped_column(ForeignKey("inventory_units.id"), index=True)
    action_type: Mapped[RefurbishActionType] = mapped_column(Enum(RefurbishActionType, native_enum=False), index=True)
    status: Mapped[RefurbishResultStatus] = mapped_column(Enum(RefurbishResultStatus, native_enum=False), index=True)
    cost_vnd: Mapped[int] = mapped_column(Integer, default=0)
    duration_days: Mapped[int] = mapped_column(Integer, default=0)
    started_on_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completed_on_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    before_grade: Mapped[Grade | None] = mapped_column(Enum(Grade, native_enum=False), nullable=True)
    after_grade: Mapped[Grade | None] = mapped_column(Enum(Grade, native_enum=False), nullable=True)
    before_condition_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    after_condition_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    health_delta: Mapped[int] = mapped_column(Integer, default=0)
    thermal_delta: Mapped[int] = mapped_column(Integer, default=0)
    fan_delta: Mapped[int] = mapped_column(Integer, default=0)
    vram_delta: Mapped[int] = mapped_column(Integer, default=0)
    stability_delta: Mapped[int] = mapped_column(Integer, default=0)
    cosmetic_delta: Mapped[int] = mapped_column(Integer, default=0)
    risk_delta: Mapped[int] = mapped_column(Integer, default=0)
    resale_value_delta_vnd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summary: Mapped[str] = mapped_column(String(240))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    save_game: Mapped[SaveGame] = relationship(back_populates="refurbish_events")
    inventory_unit: Mapped[InventoryUnit] = relationship(back_populates="refurbish_events")


class ResaleListing(Base, TimestampMixin):
    __tablename__ = "resale_listings"

    id: Mapped[int] = mapped_column(primary_key=True)
    save_game_id: Mapped[int] = mapped_column(ForeignKey("save_games.id"), index=True)
    inventory_unit_id: Mapped[int | None] = mapped_column(ForeignKey("inventory_units.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    asking_price_vnd: Mapped[int] = mapped_column(Integer)
    estimated_market_value_vnd: Mapped[int] = mapped_column(Integer)
    minimum_accept_price_vnd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[ResaleListingStatus] = mapped_column(Enum(ResaleListingStatus, native_enum=False), default=ResaleListingStatus.DRAFT, index=True)
    listing_quality_score: Mapped[int] = mapped_column(Integer, default=50)
    buyer_interest_score: Mapped[int] = mapped_column(Integer, default=50)
    market_multiplier_at_listing: Mapped[float] = mapped_column(Float, default=1.0)
    grade_at_listing: Mapped[str | None] = mapped_column(String(10), nullable=True)
    inspection_confidence_at_listing: Mapped[int | None] = mapped_column(Integer, nullable=True)
    warranty_days_offered: Mapped[int] = mapped_column(Integer, default=0)
    created_on_day: Mapped[int] = mapped_column(Integer)
    expires_on_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sold_on_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    final_sale_price_vnd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reputation_delta: Mapped[int] = mapped_column(Integer, default=0)
    risk_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    save_game: Mapped[SaveGame] = relationship(back_populates="resale_listings")
    inventory_unit: Mapped[InventoryUnit | None] = relationship(back_populates="resale_listings")
    offers: Mapped[list["ResaleBuyerOffer"]] = relationship(back_populates="listing", cascade="all, delete-orphan")
    warranty_claims: Mapped[list["WarrantyClaim"]] = relationship(back_populates="resale_listing")
    reviews: Mapped[list["CustomerReview"]] = relationship(back_populates="resale_listing")


class ResaleBuyerOffer(Base, TimestampMixin):
    __tablename__ = "resale_buyer_offers"

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("resale_listings.id"), index=True)
    save_game_id: Mapped[int] = mapped_column(ForeignKey("save_games.id"), index=True)
    buyer_name: Mapped[str] = mapped_column(String(120))
    offer_price_vnd: Mapped[int] = mapped_column(Integer)
    status: Mapped[ResaleBuyerOfferStatus] = mapped_column(Enum(ResaleBuyerOfferStatus, native_enum=False), default=ResaleBuyerOfferStatus.PENDING, index=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    buyer_patience: Mapped[int] = mapped_column(Integer, default=50)
    buyer_strictness: Mapped[int] = mapped_column(Integer, default=50)
    created_on_day: Mapped[int] = mapped_column(Integer)
    expires_on_day: Mapped[int | None] = mapped_column(Integer, nullable=True)

    listing: Mapped[ResaleListing] = relationship(back_populates="offers")
    save_game: Mapped[SaveGame] = relationship(back_populates="resale_buyer_offers")
