import { useMutation, useQuery, useQueryClient, type UseMutationResult, type UseQueryResult } from "@tanstack/react-query";

import {
  apiRequest,
  getBrand,
  getHardwareProduct,
  listBrands,
  listHardwareProducts,
  listSupportedCurrencies,
  listFxRates,
  refreshFxRates,
  convertCurrency,
  getFxAttribution,
  type BrandListParams,
  type HardwareProductListParams,
  listSupplierOffers,
  type SupplierOfferListParams,
  listProductPrices,
  type ProductPriceListParams,
  listMarketEvents,
  getActiveMarketEvents,
  generateMarketEvent,
  advanceMarketDay,
  getMarketSummary,
  createMarketEvent,
  listPlayerProfiles,
  createPlayerProfile,
  getPlayerProfile,
  unlockPlayerProfile,
  lockPlayerProfile,
  changePlayerProfilePin,
  disablePlayerProfilePin,
  assignSaveGameProfile,
  listCustomerPersonas,
  getCustomerPersona,
  assignCustomerPersona,
  evaluateRequestQuotes,
  listCustomerConversations,
  getCustomerConversation,
  listConversationMessages,
  createConversationForRequest,
  sendConversationMessage,
  quickReplyConversation,
  assignConversationStaff,
  sendQuoteToConversation,
  markConversationReadyToOrder,
  closeConversation,
  listUsedPartListings,
  generateUsedPartListing,
  generateBatchUsedPartListings,
  getUsedPartListing,
  startUsedPartNegotiation,
  submitNegotiationOffer,
  acceptUsedPartListing,
  rejectUsedPartListing,
  getRefurbishActions,
  runRefurbishAction,
  listRefurbishEvents,
  markReadyForResale,
  unmarkReadyForResale,
  listResaleListings,
  getResaleListing,
  createResaleListing,
  cancelResaleListing,
  generateResaleOffer,
  listResaleOffers,
  acceptResaleOffer,
  rejectResaleOffer,
  listStaff,
  getStaffMember,
  hireStaff,
  generateStaffCandidates,
  fireStaffMember,
  getStaffSummary,
  listStaffAssignments,
  assignStaff,
  listWarrantyClaims,
  getWarrantyClaim,
  getWarrantySummary,
  generateWarrantyClaim,
  reviewWarrantyClaim,
  resolveWarrantyClaim,
  listReviews,
  getReview,
  getReputationSummary,
  generateReview,
  generateOrderReview,
  generateResaleReview,
  generateWarrantyReview,
  getProgressionState,
  listShopUpgrades,
  purchaseShopUpgrade,
  evaluateCompatibility,
  getQuoteCompatibility,
  getOrderCompatibility,
} from "./client";
import type {
  Customer,
  CustomerRequest,
  DashboardState,
  HardwareProduct,
  InventoryUnit,
  Order,
  DeliverOrderResponse,
  OrderDetail,
  OrderFulfillmentEvent,
  PurchaseOrder,
  QuoteDetail,
  SaveGame,
  Supplier,
  SupplierOffer,
  WarrantyClaimDetail,
  WarrantyClaimSummary,
  WarrantyClaimReason,
  WarrantyEvent,
  WarrantyClaimGenerateRequest,
  WarrantyClaimReviewRequest,
  WarrantyClaimResolveRequest,
  WarrantyClaimResolveResponse,
  ProgressionState,
  ShopUpgradeDefinition,
  ShopUpgradePurchaseResponse,
  ProductPriceSnapshot,
  MarketEvent,
  MarketSummary,
  PlayerProfile,
  ProfileUnlockResponse,
  UsedPartListing,
  UsedPartNegotiation,
  ResaleListing,
  ResaleBuyerOffer,
  ResaleListingCreate,
  ResaleOfferGenerateResponse,
  ResaleSaleResponse,
  CustomerReview,
  ReputationSummary,
  ReviewGenerateRequest,
  StaffMember,
  StaffMemberCreate,
  StaffCandidate,
  StaffSummary,
  StaffAssignmentLog,
  StaffAssignRequest,
  StaffAssignResponse,
  StaffRole,
  StaffStatus,
  CompatibilityEvaluateRequest,
  MarketEventCreateRequest,
  CustomerPersonaDefinition,
  CustomerConversation,
  CustomerConversationMessage,
  CustomerConversationCreateResponse,
  QuotePersonaEvaluation,
  ConversationSendQuoteResponse,
} from "../types/game";

export function useSaveGames() {
  return useQuery({ queryKey: ["save-games"], queryFn: () => apiRequest<SaveGame[]>("/api/save-games") });
}

export function useCreateSaveGame() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => apiRequest<SaveGame>("/api/save-games", { method: "POST", body: JSON.stringify({ name }) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["save-games"] }),
  });
}

export function useDashboardState(saveId: number | null) {
  return useQuery({
    queryKey: ["save-state", saveId],
    queryFn: () => apiRequest<DashboardState>(`/api/save-games/${saveId}/state`),
    enabled: Boolean(saveId),
  });
}

export function useHardwareProducts(params: HardwareProductListParams = {}) {
  return useQuery({ queryKey: ["hardware", params], queryFn: () => listHardwareProducts(params) });
}

export function useHardwareProduct(productId: number | null) {
  return useQuery({
    queryKey: ["hardware", productId],
    queryFn: () => getHardwareProduct(productId as number),
    enabled: Boolean(productId),
  });
}

export function useBrands(params: BrandListParams = {}) {
  return useQuery({ queryKey: ["brands", params], queryFn: () => listBrands(params) });
}

export function useBrand(brandId: number | null) {
  return useQuery({
    queryKey: ["brands", brandId],
    queryFn: () => getBrand(brandId as number),
    enabled: Boolean(brandId),
  });
}

