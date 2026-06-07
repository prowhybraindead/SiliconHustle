import type { Brand, HardwareProduct, SupplierOffer, ProductPriceSnapshot, MarketEventCreateRequest } from "../types/game";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export interface BrandListParams {
  category?: string;
  q?: string;
  market_tier?: string;
  brand_type?: string;
  origin_code?: string;
}

export interface HardwareProductListParams {
  category?: string;
  brand_slug?: string;
  q?: string;
  origin_code?: string;
  data_confidence?: string;
  save_game_id?: number;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("profile_unlock_token") : null;
  const extraHeaders: Record<string, string> = {};
  if (token) {
    extraHeaders["X-Profile-Unlock-Token"] = token;
  }
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...extraHeaders,
      ...(options.headers ?? {}),
    },
    ...options,
  });

  if (!response.ok) {
    let message = response.statusText;
    try {
      const body = (await response.json()) as { detail?: string };
      message = body.detail ?? message;
    } catch {
      message = response.statusText;
    }
    throw new ApiError(message, response.status);
  }

  return response.json() as Promise<T>;
}

export const apiBaseUrl = API_BASE_URL;

export function listBrands(params: BrandListParams = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value) query.set(key, value);
  });
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return apiRequest<Brand[]>(`/api/brands${suffix}`);
}

export function getBrand(brandId: number) {
  return apiRequest<Brand>(`/api/brands/${brandId}`);
}

export function listHardwareProducts(params: HardwareProductListParams = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value) query.set(key, value);
  });
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return apiRequest<HardwareProduct[]>(`/api/hardware-products${suffix}`);
}

export function getHardwareProduct(productId: number, saveGameId?: number) {
  const query = saveGameId ? `?save_game_id=${saveGameId}` : "";
  return apiRequest<HardwareProduct>(`/api/hardware-products/${productId}${query}`);
}

export function listSupportedCurrencies() {
  return apiRequest<import("../types/game").SupportedCurrency[]>("/api/fx/supported-currencies");
}

export function listFxRates(base?: string, quote?: string) {
  const query = new URLSearchParams();
  if (base) query.set("base", base);
  if (quote) query.set("quote", quote);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return apiRequest<import("../types/game").ExchangeRate[] | import("../types/game").ExchangeRate>(`/api/fx/rates${suffix}`);
}

export function refreshFxRates(force: boolean = false) {
  return apiRequest<import("../types/game").ExchangeRate[]>(`/api/fx/rates/refresh?force=${force}`, {
    method: "POST",
  });
}

export function convertCurrency(amount: number, fromCurrency: string, toCurrency: string = "VND", spreadPercent: number = 0) {
  return apiRequest<import("../types/game").CurrencyConversionResult>(
    `/api/fx/convert?amount=${amount}&from_currency=${fromCurrency}&to_currency=${toCurrency}&spread_percent=${spreadPercent}`
  );
}

export function getFxAttribution() {
  return apiRequest<{ attribution: string }>("/api/fx/attribution");
}

export interface SupplierOfferListParams {
  category?: string;
  brand_slug?: string;
  supplier_id?: number;
  q?: string;
  currency?: string;
  save_game_id?: number;
}

export function listSupplierOffers(params: SupplierOfferListParams = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      query.set(key, String(value));
    }
  });
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return apiRequest<SupplierOffer[]>(`/api/supplier-offers${suffix}`);
}

export interface ProductPriceListParams {
  product_slug?: string;
  product_id?: number;
  price_type?: string;
  region?: string;
  current_only?: boolean;
  currency?: string;
  confidence?: string;
}

export function listProductPrices(params: ProductPriceListParams = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      query.set(key, String(value));
    }
  });
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return apiRequest<ProductPriceSnapshot[]>(`/api/product-prices${suffix}`);
}

export function listMarketEvents(saveGameId: number, activeOnly?: boolean) {
  const query = activeOnly ? "?active_only=true" : "";
  return apiRequest<import("../types/game").MarketEvent[]>(`/api/save-games/${saveGameId}/market/events${query}`);
}

export function getActiveMarketEvents(saveGameId: number) {
  return apiRequest<import("../types/game").MarketEvent[]>(`/api/save-games/${saveGameId}/market/events/active`);
}

