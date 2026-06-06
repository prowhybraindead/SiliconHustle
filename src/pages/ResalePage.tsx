import { useState, useMemo } from "react";
import {
  Store,
  DollarSign,
  Plus,
  RefreshCw,
  XCircle,
  CheckCircle2,
  Tag,
  Clock,
  ShieldAlert,
  MessageSquare,
  Sparkles,
  ArrowRight,
  Ban,
} from "lucide-react";

import {
  useInventory,
  useStaff,
  useResaleListings,
  useCreateResaleListing,
  useCancelResaleListing,
  useGenerateResaleOffer,
  useAcceptResaleOffer,
  useRejectResaleOffer,
} from "../api/hooks";
import { useGameStore } from "../store/gameStore";
import { EmptyState } from "../components/EmptyState";
import { LoadingState } from "../components/LoadingState";
import { ErrorState } from "../components/ErrorState";
import { BrandLogo } from "../components/BrandLogo";
import { formatVnd, labelize } from "../utils/format";
import type { ResaleListing, ResaleBuyerOffer, InventoryUnit, StaffMember } from "../types/game";

import { ConsolePanel } from "../components/ui/ConsolePanel";
import { StatusChip } from "../components/ui/StatusChip";
import { ActionButton } from "../components/ui/ActionButton";
import { SectionHeader } from "../components/ui/SectionHeader";