export function useInventory(saveId: number | null) {
  return useQuery({
    queryKey: ["inventory", saveId],
    queryFn: () => apiRequest<InventoryUnit[]>(`/api/save-games/${saveId}/inventory`),
    enabled: Boolean(saveId),
  });
}

export function useCreateInventoryUnit(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      apiRequest<InventoryUnit>(`/api/save-games/${saveId}/inventory`, { method: "POST", body: JSON.stringify(payload) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["inventory", saveId] }),
  });
}

export function useRunInventoryTest(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ unitId, action }: { unitId: number; action: string }) =>
      apiRequest(`/api/save-games/${saveId}/inventory/${unitId}/tests/${action}`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["inventory", saveId] });
      queryClient.invalidateQueries({ queryKey: ["save-state", saveId] });
    },
  });
}

export function useSuppliers() {
  return useQuery({ queryKey: ["suppliers"], queryFn: () => apiRequest<Supplier[]>("/api/suppliers") });
}

export function useSupplierOffers(params: SupplierOfferListParams = {}) {
  return useQuery({ queryKey: ["supplier-offers", params], queryFn: () => listSupplierOffers(params) });
}

export function usePurchaseOrders(saveId: number | null) {
  return useQuery({
    queryKey: ["purchase-orders", saveId],
    queryFn: () => apiRequest<PurchaseOrder[]>(`/api/save-games/${saveId}/purchase-orders`),
    enabled: Boolean(saveId),
  });
}

export function useCreatePurchaseOrder(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (offer: SupplierOffer) =>
      apiRequest<PurchaseOrder>(`/api/save-games/${saveId}/purchase-orders`, {
        method: "POST",
        body: JSON.stringify({
          supplier_id: offer.supplier_id,
          items: [
            {
              product_id: offer.product_id,
              quantity: offer.min_order_quantity,
              unit_price_vnd: offer.market_adjusted_unit_price_vnd ?? offer.effective_unit_price_vnd ?? offer.unit_price_vnd,
              warranty_months: offer.warranty_months,
            },
          ],
        }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["purchase-orders", saveId] });
      queryClient.invalidateQueries({ queryKey: ["save-state", saveId] });
      queryClient.invalidateQueries({ queryKey: ["supplier-offers"] });
    },
  });
}

export function useReceivePurchaseOrder(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (purchaseOrderId: number) =>
      apiRequest<PurchaseOrder>(`/api/save-games/${saveId}/purchase-orders/${purchaseOrderId}/receive`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["purchase-orders", saveId] });
      queryClient.invalidateQueries({ queryKey: ["inventory", saveId] });
      queryClient.invalidateQueries({ queryKey: ["save-state", saveId] });
    },
  });
}

export function useCustomers(saveId: number | null) {
  return useQuery({
    queryKey: ["customers", saveId],
    queryFn: () => apiRequest<Customer[]>(`/api/save-games/${saveId}/customers`),
    enabled: Boolean(saveId),
  });
}

export function useCustomerRequests(saveId: number | null) {
  return useQuery({
    queryKey: ["customer-requests", saveId],
    queryFn: () => apiRequest<CustomerRequest[]>(`/api/save-games/${saveId}/customer-requests`),
    enabled: Boolean(saveId),
  });
}

export function useGenerateCustomer(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => apiRequest(`/api/save-games/${saveId}/customers/generate-sample`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["customers", saveId] });
      queryClient.invalidateQueries({ queryKey: ["customer-requests", saveId] });
      queryClient.invalidateQueries({ queryKey: ["save-state", saveId] });
    },
  });
}

export function useCustomerPersonas() {
  return useQuery({
    queryKey: ["customer-personas"],
    queryFn: () => listCustomerPersonas(),
  }) as UseQueryResult<CustomerPersonaDefinition[]>;
}

export function useCustomerPersona(personaType: string | null) {
  return useQuery({
    queryKey: ["customer-personas", personaType],
    queryFn: () => getCustomerPersona(personaType as string),
    enabled: Boolean(personaType),
  }) as UseQueryResult<CustomerPersonaDefinition>;
}

export function useAssignCustomerPersona(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ customerId, personaType }: { customerId: number; personaType: string }) =>
      assignCustomerPersona(saveId as number, customerId, personaType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["customers", saveId] });
      queryClient.invalidateQueries({ queryKey: ["customer-requests", saveId] });
      queryClient.invalidateQueries({ queryKey: ["quotes", saveId] });
      queryClient.invalidateQueries({ queryKey: ["save-state", saveId] });
    },
  }) as UseMutationResult<import("../types/game").Customer, Error, { customerId: number; personaType: string }>;
}

export function useEvaluateRequestQuotes(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (requestId: number) => evaluateRequestQuotes(saveId as number, requestId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["quotes", saveId] });
      queryClient.invalidateQueries({ queryKey: ["customer-requests", saveId] });
    },
  }) as UseMutationResult<QuotePersonaEvaluation[], Error, number>;
}

export function useCustomerConversations(saveId: number | null, params: { status?: string } = {}) {
  return useQuery({
    queryKey: ["customer-conversations", saveId, params.status ?? null],
    queryFn: () => listCustomerConversations(saveId as number, params),
    enabled: Boolean(saveId),
  });
}

export function useCustomerConversation(saveId: number | null, conversationId: number | null) {
  return useQuery({
    queryKey: ["customer-conversations", saveId, conversationId],
    queryFn: () => getCustomerConversation(saveId as number, conversationId as number),
    enabled: Boolean(saveId && conversationId),
  });
}

export function useConversationMessages(saveId: number | null, conversationId: number | null) {
  return useQuery({
    queryKey: ["customer-conversation-messages", saveId, conversationId],
    queryFn: () => listConversationMessages(saveId as number, conversationId as number),
    enabled: Boolean(saveId && conversationId),
  });
}

