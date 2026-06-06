from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

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
    OrderFulfillmentEventType,
    OrderStatus,
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
    WarrantyEventType,
    WarrantyResolutionType,
    ProductPriceType,
    ProductPriceConfidence,
    RefurbishActionType,
    RefurbishResultStatus,
    ResaleListingStatus,
    ResaleBuyerOfferStatus,
    ShopUpgradeCategory,
    ShopUpgradeStatus,
    StaffRole,
    StaffStatus,
    StaffTaskType,
    StaffTrait,
)


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SaveGameCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class AutosavePayload(BaseModel):
    client_state_json: dict[str, Any] | None = None


class SaveGameRead(OrmModel):
    id: int
    name: str
    shop_level: int = 1
    shop_xp: int = 0
    shop_name: str | None = None
    progression_notes: str | None = None
    game_day: int
    cash: int
    reputation: int
    created_at: datetime
    updated_at: datetime
    last_autosave_at: datetime | None
    client_state_json: dict[str, Any] | None
    player_profile_id: int | None = None
    profile_display_name: str | None = None
    pin_required: bool = False
    is_locked: bool = False


class ShopUpgradeEffectSummary(OrmModel):
    inventory_capacity_bonus: int = 0
    test_confidence_bonus: int = 0
    hidden_defect_reveal_bonus: int = 0
    refurbish_cost_reduction_percent: int = 0
    refurbish_success_bonus: int = 0
    supplier_import_fee_reduction_percent: int = 0
    delivery_days_reduction: int = 0
    resale_buyer_interest_bonus: int = 0
    offer_price_bonus_percent: int = 0
    warranty_risk_reduction_percent: int = 0
    staff_xp_bonus_percent: int = 0
    staff_fatigue_reduction_percent: int = 0
    customer_budget_bonus_percent: int = 0
    reputation_gain_bonus: int = 0
    market_event_visibility_bonus: int = 0
    price_estimate_accuracy_bonus: int = 0
    dashboard_summary_bonus: bool = False
    unlock_shop_level: int = 0


class ShopUpgradeDefinitionRead(OrmModel):
    key: str
    title: str
    description: str
    category: ShopUpgradeCategory
    level: int
    max_level: int
    cost_vnd: int
    required_shop_level: int = 1
    required_upgrade_keys: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    status: ShopUpgradeStatus
    locked_reason: str | None = None
    effects_json: dict[str, Any] = Field(default_factory=dict)
    icon: str | None = None


class PurchasedShopUpgradeRead(OrmModel):
    id: int
    save_game_id: int
    upgrade_key: str
    level: int
    purchased_on_day: int | None = None
    cost_paid_vnd: int
    created_at: datetime
    updated_at: datetime


class ProgressionStateRead(OrmModel):
    shop_level: int
    shop_xp: int
    cash: int
    purchased_upgrades: list[PurchasedShopUpgradeRead]
    available_upgrades: list[ShopUpgradeDefinitionRead]
    locked_upgrades: list[ShopUpgradeDefinitionRead]
    upgrade_effect_summary: ShopUpgradeEffectSummary
    summary: dict[str, Any]
    inventory_capacity_summary: dict[str, int]


class ShopUpgradePurchaseResponse(OrmModel):
    cash_delta: int
    upgrade: PurchasedShopUpgradeRead
    progression: ProgressionStateRead


class DashboardState(OrmModel):
    save_game: SaveGameRead
    cash: int
    reputation: int
    game_day: int
    reputation_summary: "ReputationSummaryRead | None" = None
    recent_reviews: list["CustomerReviewRead"] = Field(default_factory=list)
    open_conversations_count: int = 0
    waiting_for_player_conversations_count: int = 0
    quote_proposed_conversations_count: int = 0
    customers_needing_consultation_count: int = 0
    recent_conversation_messages: list[dict[str, Any]] = Field(default_factory=list)
    staff_count: int = 0
    available_staff_count: int = 0
    daily_salary_total_vnd: int = 0
    recent_staff_assignments: list["StaffAssignmentLogRead"] = Field(default_factory=list)
    staff_summary: "StaffSummaryRead | None" = None
    inventory_summary: dict[str, int]
    active_customer_requests: list[dict[str, Any]]
    active_orders: list[dict[str, Any]]
    order_fulfillment_summary: dict[str, int]
    recent_fulfillment_events: list[dict[str, Any]]
    quote_summary: dict[str, int]
    warranty_summary: dict[str, int]
    recent_warranty_events: list[dict[str, Any]]
    recent_quotes: list[dict[str, Any]]
    supplier_offers_summary: dict[str, int]
    recent_test_results: list[dict[str, Any]]
    market_summary: dict[str, Any]
    used_market_summary: dict[str, Any] | None = None
    resale_summary: dict[str, Any] | None = None
    shop_level: int | None = None
    shop_xp: int | None = None
    purchased_upgrades_count: int | None = None
    upgrade_effect_summary: dict[str, Any] | None = None
    inventory_capacity_summary: dict[str, Any] | None = None


