import { useState, useMemo } from "react";
import { Search, Globe, Truck, Heart, Award, CreditCard, Layers } from "lucide-react";
import { useCreatePurchaseOrder, usePurchaseOrders, useReceivePurchaseOrder, useSupplierOffers, useSuppliers, useBrands } from "../api/hooks";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { BrandLogo } from "../components/BrandLogo";
import { LoadingState } from "../components/LoadingState";
import { useGameStore } from "../store/gameStore";
import { formatVnd, labelize, formatCurrency } from "../utils/format";
import type { HardwareCategory } from "../types/game";

import { ConsolePanel } from "../components/ui/ConsolePanel";
import { StatusChip } from "../components/ui/StatusChip";
import { ActionButton } from "../components/ui/ActionButton";
import { SectionHeader } from "../components/ui/SectionHeader";

const categories: Array<HardwareCategory | ""> = ["", "CPU", "GPU", "MOTHERBOARD", "RAM", "STORAGE", "SSD", "PSU", "CASE", "COOLER", "WATER_COOLING", "MONITOR", "OTHER"];
const currencies = ["", "VND", "USD", "EUR", "CNY", "TWD"];

export function SuppliersPage() {
  const saveId = useGameStore((state) => state.selectedSaveId);
  const [q, setQ] = useState("");
  const [category, setCategory] = useState<HardwareCategory | "">("");
  const [brandSlug, setBrandSlug] = useState("");
  const [supplierId, setSupplierId] = useState("");
  const [currency, setCurrency] = useState("");

  const params = useMemo(
    () => ({
      q: q.trim() || undefined,
      category: category || undefined,
      brand_slug: brandSlug || undefined,
      supplier_id: supplierId ? Number(supplierId) : undefined,
      currency: currency || undefined,
      save_game_id: saveId || undefined,
    }),
    [q, category, brandSlug, supplierId, currency, saveId]
  );

  const suppliers = useSuppliers();
  const brands = useBrands();
  const offers = useSupplierOffers(params);
  const purchaseOrders = usePurchaseOrders(saveId);
  const createOrder = useCreatePurchaseOrder(saveId);
  const receiveOrder = useReceivePurchaseOrder(saveId);

  return (
    <section className="space-y-4">
      <ConsolePanel variant="z-1" className="flex flex-col gap-2">
        <SectionHeader title="Supplier Procurement Terminal" subtitle="STATION-01 // SUPPLIER DESK" />
        <div className="font-mono text-[10px] text-slate-500 uppercase">
          Purchase agreements // global logistics tracking // FX exchange monitoring
        </div>
      </ConsolePanel>
      
      {/* Filters Panel */}
      <ConsolePanel variant="z-1" className="p-4">
        <div className="grid gap-3 md:grid-cols-[1.2fr_1fr_1fr_1fr_1fr]">
          <label className="relative block">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
            <input 
              className="h-10 w-full border border-white/10 bg-[#0c0e11] pl-9 pr-3 font-mono text-xs text-white uppercase outline-none focus:border-primary-container" 
              onChange={(event) => setQ(event.target.value)} 
              placeholder="SEARCH CATALOG OR SUPPLIER..." 
              value={q} 
            />
          </label>
          
          <select 
            className="h-10 border border-white/10 bg-[#0c0e11] px-3 font-mono text-xs text-white uppercase outline-none focus:border-primary-container" 
            onChange={(event) => setCategory(event.target.value as HardwareCategory | "")} 
            value={category}
          >
            <option value="">All Categories</option>
            {categories.filter(Boolean).map((cat) => (
              <option key={cat} value={cat}>
                {labelize(cat)}
              </option>
            ))}
          </select>
          
          <select 
            className="h-10 border border-white/10 bg-[#0c0e11] px-3 font-mono text-xs text-white uppercase outline-none focus:border-primary-container" 
            onChange={(event) => setBrandSlug(event.target.value)} 
            value={brandSlug}
          >
            <option value="">All Brands</option>
            {brands.data?.map((brand) => (
              <option key={brand.slug} value={brand.slug}>
                {brand.name}
              </option>
            ))}
          </select>
          
          <select 
            className="h-10 border border-white/10 bg-[#0c0e11] px-3 font-mono text-xs text-white uppercase outline-none focus:border-primary-container" 
            onChange={(event) => setSupplierId(event.target.value)} 
            value={supplierId}
          >
            <option value="">All Suppliers</option>
            {suppliers.data?.map((sup) => (
              <option key={sup.id} value={sup.id}>
                {sup.name}
              </option>
            ))}
          </select>
          
          <select 
            className="h-10 border border-white/10 bg-[#0c0e11] px-3 font-mono text-xs text-white uppercase outline-none focus:border-primary-container" 
            onChange={(event) => setCurrency(event.target.value)} 
            value={currency}
          >
            <option value="">All Currencies</option>
            {currencies.filter(Boolean).map((curr) => (
              <option key={curr} value={curr}>
                {curr}
              </option>
            ))}
          </select>
        </div>
      </ConsolePanel>

      {(suppliers.isLoading || offers.isLoading || (saveId && purchaseOrders.isLoading)) && <LoadingState />}
      {(suppliers.isError || offers.isError || (saveId && purchaseOrders.isError)) && <ErrorState />}
      
      <div className="grid gap-4 xl:grid-cols-[1.2fr_1fr]">
        {/* Left Column: Supplier Offers */}
        <div className="space-y-3">
          <h2 className="font-mono text-xs font-bold text-slate-300 flex justify-between items-center uppercase tracking-wider px-1">
            <span>Active Supplier Offer Manifest</span>
            <span className="text-[10px] text-slate-500 font-normal">
              {offers.data ? `${offers.data.length} records active` : ""}
            </span>
          </h2>
          {offers.data?.length === 0 ? (
            <EmptyState title="No contracts found" body="Adjust filters or check global events." />
          ) : null}
          {offers.data?.map((offer) => (
            <ConsolePanel key={offer.id} variant="z-1">
              <div className="flex items-start justify-between gap-3">
                <div className="flex min-w-0 gap-3">
                  <BrandLogo brand={offer.product.brand_ref} logoUrl={offer.product.effective_logo_url} name={offer.product.brand} />
                  <div className="min-w-0 flex-1">
                    <h3 className="font-semibold text-white font-mono truncate">{offer.product.name}</h3>
                    
                    <p className="mt-1 text-xs text-slate-400 font-mono uppercase">
                      SUPPLIER: {offer.supplier.name}
                    </p>
                    
                    {/* Rich Supplier telemetry chips */}
                    <div className="mt-2.5 flex flex-wrap gap-1.5 items-center">
                      <span className="inline-flex items-center gap-1 font-mono text-[9px] uppercase bg-white/5 border border-white/10 text-slate-300 px-1.5 py-0.5 rounded-sm">
                        <Globe className="h-3 w-3 text-slate-400" />
                        {offer.supplier.country_code || "VN"}
                      </span>
                      <span className="inline-flex items-center gap-1 font-mono text-[9px] uppercase bg-primary-container/10 border border-primary-container/30 text-[#00f2ff] px-1.5 py-0.5 rounded-sm">
                        <Layers className="h-3 w-3 text-primary-container" />
                        {labelize(offer.supplier.supplier_tier || "OTHER")}
                      </span>
                      <span className="inline-flex items-center gap-1 font-mono text-[9px] uppercase bg-white/5 border border-white/10 text-slate-300 px-1.5 py-0.5 rounded-sm">
                        <Award className="h-3 w-3 text-[#ffba20]" />
                        TRUST {offer.supplier.trust_score}%
                      </span>
                      <span className="inline-flex items-center gap-1 font-mono text-[9px] uppercase bg-white/5 border border-white/10 text-slate-300 px-1.5 py-0.5 rounded-sm">
                        <Heart className="h-3 w-3 text-rose-400" />
                        REL {offer.supplier.relationship_score}%
                      </span>
                      <span className="inline-flex items-center gap-1 font-mono text-[9px] uppercase bg-white/5 border border-white/10 text-slate-300 px-1.5 py-0.5 rounded-sm">
                        <Truck className="h-3 w-3 text-slate-400" />
                        {offer.supplier.default_delivery_days ?? offer.supplier.delivery_days} DAYS
                      </span>
                    </div>

                    <div className="mt-2 text-[10px] font-mono text-slate-400 uppercase">
                      MOQ: <span className="text-white font-bold">{offer.min_order_quantity}</span> // STOCK: <span className="text-white font-bold">{offer.available_quantity}</span> // WARRANTY: <span className="text-white font-bold">{offer.warranty_months} MONTHS</span>
                    </div>

                    {/* Dual Prices & FX status */}
                    <div className="mt-3 flex flex-col gap-1">
                      <div className="flex items-baseline gap-2 flex-wrap">
                        {offer.foreign_unit_price !== null && offer.foreign_currency ? (
                          <>
                            <span className="font-mono text-xs text-slate-500 line-through decoration-slate-700">
                              {formatCurrency(offer.foreign_unit_price, offer.foreign_currency)}
                            </span>
                            <span className="text-[10px] text-slate-600 font-mono">→</span>
                          </>
                        ) : null}
                        <span className="font-mono text-sm font-bold text-primary-container">
                          {formatVnd(offer.market_adjusted_unit_price_vnd ?? offer.effective_unit_price_vnd)}
                        </span>
                        <span className="text-[9px] text-slate-500 font-mono uppercase tracking-wider">effective cost</span>
                        {offer.market_multiplier && offer.market_multiplier !== 1.0 ? (
                          <span 
                            className={`inline-flex items-center rounded px-1.5 py-0.2 text-[9px] font-mono font-bold border ${
                              offer.market_multiplier > 1.0 
                                ? "bg-emerald-950/40 text-emerald-400 border-emerald-800/40" 
                                : "bg-rose-950/40 text-rose-400 border-rose-800/40"
                            }`}
                            title={offer.active_market_event_titles?.join(", ")}
                          >
                            x{offer.market_multiplier.toFixed(2)}
                          </span>
                        ) : null}
                      </div>
                      
                      {offer.foreign_currency && offer.foreign_currency !== "VND" && (
                        <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                          <StatusChip 
                            label={offer.effective_fx_is_fallback ? "OFFLINE FX" : "LIVE FX"} 
                            variant={offer.effective_fx_is_fallback ? "warning" : "success"}
                            className="!text-[8px] !px-1"
                          />
                          <span className="text-[9px] text-slate-500 font-mono uppercase">
                            1 {offer.foreign_currency} = {offer.effective_fx_rate_to_vnd?.toLocaleString()} VND
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
                
                <ActionButton
                  variant="primary"
                  className="!h-9 !w-auto !px-4"
                  disabled={createOrder.isPending || !saveId}
                  onClick={() => createOrder.mutate(offer)}
                  title={!saveId ? "Select a save game to make purchase orders" : undefined}
                >
                  ORDER
                </ActionButton>
              </div>
            </ConsolePanel>
          ))}
        </div>
        
        {/* Right Column: Purchase Orders */}
        <div className="space-y-3">
          <h2 className="font-mono text-xs font-bold text-slate-300 uppercase tracking-wider px-1">Active Procurement Invoices</h2>
          {!saveId ? (
            <EmptyState title="Access Denied" body="Connect showroom access to pull invoice pipeline." />
          ) : (
            <>
              {purchaseOrders.data?.length === 0 ? <EmptyState title="No active invoices" body="Initialize a procurement contract on the left." /> : null}
              {purchaseOrders.data?.map((order) => (
                <ConsolePanel key={order.id} variant="z-1" className="space-y-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1.5 flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold text-white font-mono">PO #{order.id}</h3>
                        <StatusChip label={order.status} variant={order.status === "RECEIVED" ? "success" : "warning"} />
                      </div>
                      <p className="text-xs text-slate-400 font-mono uppercase">
                        SUPPLIER: {order.supplier.name} // DELIVERY DUE: DAY {order.delivery_due_day}
                      </p>
                      
                      {/* Monospace invoice printout breakdown */}
                      <div className="bg-[#0c0e11] border border-white/5 p-3 text-[10px] font-mono space-y-1.5 rounded-sm">
                        <div className="text-slate-500 border-b border-white/5 pb-1 mb-1 uppercase tracking-wider flex items-center gap-1">
                          <CreditCard className="h-3.5 w-3.5 text-primary-container" />
                          INVOICE DETAIL
                        </div>
                        {order.invoice_currency !== "VND" ? (
                          <>
                            <div className="flex justify-between">
                              <span className="text-slate-500">Invoice Subtotal:</span>
                              <span className="text-slate-300">
                                {formatCurrency(order.foreign_subtotal, order.invoice_currency)}
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-slate-500">Converted Subtotal:</span>
                              <span className="text-slate-300">{formatVnd(order.subtotal_vnd)}</span>
                            </div>
                            {order.fx_fee_vnd > 0 && (
                              <div className="flex justify-between">
                                <span className="text-slate-500">Import & Spread Fees:</span>
                                <span className="text-secondary-fixed-dim">+{formatVnd(order.fx_fee_vnd)}</span>
                              </div>
                            )}
                            <div className="flex justify-between border-t border-white/5 pt-1.5 mt-1 font-bold">
                              <span className="text-slate-400 uppercase">Charged Total (VND):</span>
                              <span className="text-[#00f2ff]">{formatVnd(order.final_total_vnd)}</span>
                            </div>
                            <div className="text-[9px] text-slate-600 font-mono mt-1.5 pt-1 border-t border-white/5 uppercase leading-normal">
                              FX snapshot: 1 {order.invoice_currency} = {order.fx_rate_to_vnd?.toLocaleString()} VND (+{order.fx_spread_percent}%) // PROVIDER: {order.fx_provider?.toUpperCase()} {order.fx_is_fallback ? "(OFFLINE)" : "(LIVE)"}
                            </div>
                          </>
                        ) : (
                          <div className="flex justify-between font-bold">
                            <span className="text-slate-400 uppercase">Charged Total (VND):</span>
                            <span className="text-[#00f2ff]">{formatVnd(order.subtotal_vnd)}</span>
                          </div>
                        )}
                      </div>
                      
                      <p className="text-[10px] text-slate-500 font-mono truncate uppercase">
                        ITEMS: {order.items.map((item) => `${item.quantity}X ${item.product.name}`).join(", ")}
                      </p>
                    </div>
                    {order.status !== "RECEIVED" ? (
                      <ActionButton
                        variant="primary"
                        className="!h-9 !w-auto !px-4"
                        disabled={receiveOrder.isPending}
                        onClick={() => receiveOrder.mutate(order.id)}
                      >
                        RECEIVE
                      </ActionButton>
                    ) : null}
                  </div>
                </ConsolePanel>
              ))}
            </>
          )}
        </div>
      </div>
    </section>
  );
}