function invalidateConversationWorkflow(queryClient: ReturnType<typeof useQueryClient>, saveId: number | null, conversationId?: number) {
  queryClient.invalidateQueries({ queryKey: ["customer-conversations", saveId] });
  if (conversationId) {
    queryClient.invalidateQueries({ queryKey: ["customer-conversations", saveId, conversationId] });
    queryClient.invalidateQueries({ queryKey: ["customer-conversation-messages", saveId, conversationId] });
  }
  queryClient.invalidateQueries({ queryKey: ["customer-requests", saveId] });
  queryClient.invalidateQueries({ queryKey: ["quotes", saveId] });
  queryClient.invalidateQueries({ queryKey: ["save-state", saveId] });
}

export function useCreateConversationForRequest(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (requestId: number) => createConversationForRequest(saveId as number, requestId),
    onSuccess: (data, requestId) => {
      invalidateConversationWorkflow(queryClient, saveId, data.conversation.id);
      queryClient.invalidateQueries({ queryKey: ["customer-requests", saveId, requestId] });
    },
  }) as UseMutationResult<CustomerConversationCreateResponse, Error, number>;
}

export function useSendConversationMessage(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ conversationId, body }: { conversationId: number; body: string }) =>
      sendConversationMessage(saveId as number, conversationId, body),
    onSuccess: (data) => {
      invalidateConversationWorkflow(queryClient, saveId, data.id);
    },
  }) as UseMutationResult<CustomerConversation, Error, { conversationId: number; body: string }>;
}

export function useQuickReplyConversation(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ conversationId, actionType }: { conversationId: number; actionType: string }) =>
      quickReplyConversation(saveId as number, conversationId, actionType),
    onSuccess: (data) => {
      invalidateConversationWorkflow(queryClient, saveId, data.id);
    },
  }) as UseMutationResult<CustomerConversation, Error, { conversationId: number; actionType: string }>;
}

export function useAssignConversationStaff(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ conversationId, staffId }: { conversationId: number; staffId: number }) =>
      assignConversationStaff(saveId as number, conversationId, staffId),
    onSuccess: (data) => {
      invalidateConversationWorkflow(queryClient, saveId, data.id);
    },
  }) as UseMutationResult<CustomerConversation, Error, { conversationId: number; staffId: number }>;
}

export function useSendQuoteToConversation(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ conversationId, quoteId }: { conversationId: number; quoteId: number }) =>
      sendQuoteToConversation(saveId as number, conversationId, quoteId),
    onSuccess: (data) => {
      invalidateConversationWorkflow(queryClient, saveId, data.conversation.id);
      queryClient.invalidateQueries({ queryKey: ["quotes", saveId] });
      queryClient.invalidateQueries({ queryKey: ["quotes", saveId, data.quote.id] });
    },
  }) as UseMutationResult<ConversationSendQuoteResponse, Error, { conversationId: number; quoteId: number }>;
}

export function useMarkConversationReadyToOrder(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (conversationId: number) => markConversationReadyToOrder(saveId as number, conversationId),
    onSuccess: (data) => {
      invalidateConversationWorkflow(queryClient, saveId, data.id);
    },
  }) as UseMutationResult<CustomerConversation, Error, number>;
}

export function useCloseConversation(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ conversationId, won }: { conversationId: number; won: boolean }) =>
      closeConversation(saveId as number, conversationId, won),
    onSuccess: (data) => {
      invalidateConversationWorkflow(queryClient, saveId, data.id);
    },
  }) as UseMutationResult<CustomerConversation, Error, { conversationId: number; won: boolean }>;
}

export function useOrders(saveId: number | null) {
  return useQuery({
    queryKey: ["orders", saveId],
    queryFn: () => apiRequest<Order[]>(`/api/save-games/${saveId}/orders`),
    enabled: Boolean(saveId),
  });
}

export function useOrderDetail(saveId: number | null, orderId: number | null) {
  return useQuery({
    queryKey: ["orders", saveId, orderId],
    queryFn: () => apiRequest<OrderDetail>(`/api/save-games/${saveId}/orders/${orderId}`),
    enabled: Boolean(saveId && orderId),
  });
}

export function useOrderCompatibility(saveId: number | null, orderId: number | null) {
  return useQuery({
    queryKey: ["orders", saveId, orderId, "compatibility"],
    queryFn: () => getOrderCompatibility(saveId as number, orderId as number),
    enabled: Boolean(saveId && orderId),
  });
}

export function useEvaluateCompatibility() {
  return useMutation({
    mutationFn: (payload: CompatibilityEvaluateRequest) => evaluateCompatibility(payload),
  });
}

export function useOrderFulfillmentEvents(saveId: number | null, orderId: number | null) {
  return useQuery({
    queryKey: ["order-fulfillment-events", saveId, orderId],
    queryFn: () => apiRequest<OrderFulfillmentEvent[]>(`/api/save-games/${saveId}/orders/${orderId}/fulfillment-events`),
    enabled: Boolean(saveId && orderId),
  });
}

function invalidateOrderWorkflow(queryClient: ReturnType<typeof useQueryClient>, saveId: number | null, orderId?: number) {
  queryClient.invalidateQueries({ queryKey: ["orders", saveId] });
  if (orderId) {
    queryClient.invalidateQueries({ queryKey: ["orders", saveId, orderId] });
    queryClient.invalidateQueries({ queryKey: ["order-fulfillment-events", saveId, orderId] });
  }
  queryClient.invalidateQueries({ queryKey: ["inventory", saveId] });
  queryClient.invalidateQueries({ queryKey: ["customer-requests", saveId] });
  queryClient.invalidateQueries({ queryKey: ["save-state", saveId] });
}

export function useStartOrderBuild(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (orderId: number) => apiRequest<OrderDetail>(`/api/save-games/${saveId}/orders/${orderId}/start-build`, { method: "POST" }),
    onSuccess: (_, orderId) => invalidateOrderWorkflow(queryClient, saveId, orderId),
  });
}