export function ResalePage() {
  const saveId = useGameStore((state) => state.selectedSaveId);
  const inventory = useInventory(saveId);
  const staffQuery = useStaff(saveId, undefined, "AVAILABLE");
  const listingsQuery = useResaleListings(saveId);

  const createListingMut = useCreateResaleListing(saveId);
  const cancelListingMut = useCancelResaleListing(saveId);
  const genOfferMut = useGenerateResaleOffer(saveId);
  const acceptMut = useAcceptResaleOffer(saveId);
  const rejectMut = useRejectResaleOffer(saveId);

  const [tab, setTab] = useState<"active" | "history">("active");
  const [selectedListingId, setSelectedListingId] = useState<number | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createAskingPrice, setCreateAskingPrice] = useState<string>("");
  const [createWarrantyDays, setCreateWarrantyDays] = useState<number>(0);
  const [createUnitId, setCreateUnitId] = useState<number | null>(null);
  const [selectedStaffId, setSelectedStaffId] = useState<number | null>(null);
  const [saleFlash, setSaleFlash] = useState<{ price: number; reputation: number } | null>(null);

  // Eligible inventory for listing
  const eligibleUnits: InventoryUnit[] = useMemo(() => {
    if (!inventory.data) return [];
    const listedUnitIds = new Set(
      (listingsQuery.data ?? [])
        .filter((l) => ["ACTIVE", "OFFER_RECEIVED", "DRAFT"].includes(l.status))
        .map((l) => l.inventory_unit_id)
    );
    return inventory.data.filter((u) => {
      if (listedUnitIds.has(u.id)) return false;
      if (u.status === "SOLD" || u.status === "INSTALLED_IN_BUILD" || u.status === "RESERVED") return false;
      if (u.ready_for_resale) return true;
      if (u.inspection_confidence >= 60 && ["S", "A", "B", "C"].includes(u.grade)) return true;
      return false;
    });
  }, [inventory.data, listingsQuery.data]);

  // Active / history split
  const activeListings = useMemo(
    () => (listingsQuery.data ?? []).filter((l) => ["ACTIVE", "OFFER_RECEIVED", "DRAFT"].includes(l.status)),
    [listingsQuery.data]
  );
  const historyListings = useMemo(
    () => (listingsQuery.data ?? []).filter((l) => ["SOLD", "CANCELLED", "EXPIRED"].includes(l.status)),
    [listingsQuery.data]
  );

  const visibleListings = tab === "active" ? activeListings : historyListings;
  const selectedListing = (listingsQuery.data ?? []).find((l) => l.id === selectedListingId) ?? null;

  const stats = useMemo(() => {
    const readyInventory = eligibleUnits.length;
    const active = activeListings.length;
    
    let pendingOffers = 0;
    listingsQuery.data?.forEach(l => {
      if (["ACTIVE", "OFFER_RECEIVED"].includes(l.status)) {
        pendingOffers += l.offers?.filter(o => o.status === "PENDING").length ?? 0;
      }
    });

    const sold = (listingsQuery.data ?? []).filter(l => l.status === "SOLD").length;
    
    let totalMargin = 0;
    let marginCount = 0;
    activeListings.forEach(l => {
      if (l.inventory_unit) {
        totalMargin += (l.asking_price_vnd ?? 0) - l.inventory_unit.purchase_price_vnd;
        marginCount++;
      }
    });
    const avgMargin = marginCount > 0 ? Math.round(totalMargin / marginCount) : 0;

    return { readyInventory, active, pendingOffers, sold, avgMargin };
  }, [eligibleUnits, activeListings, listingsQuery.data]);

  // Handlers
  const handleCreate = async () => {
    if (createUnitId === null) return;
    try {
      const listing = await createListingMut.mutateAsync({
        inventory_unit_id: createUnitId,
        asking_price_vnd: createAskingPrice ? Number(createAskingPrice) : null,
        warranty_days_offered: createWarrantyDays,
      });
      setShowCreateModal(false);
      setCreateAskingPrice("");
      setCreateWarrantyDays(0);
      setCreateUnitId(null);
      setSelectedListingId(listing.id);
    } catch (err) {
      console.error(err);
    }
  };

  const handleGenOffer = async (listingId: number) => {
    try {
      const res = await genOfferMut.mutateAsync({ listingId, staffId: selectedStaffId ?? undefined });
      setSelectedListingId(res.listing.id);
    } catch (err) {
      console.error(err);
    }
  };

  const handleAcceptOffer = async (offerId: number) => {
    try {
      const res = await acceptMut.mutateAsync(offerId);
      setSaleFlash({ price: res.offer.offer_price_vnd, reputation: res.reputation_after_sale });
      setTimeout(() => setSaleFlash(null), 4000);
    } catch (err) {
      console.error(err);
    }
  };

  const handleRejectOffer = async (offerId: number) => {
    try {
      await rejectMut.mutateAsync(offerId);
    } catch (err) {
      console.error(err);
    }
  };

  const handleCancel = async (listingId: number) => {
    try {
      await cancelListingMut.mutateAsync(listingId);
      if (selectedListingId === listingId) setSelectedListingId(null);
    } catch (err) {
      console.error(err);
    }
  };

  if (!saveId) {
    return <EmptyState title="No save selected" body="Open a save game before accessing the Resale Marketplace." />;
  }

  return (
    <section className="space-y-4">
      {/* Station Header with Telemetry */}
      <ConsolePanel variant="z-1" className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <SectionHeader title="Resale Marketplace Board" subtitle="STATION-06 // RESALE BOARD" />
          <div className="font-mono text-[10px] text-slate-500 mt-1 uppercase">
            ACTIVE SALES PIPELINE // MARKET EXPANSION BOARD
          </div>
        </div>
        
        {/* Telemetry panel */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 font-mono text-[10px] uppercase shrink-0">
          <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
            <span className="text-slate-500 text-[8px] block tracking-wider">READY INVENTORY</span>
            <span className="text-white font-bold text-xs">{stats.readyInventory} UNITS</span>
          </div>
          <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
            <span className="text-slate-500 text-[8px] block tracking-wider">ACTIVE LISTINGS</span>
            <span className="text-[#00f2ff] font-bold text-xs">{stats.active}</span>
          </div>
          <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
            <span className="text-slate-500 text-[8px] block tracking-wider">BUYER OFFERS</span>
            <span className="text-[#ffba20] font-bold text-xs">{stats.pendingOffers}</span>
          </div>
          <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
            <span className="text-slate-500 text-[8px] block tracking-wider">SOLD ITEMS</span>
            <span className="text-emerald-400 font-bold text-xs">{stats.sold}</span>
          </div>
          <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
            <span className="text-slate-500 text-[8px] block tracking-wider">EST AVG MARGIN</span>
            <span className="text-emerald-400 font-bold text-xs">{formatVnd(stats.avgMargin)}</span>
          </div>
        </div>
      </ConsolePanel>

      {/* Action panel to create listing */}
      <ConsolePanel variant="z-1" className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xs font-bold font-mono text-white uppercase tracking-wider">Market Resale Console</h2>
          <p className="text-[10px] font-mono text-slate-500 uppercase mt-0.5 font-mono">Create new listings for active client demands.</p>
        </div>
        <ActionButton
          id="btn-create-listing"
          className="!h-9 !w-auto !px-4"
          disabled={eligibleUnits.length === 0}
          onClick={() => setShowCreateModal(true)}
        >
          <Plus className="h-4 w-4 text-on-primary-fixed" />
          CREATE RESALE LISTING
        </ActionButton>
      </ConsolePanel>

      {/* Sale Success Flash */}
      {saleFlash && (
        <div className="flex items-center gap-3 border border-emerald-500/20 bg-emerald-500/5 p-4 text-green-200 animate-pulse font-mono text-xs rounded-sm">
          <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-400" />
          <span className="uppercase tracking-wider font-bold">
            Sale logged for {formatVnd(saleFlash.price)}! Reputation delta verified: {saleFlash.reputation}
          </span>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-white/5 pb-px">
        {(["active", "history"] as const).map((t) => (
          <button
            key={t}
            className={`px-4 py-2 font-mono text-[10px] uppercase border-t border-x transition-all ${
              tab === t
                ? "bg-primary-container/10 border-primary-container/40 text-primary-container"
                : "bg-transparent border-transparent text-slate-500 hover:text-slate-300"
            }`}
            onClick={() => setTab(t)}
          >
            {t === "active" ? `Active Listings (${activeListings.length})` : `Sale History (${historyListings.length})`}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        {/* Left: Listings queue list */}
        <div className="space-y-3 lg:col-span-5 flex flex-col">
          <h2 className="font-mono text-xs font-bold text-slate-300 uppercase tracking-wider px-1">Resale Manifest Records</h2>
          {listingsQuery.isLoading && <LoadingState />}
          {listingsQuery.isError && <ErrorState message={(listingsQuery.error as Error).message} />}

          {!listingsQuery.isLoading && visibleListings.length === 0 && (
            <ConsolePanel variant="z-1" className="text-center text-slate-500 font-mono text-xs uppercase">
              {tab === "active"
                ? "No active listings. Create one to start selling."
                : "No completed or cancelled listings yet."}
            </ConsolePanel>
          )}

          <div className="max-h-[640px] overflow-y-auto space-y-2 pr-1 flex-1">
            {visibleListings.map((listing) => {
              const isSelected = listing.id === selectedListingId;
              const unit = listing.inventory_unit;
              const isOfferReceived = listing.status === "OFFER_RECEIVED";
              const isSold = listing.status === "SOLD";

              return (
                <div
                  key={listing.id}
                  id={`listing-card-${listing.id}`}
                  onClick={() => setSelectedListingId(listing.id)}
                  className={`border transition-all duration-150 p-3 cursor-pointer flex items-center justify-between ${
                    isSelected
                      ? "border-[#00f2ff] bg-primary-container/5 shadow-[0_0_8px_rgba(0,242,255,0.15)]"
                      : "border-white/5 bg-[#0e1115]/50 hover:border-white/10 hover:bg-[#0e1115]"
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    {unit && (
                      <BrandLogo
                        brand={unit.product.brand_ref}
                        logoUrl={unit.product.effective_logo_url}
                        name={unit.product.brand}
                        size="sm"
                      />
                    )}
                    <div className="min-w-0">
                      <h4 className="text-xs font-semibold text-white font-mono truncate">{listing.title}</h4>
                      <p className="text-[10px] font-mono text-slate-400 mt-0.5 uppercase">
                        ASK: {formatVnd(listing.asking_price_vnd)} • {listing.offers?.length ?? 0} OFFERS
                      </p>
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-1.5 shrink-0">
                    <StatusChip 
                      label={listing.status === "OFFER_RECEIVED" ? "OFFER RECEIVED" : listing.status} 
                      variant={
                        isSold
                          ? "success"
                          : isOfferReceived
                          ? "warning"
                          : listing.status === "ACTIVE"
                          ? "success"
                          : "neutral"
                      }
                      className="!text-[8px]"
                    />
                    {listing.final_sale_price_vnd && (
                      <span className="text-[10px] font-mono font-bold text-emerald-400">
                        {formatVnd(listing.final_sale_price_vnd)}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right: Listing Detail */}
        <div className="lg:col-span-7 space-y-4">
          {selectedListing ? (
            <ListingDetail
              listing={selectedListing}
              onGenOffer={handleGenOffer}
              onAcceptOffer={handleAcceptOffer}
              onRejectOffer={handleRejectOffer}
              onCancel={handleCancel}
              genLoading={genOfferMut.isPending}
              acceptLoading={acceptMut.isPending}
              rejectLoading={rejectMut.isPending}
              cancelLoading={cancelListingMut.isPending}
              staffOptions={staffQuery.data ?? []}
              selectedStaffId={selectedStaffId}
              setSelectedStaffId={setSelectedStaffId}
            />
          ) : (
            <ConsolePanel variant="z-1" className="p-10 text-center text-slate-500 flex flex-col items-center justify-center min-h-[400px] border border-dashed border-white/10 bg-[#0e1115]/20">
              <Store className="h-10 w-10 text-slate-600 mb-4 animate-pulse" />
              <p className="text-xs font-mono uppercase">Select a resale listing manifest to view details</p>
            </ConsolePanel>
          )}
        </div>
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <CreateListingModal
          units={eligibleUnits}
          selectedUnitId={createUnitId}
          setSelectedUnitId={setCreateUnitId}
          askingPrice={createAskingPrice}
          setAskingPrice={setCreateAskingPrice}
          warrantyDays={createWarrantyDays}
          setWarrantyDays={setCreateWarrantyDays}
          onSubmit={handleCreate}
          onClose={() => setShowCreateModal(false)}
          loading={createListingMut.isPending}
        />
      )}
    </section>
  );
}

// ─── Listing Detail Component ────────────────────────────────────
function ListingDetail({
  listing,
  onGenOffer,
  onAcceptOffer,
  onRejectOffer,
  onCancel,
  genLoading,
  acceptLoading,
  rejectLoading,
  cancelLoading,
  staffOptions,
  selectedStaffId,
  setSelectedStaffId,
}: {
  listing: ResaleListing;
  onGenOffer: (listingId: number) => void;
  onAcceptOffer: (offerId: number) => void;
  onRejectOffer: (offerId: number) => void;
  onCancel: (listingId: number) => void;
  genLoading: boolean;
  acceptLoading: boolean;
  rejectLoading: boolean;
  cancelLoading: boolean;
  staffOptions: StaffMember[];
  selectedStaffId: number | null;
  setSelectedStaffId: (staffId: number | null) => void;
}) {
  const unit = listing.inventory_unit;
  const isActive = ["ACTIVE", "OFFER_RECEIVED"].includes(listing.status);
  const pendingOffers = (listing.offers ?? []).filter((o) => o.status === "PENDING");
  const canGenOffer = isActive && pendingOffers.length < 3;

  return (
    <div className="space-y-4">
      {/* Header Overview */}
      <ConsolePanel variant="z-1" className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
          <div className="flex items-start gap-4">
            {unit && (
              <BrandLogo
                brand={unit.product.brand_ref}
                logoUrl={unit.product.effective_logo_url}
                name={unit.product.brand}
                size="lg"
              />
            )}
            <div>
              <h2 className="text-base font-bold text-white font-mono">{listing.title}</h2>
              <div className="flex flex-wrap gap-2 mt-1.5 items-center">
                <StatusChip 
                  label={listing.status === "OFFER_RECEIVED" ? "OFFER RECEIVED" : listing.status} 
                  variant={
                    listing.status === "SOLD"
                      ? "success"
                      : listing.status === "ACTIVE"
                      ? "success"
                      : "warning"
                  }
                />
                {unit && (
                  <>
                    <StatusChip label={unit.product.category} variant="neutral" className="!text-[8px] !px-1.5" />
                    <span className="text-[10px] font-mono text-slate-400 uppercase">GRADE {labelize(listing.grade_at_listing ?? unit.grade)}</span>
                  </>
                )}
              </div>
              {listing.description && (
                <p className="text-xs text-slate-400 mt-2 font-mono uppercase">{listing.description}</p>
              )}
            </div>
          </div>
          <div className="flex gap-2 shrink-0">
            {isActive && (
              <ActionButton
                variant="danger"
                className="!h-9 !w-auto !px-3 font-mono text-[10px]"
                onClick={() => onCancel(listing.id)}
                disabled={cancelLoading}
              >
                <XCircle className="h-3.5 w-3.5 text-rose-300" /> CANCEL LISTING
              </ActionButton>
            )}
          </div>
        </div>

        {/* Pricing / Telemetry grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-[10px] uppercase">
          <StatCard label="Asking Price" value={formatVnd(listing.asking_price_vnd)} />
          <StatCard label="Est Market Value" value={formatVnd(listing.estimated_market_value_vnd)} />
          <StatCard label="Listing Quality" value={`${listing.listing_quality_score}/100`} />
          <StatCard label="Warranty Terms" value={`${listing.warranty_days_offered} DAYS`} />
        </div>

        {listing.risk_note && (
          <div className="flex items-start gap-2 border border-rose-500/20 bg-rose-500/5 p-3 rounded-sm font-mono text-[10px] uppercase">
            <ShieldAlert className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
            <p className="text-rose-400">WARNING: {listing.risk_note}</p>
          </div>
        )}

        {listing.final_sale_price_vnd && (
          <div className="flex items-center gap-2 border border-emerald-500/20 bg-emerald-500/5 p-3 rounded-sm font-mono text-[10px] uppercase">
            <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
            <span className="text-emerald-400 font-bold">
              TRANSACTION SECURED FOR {formatVnd(listing.final_sale_price_vnd)} ON DAY {listing.sold_on_day}
            </span>
          </div>
        )}
      </ConsolePanel>

      {/* Offers section */}
      <ConsolePanel variant="z-1" className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/5 pb-2">
          <h3 className="text-xs font-bold text-slate-300 font-mono flex items-center gap-2 uppercase tracking-wider">
            <MessageSquare className="h-4 w-4 text-primary-container" /> ACTIVE BUYER OFFERS ({(listing.offers ?? []).length}/3)
          </h3>
          {canGenOffer && (
            <div className="flex items-center gap-2">
              <select
                className="h-8 border border-white/10 bg-[#0c0e11] px-2 font-mono text-[10px] text-white uppercase focus:outline-none focus:border-primary-container"
                value={selectedStaffId ?? ""}
                onChange={(event) => setSelectedStaffId(event.target.value ? Number(event.target.value) : null)}
              >
                <option value="">No Staff support</option>
                {(staffOptions ?? []).map((member) => (
                  <option key={member.id} value={member.id}>
                    {member.name} · {member.role}
                  </option>
                ))}
              </select>
              <ActionButton
                variant="secondary"
                className="!h-8 !w-auto !px-2.5 font-mono text-[9px]"
                onClick={() => onGenOffer(listing.id)}
                disabled={genLoading}
              >
                <RefreshCw className={`h-3 w-3 text-primary-container ${genLoading ? "animate-spin" : ""}`} />
                GENERATE OFFER
              </ActionButton>
            </div>
          )}
        </div>

        {(listing.offers ?? []).length === 0 && (
          <div className="text-center text-slate-500 font-mono text-xs py-4 uppercase">
            No offers active. Scout/Generate offers to prompt buyer activity.
          </div>
        )}

        <div className="space-y-2">
          {(listing.offers ?? []).map((offer) => (
            <OfferCard
              key={offer.id}
              offer={offer}
              isActive={isActive}
              onAccept={onAcceptOffer}
              onReject={onRejectOffer}
              acceptLoading={acceptLoading}
              rejectLoading={rejectLoading}
            />
          ))}
        </div>
      </ConsolePanel>
    </div>
  );
}

// ─── Offer Card Component ────────────────────────────────────────
function OfferCard({
  offer,
  isActive,
  onAccept,
  onReject,
  acceptLoading,
  rejectLoading,
}: {
  offer: ResaleBuyerOffer;
  isActive: boolean;
  onAccept: (offerId: number) => void;
  onReject: (offerId: number) => void;
  acceptLoading: boolean;
  rejectLoading: boolean;
}) {
  const isPending = offer.status === "PENDING";
  const isAccepted = offer.status === "ACCEPTED";
  const isRejected = offer.status === "REJECTED";

  return (
    <div
      id={`offer-card-${offer.id}`}
      className="flex items-center justify-between border border-white/5 bg-[#0c0e11]/50 p-3 rounded-sm font-mono text-[10px]"
    >
      <div className="min-w-0 space-y-1">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-white">{formatVnd(offer.offer_price_vnd)}</span>
          <StatusChip 
            label={offer.status} 
            variant={
              isAccepted
                ? "success"
                : isPending
                ? "warning"
                : isRejected
                ? "error"
                : "neutral"
            }
            className="!text-[8px] !px-1.5"
          />
        </div>
        <p className="text-slate-400 mt-1 uppercase">
          BUYER: <span className="text-slate-200 font-semibold">{offer.buyer_name}</span> // DAY: {offer.created_on_day}
          {offer.expires_on_day && (
            <span className="text-slate-500"> // EXPIRY: DAY {offer.expires_on_day}</span>
          )}
        </p>
        {offer.message && (
          <p className="text-slate-500 italic normal-case">"{offer.message}"</p>
        )}
      </div>
      {isPending && isActive && (
        <div className="flex gap-2 shrink-0 ml-3">
          <ActionButton
            id={`btn-accept-${offer.id}`}
            className="!h-8 !w-auto !px-2.5 font-mono text-[9px]"
            onClick={() => onAccept(offer.id)}
            disabled={acceptLoading}
          >
            <CheckCircle2 className="h-3.5 w-3.5 text-on-primary-fixed" /> ACCEPT
          </ActionButton>
          <ActionButton
            id={`btn-reject-${offer.id}`}
            variant="secondary"
            className="!h-8 !w-auto !px-2.5 font-mono text-[9px] hover:!bg-rose-950/20 hover:!border-rose-500/30 hover:!text-rose-400"
            onClick={() => onReject(offer.id)}
            disabled={rejectLoading}
          >
            <Ban className="h-3.5 w-3.5 text-rose-400" /> REJECT
          </ActionButton>
        </div>
      )}
    </div>
  );
}

// ─── Stat Card Component ──────────────────────────────────────────
function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-white/5 bg-[#0c0e11] p-3 rounded-sm text-center font-mono text-[10px] uppercase">
      <div className="text-slate-500 mb-1 tracking-wider">{label}</div>
      <div className="text-xs font-bold text-white">{value}</div>
    </div>
  );
}

// ─── Create Listing Modal Component ──────────────────────────────
function CreateListingModal({
  units,
  selectedUnitId,
  setSelectedUnitId,
  askingPrice,
  setAskingPrice,
  warrantyDays,
  setWarrantyDays,
  onSubmit,
  onClose,
  loading,
}: {
  units: InventoryUnit[];
  selectedUnitId: number | null;
  setSelectedUnitId: (id: number | null) => void;
  askingPrice: string;
  setAskingPrice: (v: string) => void;
  warrantyDays: number;
  setWarrantyDays: (v: number) => void;
  onSubmit: () => void;
  onClose: () => void;
  loading: boolean;
}) {
  const selectedUnit = units.find((u) => u.id === selectedUnitId) ?? null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <ConsolePanel variant="z-2-active" className="w-full max-w-lg max-h-[90vh] overflow-y-auto p-6 space-y-5 bg-[#111316] border border-primary-container/40">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold font-mono text-white flex items-center gap-2 uppercase">
            <Plus className="h-4 w-4 text-[#00f2ff]" /> NEW RESALE CONTRACT
          </h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition">
            <XCircle className="h-5 w-5" />
          </button>
        </div>

        {/* Unit Picker */}
        <div className="space-y-2 font-mono text-[10px] uppercase">
          <label className="text-slate-400 block tracking-wider">Select Resale Inventory Asset</label>
          <div className="max-h-48 overflow-y-auto space-y-1.5 pr-1">
            {units.map((u) => (
              <div
                key={u.id}
                onClick={() => setSelectedUnitId(u.id)}
                className={`flex items-center gap-3 border p-2.5 cursor-pointer transition ${
                  selectedUnitId === u.id
                    ? "border-[#00f2ff] bg-primary-container/5"
                    : "border-white/5 bg-[#0c0e11] hover:border-white/10"
                }`}
              >
                <BrandLogo
                  brand={u.product.brand_ref}
                  logoUrl={u.product.effective_logo_url}
                  name={u.product.brand}
                  size="sm"
                />
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-semibold text-white truncate normal-case">{u.product.name}</p>
                  <p className="text-[9px] text-slate-500 uppercase mt-0.5">
                    GRADE {labelize(u.grade)} • {labelize(u.product.category)}
                    {u.resale_value_estimate_vnd ? ` • EST ${formatVnd(u.resale_value_estimate_vnd)}` : ""}
                  </p>
                </div>
                {u.ready_for_resale && (
                  <StatusChip label="READY" variant="success" className="!text-[8px]" />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Asking Price */}
        <div className="space-y-1.5 font-mono text-[10px] uppercase">
          <label className="text-slate-400 block tracking-wider">Asking Price (VND, Optional)</label>
          <input
            id="input-asking-price"
            type="number"
            min="0"
            className="w-full h-9 border border-white/10 bg-[#0c0e11] px-3 text-xs text-white outline-none focus:border-primary-container font-mono"
            placeholder={selectedUnit?.resale_value_estimate_vnd ? `Suggested: ${selectedUnit.resale_value_estimate_vnd.toLocaleString()}` : "Auto-price from market value"}
            value={askingPrice}
            onChange={(e) => setAskingPrice(e.target.value)}
          />
          <p className="text-[8px] text-slate-500 uppercase">Leave blank to use market valuation.</p>
        </div>

        {/* Warranty */}
        <div className="space-y-1.5 font-mono text-[10px] uppercase">
          <label className="text-slate-400 block tracking-wider">Warranty Exposure Period (Days)</label>
          <input
            id="input-warranty-days"
            type="number"
            min="0"
            max="365"
            className="w-full h-9 border border-white/10 bg-[#0c0e11] px-3 text-xs text-white outline-none focus:border-primary-container font-mono"
            value={warrantyDays}
            onChange={(e) => setWarrantyDays(Number(e.target.value))}
          />
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 pt-2 font-mono text-[10px] uppercase">
          <button
            className="px-4 py-2 text-slate-400 hover:text-white transition"
            onClick={onClose}
          >
            Cancel
          </button>
          <ActionButton
            id="btn-submit-listing"
            className="!w-auto !px-4"
            disabled={selectedUnitId === null || loading}
            onClick={onSubmit}
          >
            {loading ? <RefreshCw className="h-4 w-4 animate-spin text-on-primary-fixed" /> : <ArrowRight className="h-4 w-4 text-on-primary-fixed" />}
            CREATE RESALE CONTRACT
          </ActionButton>
        </div>
      </ConsolePanel>
    </div>
  );
}
