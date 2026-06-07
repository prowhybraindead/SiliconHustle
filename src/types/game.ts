export type HardwareCategory =
  | "CPU"
  | "GPU"
  | "RAM"
  | "SSD"
  | "STORAGE"
  | "PSU"
  | "MOTHERBOARD"
  | "CASE"
  | "COOLER"
  | "WATER_COOLING"
  | "MONITOR"
  | "OTHER";
export type BrandCategory =
  | "CPU"
  | "GPU"
  | "MOTHERBOARD"
  | "RAM"
  | "STORAGE"
  | "PSU"
  | "CASE"
  | "COOLER"
  | "WATER_COOLING"
  | "MONITOR"
  | "OTHER";
export type BrandType = "CHIP_VENDOR" | "BOARD_PARTNER" | "MEMORY_STORAGE" | "PSU_CASE_COOLING" | "CASE_COOLING" | "RETAILER" | "OTHER";
export type MarketTier = "PREMIUM" | "MAINSTREAM" | "VALUE" | "BUDGET" | "GRAY_MARKET" | "INDUSTRIAL" | "UNKNOWN";
export type ShopUpgradeCategory = "STORAGE" | "TEST_BENCH" | "REFURBISH" | "SUPPLIER" | "RESALE" | "WARRANTY" | "STAFF" | "CUSTOMER" | "MARKET" | "OPERATIONS";
export type ShopUpgradeStatus = "AVAILABLE" | "PURCHASED" | "LOCKED";
export type StaffRole =
  | "SALES"
  | "MARKETING"
  | "TECHNICIAN"
  | "REPAIR_SPECIALIST"
  | "PROCUREMENT"
  | "WARRANTY_SUPPORT"
  | "MARKET_ANALYST"
  | "OPERATIONS";
export type StaffStatus = "AVAILABLE" | "ASSIGNED" | "RESTING" | "INACTIVE";
export type StaffTrait =
  | "SMOOTH_TALKER"
  | "HONEST_ADVISOR"
  | "OVERCONFIDENT"
  | "RGB_ADDICT"
  | "MARKET_SENSE"
  | "CAREFUL_TESTER"
  | "METICULOUS"
  | "FAST_HANDS"
  | "DAMAGE_CONTROL"
  | "BARGAIN_HUNTER";
export type StaffTaskType =
  | "CUSTOMER_CONSULT"
  | "TEST_BENCH"
  | "REFURBISH"
  | "RESALE"
  | "WARRANTY"
  | "PROCUREMENT"
  | "MARKET_ANALYSIS"
  | "OPERATIONS";
export type UiLanguage = "vi" | "en";

export type ConditionType = "NEW" | "OPEN_BOX" | "USED" | "REFURBISHED" | "DEFECTIVE" | "FOR_PARTS";
export type InventoryStatus =
  | "UNTESTED"
  | "BASIC_CHECKED"
  | "BENCHMARKED"
  | "STRESS_TESTED"
  | "FULLY_INSPECTED"
  | "REFURBISHED"
  | "READY_FOR_SALE"
  | "RESERVED"
  | "INSTALLED_IN_BUILD"
  | "SOLD"
  | "WARRANTY_RETURN"
  | "DEFECTIVE"
  | "FOR_PARTS"
  | "MINING_USE"
  | "RETIRED";
export type Grade = "A_PLUS" | "A" | "B" | "C" | "D" | "F" | "UNKNOWN";
export type PurchaseOrderStatus = "DRAFT" | "ORDERED" | "IN_TRANSIT" | "RECEIVED" | "CANCELLED";
export type OrderStatus = "DRAFT" | "QUOTED" | "ACCEPTED" | "IN_PROGRESS" | "TESTING" | "DELIVERED" | "CANCELLED" | "WARRANTY";
export type QuoteStatus = "DRAFT" | "PRESENTED" | "ACCEPTED" | "REJECTED" | "EXPIRED" | "CONVERTED_TO_ORDER";
export type QuoteItemSource = "INVENTORY" | "CATALOG_PLACEHOLDER" | "SUPPLIER_NEEDED";
export type OrderFulfillmentEventType = "BUILD_STARTED" | "BUILD_TESTED" | "DELIVERED" | "DELIVERY_FAILED" | "CANCELLED";
export type WarrantyClaimStatus =
  | "OPEN"
  | "IN_REVIEW"
  | "DIAGNOSING"
  | "AWAITING_DECISION"
  | "APPROVED"
  | "REJECTED"
  | "RESOLVED"
  | "CANCELLED"
  | "IN_REPAIR"
  | "REPLACED"
  | "REFUNDED"
  | "RMA_SUBMITTED"
  | "RMA_COMPLETED"
  | "CLOSED";
export type WarrantyClaimType =
  | "DOA"
  | "OVERHEATING"
  | "RANDOM_CRASH"
  | "PERFORMANCE_ISSUE"
  | "FAN_NOISE"
  | "STORAGE_FAILURE"
  | "ARTIFACTING"
  | "POWER_ISSUE"
  | "CUSTOMER_DAMAGE"
  | "COSMETIC_COMPLAINT"
  | "OTHER";
export type WarrantyClaimReason =
  | "NO_DISPLAY"
  | "CRASHING"
  | "OVERHEATING"
  | "ARTIFACTING"
  | "NOISY_FAN"
  | "PERFORMANCE_ISSUE"
  | "RANDOM_SHUTDOWN"
  | "DOA"
  | "OTHER";