export function useRunOrderBuildTest(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (orderId: number) => apiRequest<OrderDetail>(`/api/save-games/${saveId}/orders/${orderId}/run-build-test`, { method: "POST" }),
    onSuccess: (_, orderId) => invalidateOrderWorkflow(queryClient, saveId, orderId),
  });
}

export function useDeliverOrder(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ orderId, force = false }: { orderId: number; force?: boolean }) =>
      apiRequest<DeliverOrderResponse>(`/api/save-games/${saveId}/orders/${orderId}/deliver`, {
        method: "POST",
        body: JSON.stringify({ force }),
      }),
    onSuccess: (_, variables) => invalidateOrderWorkflow(queryClient, saveId, variables.orderId),
  });
}

export function useQuotes(saveId: number | null) {
  return useQuery({
    queryKey: ["quotes", saveId],
    queryFn: () => apiRequest<QuoteDetail[]>(`/api/save-games/${saveId}/quotes`),
    enabled: Boolean(saveId),
  });
}

export function useQuote(saveId: number | null, quoteId: number | null) {
  return useQuery({
    queryKey: ["quotes", saveId, quoteId],
    queryFn: () => apiRequest<QuoteDetail>(`/api/save-games/${saveId}/quotes/${quoteId}`),
    enabled: Boolean(saveId && quoteId),
  });
}

export function useQuoteCompatibility(saveId: number | null, quoteId: number | null) {
  return useQuery({
    queryKey: ["quotes", saveId, quoteId, "compatibility"],
    queryFn: () => getQuoteCompatibility(saveId as number, quoteId as number),
    enabled: Boolean(saveId && quoteId),
  });
}

export function useGenerateQuote(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (requestId: number) =>
      apiRequest<QuoteDetail>(`/api/save-games/${saveId}/customer-requests/${requestId}/generate-quote`, {
        method: "POST",
        body: JSON.stringify({}),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["quotes", saveId] });
      queryClient.invalidateQueries({ queryKey: ["customer-requests", saveId] });
      queryClient.invalidateQueries({ queryKey: ["save-state", saveId] });
    },
  });
}

export function useReserveQuote(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (quoteId: number) => apiRequest<QuoteDetail>(`/api/save-games/${saveId}/quotes/${quoteId}/reserve`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["quotes", saveId] });
      queryClient.invalidateQueries({ queryKey: ["inventory", saveId] });
      queryClient.invalidateQueries({ queryKey: ["save-state", saveId] });
    },
  });
}

export function useReleaseQuote(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (quoteId: number) => apiRequest<QuoteDetail>(`/api/save-games/${saveId}/quotes/${quoteId}/release`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["quotes", saveId] });
      queryClient.invalidateQueries({ queryKey: ["inventory", saveId] });
      queryClient.invalidateQueries({ queryKey: ["save-state", saveId] });
    },
  });
}

export function useAcceptQuote(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (quoteId: number) =>
      apiRequest<Order>(`/api/save-games/${saveId}/quotes/${quoteId}/accept`, { method: "POST", body: JSON.stringify({}) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["quotes", saveId] });
      queryClient.invalidateQueries({ queryKey: ["orders", saveId] });
      queryClient.invalidateQueries({ queryKey: ["inventory", saveId] });
      queryClient.invalidateQueries({ queryKey: ["customer-requests", saveId] });
      queryClient.invalidateQueries({ queryKey: ["save-state", saveId] });
    },
  });
}

function invalidateWarrantyWorkflow(queryClient: ReturnType<typeof useQueryClient>, saveId: number | null, claimId?: number) {
  queryClient.invalidateQueries({ queryKey: ["warranty-claims", saveId] });
  queryClient.invalidateQueries({ queryKey: ["warranty-summary", saveId] });
  if (claimId) {
    queryClient.invalidateQueries({ queryKey: ["warranty-claims", saveId, claimId] });
    queryClient.invalidateQueries({ queryKey: ["warranty-events", saveId, claimId] });
  }
  queryClient.invalidateQueries({ queryKey: ["orders", saveId] });
  queryClient.invalidateQueries({ queryKey: ["inventory", saveId] });
  queryClient.invalidateQueries({ queryKey: ["save-state", saveId] });
}

export function useWarrantyClaims(saveId: number | null) {
  return useQuery({
    queryKey: ["warranty-claims", saveId],
    queryFn: () => listWarrantyClaims(saveId as number),
    enabled: Boolean(saveId),
  });
}

export function useWarrantyClaim(saveId: number | null, claimId: number | null) {
  return useQuery({
    queryKey: ["warranty-claims", saveId, claimId],
    queryFn: () => getWarrantyClaim(saveId as number, claimId as number),
    enabled: Boolean(saveId && claimId),
  });
}

export function useWarrantySummary(saveId: number | null) {
  return useQuery({
    queryKey: ["warranty-summary", saveId],
    queryFn: () => getWarrantySummary(saveId as number),
    enabled: Boolean(saveId),
  });
}

export function useWarrantyEvents(saveId: number | null, claimId: number | null) {
  return useQuery({
    queryKey: ["warranty-events", saveId, claimId],
    queryFn: () => apiRequest<WarrantyEvent[]>(`/api/save-games/${saveId}/warranty-claims/${claimId}/events`),
    enabled: Boolean(saveId && claimId),
  });
}

export function useGenerateWarrantyClaim(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload?: WarrantyClaimGenerateRequest) => generateWarrantyClaim(saveId as number, payload),
    onSuccess: (detail) => invalidateWarrantyWorkflow(queryClient, saveId, detail.claim.id),
  });
}

export function useReviewWarrantyClaim(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ claimId, payload }: { claimId: number; payload?: WarrantyClaimReviewRequest }) =>
      reviewWarrantyClaim(saveId as number, claimId, payload),
    onSuccess: (_, variables) => invalidateWarrantyWorkflow(queryClient, saveId, variables.claimId),
  });
}