class StaffMemberCore(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    role: StaffRole
    status: StaffStatus = StaffStatus.AVAILABLE
    level: int = Field(default=1, ge=1)
    xp: int = Field(default=0, ge=0)
    salary_per_day_vnd: int = Field(default=0, ge=0)
    morale: int = Field(default=70, ge=0, le=100)
    fatigue: int = Field(default=0, ge=0, le=100)
    traits_json: list[str] | None = Field(default_factory=list)
    sales_skill: int = Field(default=30, ge=0, le=100)
    marketing_skill: int = Field(default=30, ge=0, le=100)
    diagnostic_skill: int = Field(default=30, ge=0, le=100)
    repair_skill: int = Field(default=30, ge=0, le=100)
    procurement_skill: int = Field(default=30, ge=0, le=100)
    support_skill: int = Field(default=30, ge=0, le=100)
    market_skill: int = Field(default=30, ge=0, le=100)
    speed: int = Field(default=50, ge=0, le=100)
    carefulness: int = Field(default=50, ge=0, le=100)
    hired_on_day: int | None = None
    last_assigned_on_day: int | None = None
    notes: str | None = None


class StaffMemberCreate(StaffMemberCore):
    pass


class StaffMemberRead(OrmModel, StaffMemberCore):
    id: int
    save_game_id: int
    created_at: datetime
    updated_at: datetime


class StaffCandidateRead(StaffMemberCore):
    id: int | None = None
    save_game_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    preview_effects: dict[str, Any] = Field(default_factory=dict)


class StaffAssignmentLogRead(OrmModel):
    id: int
    save_game_id: int
    staff_member_id: int
    staff_member: StaffMemberRead | None = None
    task_type: StaffTaskType
    target_type: str | None = None
    target_id: int | None = None
    result_summary: str | None = None
    xp_gained: int = 0
    fatigue_gained: int = 0
    effect_json: dict[str, Any] | None = None
    assigned_on_day: int | None = None
    created_at: datetime


class StaffSummaryRead(BaseModel):
    save_game_id: int
    staff_count: int
    available_staff_count: int
    inactive_staff_count: int
    daily_salary_total_vnd: int
    average_morale: float
    average_fatigue: float
    role_counts: dict[str, int] = Field(default_factory=dict)
    strongest_roles: list[str] = Field(default_factory=list)


class StaffAssignRequest(BaseModel):
    task_type: StaffTaskType
    target_type: str | None = None
    target_id: int | None = None


class StaffAssistRequest(BaseModel):
    staff_id: int | None = None


class StaffAssignResponse(BaseModel):
    staff_member: StaffMemberRead
    assignment_log: StaffAssignmentLogRead
    effect_json: dict[str, Any]
    summary: str


class BrandCategoryRead(OrmModel):
    id: int
    brand_id: int
    category: BrandCategoryName
    created_at: datetime
    updated_at: datetime


class BrandRead(OrmModel):
    id: int
    name: str
    slug: str
    origin_name_vi: str | None
    origin_code: str | None
    logo_url: str | None
    website_url: str | None
    brand_type: BrandType
    market_tier: MarketTier
    base_trust_score: int
    used_market_risk_modifier: int
    categories: list[BrandCategoryName] = Field(default_factory=list)
    notes: str | None
    created_at: datetime
    updated_at: datetime

    @field_validator("categories", mode="before")
    @classmethod
    def read_category_values(cls, value: Any) -> list[Any]:
        if value is None:
            return []
        return [item.category if hasattr(item, "category") else item for item in value]


class HardwareProductRead(OrmModel):
    id: int
    slug: str | None = None
    name: str
    brand: str
    category: HardwareCategory
    release_year: int | None
    origin_name_vi: str | None = None
    origin_code: str | None = None
    base_performance_score: int
    base_power_watts: int
    base_heat_score: int
    base_reliability_score: int
    msrp_vnd: int | None
    used_demand_score: int
    mining_popularity_score: int
    depreciation_rate: int
    specs_json: dict[str, Any] | None
    image_url: str | None
    brand_logo_url: str | None
    brand_id: int | None = None
    chip_vendor_brand_id: int | None = None
    brand_ref: BrandRead | None = None
    chip_vendor_brand: BrandRead | None = None
    effective_logo_url: str | None = None
    source_name: str | None = None
    source_url: str | None = None
    data_confidence: str | None = None
    real_specs_json: dict[str, Any] | None = None
    game_balance_json: dict[str, Any] | None = None
    base_local_price_vnd: int | None = None
    base_used_price_vnd: int | None = None
    supplier_cost_vnd: int | None = None
    notes: str | None = None
    latest_local_retail_vnd: int | None = None
    latest_used_market_vnd: int | None = None
    latest_supplier_cost_vnd: int | None = None
    latest_msrp_vnd: int | None = None
    latest_price_updated_at: datetime | None = None
    market_multiplier: float | None = 1.0
    market_adjusted_local_retail_vnd: int | None = None
    market_adjusted_used_market_vnd: int | None = None
    market_adjusted_supplier_cost_vnd: int | None = None
    active_market_event_titles: list[str] = []
    created_at: datetime
    updated_at: datetime


class InventoryUnitCreate(BaseModel):
    product_id: int
    condition_type: ConditionType = ConditionType.USED
    source: InventorySource = InventorySource.USED_MARKET
    purchase_price_vnd: int = 0
    listed_price_vnd: int | None = None
    warranty_months_remaining: int = 0
    notes: str | None = None


class InventoryUnitUpdate(BaseModel):
    status: InventoryStatus | None = None
    grade: Grade | None = None
    listed_price_vnd: int | None = None
    warranty_months_remaining: int | None = None
    notes: str | None = None


class InventoryUnitRead(OrmModel):
    id: int
    save_game_id: int
    product_id: int
    product: HardwareProductRead
    serial_number: str | None
    condition_type: ConditionType
    status: InventoryStatus
    grade: Grade
    inspection_confidence: int
    purchase_price_vnd: int
    listed_price_vnd: int | None
    warranty_months_remaining: int
    source: InventorySource
    health_score: int | None
    performance_score: int | None
    thermal_score: int | None
    fan_score: int | None
    vram_score: int | None
    stability_score: int | None
    warranty_risk: str | None
    hidden_defect_revealed: bool
    notes: str | None
    refurbish_count: int
    last_refurbished_at: datetime | None
    refurbish_notes: str | None
    repair_risk_score: int | None
    resale_value_estimate_vnd: int | None
    ready_for_resale: bool
    created_at: datetime
    updated_at: datetime


class TestResultRead(OrmModel):
    id: int
    inventory_unit_id: int
    test_type: TestType
    summary: str
    raw_result_json: dict[str, Any] | None
    created_at: datetime


class TestActionResponse(BaseModel):
    unit: InventoryUnitRead
    result: TestResultRead


class CompatibilityWarningRead(OrmModel):
    severity: str
    code: str
    message: str
    affected_categories: list[str] = Field(default_factory=list)


class CompatibilityComponentSummaryRead(OrmModel):
    product_id: int | None = None
    inventory_unit_id: int | None = None
    name: str
    category: str
    quantity: int = 1
    condition_type: ConditionType | None = None
    grade: Grade | None = None
    inspection_confidence: int | None = None
    power_watts: int | None = None
    performance_score: int | None = None
    heat_score: int | None = None
    socket_slot: str | None = None
    memory_type: str | None = None
    form_factor: str | None = None
    source: str | None = None


class CompatibilityResultRead(OrmModel):
    compatibility_score: int
    power_headroom_score: int
    thermal_score: int
    bottleneck_score: int
    build_quality_score_estimate: int
    warranty_risk_delta: int
    blocking_issues: list[CompatibilityWarningRead] = Field(default_factory=list)
    warnings: list[CompatibilityWarningRead] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    component_summary: list[CompatibilityComponentSummaryRead] = Field(default_factory=list)


class CompatibilityEvaluateRequest(BaseModel):
    save_game_id: int | None = None
    product_ids: list[int] = Field(default_factory=list)
    inventory_unit_ids: list[int] = Field(default_factory=list)


class SupplierRead(OrmModel):
    id: int
    name: str
    slug: str | None = None
    type: SupplierType
    supplier_tier: SupplierTier | None = None
    trust_score: int
    relationship_score: int
    delivery_days: int
    default_delivery_days: int | None = None
    notes: str | None
    country_code: str | None = None
    invoice_currency: str = "VND"
    fx_spread_percent: float | None = None
    import_fee_percent: float | None = None
    payment_fee_flat_vnd: int | None = None
    supported_brand_slugs_json: list[str] | None = None
    supported_category_json: list[str] | None = None


class SupplierOfferRead(OrmModel):
    id: int
    supplier_id: int
    supplier: SupplierRead
    product_id: int
    product: HardwareProductRead
    unit_price_vnd: int
    min_order_quantity: int
    available_quantity: int
    warranty_months: int
    expires_at: datetime | None
    foreign_unit_price: float | None = None
    foreign_currency: str | None = None
    quality_risk_modifier: float | None = None
    expires_on_day: int | None = None
    offer_type: str | None = None
    effective_unit_price_vnd: int
    effective_fx_rate_to_vnd: float | None = None
    effective_fx_provider: str | None = None
    effective_fx_is_fallback: bool = False
    effective_fx_fetched_at: datetime | None = None
    market_multiplier: float | None = 1.0
    market_adjusted_unit_price_vnd: int | None = None
    active_market_event_titles: list[str] = []


class PurchaseOrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    unit_price_vnd: int = Field(ge=0)
    warranty_months: int = Field(ge=0)


class PurchaseOrderCreate(BaseModel):
    supplier_id: int
    items: list[PurchaseOrderItemCreate]


class PurchaseOrderItemRead(OrmModel):
    id: int
    purchase_order_id: int
    product_id: int
    product: HardwareProductRead
    quantity: int
    unit_price_vnd: int
    warranty_months: int


class PurchaseOrderRead(OrmModel):
    id: int
    save_game_id: int
    supplier_id: int
    supplier: SupplierRead
    status: PurchaseOrderStatus
    subtotal_vnd: int
    delivery_due_day: int
    created_at: datetime
    updated_at: datetime
    items: list[PurchaseOrderItemRead]
    invoice_currency: str = "VND"
    foreign_subtotal: float | None = None
    fx_rate_to_vnd: float | None = None
    fx_provider: str | None = None
    fx_fetched_at: datetime | None = None
    fx_is_fallback: bool = False
    fx_spread_percent: float | None = None
    fx_fee_vnd: int = 0
    final_total_vnd: int | None = None


class CustomerRead(OrmModel):
    id: int
    save_game_id: int
    name: str
    archetype: CustomerArchetype
    knowledge_level: KnowledgeLevel
    patience: int
    negotiation_score: int
    risk_tolerance: RiskTolerance
    created_at: datetime
    country_code: str | None = None
    preferred_currency: str = "VND"
    persona_type: str | None = None
    preference_json: dict[str, Any] | None = None
    preferred_brand_slugs_json: list[str] | None = None
    disliked_brand_slugs_json: list[str] | None = None
    accepts_used_parts: bool | None = None
    warranty_sensitivity: int | None = None
    price_sensitivity: int | None = None
    performance_priority: int | None = None
    aesthetics_priority: int | None = None
    reliability_priority: int | None = None


class CustomerPersonaDefinitionRead(BaseModel):
    persona_type: str
    label: str
    description: str
    budget_multiplier_range: list[float]
    accepts_used_parts_default: bool
    price_sensitivity: int
    performance_priority: int
    reliability_priority: int
    aesthetics_priority: int
    warranty_sensitivity: int
    preferred_priorities: list[str] = Field(default_factory=list)
    default_min_compatibility_score: int
    default_min_build_quality_score: int
    preference_hints: list[str] = Field(default_factory=list)
    preferred_brand_slugs: list[str] = Field(default_factory=list)
    disliked_brand_slugs: list[str] = Field(default_factory=list)
    used_part_tolerance: int
    warranty_expectation_days: int
    sample_use_case: str


class CustomerPersonaAssignRequest(BaseModel):
    persona_type: str


class CustomerRequestRead(OrmModel):
    id: int
    customer_id: int
    customer: CustomerRead
    request_type: RequestType
    budget_vnd: int
    use_case: str
    target_performance_score: int | None
    requirements_json: dict[str, Any] | None
    persona_type: str | None = None
    preference_json: dict[str, Any] | None = None
    priority_tags_json: list[str] | None = None
    accepts_used_parts: bool | None = None
    min_compatibility_score: int | None = None
    min_build_quality_score: int | None = None
    used_part_tolerance: int | None = None
    warranty_expectation_days: int | None = None
    status: CustomerRequestStatus
    created_at: datetime
    updated_at: datetime
    budget_currency: str = "VND"
    foreign_budget_amount: float | None = None
    budget_fx_rate_to_vnd: float | None = None
    conversation_id: int | None = None
    conversation_status: str | None = None


class GeneratedCustomerResponse(BaseModel):
    customer: CustomerRead
    request: CustomerRequestRead


class CustomerConversationMessageRead(OrmModel):
    id: int
    conversation_id: int
    sender_type: ConversationMessageSender
    sender_label: str | None = None
    staff_id: int | None = None
    message_type: ConversationMessageType
    body: str
    action_type: ConversationActionType | None = None
    quote_id: int | None = None
    metadata_json: dict[str, Any] | None = None
    created_on_day: int | None = None
    created_at: datetime


class CustomerConversationRead(OrmModel):
    id: int
    save_game_id: int
    customer_id: int | None = None
    customer: CustomerRead | None = None
    customer_request_id: int | None = None
    customer_request: CustomerRequestRead | None = None
    assigned_staff_id: int | None = None
    assigned_staff: StaffMemberRead | None = None
    status: CustomerConversationStatus
    stage: CustomerConversationStage
    persona_type: str | None = None
    title: str | None = None
    customer_mood: str | None = None
    engagement_score: int = 50
    urgency_score: int = 50
    conversion_probability: int | None = None
    detected_budget_vnd: int | None = None
    detected_use_case: str | None = None
    detected_preferences_json: dict[str, Any] | None = None
    accepts_used_parts: bool | None = None
    last_message_at: datetime | None = None
    created_on_day: int | None = None
    created_at: datetime


class CustomerConversationDetailRead(CustomerConversationRead):
    messages: list[CustomerConversationMessageRead] = Field(default_factory=list)


class CustomerConversationCreateResponse(BaseModel):
    conversation: CustomerConversationDetailRead
    created: bool = True


class ConversationMessageCreateRequest(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class ConversationQuickReplyRequest(BaseModel):
    action_type: ConversationActionType


class ConversationAssignStaffRequest(BaseModel):
    staff_id: int


class ConversationCloseRequest(BaseModel):
    won: bool


class ConversationSendQuoteResponse(BaseModel):
    conversation: CustomerConversationDetailRead
    quote: "QuoteRead"
    message: CustomerConversationMessageRead
    conversion_probability: int | None = None


class QuoteItemCreate(BaseModel):
    product_id: int
    inventory_unit_id: int | None = None
    quantity: int = Field(default=1, gt=0)
    unit_price_vnd: int = Field(ge=0)
    unit_cost_vnd: int = Field(ge=0)
    source: QuoteItemSource = QuoteItemSource.CATALOG_PLACEHOLDER
    notes: str | None = None


class QuoteCreate(BaseModel):
    customer_request_id: int
    title: str = Field(min_length=1, max_length=160)
    summary: str = ""
    quoted_price_vnd: int | None = None
    estimated_cost_vnd: int | None = None
    notes: str | None = None
    items: list[QuoteItemCreate] = Field(default_factory=list)


class QuoteUpdate(BaseModel):
    status: QuoteStatus | None = None
    title: str | None = Field(default=None, min_length=1, max_length=160)
    summary: str | None = None
    quoted_price_vnd: int | None = Field(default=None, ge=0)
    estimated_cost_vnd: int | None = Field(default=None, ge=0)
    customer_fit_score: int | None = Field(default=None, ge=0, le=100)
    performance_score: int | None = Field(default=None, ge=0, le=100)
    value_score: int | None = Field(default=None, ge=0, le=100)
    thermal_score: int | None = Field(default=None, ge=0, le=100)
    reliability_score: int | None = Field(default=None, ge=0, le=100)
    warranty_risk: str | None = None
    notes: str | None = None


class QuoteGenerateRequest(BaseModel):
    notes: str | None = None


class QuoteAcceptRequest(BaseModel):
    notes: str | None = None


class QuoteRead(OrmModel):
    id: int
    save_game_id: int
    customer_id: int
    customer: CustomerRead
    customer_request_id: int
    customer_request: CustomerRequestRead
    status: QuoteStatus
    title: str
    summary: str
    quoted_price_vnd: int
    estimated_cost_vnd: int
    estimated_profit_vnd: int
    customer_fit_score: int | None
    performance_score: int | None
    value_score: int | None
    thermal_score: int | None
    reliability_score: int | None
    persona_match_score: int | None
    price_fit_score: int | None
    performance_fit_score: int | None
    reliability_fit_score: int | None
    aesthetics_fit_score: int | None
    used_part_fit_score: int | None
    quote_acceptance_chance: int | None
    customer_feedback_summary: str | None
    persona_warnings_json: list[CompatibilityWarningRead] | None
    warranty_risk: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    quote_currency: str = "VND"
    foreign_quoted_price: float | None = None
    fx_rate_to_vnd: float | None = None
    fx_provider: str | None = None
    fx_fetched_at: datetime | None = None
    fx_is_fallback: bool = False
    fx_spread_percent: float | None = None
    compatibility_score: int | None = None
    power_headroom_score: int | None = None
    bottleneck_score: int | None = None
    build_quality_score_estimate: int | None = None
    warranty_risk_delta: int | None = None
    compatibility_warnings_json: list[CompatibilityWarningRead] | None = None
    compatibility_result: CompatibilityResultRead | None = None


class QuotePersonaEvaluationRead(BaseModel):
    quote_id: int
    customer_fit_score: int | None = None
    persona_match_score: int | None = None
    price_fit_score: int | None = None
    performance_fit_score: int | None = None
    reliability_fit_score: int | None = None
    aesthetics_fit_score: int | None = None
    used_part_fit_score: int | None = None
    quote_acceptance_chance: int | None = None
    customer_feedback_summary: str | None = None
    warnings: list[CompatibilityWarningRead] = Field(default_factory=list)


class QuoteItemRead(OrmModel):
    id: int
    quote_id: int
    product_id: int
    product: HardwareProductRead
    inventory_unit_id: int | None
    inventory_unit: InventoryUnitRead | None
    quantity: int
    unit_price_vnd: int
    unit_cost_vnd: int
    source: QuoteItemSource
    is_reserved: bool
    notes: str | None


class QuoteDetailRead(BaseModel):
    quote: QuoteRead
    quote_items: list[QuoteItemRead]
    compatibility_result: CompatibilityResultRead | None = None


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    unit_price_vnd: int = Field(ge=0)
    cost_vnd: int = Field(ge=0)
    inventory_unit_id: int | None = None


class OrderCreate(BaseModel):
    customer_id: int
    request_id: int | None = None
    quoted_price_vnd: int = Field(ge=0)
    cost_vnd: int = Field(ge=0)
    notes: str | None = None
    items: list[OrderItemCreate] = Field(default_factory=list)


class OrderItemRead(OrmModel):
    id: int
    order_id: int
    inventory_unit_id: int | None
    inventory_unit: InventoryUnitRead | None
    product_id: int
    product: HardwareProductRead
    quantity: int
    unit_price_vnd: int
    cost_vnd: int


class OrderRead(OrmModel):
    id: int
    save_game_id: int
    customer_id: int
    customer: CustomerRead
    request_id: int | None
    status: OrderStatus
    quoted_price_vnd: int
    cost_vnd: int
    profit_vnd: int
    customer_fit_score: int | None
    started_at: datetime | None
    testing_started_at: datetime | None
    delivered_at: datetime | None
    build_quality_score: int | None
    final_test_score: int | None
    final_warranty_risk: str | None
    reputation_delta: int | None
    delivery_summary: str | None
    warranty_eligible: bool
    warranty_expires_at: datetime | None
    warranty_claim_count: int
    warranty_status: str | None
    last_warranty_event_at: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemRead]
    order_currency: str = "VND"
    foreign_order_amount: float | None = None
    fx_rate_to_vnd: float | None = None
    fx_provider: str | None = None
    fx_fetched_at: datetime | None = None
    fx_is_fallback: bool = False
    fx_spread_percent: float | None = None
    compatibility_score: int | None = None
    power_headroom_score: int | None = None
    thermal_score: int | None = None
    bottleneck_score: int | None = None
    build_quality_score_estimate: int | None = None
    warranty_risk_delta: int | None = None
    compatibility_warnings_json: list[CompatibilityWarningRead] | None = None
    compatibility_result: CompatibilityResultRead | None = None


class OrderFulfillmentEventRead(OrmModel):
    id: int
    order_id: int
    event_type: OrderFulfillmentEventType
    summary: str
    raw_result_json: dict[str, Any] | None
    created_at: datetime


class OrderDetailRead(BaseModel):
    order: OrderRead
    fulfillment_events: list[OrderFulfillmentEventRead]
    compatibility_result: CompatibilityResultRead | None = None


class DeliverOrderRequest(BaseModel):
    force: bool = False


class DeliverOrderResponse(BaseModel):
    order_detail: OrderDetailRead
    cash_delta: int
    reputation_delta: int


class WarrantyClaimCreate(BaseModel):
    claim_reason: WarrantyClaimReason = WarrantyClaimReason.OTHER
    complaint_summary: str = Field(default="Customer reported a post-delivery issue.", min_length=1)
    internal_notes: str | None = None


class WarrantyClaimGenerateRequest(BaseModel):
    source_type: str | None = None
    order_id: int | None = None
    resale_listing_id: int | None = None
    inventory_unit_id: int | None = None


class WarrantyClaimReviewRequest(BaseModel):
    notes: str | None = None


class WarrantyClaimResolveRequest(BaseModel):
    resolution_type: WarrantyResolutionType
    notes: str | None = None


class WarrantyClaimResolveResponse(BaseModel):
    claim: "WarrantyClaimRead"
    cash_delta: int
    reputation_delta: int


class WarrantyClaimSummary(BaseModel):
    save_game_id: int
    total_claims: int
    open_claims_count: int
    in_review_claims_count: int
    approved_claims_count: int
    resolved_claims_count: int
    rejected_claims_count: int
    due_soon_claims_count: int
    overdue_claims_count: int
    estimated_exposure_vnd: int
    unresolved_risk_score: int
    recent_claims: list["WarrantyClaimRead"] = Field(default_factory=list)


class WarrantyClaimUpdate(BaseModel):
    status: WarrantyClaimStatus | None = None
    complaint_summary: str | None = None
    diagnostic_summary: str | None = None
    resolution_summary: str | None = None
    internal_notes: str | None = None


class WarrantyDiagnosisRequest(BaseModel):
    notes: str | None = None


class WarrantyResolutionRequest(BaseModel):
    notes: str | None = None


class WarrantyRejectRequest(BaseModel):
    reason: str | None = None


class WarrantyEventRead(OrmModel):
    id: int
    warranty_claim_id: int
    event_type: WarrantyEventType
    summary: str
    raw_result_json: dict[str, Any] | None
    created_at: datetime


class WarrantyClaimItemRead(OrmModel):
    id: int
    warranty_claim_id: int
    order_item_id: int | None
    inventory_unit_id: int | None
    inventory_unit: InventoryUnitRead | None
    product_id: int | None
    product: HardwareProductRead | None
    suspected_issue: str | None
    diagnosis_result: str | None
    action_taken: str | None
    replacement_inventory_unit_id: int | None
    replacement_inventory_unit: InventoryUnitRead | None
    created_at: datetime
    updated_at: datetime


class WarrantyClaimRead(OrmModel):
    id: int
    save_game_id: int
    order_id: int | None = None
    resale_listing_id: int | None = None
    inventory_unit_id: int | None = None
    customer_id: int | None = None
    customer: CustomerRead | None = None
    order: OrderRead | None = None
    resale_listing: "ResaleListingRead | None" = None
    inventory_unit: InventoryUnitRead | None = None
    claim_type: WarrantyClaimType
    status: WarrantyClaimStatus
    claim_reason: WarrantyClaimReason
    title: str
    complaint_summary: str
    description: str | None
    severity: int
    claimed_on_day: int
    due_on_day: int | None
    resolved_on_day: int | None
    customer_message: str | None
    internal_risk_score: int
    estimated_cost_vnd: int
    final_cost_vnd: int | None
    diagnostic_summary: str | None
    resolution_summary: str | None
    resolution_type: WarrantyResolutionType | None
    notes: str | None
    claimed_at: datetime
    updated_at: datetime
    diagnosed_at: datetime | None
    resolved_at: datetime | None
    reimbursement_vnd: int
    repair_cost_vnd: int
    replacement_cost_vnd: int
    rma_shipping_cost_vnd: int
    reputation_delta: int | None
    warranty_valid: bool
    internal_notes: str | None


class WarrantyClaimDetailRead(BaseModel):
    claim: WarrantyClaimRead
    claim_items: list[WarrantyClaimItemRead]
    order: OrderRead | None = None
    resale_listing: "ResaleListingRead | None" = None
    events: list[WarrantyEventRead]


WarrantyClaimDetail = WarrantyClaimDetailRead


class ExchangeRateRead(OrmModel):
    id: int
    base_currency: str
    quote_currency: str
    rate: float
    provider: str
    source: str | None
    fetched_at: datetime
    valid_for_day: str | None = None
    is_fallback: bool
    created_at: datetime
    updated_at: datetime


class CurrencyConversionResult(BaseModel):
    amount: float
    from_currency: str
    to_currency: str
    converted_amount: float
    rate: float
    provider: str
    fetched_at: datetime
    is_fallback: bool
    spread_applied: float
    final_amount_vnd: int | None = None


class SupportedCurrency(BaseModel):
    code: str
    name: str
    symbol: str
    country: str


class ProductPriceSnapshotRead(OrmModel):
    id: int
    product_id: int
    product_slug: str
    price_type: ProductPriceType
    currency: str
    amount: float
    amount_vnd: int
    fx_rate_to_vnd: float | None = None
    fx_provider: str | None = None
    fx_fetched_at: datetime | None = None
    fx_is_fallback: bool = False
    region: str | None = None
    source_name: str | None = None
    source_url: str | None = None
    confidence: ProductPriceConfidence
    observed_at: datetime
    is_current: bool
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class RefurbishActionEstimateRead(BaseModel):
    action_type: str
    cost_vnd: int
    duration_days: int
    applicable: bool
    unavailable_reason: str | None = None


class InventoryRefurbishEventRead(OrmModel):
    id: int
    save_game_id: int
    inventory_unit_id: int
    action_type: RefurbishActionType
    status: RefurbishResultStatus
    cost_vnd: int
    duration_days: int
    started_on_day: int | None = None
    completed_on_day: int | None = None
    before_grade: Grade | None = None
    after_grade: Grade | None = None
    before_condition_json: dict[str, Any] | None = None
    after_condition_json: dict[str, Any] | None = None
    health_delta: int = 0
    thermal_delta: int = 0
    fan_delta: int = 0
    vram_delta: int = 0
    stability_delta: int = 0
    cosmetic_delta: int = 0
    risk_delta: int = 0
    resale_value_delta_vnd: int | None = None
    summary: str
    notes: str | None = None
    created_at: datetime


class RefurbishActionRunResponse(BaseModel):
    event: InventoryRefurbishEventRead
    unit: InventoryUnitRead


class ResaleBuyerOfferRead(OrmModel):
    id: int
    listing_id: int
    save_game_id: int
    buyer_name: str
    offer_price_vnd: int
    status: ResaleBuyerOfferStatus
    message: str | None = None
    buyer_patience: int
    buyer_strictness: int
    created_on_day: int
    expires_on_day: int | None = None
    created_at: datetime
    updated_at: datetime


class ResaleListingRead(OrmModel):
    id: int
    save_game_id: int
    inventory_unit_id: int | None = None
    inventory_unit: InventoryUnitRead | None = None
    title: str
    description: str | None = None
    asking_price_vnd: int
    estimated_market_value_vnd: int
    minimum_accept_price_vnd: int | None = None
    status: ResaleListingStatus
    listing_quality_score: int
    buyer_interest_score: int
    market_multiplier_at_listing: float
    grade_at_listing: str | None = None
    inspection_confidence_at_listing: int | None = None
    warranty_days_offered: int
    created_on_day: int
    expires_on_day: int | None = None
    sold_on_day: int | None = None
    final_sale_price_vnd: int | None = None
    reputation_delta: int
    risk_note: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    offers: list[ResaleBuyerOfferRead] = Field(default_factory=list)


class ResaleListingCreate(BaseModel):
    inventory_unit_id: int
    asking_price_vnd: int | None = None
    warranty_days_offered: int = Field(default=0, ge=0)


class ResaleOfferGenerateResponse(BaseModel):
    offer: ResaleBuyerOfferRead
    listing: ResaleListingRead


class ResaleSaleResponse(BaseModel):
    offer: ResaleBuyerOfferRead
    listing: ResaleListingRead
    cash_after_sale: int
    reputation_after_sale: int


class CustomerReviewRead(OrmModel):
    id: int
    save_game_id: int
    customer_id: int | None = None
    order_id: int | None = None
    resale_listing_id: int | None = None
    warranty_claim_id: int | None = None
    source_type: str
    source_key: str
    sentiment: str
    rating: int
    title: str
    body: str
    tags_json: list[str] | None = None
    persona_type: str | None = None
    source_summary: str | None = None
    quote_fit_score: int | None = None
    compatibility_score: int | None = None
    build_quality_score: int | None = None
    warranty_risk_score: int | None = None
    final_price_vnd: int | None = None
    reputation_delta: int
    generated_on_day: int | None = None
    is_public: bool = True
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class ReviewGenerateRequest(BaseModel):
    source_type: str | None = None
    order_id: int | None = None
    resale_listing_id: int | None = None
    warranty_claim_id: int | None = None


class ReputationSummaryRead(BaseModel):
    save_game_id: int
    reputation: int
    total_reviews: int
    average_rating: float | None = None
    positive_reviews: int = 0
    neutral_reviews: int = 0
    negative_reviews: int = 0
    sentiment_counts: dict[str, int] = Field(default_factory=dict)
    source_counts: dict[str, int] = Field(default_factory=dict)