export type WarrantyResolutionType = "REPAIR" | "REPLACE" | "REFUND" | "REJECT" | "GOODWILL_CREDIT";
export type WarrantyEventType =
  | "CLAIM_OPENED"
  | "DIAGNOSIS_STARTED"
  | "DIAGNOSIS_COMPLETED"
  | "APPROVED"
  | "REJECTED"
  | "REPAIR_STARTED"
  | "REPAIR_COMPLETED"
  | "REPLACEMENT_ISSUED"
  | "REFUND_ISSUED"
  | "RMA_SUBMITTED"
  | "RMA_COMPLETED"
  | "CLAIM_CLOSED";

export interface CompatibilityWarning {
  severity: "INFO" | "WARNING" | "CRITICAL" | string;
  code: string;
  message: string;
  affected_categories: string[];
}

export interface CompatibilityComponentSummary {
  product_id: number | null;
  inventory_unit_id: number | null;
  name: string;
  category: string;
  quantity: number;
  condition_type: ConditionType | null;
  grade: Grade | null;
  inspection_confidence: number | null;
  power_watts: number;
  performance_score: number;
  heat_score: number;
  socket_slot: string | null;
  memory_type: string | null;
  form_factor: string | null;
  cooler_type: string | null;
  psu_watts: number | null;
  source: string;
  ready_for_resale: boolean | null;
  repair_risk_score: number | null;
}

export interface CompatibilityResult {
  compatibility_score: number;
  power_headroom_score: number;
  thermal_score: number;
  bottleneck_score: number;
  build_quality_score_estimate: number;
  warranty_risk_delta: number;
  blocking_issues: CompatibilityWarning[];
  warnings: CompatibilityWarning[];
  suggestions: string[];
  component_summary: CompatibilityComponentSummary[];
}

export interface CompatibilityEvaluateRequest {
  save_game_id?: number | null;
  product_ids?: number[];
  inventory_unit_ids?: number[];
}

export interface SaveGame {
  id: number;
  slug: string | null;
  name: string;
  shop_level: number;
  shop_xp: number;
  shop_name: string | null;
  progression_notes: string | null;
  game_day: number;
  cash: number;
  reputation: number;
  created_at: string;
  updated_at: string;
  last_autosave_at: string | null;
  client_state_json: Record<string, unknown> | null;
  player_profile_id: number | null;
  profile_display_name: string | null;
  pin_required: boolean;
  is_locked: boolean;
}

export interface HardwareProduct {
  id: number;
  name: string;
  brand: string;
  category: HardwareCategory;
  release_year: number | null;
  origin_name_vi: string | null;
  origin_code: string | null;
  base_performance_score: number;
  base_power_watts: number;
  base_heat_score: number;
  base_reliability_score: number;
  msrp_vnd: number | null;
  used_demand_score: number;
  mining_popularity_score: number;
  depreciation_rate: number;
  specs_json: Record<string, unknown> | null;
  image_url: string | null;
  brand_logo_url: string | null;
  brand_id: number | null;
  chip_vendor_brand_id: number | null;
  brand_ref: Brand | null;
  chip_vendor_brand: Brand | null;
  effective_logo_url: string | null;
  source_name: string | null;
  source_url: string | null;
  data_confidence: string | null;
  real_specs_json: Record<string, unknown> | null;
  game_balance_json: Record<string, unknown> | null;
  base_local_price_vnd: number | null;
  base_used_price_vnd: number | null;
  supplier_cost_vnd: number | null;
  notes: string | null;
  latest_local_retail_vnd: number | null;
  latest_used_market_vnd: number | null;
  latest_supplier_cost_vnd: number | null;
  latest_msrp_vnd: number | null;
  latest_price_updated_at: string | null;
  market_multiplier?: number;
  market_adjusted_local_retail_vnd?: number | null;
  market_adjusted_used_market_vnd?: number | null;
  market_adjusted_supplier_cost_vnd?: number | null;
  active_market_event_titles?: string[];
  created_at: string;
  updated_at: string;
}