export function useResolveWarrantyClaim(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ claimId, payload }: { claimId: number; payload: WarrantyClaimResolveRequest }) =>
      resolveWarrantyClaim(saveId as number, claimId, payload),
    onSuccess: (_, variables) => invalidateWarrantyWorkflow(queryClient, saveId, variables.claimId),
  });
}

export function useOpenWarrantyClaim(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      orderId,
      claim_reason,
      complaint_summary,
    }: {
      orderId: number;
      claim_reason: WarrantyClaimReason;
      complaint_summary: string;
    }) =>
      apiRequest<WarrantyClaimDetail>(`/api/save-games/${saveId}/orders/${orderId}/warranty-claims`, {
        method: "POST",
        body: JSON.stringify({ claim_reason, complaint_summary }),
      }),
    onSuccess: (detail) => invalidateWarrantyWorkflow(queryClient, saveId, detail.claim.id),
  });
}

export function useStartWarrantyDiagnosis(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (claimId: number) =>
      apiRequest<WarrantyClaimDetail>(`/api/save-games/${saveId}/warranty-claims/${claimId}/start-diagnosis`, { method: "POST" }),
    onSuccess: (_, claimId) => invalidateWarrantyWorkflow(queryClient, saveId, claimId),
  });
}

export function useCompleteWarrantyDiagnosis(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (claimId: number) =>
      apiRequest<WarrantyClaimDetail>(`/api/save-games/${saveId}/warranty-claims/${claimId}/complete-diagnosis`, {
        method: "POST",
        body: JSON.stringify({}),
      }),
    onSuccess: (_, claimId) => invalidateWarrantyWorkflow(queryClient, saveId, claimId),
  });
}

export function useApproveWarrantyClaim(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (claimId: number) =>
      apiRequest<WarrantyClaimDetail>(`/api/save-games/${saveId}/warranty-claims/${claimId}/approve`, { method: "POST" }),
    onSuccess: (_, claimId) => invalidateWarrantyWorkflow(queryClient, saveId, claimId),
  });
}

export function useRejectWarrantyClaim(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ claimId, reason }: { claimId: number; reason?: string }) =>
      apiRequest<WarrantyClaimDetail>(`/api/save-games/${saveId}/warranty-claims/${claimId}/reject`, {
        method: "POST",
        body: JSON.stringify({ reason }),
      }),
    onSuccess: (_, variables) => invalidateWarrantyWorkflow(queryClient, saveId, variables.claimId),
  });
}

function useResolveWarranty(saveId: number | null, action: "repair" | "replace" | "refund" | "rma") {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (claimId: number) =>
      apiRequest<WarrantyClaimDetail>(`/api/save-games/${saveId}/warranty-claims/${claimId}/resolve/${action}`, {
        method: "POST",
        body: JSON.stringify({}),
      }),
    onSuccess: (_, claimId) => invalidateWarrantyWorkflow(queryClient, saveId, claimId),
  });
}

export function useResolveWarrantyRepair(saveId: number | null) {
  return useResolveWarranty(saveId, "repair");
}

export function useResolveWarrantyReplace(saveId: number | null) {
  return useResolveWarranty(saveId, "replace");
}

export function useResolveWarrantyRefund(saveId: number | null) {
  return useResolveWarranty(saveId, "refund");
}

export function useResolveWarrantyRma(saveId: number | null) {
  return useResolveWarranty(saveId, "rma");
}

export function useCloseWarrantyClaim(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (claimId: number) =>
      apiRequest<WarrantyClaimDetail>(`/api/save-games/${saveId}/warranty-claims/${claimId}/close`, { method: "POST" }),
    onSuccess: (_, claimId) => invalidateWarrantyWorkflow(queryClient, saveId, claimId),
  });
}

function invalidateReviewWorkflow(
  queryClient: ReturnType<typeof useQueryClient>,
  saveId: number | null,
  opts?: { orderId?: number; listingId?: number; claimId?: number },
) {
  queryClient.invalidateQueries({ queryKey: ["reviews", saveId] });
  queryClient.invalidateQueries({ queryKey: ["reputation-summary", saveId] });
  queryClient.invalidateQueries({ queryKey: ["save-state", saveId] });
  if (opts?.orderId) {
    queryClient.invalidateQueries({ queryKey: ["orders", saveId, opts.orderId] });
    queryClient.invalidateQueries({ queryKey: ["order-detail", saveId, opts.orderId] });
  }
  if (opts?.listingId) {
    queryClient.invalidateQueries({ queryKey: ["resale-listings", saveId] });
    queryClient.invalidateQueries({ queryKey: ["resale-listings", saveId, opts.listingId] });
  }
  if (opts?.claimId) {
    queryClient.invalidateQueries({ queryKey: ["warranty-claims", saveId] });
    queryClient.invalidateQueries({ queryKey: ["warranty-claims", saveId, opts.claimId] });
  }
}

export function useReviews(saveId: number | null, params: { sourceType?: string; sentiment?: string } = {}) {
  return useQuery({
    queryKey: ["reviews", saveId, params],
    queryFn: () => listReviews(saveId as number, params),
    enabled: Boolean(saveId),
  });
}

export function useReview(saveId: number | null, reviewId: number | null) {
  return useQuery({
    queryKey: ["reviews", saveId, reviewId],
    queryFn: () => getReview(saveId as number, reviewId as number),
    enabled: Boolean(saveId && reviewId),
  });
}

export function useReputationSummary(saveId: number | null) {
  return useQuery({
    queryKey: ["reputation-summary", saveId],
    queryFn: () => getReputationSummary(saveId as number),
    enabled: Boolean(saveId),
  });
}

export function useGenerateReview(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload?: ReviewGenerateRequest) => generateReview(saveId as number, payload),
    onSuccess: () => invalidateReviewWorkflow(queryClient, saveId),
  });
}

export function useGenerateOrderReview(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (orderId: number) => generateOrderReview(saveId as number, orderId),
    onSuccess: (_, orderId) => invalidateReviewWorkflow(queryClient, saveId, { orderId }),
  });
}