export function generateMarketEvent(saveGameId: number, mode: string = "rule") {
  return apiRequest<import("../types/game").MarketEvent>(`/api/save-games/${saveGameId}/market/events/generate?mode=${mode}`, {
    method: "POST"
  });
}

export function advanceMarketDay(saveGameId: number) {
  return apiRequest<import("../types/game").MarketSummary>(`/api/save-games/${saveGameId}/advance-day`, {
    method: "POST"
  });
}

export function getMarketSummary(saveGameId: number) {
  return apiRequest<import("../types/game").MarketSummary>(`/api/save-games/${saveGameId}/market/summary`);
}

export function createMarketEvent(saveGameId: number, payload: MarketEventCreateRequest) {
  return apiRequest<import("../types/game").MarketEvent>(`/api/save-games/${saveGameId}/market/events`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export interface SaveGamePinPayload {
  pin: string;
  current_pin?: string;
}

export function updateSaveGamePin(saveGameId: number, payload: SaveGamePinPayload) {
  return apiRequest<import("../types/game").SaveGame>(`/api/save-games/${saveGameId}/pin`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function disableSaveGamePin(saveGameId: number, currentPin?: string) {
  return apiRequest<import("../types/game").SaveGame>(`/api/save-games/${saveGameId}/pin`, {
    method: "DELETE",
    body: JSON.stringify({ current_pin: currentPin }),
  });
}

export function deleteSaveGame(saveGameId: number) {
  return apiRequest<{ message: string }>(`/api/save-games/${saveGameId}`, {
    method: "DELETE",
  });
}

// Player Profile APIs
export function listPlayerProfiles() {
  return apiRequest<import("../types/game").PlayerProfile[]>("/api/player-profiles");
}

export function createPlayerProfile(displayName: string, pin?: string) {
  return apiRequest<import("../types/game").PlayerProfile>("/api/player-profiles", {
    method: "POST",
    body: JSON.stringify({ display_name: displayName, pin })
  });
}

export function getPlayerProfile(profileId: number) {
  return apiRequest<import("../types/game").PlayerProfile>(`/api/player-profiles/${profileId}`);
}

export function unlockPlayerProfile(profileId: number, pin: string) {
  return apiRequest<import("../types/game").ProfileUnlockResponse>(`/api/player-profiles/${profileId}/unlock`, {
    method: "POST",
    body: JSON.stringify({ pin })
  });
}

export function lockPlayerProfile(profileId: number) {
  return apiRequest<{ message: string }>(`/api/player-profiles/${profileId}/lock`, {
    method: "POST"
  });
}

export function changePlayerProfilePin(profileId: number, pin: string, currentPin?: string) {
  return apiRequest<import("../types/game").PlayerProfile>(`/api/player-profiles/${profileId}/pin`, {
    method: "PATCH",
    body: JSON.stringify({ pin, current_pin: currentPin })
  });
}

export function disablePlayerProfilePin(profileId: number, currentPin?: string) {
  return apiRequest<import("../types/game").PlayerProfile>(`/api/player-profiles/${profileId}/pin`, {
    method: "DELETE",
    body: JSON.stringify({ current_pin: currentPin })
  });
}

export function assignSaveGameProfile(saveGameId: number, profileId: number) {
  return apiRequest<import("../types/game").SaveGame>(`/api/save-games/${saveGameId}/assign-profile`, {
    method: "POST",
    body: JSON.stringify({ profile_id: profileId })
  });
}

// Customer Persona APIs
export function listCustomerPersonas() {
  return apiRequest<import("../types/game").CustomerPersonaDefinition[]>("/api/customer-personas");
}

export function getCustomerPersona(personaType: string) {
  return apiRequest<import("../types/game").CustomerPersonaDefinition>(`/api/customer-personas/${encodeURIComponent(personaType)}`);
}

export function assignCustomerPersona(saveGameId: number, customerId: number, personaType: string) {
  return apiRequest<import("../types/game").Customer>(
    `/api/save-games/${saveGameId}/customers/${customerId}/persona`,
    {
      method: "POST",
      body: JSON.stringify({ persona_type: personaType }),
    }
  );
}

export function evaluateRequestQuotes(saveGameId: number, requestId: number) {
  return apiRequest<import("../types/game").QuotePersonaEvaluation[]>(
    `/api/save-games/${saveGameId}/customer-requests/${requestId}/evaluate-quotes`,
    {
      method: "POST",
    }
  );
}

export interface CustomerConversationListParams {
  status?: string;
}

export function listCustomerConversations(saveGameId: number, params: CustomerConversationListParams = {}) {
  const query = new URLSearchParams();
  if (params.status) query.set("status", params.status);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return apiRequest<import("../types/game").CustomerConversation[]>(`/api/save-games/${saveGameId}/customer-conversations${suffix}`);
}

export function getCustomerConversation(saveGameId: number, conversationId: number) {
  return apiRequest<import("../types/game").CustomerConversation>(`/api/save-games/${saveGameId}/customer-conversations/${conversationId}`);
}

export function listConversationMessages(saveGameId: number, conversationId: number) {
  return apiRequest<import("../types/game").CustomerConversationMessage[]>(
    `/api/save-games/${saveGameId}/customer-conversations/${conversationId}/messages`
  );
}

export function createConversationForRequest(
  saveGameId: number,
  requestId: number,
  locale: import("../types/game").UiLanguage = "vi",
) {
  return apiRequest<import("../types/game").CustomerConversationCreateResponse>(
    `/api/save-games/${saveGameId}/customer-requests/${requestId}/conversation?locale=${locale}`,
    { method: "POST" }
  );
}

export function sendConversationMessage(
  saveGameId: number,
  conversationId: number,
  body: string,
  locale: import("../types/game").UiLanguage = "vi",
) {
  return apiRequest<import("../types/game").CustomerConversation>(`/api/save-games/${saveGameId}/customer-conversations/${conversationId}/messages`, {
    method: "POST",
    body: JSON.stringify({ body, locale }),
  });
}

export function quickReplyConversation(
  saveGameId: number,
  conversationId: number,
  actionType: string,
  locale: import("../types/game").UiLanguage = "vi",
) {
  return apiRequest<import("../types/game").CustomerConversation>(`/api/save-games/${saveGameId}/customer-conversations/${conversationId}/quick-reply`, {
    method: "POST",
    body: JSON.stringify({ action_type: actionType, locale }),
  });
}

export function assignConversationStaff(
  saveGameId: number,
  conversationId: number,
  staffId: number,
  locale: import("../types/game").UiLanguage = "vi",
) {
  return apiRequest<import("../types/game").CustomerConversation>(`/api/save-games/${saveGameId}/customer-conversations/${conversationId}/assign-staff`, {
    method: "POST",
    body: JSON.stringify({ staff_id: staffId, locale }),
  });
}

export function sendQuoteToConversation(
  saveGameId: number,
  conversationId: number,
  quoteId: number,
  locale: import("../types/game").UiLanguage = "vi",
) {
  return apiRequest<import("../types/game").ConversationSendQuoteResponse>(
    `/api/save-games/${saveGameId}/customer-conversations/${conversationId}/send-quote/${quoteId}?locale=${locale}`,
    { method: "POST" }
  );
}

export function markConversationReadyToOrder(
  saveGameId: number,
  conversationId: number,
  locale: import("../types/game").UiLanguage = "vi",
) {
  return apiRequest<import("../types/game").CustomerConversation>(
    `/api/save-games/${saveGameId}/customer-conversations/${conversationId}/ready-to-order?locale=${locale}`,
    { method: "POST" }
  );
}

export function closeConversation(
  saveGameId: number,
  conversationId: number,
  won: boolean,
  locale: import("../types/game").UiLanguage = "vi",
) {
  return apiRequest<import("../types/game").CustomerConversation>(
    `/api/save-games/${saveGameId}/customer-conversations/${conversationId}/close`,
    { method: "POST", body: JSON.stringify({ won, locale }) }
  );
}

// Used Market APIs
export function listUsedPartListings(saveGameId: number, activeOnly: boolean = true) {
  return apiRequest<import("../types/game").UsedPartListing[]>(`/api/save-games/${saveGameId}/used-market/listings?active_only=${activeOnly}`);
}

export function generateUsedPartListing(saveGameId: number) {
  return apiRequest<import("../types/game").UsedPartListing>(`/api/save-games/${saveGameId}/used-market/listings/generate`, {
    method: "POST"
  });
}

export function generateBatchUsedPartListings(saveGameId: number, count: number = 5) {
  return apiRequest<import("../types/game").UsedPartListing[]>(`/api/save-games/${saveGameId}/used-market/listings/generate-batch?count=${count}`, {
    method: "POST"
  });
}

export function getUsedPartListing(saveGameId: number, listingId: number) {
  return apiRequest<import("../types/game").UsedPartListing>(`/api/save-games/${saveGameId}/used-market/listings/${listingId}`);
}

export function startUsedPartNegotiation(saveGameId: number, listingId: number) {
  return apiRequest<import("../types/game").UsedPartNegotiation>(`/api/save-games/${saveGameId}/used-market/listings/${listingId}/start-negotiation`, {
    method: "POST"
  });
}

export function submitNegotiationOffer(saveGameId: number, negotiationId: number, offerVnd: number, message?: string) {
  return apiRequest<import("../types/game").UsedPartNegotiation>(`/api/save-games/${saveGameId}/used-market/negotiations/${negotiationId}/offer`, {
    method: "POST",
    body: JSON.stringify({ offer_vnd: offerVnd, message })
  });
}

export function acceptUsedPartListing(saveGameId: number, listingId: number, finalPriceVnd?: number) {
  const query = finalPriceVnd ? `?final_price_vnd=${finalPriceVnd}` : "";
  return apiRequest<import("../types/game").UsedPartListing>(`/api/save-games/${saveGameId}/used-market/listings/${listingId}/accept${query}`, {
    method: "POST"
  });
}

export function rejectUsedPartListing(saveGameId: number, listingId: number) {
  return apiRequest<import("../types/game").UsedPartListing>(`/api/save-games/${saveGameId}/used-market/listings/${listingId}/reject`, {
    method: "POST"
  });
}

// Refurbish APIs
export function getRefurbishActions(saveGameId: number, inventoryUnitId: number) {
  return apiRequest<import("../types/game").RefurbishActionEstimate[]>(
    `/api/save-games/${saveGameId}/inventory/${inventoryUnitId}/refurbish/actions`
  );
}

export function runRefurbishAction(saveGameId: number, inventoryUnitId: number, actionType: string, staffId?: number) {
  return apiRequest<import("../types/game").RefurbishActionRunResponse>(
    `/api/save-games/${saveGameId}/inventory/${inventoryUnitId}/refurbish/actions/${actionType}`,
    {
      method: "POST",
      body: JSON.stringify(staffId ? { staff_id: staffId } : {}),
    }
  );
}

export function listRefurbishEvents(saveGameId: number, inventoryUnitId?: number) {
  const path = inventoryUnitId
    ? `/api/save-games/${saveGameId}/inventory/${inventoryUnitId}/refurbish/events`
    : `/api/save-games/${saveGameId}/refurbish/events`;
  return apiRequest<import("../types/game").InventoryRefurbishEvent[]>(path);
}

export function markReadyForResale(saveGameId: number, inventoryUnitId: number) {
  return apiRequest<import("../types/game").InventoryUnit>(
    `/api/save-games/${saveGameId}/inventory/${inventoryUnitId}/ready-for-resale`,
    { method: "POST" }
  );
}

export function unmarkReadyForResale(saveGameId: number, inventoryUnitId: number) {
  return apiRequest<import("../types/game").InventoryUnit>(
    `/api/save-games/${saveGameId}/inventory/${inventoryUnitId}/ready-for-resale`,
    { method: "DELETE" }
  );
}

// Resale APIs
export function listResaleListings(saveGameId: number, status?: string) {
  const query = status ? `?status=${status}` : "";
  return apiRequest<import("../types/game").ResaleListing[]>(
    `/api/save-games/${saveGameId}/resale/listings${query}`
  );
}

export function getResaleListing(saveGameId: number, listingId: number) {
  return apiRequest<import("../types/game").ResaleListing>(
    `/api/save-games/${saveGameId}/resale/listings/${listingId}`
  );
}

export function createResaleListing(saveGameId: number, payload: import("../types/game").ResaleListingCreate) {
  return apiRequest<import("../types/game").ResaleListing>(
    `/api/save-games/${saveGameId}/resale/listings`,
    { method: "POST", body: JSON.stringify(payload) }
  );
}

export function cancelResaleListing(saveGameId: number, listingId: number) {
  return apiRequest<import("../types/game").ResaleListing>(
    `/api/save-games/${saveGameId}/resale/listings/${listingId}`,
    { method: "DELETE" }
  );
}

export function generateResaleOffer(saveGameId: number, listingId: number, staffId?: number) {
  return apiRequest<import("../types/game").ResaleOfferGenerateResponse>(
    `/api/save-games/${saveGameId}/resale/listings/${listingId}/generate-offer`,
    {
      method: "POST",
      body: JSON.stringify(staffId ? { staff_id: staffId } : {}),
    }
  );
}

export function listResaleOffers(saveGameId: number, listingId?: number) {
  const query = listingId ? `?listing_id=${listingId}` : "";
  return apiRequest<import("../types/game").ResaleBuyerOffer[]>(
    `/api/save-games/${saveGameId}/resale/offers${query}`
  );
}

export function acceptResaleOffer(saveGameId: number, offerId: number) {
  return apiRequest<import("../types/game").ResaleSaleResponse>(
    `/api/save-games/${saveGameId}/resale/offers/${offerId}/accept`,
    { method: "POST" }
  );
}

export function rejectResaleOffer(saveGameId: number, offerId: number) {
  return apiRequest<import("../types/game").ResaleBuyerOffer>(
    `/api/save-games/${saveGameId}/resale/offers/${offerId}/reject`,
    { method: "POST" }
  );
}

// Staff APIs
export function listStaff(saveGameId: number, role?: string, status?: string) {
  const query = new URLSearchParams();
  if (role) query.set("role", role);
  if (status) query.set("status", status);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return apiRequest<import("../types/game").StaffMember[]>(`/api/save-games/${saveGameId}/staff${suffix}`);
}

export function getStaffMember(saveGameId: number, staffId: number) {
  return apiRequest<import("../types/game").StaffMember>(`/api/save-games/${saveGameId}/staff/${staffId}`);
}

export function hireStaff(saveGameId: number, payload: import("../types/game").StaffMemberCreate) {
  return apiRequest<import("../types/game").StaffMember>(`/api/save-games/${saveGameId}/staff`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function generateStaffCandidates(saveGameId: number, role?: string, count: number = 3) {
  const query = new URLSearchParams();
  if (role) query.set("role", role);
  query.set("count", String(count));
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return apiRequest<import("../types/game").StaffCandidate[]>(
    `/api/save-games/${saveGameId}/staff/candidates/generate${suffix}`,
    { method: "POST", body: JSON.stringify({}) }
  );
}

export function fireStaffMember(saveGameId: number, staffId: number) {
  return apiRequest<import("../types/game").StaffMember>(`/api/save-games/${saveGameId}/staff/${staffId}`, {
    method: "DELETE",
  });
}

export function getStaffSummary(saveGameId: number) {
  return apiRequest<import("../types/game").StaffSummary>(`/api/save-games/${saveGameId}/staff/summary`);
}

export function listStaffAssignments(saveGameId: number, limit: number = 20) {
  return apiRequest<import("../types/game").StaffAssignmentLog[]>(
    `/api/save-games/${saveGameId}/staff/assignments?limit=${limit}`
  );
}

export function assignStaff(saveGameId: number, staffId: number, payload: import("../types/game").StaffAssignRequest) {
  return apiRequest<import("../types/game").StaffAssignResponse>(`/api/save-games/${saveGameId}/staff/${staffId}/assign`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// Warranty APIs
export function listWarrantyClaims(saveGameId: number, status?: string) {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  return apiRequest<import("../types/game").WarrantyClaimDetail[]>(`/api/save-games/${saveGameId}/warranty/claims${query}`);
}

export function getWarrantyClaim(saveGameId: number, claimId: number) {
  return apiRequest<import("../types/game").WarrantyClaimDetail>(`/api/save-games/${saveGameId}/warranty/claims/${claimId}`);
}

export function getWarrantySummary(saveGameId: number) {
  return apiRequest<import("../types/game").WarrantyClaimSummary>(`/api/save-games/${saveGameId}/warranty/summary`);
}

export function generateWarrantyClaim(saveGameId: number, payload?: import("../types/game").WarrantyClaimGenerateRequest) {
  return apiRequest<import("../types/game").WarrantyClaimDetail>(
    `/api/save-games/${saveGameId}/warranty/claims/generate`,
    { method: "POST", body: JSON.stringify(payload ?? {}) }
  );
}

export function reviewWarrantyClaim(saveGameId: number, claimId: number, payload?: import("../types/game").WarrantyClaimReviewRequest) {
  return apiRequest<import("../types/game").WarrantyClaimDetail>(
    `/api/save-games/${saveGameId}/warranty/claims/${claimId}/review`,
    { method: "POST", body: JSON.stringify(payload ?? {}) }
  );
}

export function resolveWarrantyClaim(saveGameId: number, claimId: number, payload: import("../types/game").WarrantyClaimResolveRequest) {
  return apiRequest<import("../types/game").WarrantyClaimResolveResponse>(
    `/api/save-games/${saveGameId}/warranty/claims/${claimId}/resolve`,
    { method: "POST", body: JSON.stringify(payload) }
  );
}

export interface ReviewListParams {
  sourceType?: string;
  sentiment?: string;
}

export function listReviews(saveGameId: number, params: ReviewListParams = {}) {
  const query = new URLSearchParams();
  if (params.sourceType) query.set("source_type", params.sourceType);
  if (params.sentiment) query.set("sentiment", params.sentiment);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return apiRequest<import("../types/game").CustomerReview[]>(`/api/save-games/${saveGameId}/reviews${suffix}`);
}

export function getReview(saveGameId: number, reviewId: number) {
  return apiRequest<import("../types/game").CustomerReview>(`/api/save-games/${saveGameId}/reviews/${reviewId}`);
}

export function getReputationSummary(saveGameId: number) {
  return apiRequest<import("../types/game").ReputationSummary>(`/api/save-games/${saveGameId}/reputation/summary`);
}

export function generateReview(saveGameId: number, payload?: import("../types/game").ReviewGenerateRequest) {
  return apiRequest<import("../types/game").CustomerReview>(`/api/save-games/${saveGameId}/reviews/generate`, {
    method: "POST",
    body: JSON.stringify(payload ?? {}),
  });
}

export function generateOrderReview(saveGameId: number, orderId: number) {
  return apiRequest<import("../types/game").CustomerReview>(`/api/save-games/${saveGameId}/orders/${orderId}/generate-review`, {
    method: "POST",
  });
}

export function generateResaleReview(saveGameId: number, listingId: number) {
  return apiRequest<import("../types/game").CustomerReview>(`/api/save-games/${saveGameId}/resale/listings/${listingId}/generate-review`, {
    method: "POST",
  });
}

export function generateWarrantyReview(saveGameId: number, claimId: number) {
  return apiRequest<import("../types/game").CustomerReview>(`/api/save-games/${saveGameId}/warranty/claims/${claimId}/generate-review`, {
    method: "POST",
  });
}

// Progression / Shop Upgrade APIs
export function getProgressionState(saveGameId: number) {
  return apiRequest<import("../types/game").ProgressionState>(`/api/save-games/${saveGameId}/progression`);
}

export function listShopUpgrades(saveGameId: number) {
  return apiRequest<import("../types/game").ShopUpgradeDefinition[]>(`/api/save-games/${saveGameId}/progression/upgrades`);
}

export function purchaseShopUpgrade(saveGameId: number, upgradeKey: string) {
  return apiRequest<import("../types/game").ShopUpgradePurchaseResponse>(
    `/api/save-games/${saveGameId}/progression/upgrades/${encodeURIComponent(upgradeKey)}/purchase`,
    { method: "POST" }
  );
}

export function evaluateCompatibility(payload: import("../types/game").CompatibilityEvaluateRequest) {
  return apiRequest<import("../types/game").CompatibilityResult>("/api/compatibility/evaluate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getQuoteCompatibility(saveGameId: number, quoteId: number) {
  return apiRequest<import("../types/game").CompatibilityResult>(
    `/api/save-games/${saveGameId}/quotes/${quoteId}/compatibility`
  );
}

export function getOrderCompatibility(saveGameId: number, orderId: number) {
  return apiRequest<import("../types/game").CompatibilityResult>(
    `/api/save-games/${saveGameId}/orders/${orderId}/compatibility`
  );
}