export interface Brand {
  id: number;
  name: string;
  slug: string;
  origin_name_vi: string | null;
  origin_code: string | null;
  logo_url: string | null;
  website_url: string | null;
  brand_type: BrandType;
  market_tier: MarketTier;
  base_trust_score: number;
  used_market_risk_modifier: number;
  categories: BrandCategory[];
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface InventoryUnit {
  id: number;
  save_game_id: number;
  product_id: number;
  product: HardwareProduct;
  serial_number: string | null;
  condition_type: ConditionType;
  status: InventoryStatus;
  grade: Grade;
  inspection_confidence: number;
  purchase_price_vnd: number;
  listed_price_vnd: number | null;
  warranty_months_remaining: number;
  source: string;
  health_score: number | null;
  performance_score: number | null;
  thermal_score: number | null;
  fan_score: number | null;
  vram_score: number | null;
  stability_score: number | null;
  warranty_risk: string | null;
  hidden_defect_revealed: boolean;
  notes: string | null;
  refurbish_count: number;
  last_refurbished_at: string | null;
  refurbish_notes: string | null;
  repair_risk_score: number | null;
  resale_value_estimate_vnd: number | null;
  ready_for_resale: boolean;
  created_at: string;
  updated_at: string;
}

export interface DashboardState {
  save_game: SaveGame;
  cash: number;
  reputation: number;
  game_day: number;
  reputation_summary?: ReputationSummary | null;
  recent_reviews?: CustomerReview[];
  open_conversations_count?: number;
  waiting_for_player_conversations_count?: number;
  quote_proposed_conversations_count?: number;
  customers_needing_consultation_count?: number;
  recent_conversation_messages?: CustomerConversationMessage[];
  inventory_summary: Record<string, number>;
  active_customer_requests: Array<Record<string, unknown>>;
  active_orders: Array<Record<string, unknown>>;
  order_fulfillment_summary: Record<string, number>;
  recent_fulfillment_events: Array<Record<string, unknown>>;
  quote_summary: Record<string, number>;
  warranty_summary: Record<string, number>;
  recent_warranty_events: Array<Record<string, unknown>>;
  recent_quotes: Array<Record<string, unknown>>;
  supplier_offers_summary: Record<string, number>;
  recent_test_results: Array<Record<string, unknown>>;
  market_summary?: MarketSummary;
  used_market_summary?: UsedMarketSummary | null;
  refurbish_summary?: RefurbishSummary;
  staff_count?: number | null;
  available_staff_count?: number | null;
  daily_salary_total_vnd?: number | null;
  recent_staff_assignments?: StaffAssignmentLog[];
  staff_summary?: StaffSummary | null;
  shop_level?: number | null;
  shop_xp?: number | null;
  purchased_upgrades_count?: number | null;
  upgrade_effect_summary?: Record<string, unknown> | null;
  inventory_capacity_summary?: Record<string, unknown> | null;
}

export interface StaffMemberCore {
  name: string;
  role: StaffRole;
  status: StaffStatus;
  level: number;
  xp: number;
  salary_per_day_vnd: number;
  morale: number;
  fatigue: number;
  traits_json: string[] | null;
  sales_skill: number;
  marketing_skill: number;
  diagnostic_skill: number;
  repair_skill: number;
  procurement_skill: number;
  support_skill: number;
  market_skill: number;
  speed: number;
  carefulness: number;
  hired_on_day: number | null;
  last_assigned_on_day: number | null;
  notes: string | null;
}

export interface StaffMemberCreate extends StaffMemberCore {}

export interface StaffMember extends StaffMemberCore {
  id: number;
  save_game_id: number;
  created_at: string;
  updated_at: string;
}

export interface StaffCandidate extends StaffMemberCore {
  id?: number | null;
  save_game_id?: number | null;
  created_at?: string | null;
  updated_at?: string | null;
  preview_effects: Record<string, unknown>;
}

export interface StaffAssignmentLog {
  id: number;
  save_game_id: number;
  staff_member_id: number;
  staff_member?: StaffMember | null;
  task_type: StaffTaskType;
  target_type: string | null;
  target_id: number | null;
  result_summary: string | null;
  xp_gained: number;
  fatigue_gained: number;
  effect_json: Record<string, unknown> | null;
  assigned_on_day: number | null;
  created_at: string;
}

export interface StaffSummary {
  save_game_id: number;
  staff_count: number;
  available_staff_count: number;
  inactive_staff_count: number;
  daily_salary_total_vnd: number;
  average_morale: number;
  average_fatigue: number;
  role_counts: Record<string, number>;
  strongest_roles: string[];
}

export interface StaffAssignRequest {
  task_type: StaffTaskType;
  target_type?: string | null;
  target_id?: number | null;
}

export interface StaffAssistRequest {
  staff_id?: number | null;
}

export interface StaffAssignResponse {
  staff_member: StaffMember;
  assignment_log: StaffAssignmentLog;
  effect_json: Record<string, unknown>;
  summary: string;
}

export interface ShopUpgradeEffectSummary {
  inventory_capacity_bonus: number;
  test_confidence_bonus: number;
  hidden_defect_reveal_bonus: number;
  refurbish_cost_reduction_percent: number;
  refurbish_success_bonus: number;
  supplier_import_fee_reduction_percent: number;
  delivery_days_reduction: number;
  resale_buyer_interest_bonus: number;
  offer_price_bonus_percent: number;
  warranty_risk_reduction_percent: number;
  staff_xp_bonus_percent: number;
  staff_fatigue_reduction_percent: number;
  customer_budget_bonus_percent: number;
  reputation_gain_bonus: number;
  market_event_visibility_bonus: number;
  price_estimate_accuracy_bonus: number;
  dashboard_summary_bonus: boolean;
  unlock_shop_level: number;
}

export interface ShopUpgradeDefinition {
  key: string;
  title: string;
  description: string;
  category: ShopUpgradeCategory;
  level: number;
  max_level: number;
  cost_vnd: number;
  required_shop_level: number;
  required_upgrade_keys: string[];
  requirements: string[];
  status: ShopUpgradeStatus;
  locked_reason: string | null;
  effects_json: Record<string, unknown>;
  icon: string | null;
}

export interface PurchasedShopUpgrade {
  id: number;
  save_game_id: number;
  upgrade_key: string;
  level: number;
  purchased_on_day: number | null;
  cost_paid_vnd: number;
  created_at: string;
  updated_at: string;
}

export interface ProgressionState {
  shop_level: number;
  shop_xp: number;
  cash: number;
  purchased_upgrades: PurchasedShopUpgrade[];
  available_upgrades: ShopUpgradeDefinition[];
  locked_upgrades: ShopUpgradeDefinition[];
  upgrade_effect_summary: ShopUpgradeEffectSummary;
  summary: Record<string, unknown>;
  inventory_capacity_summary: Record<string, number>;
}

export interface ShopUpgradePurchaseResponse {
  cash_delta: number;
  upgrade: PurchasedShopUpgrade;
  progression: ProgressionState;
}

export type RefurbishActionType =
  | "CLEAN_DUST"
  | "REPASTE"
  | "REPLACE_FAN"
  | "REPLACE_THERMAL_PADS"
  | "FIRMWARE_FLASH"
  | "BASIC_REPAIR"
  | "DEEP_DIAGNOSTIC"
  | "STRESS_VALIDATION"
  | "COSMETIC_CLEANUP";

export type RefurbishResultStatus = "COMPLETED" | "PARTIAL_SUCCESS" | "FAILED" | "NOT_APPLICABLE" | "BLOCKED";

export interface RefurbishActionEstimate {
  action_type: RefurbishActionType;
  cost_vnd: number;
  duration_days: number;
  applicable: boolean;
  unavailable_reason: string | null;
}

export interface InventoryRefurbishEvent {
  id: number;
  save_game_id: number;
  inventory_unit_id: number;
  action_type: RefurbishActionType;
  status: RefurbishResultStatus;
  cost_vnd: number;
  duration_days: number;
  started_on_day: number | null;
  completed_on_day: number | null;
  before_grade: Grade | null;
  after_grade: Grade | null;
  before_condition_json: Record<string, unknown> | null;
  after_condition_json: Record<string, unknown> | null;
  health_delta: number;
  thermal_delta: number;
  fan_delta: number;
  vram_delta: number;
  stability_delta: number;
  cosmetic_delta: number;
  risk_delta: number;
  resale_value_delta_vnd: number | null;
  summary: string;
  notes: string | null;
  created_at: string;
}

export interface RefurbishActionRunResponse {
  event: InventoryRefurbishEvent;
  unit: InventoryUnit;
}

export interface RefurbishSummary {
  queue_count: number;
  ready_for_resale_count: number;
  recent_events: Array<{
    id: number;
    inventory_unit_id: number;
    action_type: RefurbishActionType;
    status: RefurbishResultStatus;
    cost_vnd: number;
    summary: string;
    created_at: string;
  }>;
}

export interface UsedMarketSummary {
  active_listings_count: number;
  open_negotiations_count: number;
  recent_listings: Array<{
    id: number;
    seller_name: string;
    product_name: string;
    asking_price_vnd: number;
    estimated_fair_value_vnd: number;
    status: string;
    visible_condition_grade: string | null;
    expires_on_day: number;
  }>;
}

export type SupplierTier = "OFFICIAL_DISTRIBUTOR" | "WHOLESALE" | "IMPORTER" | "GRAY_MARKET" | "USED_MARKET" | "OTHER";

export interface Supplier {
  id: number;
  name: string;
  slug: string | null;
  type: string;
  supplier_tier: SupplierTier | null;
  trust_score: number;
  relationship_score: number;
  delivery_days: number;
  default_delivery_days: number | null;
  notes: string | null;
  country_code: string | null;
  invoice_currency: string;
  fx_spread_percent: number | null;
  import_fee_percent: number | null;
  payment_fee_flat_vnd: number | null;
  supported_brand_slugs_json: string[] | null;
  supported_category_json: string[] | null;
}

export interface SupplierOffer {
  id: number;
  supplier_id: number;
  supplier: Supplier;
  product_id: number;
  product: HardwareProduct;
  unit_price_vnd: number;
  min_order_quantity: number;
  available_quantity: number;
  warranty_months: number;
  expires_at: string | null;
  foreign_unit_price: number | null;
  foreign_currency: string | null;
  quality_risk_modifier: number | null;
  expires_on_day: number | null;
  offer_type: string | null;
  effective_unit_price_vnd: number;
  effective_fx_rate_to_vnd: number | null;
  effective_fx_provider: string | null;
  effective_fx_is_fallback: boolean;
  effective_fx_fetched_at: string | null;
  market_multiplier?: number;
  market_adjusted_unit_price_vnd?: number;
  active_market_event_titles?: string[];
}

export interface PurchaseOrderItem {
  id: number;
  purchase_order_id: number;
  product_id: number;
  product: HardwareProduct;
  quantity: number;
  unit_price_vnd: number;
  warranty_months: number;
}

export interface PurchaseOrder {
  id: number;
  save_game_id: number;
  supplier_id: number;
  supplier: Supplier;
  status: PurchaseOrderStatus;
  subtotal_vnd: number;
  delivery_due_day: number;
  created_at: string;
  updated_at: string;
  items: PurchaseOrderItem[];
  invoice_currency: string;
  foreign_subtotal: number | null;
  fx_rate_to_vnd: number | null;
  fx_provider: string | null;
  fx_fetched_at: string | null;
  fx_is_fallback: boolean;
  fx_spread_percent: number | null;
  fx_fee_vnd: number;
  final_total_vnd: number | null;
}

export interface Customer {
  id: number;
  save_game_id: number;
  name: string;
  archetype: string;
  knowledge_level: string;
  patience: number;
  negotiation_score: number;
  risk_tolerance: string;
  created_at: string;
  country_code: string | null;
  preferred_currency: string;
  persona_type: CustomerPersonaType | null;
  preference_json: Record<string, unknown> | null;
  preferred_brand_slugs_json: string[] | null;
  disliked_brand_slugs_json: string[] | null;
  accepts_used_parts: boolean | null;
  warranty_sensitivity: number | null;
  price_sensitivity: number | null;
  performance_priority: number | null;
  aesthetics_priority: number | null;
  reliability_priority: number | null;
}

export interface CustomerRequest {
  id: number;
  customer_id: number;
  customer: Customer;
  request_type: string;
  budget_vnd: number;
  use_case: string;
  target_performance_score: number | null;
  requirements_json: Record<string, unknown> | null;
  persona_type: CustomerPersonaType | null;
  preference_json: Record<string, unknown> | null;
  priority_tags_json: string[] | null;
  accepts_used_parts: boolean | null;
  min_compatibility_score: number | null;
  min_build_quality_score: number | null;
  used_part_tolerance: number | null;
  warranty_expectation_days: number | null;
  status: string;
  created_at: string;
  updated_at: string;
  budget_currency: string;
  foreign_budget_amount: number | null;
  budget_fx_rate_to_vnd: number | null;
  conversation_id: number | null;
  conversation_status: string | null;
}

export type CustomerPersonaType =
  | "BUDGET_GAMER"
  | "ESPORTS_PLAYER"
  | "STREAMER"
  | "OFFICE_BUYER"
  | "CREATOR_EDITOR"
  | "AI_WORKSTATION"
  | "STUDENT"
  | "RGB_ENTHUSIAST"
  | "QUIET_PC_LOVER"
  | "BRAND_LOYALIST"
  | "WARRANTY_SENSITIVE"
  | "BARGAIN_HUNTER"
  | "PREMIUM_BUILDER";

export type ReviewSourceType = "ORDER_DELIVERY" | "RESALE_SALE" | "WARRANTY_RMA" | "MANUAL";
export type ReviewSentiment = "POSITIVE" | "NEUTRAL" | "NEGATIVE";
export type CustomerConversationStatus =
  | "OPEN"
  | "WAITING_FOR_PLAYER"
  | "WAITING_FOR_CUSTOMER"
  | "QUOTE_PROPOSED"
  | "READY_TO_ORDER"
  | "CLOSED_WON"
  | "CLOSED_LOST"
  | "ARCHIVED";
export type CustomerConversationStage =
  | "NEW_REQUEST"
  | "NEEDS_CONSULTATION"
  | "QUALIFYING_NEEDS"
  | "DISCUSSING_USED_PARTS"
  | "QUOTE_BUILDING"
  | "QUOTE_SENT"
  | "NEGOTIATING"
  | "READY_TO_ORDER"
  | "CLOSED";
export type ConversationMessageSender = "CUSTOMER" | "PLAYER" | "STAFF" | "SYSTEM";
export type ConversationMessageType = "TEXT" | "SYSTEM_NOTE" | "QUICK_REPLY" | "QUOTE_ATTACHMENT" | "ACTION_EVENT";
export type ConversationActionType =
  | "ASK_BUDGET"
  | "ASK_USE_CASE"
  | "ASK_USED_PARTS"
  | "RECOMMEND_VALUE_BUILD"
  | "RECOMMEND_ALL_NEW_BUILD"
  | "EXPLAIN_WARRANTY_RISK"
  | "ASSIGN_SALES_STAFF"
  | "GENERATE_QUOTE"
  | "SEND_QUOTE"
  | "CONVERT_TO_ORDER"
  | "CLOSE_WON"
  | "CLOSE_LOST";

export interface CustomerPersonaDefinition {
  persona_type: CustomerPersonaType | "GENERIC";
  label: string;
  description: string;
  budget_multiplier_range: [number, number];
  accepts_used_parts_default: boolean;
  price_sensitivity: number;
  performance_priority: number;
  reliability_priority: number;
  aesthetics_priority: number;
  warranty_sensitivity: number;
  preferred_priorities: string[];
  default_min_compatibility_score: number;
  default_min_build_quality_score: number;
  preference_hints: string[];
  preferred_brand_slugs: string[];
  disliked_brand_slugs: string[];
  used_part_tolerance: number;
  warranty_expectation_days: number;
  sample_use_case: string;
}

export interface QuotePersonaEvaluation {
  quote_id: number;
  customer_fit_score: number | null;
  persona_match_score: number | null;
  price_fit_score: number | null;
  performance_fit_score: number | null;
  reliability_fit_score: number | null;
  aesthetics_fit_score: number | null;
  used_part_fit_score: number | null;
  quote_acceptance_chance: number | null;
  customer_feedback_summary: string | null;
  warnings: CompatibilityWarning[];
}

export interface CustomerReview {
  id: number;
  save_game_id: number;
  customer_id: number | null;
  order_id: number | null;
  resale_listing_id: number | null;
  warranty_claim_id: number | null;
  source_type: ReviewSourceType;
  source_key: string;
  sentiment: ReviewSentiment;
  rating: number;
  title: string;
  body: string;
  tags_json: string[] | null;
  persona_type: CustomerPersonaType | string | null;
  source_summary: string | null;
  quote_fit_score: number | null;
  compatibility_score: number | null;
  build_quality_score: number | null;
  warranty_risk_score: number | null;
  final_price_vnd: number | null;
  reputation_delta: number;
  generated_on_day: number | null;
  is_public: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReputationSummary {
  save_game_id: number;
  reputation: number;
  total_reviews: number;
  average_rating: number | null;
  positive_reviews: number;
  neutral_reviews: number;
  negative_reviews: number;
  sentiment_counts: Record<string, number>;
  source_counts: Record<string, number>;
}

export interface ReviewGenerateRequest {
  source_type?: ReviewSourceType | null;
  order_id?: number | null;
  resale_listing_id?: number | null;
  warranty_claim_id?: number | null;
}

export interface CustomerConversationMessage {
  id: number;
  conversation_id: number;
  sender_type: ConversationMessageSender;
  sender_label: string | null;
  staff_id: number | null;
  message_type: ConversationMessageType;
  body: string;
  action_type: ConversationActionType | null;
  quote_id: number | null;
  metadata_json: Record<string, unknown> | null;
  created_on_day: number | null;
  created_at: string;
}

export interface CustomerConversation {
  id: number;
  save_game_id: number;
  customer_id: number | null;
  customer?: Customer | null;
  customer_request_id: number | null;
  customer_request?: CustomerRequest | null;
  assigned_staff_id: number | null;
  assigned_staff?: StaffMember | null;
  status: CustomerConversationStatus;
  stage: CustomerConversationStage;
  persona_type: string | null;
  title: string | null;
  customer_mood: string | null;
  engagement_score: number;
  urgency_score: number;
  conversion_probability: number | null;
  detected_budget_vnd: number | null;
  detected_use_case: string | null;
  detected_preferences_json: Record<string, unknown> | null;
  accepts_used_parts: boolean | null;
  last_message_at: string | null;
  created_on_day: number | null;
  created_at: string;
  messages?: CustomerConversationMessage[];
}

export interface CustomerConversationCreateResponse {
  conversation: CustomerConversation;
  created: boolean;
}

export interface ConversationMessageCreateRequest {
  body: string;
  locale?: UiLanguage;
}

export interface ConversationQuickReplyRequest {
  action_type: ConversationActionType;
  locale?: UiLanguage;
}

export interface ConversationAssignStaffRequest {
  staff_id: number;
  locale?: UiLanguage;
}

export interface ConversationCloseRequest {
  won: boolean;
  locale?: UiLanguage;
}

export interface ConversationSendQuoteResponse {
  conversation: CustomerConversation;
  quote: Quote;
  message: CustomerConversationMessage;
  conversion_probability: number | null;
}

export interface Order {
  id: number;
  save_game_id: number;
  customer_id: number;
  customer: Customer;
  request_id: number | null;
  status: OrderStatus;
  quoted_price_vnd: number;
  cost_vnd: number;
  profit_vnd: number;
  customer_fit_score: number | null;
  started_at: string | null;
  testing_started_at: string | null;
  delivered_at: string | null;
  build_quality_score: number | null;
  final_test_score: number | null;
  final_warranty_risk: string | null;
  reputation_delta: number | null;
  delivery_summary: string | null;
  warranty_eligible: boolean;
  warranty_expires_at: string | null;
  warranty_claim_count: number;
  warranty_status: string | null;
  last_warranty_event_at: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  items: OrderItem[];
  order_currency: string;
  foreign_order_amount: number | null;
  fx_rate_to_vnd: number | null;
  fx_provider: string | null;
  fx_fetched_at: string | null;
  fx_is_fallback: boolean;
  fx_spread_percent: number | null;
  compatibility_score?: number | null;
  power_headroom_score?: number | null;
  bottleneck_score?: number | null;
  build_quality_score_estimate?: number | null;
  warranty_risk_delta?: number | null;
  compatibility_warnings_json?: CompatibilityWarning[] | null;
  compatibility_result?: CompatibilityResult | null;
}

export interface OrderItem {
  id: number;
  order_id: number;
  inventory_unit_id: number | null;
  inventory_unit?: InventoryUnit | null;
  product_id: number;
  product: HardwareProduct;
  quantity: number;
  unit_price_vnd: number;
  cost_vnd: number;
}

export interface OrderFulfillmentEvent {
  id: number;
  order_id: number;
  event_type: OrderFulfillmentEventType;
  summary: string;
  raw_result_json: Record<string, unknown> | null;
  created_at: string;
}

export interface OrderDetail {
  order: Order;
  fulfillment_events: OrderFulfillmentEvent[];
}

export interface DeliverOrderResponse {
  order_detail: OrderDetail;
  cash_delta: number;
  reputation_delta: number;
}

export interface Quote {
  id: number;
  save_game_id: number;
  customer_id: number;
  customer: Customer;
  customer_request_id: number;
  customer_request: CustomerRequest;
  status: QuoteStatus;
  title: string;
  summary: string;
  quoted_price_vnd: number;
  estimated_cost_vnd: number;
  estimated_profit_vnd: number;
  customer_fit_score: number | null;
  performance_score: number | null;
  value_score: number | null;
  thermal_score: number | null;
  reliability_score: number | null;
  persona_match_score: number | null;
  price_fit_score: number | null;
  performance_fit_score: number | null;
  reliability_fit_score: number | null;
  aesthetics_fit_score: number | null;
  used_part_fit_score: number | null;
  quote_acceptance_chance: number | null;
  customer_feedback_summary: string | null;
  persona_warnings_json?: CompatibilityWarning[] | null;
  warranty_risk: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  quote_currency: string;
  foreign_quoted_price: number | null;
  fx_rate_to_vnd: number | null;
  fx_provider: string | null;
  fx_fetched_at: string | null;
  fx_is_fallback: boolean;
  fx_spread_percent: number | null;
  compatibility_score?: number | null;
  power_headroom_score?: number | null;
  bottleneck_score?: number | null;
  build_quality_score_estimate?: number | null;
  warranty_risk_delta?: number | null;
  compatibility_warnings_json?: CompatibilityWarning[] | null;
  compatibility_result?: CompatibilityResult | null;
}

export interface QuoteItem {
  id: number;
  quote_id: number;
  product_id: number;
  product: HardwareProduct;
  inventory_unit_id: number | null;
  inventory_unit: InventoryUnit | null;
  quantity: number;
  unit_price_vnd: number;
  unit_cost_vnd: number;
  source: QuoteItemSource;
  is_reserved: boolean;
  notes: string | null;
}

export interface QuoteDetail {
  quote: Quote;
  quote_items: QuoteItem[];
}

export interface WarrantyClaim {
  id: number;
  save_game_id: number;
  order_id: number | null;
  resale_listing_id: number | null;
  inventory_unit_id: number | null;
  customer_id: number | null;
  customer: Customer | null;
  order?: Order | null;
  resale_listing?: ResaleListing | null;
  inventory_unit?: InventoryUnit | null;
  claim_type: WarrantyClaimType;
  status: WarrantyClaimStatus;
  claim_reason: WarrantyClaimReason;
  title: string;
  complaint_summary: string;
  description: string | null;
  severity: number;
  claimed_on_day: number;
  due_on_day: number | null;
  resolved_on_day: number | null;
  customer_message: string | null;
  internal_risk_score: number;
  estimated_cost_vnd: number;
  final_cost_vnd: number | null;
  diagnostic_summary: string | null;
  resolution_summary: string | null;
  resolution_type: WarrantyResolutionType | null;
  notes: string | null;
  claimed_at: string;
  updated_at: string;
  diagnosed_at: string | null;
  resolved_at: string | null;
  reimbursement_vnd: number;
  repair_cost_vnd: number;
  replacement_cost_vnd: number;
  rma_shipping_cost_vnd: number;
  reputation_delta: number | null;
  warranty_valid: boolean;
  internal_notes: string | null;
}

export interface WarrantyClaimItem {
  id: number;
  warranty_claim_id: number;
  order_item_id: number | null;
  inventory_unit_id: number | null;
  inventory_unit: InventoryUnit | null;
  product_id: number | null;
  product: HardwareProduct | null;
  suspected_issue: string | null;
  diagnosis_result: string | null;
  action_taken: string | null;
  replacement_inventory_unit_id: number | null;
  replacement_inventory_unit: InventoryUnit | null;
  created_at: string;
  updated_at: string;
}

export interface WarrantyEvent {
  id: number;
  warranty_claim_id: number;
  event_type: WarrantyEventType;
  summary: string;
  raw_result_json: Record<string, unknown> | null;
  created_at: string;
}

export interface WarrantyClaimDetail {
  claim: WarrantyClaim;
  claim_items: WarrantyClaimItem[];
  order: Order | null;
  resale_listing?: ResaleListing | null;
  events: WarrantyEvent[];
}

export interface WarrantyClaimGenerateRequest {
  source_type?: string | null;
  order_id?: number | null;
  resale_listing_id?: number | null;
  inventory_unit_id?: number | null;
}

export interface WarrantyClaimReviewRequest {
  notes?: string | null;
}

export interface WarrantyClaimResolveRequest {
  resolution_type: WarrantyResolutionType;
  notes?: string | null;
}

export interface WarrantyClaimResolveResponse {
  claim: WarrantyClaim;
  cash_delta: number;
  reputation_delta: number;
}

export interface WarrantyClaimSummary {
  save_game_id: number;
  total_claims: number;
  open_claims_count: number;
  in_review_claims_count: number;
  approved_claims_count: number;
  resolved_claims_count: number;
  rejected_claims_count: number;
  due_soon_claims_count: number;
  overdue_claims_count: number;
  estimated_exposure_vnd: number;
  unresolved_risk_score: number;
  recent_claims: WarrantyClaim[];
}

export type CurrencyCode = "VND" | "USD" | "EUR" | "JPY" | "CNY" | "TWD" | "HKD" | "KRW" | "SGD" | "THB";

export interface ExchangeRate {
  id: number;
  base_currency: string;
  quote_currency: string;
  rate: number;
  provider: string;
  source: string | null;
  fetched_at: string;
  valid_for_day: string | null;
  is_fallback: boolean;
  created_at: string;
  updated_at: string;
}

export interface CurrencyConversionResult {
  amount: number;
  from_currency: string;
  to_currency: string;
  converted_amount: number;
  rate: number;
  provider: string;
  fetched_at: string;
  is_fallback: boolean;
  spread_applied: number;
  final_amount_vnd: number | null;
}

export interface SupportedCurrency {
  code: string;
  name: string;
  symbol: string;
  country: string;
}

export interface ProductPriceSnapshot {
  id: number;
  product_id: number;
  product_slug: string;
  price_type: string;
  currency: string;
  amount: number;
  amount_vnd: number;
  fx_rate_to_vnd: number | null;
  fx_provider: string | null;
  fx_fetched_at: string | null;
  fx_is_fallback: boolean;
  region: string | null;
  source_name: string | null;
  source_url: string | null;
  confidence: string;
  observed_at: string;
  is_current: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export type MarketEventType =
  | "MINING_BOOM"
  | "MINING_CRASH"
  | "AI_DATACENTER_DEMAND"
  | "NEW_GPU_GENERATION"
  | "SUPPLY_SHORTAGE"
  | "OVERSUPPLY_CLEARANCE"
  | "ESPORTS_SEASON"
  | "BACK_TO_SCHOOL"
  | "DEFECTIVE_BATCH_RUMOR"
  | "DRIVER_DRAMA"
  | "TAIWAN_SUPPLY_DELAY"
  | "CHINA_BUDGET_PARTS_FLOOD"
  | "CURRENCY_SHOCK"
  | "RANDOM_DEMAND_SPIKE"
  | "RANDOM_PRICE_CRASH";

export type MarketEventGenerationSource = "RULE" | "AI_PROPOSED" | "AI_FALLBACK" | "MANUAL";

export interface MarketEventCreateRequest {
  event_type?: MarketEventType;
  title: string;
  summary: string;
  severity: number;
  affected_category?: string | null;
  affected_brand_slug?: string | null;
  affected_origin_code?: string | null;
  affected_currency?: string | null;
  affected_product_id?: number | null;
  price_multiplier?: number;
  demand_delta?: number;
  supply_delta?: number;
  reliability_delta?: number;
  quality_risk_delta?: number;
  starts_on_day: number;
  ends_on_day: number;
  is_active?: boolean;
}

export interface MarketEvent {
  id: number;
  save_game_id: number | null;
  event_type: MarketEventType;
  title: string;
  summary: string;
  severity: number;
  affected_category: HardwareCategory | null;
  affected_brand_slug: string | null;
  affected_origin_code: string | null;
  affected_currency: string | null;
  affected_product_id: number | null;
  price_multiplier: number;
  demand_delta: number;
  supply_delta: number;
  reliability_delta: number;
  quality_risk_delta: number;
  starts_on_day: number;
  ends_on_day: number;
  is_active: boolean;
  generation_source: MarketEventGenerationSource;
  ai_prompt_context_json: Record<string, unknown> | null;
  ai_raw_proposal_json: Record<string, unknown> | null;
  raw_effect_json: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface MarketSummary {
  active_market_events_count: number;
  impacted_categories: string[];
  impacted_brands: string[];
  impacted_origins: string[];
  strongest_market_multiplier: number;
  recent_market_events: Array<{
    id: number;
    title: string;
    event_type: string;
    severity: number;
    price_multiplier: number;
    starts_on_day: number;
    ends_on_day: number;
    is_active: boolean;
  }>;
  market_pressure_summary: string;
}

export type UsedPartListingStatus = "AVAILABLE" | "NEGOTIATING" | "ACCEPTED" | "REJECTED" | "EXPIRED";
export type UsedPartNegotiationStatus = "OPEN" | "ACCEPTED" | "REJECTED" | "FAILED" | "CLOSED";
export type NegotiationSender = "PLAYER" | "SELLER" | "SYSTEM";

export interface PlayerProfile {
  id: number;
  display_name: string;
  slug: string;
  pin_enabled: boolean;
  last_unlocked_at: string | null;
  failed_unlock_attempts: number;
  locked_until: string | null;
  last_failed_unlock_at: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProfileUnlockResponse {
  token: string;
  expires_at: string;
}

export interface NegotiationMessage {
  id: number;
  negotiation_id: number;
  sender: NegotiationSender;
  message: string;
  offer_vnd: number | null;
  created_at: string;
  updated_at: string;
}

export interface UsedPartNegotiation {
  id: number;
  listing_id: number;
  save_game_id: number;
  status: UsedPartNegotiationStatus;
  current_offer_vnd: number | null;
  last_seller_response: string | null;
  rounds_count: number;
  accepted_price_vnd: number | null;
  created_at: string;
  updated_at: string;
  messages: NegotiationMessage[];
}

export interface UsedPartListing {
  id: number;
  save_game_id: number;
  seller_name: string;
  product_id: number;
  product: HardwareProduct;
  asking_price_vnd: number;
  estimated_fair_value_vnd: number;
  min_accept_price_vnd: number;
  status: UsedPartListingStatus;
  seller_honesty: number;
  seller_patience: number;
  claimed_condition: string | null;
  claimed_usage: string | null;
  claimed_warranty_months: number | null;
  visible_condition_grade: string | null;
  risk_score: number;
  market_multiplier_at_creation: number;
  created_on_day: number;
  expires_on_day: number;
  final_price_vnd: number | null;
  created_at: string;
  updated_at: string;
}

export type ResaleListingStatus = "DRAFT" | "ACTIVE" | "OFFER_RECEIVED" | "SOLD" | "CANCELLED" | "EXPIRED";
export type ResaleBuyerOfferStatus = "PENDING" | "ACCEPTED" | "REJECTED" | "EXPIRED";

export interface ResaleBuyerOffer {
  id: number;
  listing_id: number;
  save_game_id: number;
  buyer_name: string;
  offer_price_vnd: number;
  status: ResaleBuyerOfferStatus;
  message: string | null;
  buyer_patience: number;
  buyer_strictness: number;
  created_on_day: number;
  expires_on_day: number | null;
  created_at: string;
  updated_at: string;
}

export interface ResaleListing {
  id: number;
  save_game_id: number;
  inventory_unit_id: number | null;
  inventory_unit: InventoryUnit | null;
  title: string;
  description: string | null;
  asking_price_vnd: number;
  estimated_market_value_vnd: number;
  minimum_accept_price_vnd: number | null;
  status: ResaleListingStatus;
  listing_quality_score: number;
  buyer_interest_score: number;
  market_multiplier_at_listing: number;
  grade_at_listing: string | null;
  inspection_confidence_at_listing: number | null;
  warranty_days_offered: number;
  created_on_day: number;
  expires_on_day: number | null;
  sold_on_day: number | null;
  final_sale_price_vnd: number | null;
  reputation_delta: number;
  risk_note: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  offers: ResaleBuyerOffer[];
}

export interface ResaleListingCreate {
  inventory_unit_id: number;
  asking_price_vnd?: number | null;
  warranty_days_offered?: number;
}

export interface ResaleOfferGenerateResponse {
  offer: ResaleBuyerOffer;
  listing: ResaleListing;
}

export interface ResaleSaleResponse {
  offer: ResaleBuyerOffer;
  listing: ResaleListing;
  cash_after_sale: number;
  reputation_after_sale: number;
}