export function useGenerateResaleReview(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (listingId: number) => generateResaleReview(saveId as number, listingId),
    onSuccess: (_, listingId) => invalidateReviewWorkflow(queryClient, saveId, { listingId }),
  });
}

export function useGenerateWarrantyReview(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (claimId: number) => generateWarrantyReview(saveId as number, claimId),
    onSuccess: (_, claimId) => invalidateReviewWorkflow(queryClient, saveId, { claimId }),
  });
}

function invalidateProgressionState(queryClient: ReturnType<typeof useQueryClient>, saveId: number | null) {
  queryClient.invalidateQueries({ queryKey: ["progression", saveId] });
  queryClient.invalidateQueries({ queryKey: ["progression-upgrades", saveId] });
  queryClient.invalidateQueries({ queryKey: ["save-state", saveId] });
  queryClient.invalidateQueries({ queryKey: ["save-games"] });
}

export function useProgression(saveId: number | null) {
  return useQuery({
    queryKey: ["progression", saveId],
    queryFn: () => getProgressionState(saveId as number),
    enabled: Boolean(saveId),
  }) as UseQueryResult<ProgressionState>;
}

export function useShopUpgrades(saveId: number | null) {
  return useQuery({
    queryKey: ["progression-upgrades", saveId],
    queryFn: () => listShopUpgrades(saveId as number),
    enabled: Boolean(saveId),
  }) as UseQueryResult<ShopUpgradeDefinition[]>;
}

export function usePurchaseShopUpgrade(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (upgradeKey: string) => purchaseShopUpgrade(saveId as number, upgradeKey),
    onSuccess: (_payload: ShopUpgradePurchaseResponse) => {
      invalidateProgressionState(queryClient, saveId);
      queryClient.invalidateQueries({ queryKey: ["inventory", saveId] });
      queryClient.invalidateQueries({ queryKey: ["orders", saveId] });
      queryClient.invalidateQueries({ queryKey: ["quotes", saveId] });
      queryClient.invalidateQueries({ queryKey: ["warranty-claims", saveId] });
      queryClient.invalidateQueries({ queryKey: ["resale-listings", saveId] });
      queryClient.invalidateQueries({ queryKey: ["resale-offers", saveId] });
    },
  }) as UseMutationResult<ShopUpgradePurchaseResponse, Error, string>;
}

export function useSupportedCurrencies() {
  return useQuery({
    queryKey: ["fx-supported-currencies"],
    queryFn: () => listSupportedCurrencies(),
  });
}

export function useFxRates(base?: string, quote?: string) {
  return useQuery({
    queryKey: ["fx-rates", base, quote],
    queryFn: () => listFxRates(base, quote),
  });
}

export function useRefreshFxRates() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (force: boolean = false) => refreshFxRates(force),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fx-rates"] });
    },
  });
}

export function useConvertCurrency(amount: number, fromCurrency: string, toCurrency: string = "VND", spreadPercent: number = 0, enabled: boolean = true) {
  return useQuery({
    queryKey: ["fx-convert", amount, fromCurrency, toCurrency, spreadPercent],
    queryFn: () => convertCurrency(amount, fromCurrency, toCurrency, spreadPercent),
    enabled: enabled && Boolean(amount && fromCurrency),
  });
}

export function useFxAttribution() {
  return useQuery({
    queryKey: ["fx-attribution"],
    queryFn: () => getFxAttribution(),
  });
}

export function useProductPrices(params: ProductPriceListParams = {}) {
  return useQuery({
    queryKey: ["product-prices", params],
    queryFn: () => listProductPrices(params),
  });
}

export function useMarketEvents(saveId: number | null, activeOnly?: boolean) {
  return useQuery({
    queryKey: ["market-events", saveId, activeOnly],
    queryFn: () => listMarketEvents(saveId as number, activeOnly),
    enabled: Boolean(saveId),
  });
}

export function useActiveMarketEvents(saveId: number | null) {
  return useQuery({
    queryKey: ["active-market-events", saveId],
    queryFn: () => getActiveMarketEvents(saveId as number),
    enabled: Boolean(saveId),
  });
}

export function useGenerateMarketEvent(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (mode: string = "rule") => generateMarketEvent(saveId as number, mode),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["market-events", saveId] });
      queryClient.invalidateQueries({ queryKey: ["active-market-events", saveId] });
      queryClient.invalidateQueries({ queryKey: ["market-summary", saveId] });
      queryClient.invalidateQueries({ queryKey: ["save-state", saveId] });
      queryClient.invalidateQueries({ queryKey: ["hardware"] });
      queryClient.invalidateQueries({ queryKey: ["supplier-offers"] });
    },
  });
}

export function useAdvanceMarketDay(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => advanceMarketDay(saveId as number),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["market-events", saveId] });
      queryClient.invalidateQueries({ queryKey: ["active-market-events", saveId] });
      queryClient.invalidateQueries({ queryKey: ["market-summary", saveId] });
      queryClient.invalidateQueries({ queryKey: ["save-state", saveId] });
      queryClient.invalidateQueries({ queryKey: ["hardware"] });
      queryClient.invalidateQueries({ queryKey: ["supplier-offers"] });
    },
  });
}

export function useMarketSummary(saveId: number | null) {
  return useQuery({
    queryKey: ["market-summary", saveId],
    queryFn: () => getMarketSummary(saveId as number),
    enabled: Boolean(saveId),
  });
}

export function useCreateMarketEvent(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: MarketEventCreateRequest) => createMarketEvent(saveId as number, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["market-events", saveId] });
      queryClient.invalidateQueries({ queryKey: ["active-market-events", saveId] });
      queryClient.invalidateQueries({ queryKey: ["market-summary", saveId] });
      queryClient.invalidateQueries({ queryKey: ["save-state", saveId] });
      queryClient.invalidateQueries({ queryKey: ["hardware"] });
      queryClient.invalidateQueries({ queryKey: ["supplier-offers"] });
    },
  });
}

