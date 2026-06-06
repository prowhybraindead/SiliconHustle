import { useState, useMemo } from "react";
import { MessageSquare, Sparkles, Send, CheckCircle, XCircle, ShoppingBag, Info, Heart, Calendar } from "lucide-react";

import {
  useUsedPartListings,
  useGenerateUsedPartListing,
  useGenerateBatchUsedPartListings,
  useStartUsedPartNegotiation,
  useUsedPartNegotiation,
  useSubmitNegotiationOffer,
  useAcceptUsedPartListing,
  useRejectUsedPartListing,
  useDashboardState,
} from "../api/hooks";
import { useGameStore } from "../store/gameStore";
import { EmptyState } from "../components/EmptyState";
import { LoadingState } from "../components/LoadingState";
import { formatVnd, labelize } from "../utils/format";
import type { UsedPartListing } from "../types/game";
import { getErrorMessage } from "../utils/error";

import { ConsolePanel } from "../components/ui/ConsolePanel";
import { StatusChip } from "../components/ui/StatusChip";
import { ActionButton } from "../components/ui/ActionButton";
import { SectionHeader } from "../components/ui/SectionHeader";

export function UsedMarketPage() {
  const saveId = useGameStore((state) => state.selectedSaveId);
  const dashboard = useDashboardState(saveId);
  const listings = useUsedPartListings(saveId, true);
  
  const generateOne = useGenerateUsedPartListing(saveId);
  const generateBatch = useGenerateBatchUsedPartListings(saveId);
  
  const startNegotiation = useStartUsedPartNegotiation(saveId);
  const acceptListing = useAcceptUsedPartListing(saveId);
  const rejectListing = useRejectUsedPartListing(saveId);

  const [activeNegotiationId, setActiveNegotiationId] = useState<number | null>(null);
  const [offerVnd, setOfferVnd] = useState("");
  const [customMsg, setCustomMsg] = useState("");

  const activeNeg = useUsedPartNegotiation(saveId, activeNegotiationId);
  const submitOffer = useSubmitNegotiationOffer(saveId);

  const stats = useMemo(() => {
    if (!listings.data) return { available: 0, negotiating: 0, accepted: 0, expired: 0 };
    const available = listings.data.filter(l => l.status === "AVAILABLE").length;
    const negotiating = listings.data.filter(l => l.status === "NEGOTIATING").length;
    const accepted = listings.data.filter(l => l.status === "ACCEPTED").length;
    const expired = listings.data.filter(l => l.status === "EXPIRED").length;
    return { available, negotiating, accepted, expired };
  }, [listings.data]);

  if (!saveId) return <EmptyState title="No Save Selected" body="Please select or create a showroom save game first." />;
  if (listings.isLoading) return <LoadingState />;

  const cash = dashboard.data?.cash ?? 0;
  const gameDay = dashboard.data?.game_day ?? 1;

  // Active listing derived from local listings list
  const activeListing = listings.data?.find((l) => l.id === activeNeg.data?.listing_id);

  async function handleStartNegotiate(listingId: number) {
    try {
      const neg = await startNegotiation.mutateAsync(listingId);
      setActiveNegotiationId(neg.id);
      setOfferVnd("");
      setCustomMsg("");
    } catch (err: unknown) {
      alert(getErrorMessage(err, "Failed to start negotiation."));
    }
  }

  async function handleBuyNow(listing: UsedPartListing) {
    if (cash < listing.asking_price_vnd) {
      alert("Không đủ tiền mặt để thanh toán.");
      return;
    }
    const confirmBuy = window.confirm(`Bạn có chắc chắn muốn mua ${listing.product.name} ngay với giá ${formatVnd(listing.asking_price_vnd)}?`);
    if (!confirmBuy) return;
    try {
      await acceptListing.mutateAsync({ listingId: listing.id });
      alert("Mua thành công! Linh kiện đã được thêm vào kho của bạn.");
    } catch (err: unknown) {
      alert(getErrorMessage(err, "Failed to buy used listing."));
    }
  }

  async function handleRejectListing(listingId: number) {
    try {
      await rejectListing.mutateAsync(listingId);
    } catch (err: unknown) {
      alert(getErrorMessage(err, "Failed to reject listing."));
    }
  }

  async function handleOfferSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!activeNegotiationId || !offerVnd) return;
    const value = parseInt(offerVnd.replace(/\D/g, ""), 10);
    if (isNaN(value) || value <= 0) {
      alert("Please enter a valid positive offer amount.");
      return;
    }
    try {
      await submitOffer.mutateAsync({
        negotiationId: activeNegotiationId,
        offerVnd: value,
        message: customMsg.trim() || undefined
      });
      setCustomMsg("");
      setOfferVnd("");
    } catch (err: unknown) {
      alert(getErrorMessage(err, "Failed to submit offer."));
    }
  }

  async function handleBuyNegotiated(listingId: number, price: number) {
    if (cash < price) {
      alert("Không đủ tiền mặt để thanh toán.");
      return;
    }
    try {
      await acceptListing.mutateAsync({ listingId, finalPriceVnd: price });
      setActiveNegotiationId(null);
      alert("Chốt giao dịch thành công! Linh kiện đã được thêm vào kho.");
    } catch (err: unknown) {
      alert(getErrorMessage(err, "Failed to complete purchase."));
    }
  }

  return (
    <div className="space-y-4">
      {/* Page Header */}
      <ConsolePanel variant="z-1" className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <SectionHeader title="Used Market / Trade-in Console" subtitle="STATION-05 // USED MARKET" />
          <div className="font-mono text-[10px] text-slate-500 mt-1 uppercase">
            CASH DEPOSIT: <span className="text-emerald-400 font-bold">{formatVnd(cash)}</span> // PROCESS DAY: <span className="text-[#00f2ff] font-bold">{gameDay}</span>
          </div>
        </div>

        {/* Telemetry metrics */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-[10px] uppercase shrink-0">
          <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
            <span className="text-slate-500 text-[8px] block tracking-wider">AVAILABLE</span>
            <span className="text-white font-bold text-xs">{stats.available} PARTS</span>
          </div>
          <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
            <span className="text-slate-500 text-[8px] block tracking-wider">NEGOTIATING</span>
            <span className="text-[#ffba20] font-bold text-xs">{stats.negotiating}</span>
          </div>
          <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
            <span className="text-slate-500 text-[8px] block tracking-wider">ACCEPTED</span>
            <span className="text-emerald-400 font-bold text-xs">{stats.accepted}</span>
          </div>
          <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
            <span className="text-slate-500 text-[8px] block tracking-wider">EXPIRED</span>
            <span className="text-slate-500 font-bold text-xs">{stats.expired}</span>
          </div>
        </div>
      </ConsolePanel>

      {/* Listing generation block */}
      <ConsolePanel variant="z-1" className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xs font-bold font-mono text-white uppercase tracking-wider">Generate Used Market Manifest</h2>
          <p className="text-[10px] font-mono text-slate-500 uppercase mt-0.5">Scout local forums and scrap shops to generate new trade-in offers.</p>
        </div>
        <div className="flex gap-2">
          <ActionButton
            variant="secondary"
            onClick={() => generateOne.mutate()}
            disabled={generateOne.isPending}
            className="!h-9 !w-auto !px-4"
          >
            <Sparkles className="h-3.5 w-3.5 text-primary-container" />
            SCOUT LISTING
          </ActionButton>
          <ActionButton
            onClick={() => generateBatch.mutate(5)}
            disabled={generateBatch.isPending}
            className="!h-9 !w-auto !px-4"
          >
            <Sparkles className="h-3.5 w-3.5 text-on-primary-fixed" />
            SCOUT BATCH (5)
          </ActionButton>
        </div>
      </ConsolePanel>

      <div className="grid gap-4 lg:grid-cols-[1.5fr_1fr]">
        {/* Listings view */}
        <div className="space-y-3">
          <h2 className="font-mono text-xs font-bold text-slate-300 uppercase tracking-wider px-1">Available Used Manifests</h2>
          {listings.data?.length === 0 ? (
            <EmptyState
              title="No Listings Found"
              body="No active used listings at the moment. Use the Scout buttons above to search for sellers."
            />
          ) : (
            <div className="grid gap-3 sm:grid-cols-1">
              {listings.data?.map((listing) => {
                const isNegotiating = listing.status === "NEGOTIATING";
                const isUndergoingNeg = activeNeg.data?.listing_id === listing.id;
                
                return (
                  <div key={listing.id} className="border border-white/5 bg-[#0e1115]/50 p-4 transition duration-150 flex flex-col justify-between hover:border-white/10 hover:bg-[#0e1115]">
                    <div>
                      {/* Product Header */}
                      <div className="flex items-start justify-between gap-3">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-[9px] font-bold text-white uppercase pr-2">
                              {listing.product.name}
                            </span>
                            <StatusChip label={listing.product.category} variant="neutral" className="!text-[8px] !px-1.5" />
                          </div>
                          <span className="text-[10px] text-slate-400 font-mono uppercase block mt-1">
                            SELLER: <span className="text-slate-200 font-semibold">{listing.seller_name}</span> // HONESTY: {listing.seller_honesty}%
                          </span>
                        </div>

                        {listing.visible_condition_grade && (
                          <StatusChip 
                            label={`GRADE ${listing.visible_condition_grade.replace("_PLUS", "+")}`} 
                            variant={
                              ["A_PLUS", "A"].includes(listing.visible_condition_grade) ? "success" :
                              ["B", "C"].includes(listing.visible_condition_grade) ? "warning" :
                              "error"
                            }
                            className="!text-[10px] !px-2"
                          />
                        )}
                      </div>

                      {/* Claims block */}
                      <div className="mt-4 border border-white/5 bg-[#0c0e11] p-3 text-[10px] font-mono uppercase space-y-1.5 rounded-sm">
                        <div>
                          <span className="text-slate-500 block text-[8px] tracking-wider">Seller Claimed Condition:</span>
                          <span className="text-slate-200 normal-case italic">"{listing.claimed_condition}"</span>
                        </div>
                        <div>
                          <span className="text-slate-500 block text-[8px] tracking-wider">Reported Usage Metrics:</span>
                          <span className="text-slate-200 normal-case">{listing.claimed_usage}</span>
                        </div>
                        <div className="flex flex-wrap gap-4 text-slate-500 mt-2 pt-2 border-t border-white/5">
                          <span className="flex items-center gap-1">
                            <Heart className="h-3 w-3 text-rose-400" />
                            WARRANTY: {listing.claimed_warranty_months ? `${listing.claimed_warranty_months} MTH` : "NONE"}
                          </span>
                          <span className="flex items-center gap-1">
                            <Calendar className="h-3 w-3 text-[#00f2ff]" />
                            EXPIRY: DAY {listing.expires_on_day}
                          </span>
                        </div>
                      </div>

                      {/* Pricing block */}
                      <div className="mt-4 grid grid-cols-2 gap-4 border-t border-white/5 pt-3 font-mono">
                        <div>
                          <span className="text-[9px] uppercase text-slate-500 block tracking-wider">Asking Price</span>
                          <span className="text-sm font-bold text-white">{formatVnd(listing.asking_price_vnd)}</span>
                        </div>
                        <div>
                          <span className="text-[9px] uppercase text-slate-500 block tracking-wider flex items-center gap-1">
                            Fair Value Estimation
                            <span className="group relative">
                              <Info className="h-3 w-3 text-slate-500 cursor-pointer" />
                              <span className="pointer-events-none absolute bottom-5 left-1/2 -translate-x-1/2 w-48 p-2 rounded bg-[#0c0e11] border border-white/10 text-[9px] text-slate-300 font-normal leading-normal opacity-0 group-hover:opacity-100 transition z-10 shadow-xl normal-case">
                                AI-estimated fair trade value based on specifications, grade, and current multipliers.
                              </span>
                            </span>
                          </span>
                          <span className="text-sm font-bold text-[#00f2ff]">{formatVnd(listing.estimated_fair_value_vnd)}</span>
                        </div>
                      </div>
                    </div>

                    {/* Actions block */}
                    <div className="mt-4 flex gap-2 border-t border-white/5 pt-3">
                      <ActionButton
                        onClick={() => handleBuyNow(listing)}
                        disabled={cash < listing.asking_price_vnd}
                        className="flex-1 font-mono text-[11px]"
                      >
                        Buy Now
                      </ActionButton>
                      <ActionButton
                        variant="secondary"
                        onClick={() => handleStartNegotiate(listing.id)}
                        className={`flex-1 font-mono text-[11px] ${
                          isUndergoingNeg 
                            ? "bg-amber-400 text-slate-950 hover:bg-amber-300"
                            : ""
                        }`}
                      >
                        <MessageSquare className="h-3.5 w-3.5 text-primary-container" />
                        {isNegotiating ? "View Chat" : "Negotiate"}
                      </ActionButton>
                      <ActionButton
                        variant="secondary"
                        onClick={() => handleRejectListing(listing.id)}
                        className="!w-9 shrink-0 flex items-center justify-center hover:!bg-rose-950/20 hover:!border-rose-500/30"
                        title="Pass Listing"
                      >
                        <XCircle className="h-4 w-4 text-rose-400" />
                      </ActionButton>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Negotiation Chat Panel */}
        <div>
          {activeNegotiationId ? (
            <ConsolePanel variant="z-1" className="p-0 border border-white/10 overflow-hidden flex flex-col min-h-[500px]">
              {/* Chat Header */}
              {activeNeg.isLoading ? <LoadingState /> : activeNeg.data ? (
                <>
                  <div className="bg-[#0c0e11] p-4 border-b border-white/10 flex items-center justify-between">
                    <div>
                      <h3 className="font-bold text-white text-sm font-mono uppercase">
                        Negotiation Comms with {activeListing?.seller_name ?? "Seller"}
                      </h3>
                      <p className="text-[10px] text-slate-500 truncate mt-0.5 font-mono uppercase">
                        ITEM: {activeListing?.product.name ?? "Hardware Product"}
                      </p>
                    </div>
                    <button
                      onClick={() => setActiveNegotiationId(null)}
                      className="text-xs font-mono text-slate-400 hover:text-white uppercase"
                    >
                      Close Chat
                    </button>
                  </div>

                  {/* Patience Bar */}
                  <div className="bg-[#0c0e11]/80 px-4 py-2 border-b border-white/5 flex items-center justify-between gap-4 font-mono">
                    <span className="text-[9px] text-slate-500 uppercase shrink-0">Seller Patience:</span>
                    <div className="w-full bg-white/5 h-2 border border-white/10 p-[1px] flex rounded-none">
                      <div
                        className={`h-full transition-all duration-300 ${
                          (activeListing?.seller_patience ?? 100) > 60 ? "bg-emerald-400" :
                          (activeListing?.seller_patience ?? 100) > 30 ? "bg-[#ffba20]" :
                          "bg-rose-500"
                        }`}
                        style={{ width: `${activeListing?.seller_patience ?? 100}%` }}
                      />
                    </div>
                    <span className="text-[9px] text-slate-300 shrink-0">
                      {activeListing?.seller_patience ?? 100}/100
                    </span>
                  </div>

                  {/* Chat Messages */}
                  <div className="flex-1 p-4 overflow-y-auto space-y-3 bg-[#0c0e11]/20 font-mono text-[10px]">
                    {activeNeg.data.messages.map((m) => {
                      const isPlayer = m.sender === "PLAYER";
                      const isSystem = m.sender === "SYSTEM";
                      
                      if (isSystem) {
                        return (
                          <div key={m.id} className="text-center">
                            <span className="inline-block bg-white/5 border border-white/10 rounded-sm px-2.5 py-1 text-[9px] text-slate-400 uppercase">
                              {m.message}
                            </span>
                          </div>
                        );
                      }
                      
                      return (
                        <div
                          key={m.id}
                          className={`flex flex-col ${isPlayer ? "items-end" : "items-start"}`}
                        >
                          <div className={`max-w-[85%] rounded-sm px-3 py-2 leading-relaxed border ${
                            isPlayer 
                              ? "bg-primary-container/5 text-white border-primary-container/20" 
                              : "bg-white/5 text-slate-200 border-white/10"
                          }`}>
                            <div className="text-[8px] text-slate-500 uppercase font-bold mb-1">
                              {isPlayer ? "[YOU]" : `[${activeListing?.seller_name ?? "SELLER"}]`}
                            </div>
                            <p className="normal-case">{m.message}</p>
                            {m.offer_vnd && (
                              <span className="block mt-1.5 font-bold text-[#ffba20]">
                                SUBMITTED OFFER: {formatVnd(m.offer_vnd)}
                              </span>
                            )}
                          </div>
                          <span className="text-[8px] text-slate-600 mt-1">
                            {new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>
                      );
                    })}
                  </div>

                  {/* Input Form or Accepted controls */}
                  <div className="p-4 bg-[#0c0e11] border-t border-white/10 space-y-3 font-mono">
                    {activeNeg.data.status === "OPEN" && (
                      <form onSubmit={handleOfferSubmit} className="space-y-3">
                        <div className="flex gap-2">
                          <input
                            type="text"
                            required
                            placeholder="OFFER AMOUNT IN VND (e.g. 1200000)"
                            value={offerVnd}
                            onChange={(e) => setOfferVnd(e.target.value)}
                            className="flex-1 h-9 border border-white/10 bg-[#0c0e11] px-3 text-xs text-white outline-none focus:border-primary-container font-mono"
                          />
                          <button
                            type="submit"
                            disabled={submitOffer.isPending}
                            className="h-9 px-4 bg-[#00f2ff] text-slate-950 hover:bg-[#00dbe7] text-xs font-bold uppercase transition flex items-center gap-1 shrink-0"
                          >
                            <Send className="h-3.5 w-3.5" />
                            SEND
                          </button>
                        </div>
                        <input
                          type="text"
                          placeholder="OPTIONAL COMPACT ARGUMENT OR MESSAGE..."
                          value={customMsg}
                          onChange={(e) => setCustomMsg(e.target.value)}
                          className="w-full h-8 border border-white/10 bg-[#0c0e11] px-3 text-[10px] text-white outline-none focus:border-primary-container"
                        />
                      </form>
                    )}

                    {activeNeg.data.status === "ACCEPTED" && (
                      <div className="border border-emerald-500/20 bg-emerald-500/5 p-4 text-center space-y-3 rounded-sm">
                        <CheckCircle className="h-6 w-6 text-emerald-400 mx-auto" />
                        <div>
                          <h4 className="text-xs font-bold text-emerald-400 uppercase">Offer Accepted!</h4>
                          <p className="text-[10px] text-slate-400 mt-1 uppercase">
                            Seller agreed to sell for <span className="font-bold text-white">{formatVnd(activeNeg.data.accepted_price_vnd ?? 0)}</span>.
                          </p>
                        </div>
                        <ActionButton
                          onClick={() => handleBuyNegotiated(activeNeg.data!.listing_id, activeNeg.data!.accepted_price_vnd ?? 0)}
                          disabled={cash < (activeNeg.data.accepted_price_vnd ?? 0)}
                          className="w-full !h-9 text-xs"
                        >
                          CHỐT GIAO DỊCH
                        </ActionButton>
                      </div>
                    )}

                    {activeNeg.data.status === "FAILED" && (
                      <div className="border border-rose-500/20 bg-rose-500/5 p-4 text-center space-y-2 rounded-sm">
                        <XCircle className="h-6 w-6 text-rose-400 mx-auto" />
                        <h4 className="text-xs font-bold text-rose-400 uppercase">Negotiation Terminated</h4>
                        <p className="text-[10px] text-slate-500 uppercase leading-normal">
                          Seller's patience was completely exhausted. Negotiation channels have been closed.
                        </p>
                      </div>
                    )}

                    {activeNeg.data.status === "CLOSED" && (
                      <div className="border border-white/10 bg-white/5 p-4 text-center space-y-2 rounded-sm">
                        <ShoppingBag className="h-6 w-6 text-primary-container mx-auto" />
                        <h4 className="text-xs font-bold text-slate-300 uppercase">Deal Logged</h4>
                        <p className="text-[10px] text-slate-500 uppercase">
                          Linh kiện has been successfully acquired.
                        </p>
                      </div>
                    )}
                  </div>
                </>
              ) : null}
            </ConsolePanel>
          ) : (
            <div className="panel p-8 text-center text-slate-400 border border-white/10 min-h-[500px] flex flex-col justify-center items-center gap-3 bg-[#0e1115]/20">
              <MessageSquare className="h-8 w-8 text-slate-600 animate-pulse" />
              <div className="font-mono uppercase">
                <h3 className="font-semibold text-white text-xs">No Active Negotiation</h3>
                <p className="text-[10px] text-slate-500 mt-1.5 max-w-[220px] mx-auto leading-normal">
                  Click the "Negotiate" button on any available listing to start dickering with the seller.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