// Player Profiles hooks
export function usePlayerProfiles() {
  return useQuery({
    queryKey: ["player-profiles"],
    queryFn: () => listPlayerProfiles()
  });
}

export function useCreatePlayerProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ displayName, pin }: { displayName: string; pin?: string }) =>
      createPlayerProfile(displayName, pin),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["player-profiles"] });
    }
  });
}

export function useUnlockPlayerProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ profileId, pin }: { profileId: number; pin: string }) =>
      unlockPlayerProfile(profileId, pin),
    onSuccess: (data) => {
      localStorage.setItem("profile_unlock_token", data.token);
      queryClient.invalidateQueries({ queryKey: ["save-games"] });
    }
  });
}

export function useLockPlayerProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (profileId: number) => lockPlayerProfile(profileId),
    onSuccess: () => {
      localStorage.removeItem("profile_unlock_token");
      queryClient.invalidateQueries({ queryKey: ["save-games"] });
    }
  });
}

export function useChangePlayerProfilePin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ profileId, pin, currentPin }: { profileId: number; pin: string; currentPin?: string }) =>
      changePlayerProfilePin(profileId, pin, currentPin),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["player-profiles"] });
    }
  });
}

export function useDisablePlayerProfilePin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ profileId, currentPin }: { profileId: number; currentPin?: string }) =>
      disablePlayerProfilePin(profileId, currentPin),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["player-profiles"] });
    }
  });
}

export function useAssignSaveGameProfile(saveGameId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (profileId: number) => assignSaveGameProfile(saveGameId as number, profileId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["save-games"] });
      queryClient.invalidateQueries({ queryKey: ["save-state", saveGameId] });
    }
  });
}

// Used Market hooks
export function useUsedPartListings(saveId: number | null, activeOnly: boolean = true) {
  return useQuery({
    queryKey: ["used-listings", saveId, activeOnly],
    queryFn: () => listUsedPartListings(saveId as number, activeOnly),
    enabled: Boolean(saveId)
  });
}

export function useGenerateUsedPartListing(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => generateUsedPartListing(saveId as number),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["used-listings", saveId] });
      queryClient.invalidateQueries({ queryKey: ["save-state", saveId] });
    }
  });
}

export function useGenerateBatchUsedPartListings(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (count: number = 5) => generateBatchUsedPartListings(saveId as number, count),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["used-listings", saveId] });
      queryClient.invalidateQueries({ queryKey: ["save-state", saveId] });
    }
  });
}

export function useStartUsedPartNegotiation(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (listingId: number) => startUsedPartNegotiation(saveId as number, listingId),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["used-listings", saveId] });
      queryClient.invalidateQueries({ queryKey: ["negotiation", saveId, data.id] });
      queryClient.invalidateQueries({ queryKey: ["save-state", saveId] });
    }
  });
}

export function useUsedPartNegotiation(saveId: number | null, negotiationId: number | null) {
  return useQuery({
    queryKey: ["negotiation", saveId, negotiationId],
    queryFn: () => apiRequest<UsedPartNegotiation>(`/api/save-games/${saveId}/used-market/negotiations/${negotiationId}`),
    enabled: Boolean(saveId && negotiationId)
  });
}

export function useSubmitNegotiationOffer(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ negotiationId, offerVnd, message }: { negotiationId: number; offerVnd: number; message?: string }) =>
      submitNegotiationOffer(saveId as number, negotiationId, offerVnd, message),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["negotiation", saveId, data.id] });
      queryClient.invalidateQueries({ queryKey: ["used-listings", saveId] });
      queryClient.invalidateQueries({ queryKey: ["save-state", saveId] });
    }
  });
}

export function useAcceptUsedPartListing(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ listingId, finalPriceVnd }: { listingId: number; finalPriceVnd?: number }) =>
      acceptUsedPartListing(saveId as number, listingId, finalPriceVnd),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["used-listings", saveId] });
      queryClient.invalidateQueries({ queryKey: ["inventory", saveId] });
      queryClient.invalidateQueries({ queryKey: ["save-state", saveId] });
    }
  });
}

export function useRejectUsedPartListing(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (listingId: number) => rejectUsedPartListing(saveId as number, listingId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["used-listings", saveId] });
      queryClient.invalidateQueries({ queryKey: ["save-state", saveId] });
    }
  });
}

// Refurbish hooks
export function useRefurbishActions(saveId: number | null, inventoryUnitId: number | null) {
  return useQuery({
    queryKey: ["refurbish-actions", saveId, inventoryUnitId],
    queryFn: () => getRefurbishActions(saveId as number, inventoryUnitId as number),
    enabled: Boolean(saveId && inventoryUnitId),
  });
}

export function useRunRefurbishAction(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ inventoryUnitId, actionType, staffId }: { inventoryUnitId: number; actionType: string; staffId?: number }) =>
      runRefurbishAction(saveId as number, inventoryUnitId, actionType, staffId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["refurbish-actions", saveId, variables.inventoryUnitId] });
      queryClient.invalidateQueries({ queryKey: ["refurbish-events", saveId] });
      queryClient.invalidateQueries({ queryKey: ["inventory", saveId] });
      queryClient.invalidateQueries({ queryKey: ["save-state", saveId] });
    },
  });
}

export function useRefurbishEvents(saveId: number | null, inventoryUnitId?: number) {
  return useQuery({
    queryKey: ["refurbish-events", saveId, inventoryUnitId],
    queryFn: () => listRefurbishEvents(saveId as number, inventoryUnitId),
    enabled: Boolean(saveId),
  });
}

export function useMarkReadyForResale(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (inventoryUnitId: number) => markReadyForResale(saveId as number, inventoryUnitId),
    onSuccess: (_, inventoryUnitId) => {
      queryClient.invalidateQueries({ queryKey: ["refurbish-actions", saveId, inventoryUnitId] });
      queryClient.invalidateQueries({ queryKey: ["inventory", saveId] });
      queryClient.invalidateQueries({ queryKey: ["save-state", saveId] });
    },
  });
}

export function useUnmarkReadyForResale(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (inventoryUnitId: number) => unmarkReadyForResale(saveId as number, inventoryUnitId),
    onSuccess: (_, inventoryUnitId) => {
      queryClient.invalidateQueries({ queryKey: ["refurbish-actions", saveId, inventoryUnitId] });
      queryClient.invalidateQueries({ queryKey: ["inventory", saveId] });
      queryClient.invalidateQueries({ queryKey: ["save-state", saveId] });
    },
  });
}

// Resale hooks
export function useResaleListings(saveId: number | null, status?: string) {
  return useQuery({
    queryKey: ["resale-listings", saveId, status],
    queryFn: () => listResaleListings(saveId as number, status),
    enabled: Boolean(saveId),
  });
}

export function useResaleListing(saveId: number | null, listingId: number | null) {
  return useQuery({
    queryKey: ["resale-listing", saveId, listingId],
    queryFn: () => getResaleListing(saveId as number, listingId as number),
    enabled: Boolean(saveId) && Boolean(listingId),
  });
}

export function useCreateResaleListing(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ResaleListingCreate) => createResaleListing(saveId as number, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["resale-listings", saveId] });
      queryClient.invalidateQueries({ queryKey: ["inventory", saveId] });
      queryClient.invalidateQueries({ queryKey: ["save-state", saveId] });
    },
  });
}

export function useCancelResaleListing(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (listingId: number) => cancelResaleListing(saveId as number, listingId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["resale-listings", saveId] });
      queryClient.invalidateQueries({ queryKey: ["inventory", saveId] });
      queryClient.invalidateQueries({ queryKey: ["save-state", saveId] });
    },
  });
}

export function useGenerateResaleOffer(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ listingId, staffId }: { listingId: number; staffId?: number }) =>
      generateResaleOffer(saveId as number, listingId, staffId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["resale-listings", saveId] });
      queryClient.invalidateQueries({ queryKey: ["resale-listing", saveId, variables.listingId] });
      queryClient.invalidateQueries({ queryKey: ["resale-offers", saveId] });
    },
  });
}

export function useResaleOffers(saveId: number | null, listingId?: number) {
  return useQuery({
    queryKey: ["resale-offers", saveId, listingId],
    queryFn: () => listResaleOffers(saveId as number, listingId),
    enabled: Boolean(saveId),
  });
}

export function useAcceptResaleOffer(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (offerId: number) => acceptResaleOffer(saveId as number, offerId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["resale-listings", saveId] });
      queryClient.invalidateQueries({ queryKey: ["resale-offers", saveId] });
      queryClient.invalidateQueries({ queryKey: ["inventory", saveId] });
      queryClient.invalidateQueries({ queryKey: ["save-state", saveId] });
    },
  });
}

export function useRejectResaleOffer(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (offerId: number) => rejectResaleOffer(saveId as number, offerId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["resale-listings", saveId] });
      queryClient.invalidateQueries({ queryKey: ["resale-offers", saveId] });
    },
  });
}

// Staff hooks
export function useStaff(saveId: number | null, role?: StaffRole, status?: StaffStatus) {
  return useQuery({
    queryKey: ["staff", saveId, role, status],
    queryFn: () => listStaff(saveId as number, role, status),
    enabled: Boolean(saveId),
  });
}

export function useStaffSummary(saveId: number | null) {
  return useQuery({
    queryKey: ["staff-summary", saveId],
    queryFn: () => getStaffSummary(saveId as number),
    enabled: Boolean(saveId),
  });
}

export function useStaffAssignments(saveId: number | null, limit: number = 20) {
  return useQuery({
    queryKey: ["staff-assignments", saveId, limit],
    queryFn: () => listStaffAssignments(saveId as number, limit),
    enabled: Boolean(saveId),
  });
}

export function useGenerateStaffCandidates(saveId: number | null) {
  return useMutation({
    mutationFn: ({ role, count }: { role?: StaffRole; count?: number }) =>
      generateStaffCandidates(saveId as number, role, count ?? 3),
  }) as UseMutationResult<StaffCandidate[], Error, { role?: StaffRole; count?: number }>;
}

export function useHireStaff(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: StaffMemberCreate) => hireStaff(saveId as number, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["staff", saveId] });
      queryClient.invalidateQueries({ queryKey: ["staff-summary", saveId] });
      queryClient.invalidateQueries({ queryKey: ["staff-assignments", saveId] });
      queryClient.invalidateQueries({ queryKey: ["save-state", saveId] });
    },
  }) as UseMutationResult<StaffMember, Error, StaffMemberCreate>;
}

export function useFireStaff(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (staffId: number) => fireStaffMember(saveId as number, staffId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["staff", saveId] });
      queryClient.invalidateQueries({ queryKey: ["staff-summary", saveId] });
      queryClient.invalidateQueries({ queryKey: ["staff-assignments", saveId] });
      queryClient.invalidateQueries({ queryKey: ["save-state", saveId] });
    },
  }) as UseMutationResult<StaffMember, Error, number>;
}

export function useAssignStaff(saveId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ staffId, payload }: { staffId: number; payload: StaffAssignRequest }) =>
      assignStaff(saveId as number, staffId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["staff", saveId] });
      queryClient.invalidateQueries({ queryKey: ["staff-summary", saveId] });
      queryClient.invalidateQueries({ queryKey: ["staff-assignments", saveId] });
      queryClient.invalidateQueries({ queryKey: ["save-state", saveId] });
    },
  }) as UseMutationResult<StaffAssignResponse, Error, { staffId: number; payload: StaffAssignRequest }>;
}
