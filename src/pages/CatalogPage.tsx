import { ChevronDown, ChevronRight, Search, Activity } from "lucide-react";
import { useMemo, useState } from "react";

import { useBrands, useHardwareProducts } from "../api/hooks";
import { BrandLogo } from "../components/BrandLogo";
import { EmptyState } from "../components/EmptyState";
import type { HardwareCategory, HardwareProduct } from "../types/game";
import { formatVnd, labelize } from "../utils/format";
import { useGameStore } from "../store/gameStore";

import { ConsolePanel } from "../components/ui/ConsolePanel";
import { StatusChip } from "../components/ui/StatusChip";
import { ActionButton } from "../components/ui/ActionButton";
import { SectionHeader } from "../components/ui/SectionHeader";

const categories: Array<HardwareCategory | ""> = ["", "CPU", "GPU", "MOTHERBOARD", "RAM", "STORAGE", "SSD", "PSU", "CASE", "COOLER", "WATER_COOLING", "MONITOR", "OTHER"];
const confidences = ["", "OFFICIAL", "RETAILER", "COMMUNITY_DATABASE", "MANUAL", "ESTIMATED"];

export function CatalogPage() {
  const saveId = useGameStore((state) => state.selectedSaveId);
  const [q, setQ] = useState("");
  const [category, setCategory] = useState<HardwareCategory | "">("");
  const [brandSlug, setBrandSlug] = useState("");
  const [originCode, setOriginCode] = useState("");
  const [dataConfidence, setDataConfidence] = useState("");
  
  const params = useMemo(
    () => ({
      q: q.trim() || undefined,
      category: category || undefined,
      brand_slug: brandSlug || undefined,
      origin_code: originCode.trim().toUpperCase() || undefined,
      data_confidence: dataConfidence || undefined,
      save_game_id: saveId || undefined,
    }),
    [brandSlug, category, dataConfidence, originCode, q, saveId],
  );
  
  const products = useHardwareProducts(params);
  const brands = useBrands();

  return (
    <div className="space-y-4">
      <ConsolePanel variant="z-1" className="flex flex-col gap-2">
        <SectionHeader title="Hardware Intelligence Database" subtitle="STATION-01 // TELEMETRY DATABASE" />
        <div className="font-mono text-[10px] text-slate-500 uppercase">
          Query terminal active // records matching search parameters
        </div>
      </ConsolePanel>

      {/* Terminal query search dashboard */}
      <ConsolePanel variant="z-1" className="p-4">
        <div className="grid gap-3 lg:grid-cols-[1.4fr_1fr_1fr_0.7fr_1fr]">
          <label className="relative block">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
            <input
              className="h-10 w-full border border-white/10 bg-[#0c0e11] pl-9 pr-3 font-mono text-xs text-white uppercase outline-none focus:border-primary-container"
              onChange={(event) => setQ(event.target.value)}
              placeholder="QUERY DATABASE BRAND/MODEL..."
              value={q}
            />
          </label>
          
          <Select label="All Categories" onChange={(value) => setCategory(value as HardwareCategory | "")} options={categories} value={category} />
          
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
          
          <input
            className="h-10 border border-white/10 bg-[#0c0e11] px-3 font-mono text-xs uppercase text-white outline-none focus:border-primary-container"
            maxLength={2}
            onChange={(event) => setOriginCode(event.target.value)}
            placeholder="Origin"
            value={originCode}
          />
          
          <Select label="All Confidence" onChange={setDataConfidence} options={confidences} value={dataConfidence} />
        </div>
      </ConsolePanel>

      {products.isLoading ? <EmptyState title="Accessing central repository" body="Scraping active hardware databases..." /> : null}
      {products.error ? <EmptyState title="Telemetry connection failed" body={(products.error as Error).message} /> : null}
      {products.data?.length === 0 ? <EmptyState title="No assets match query" body="Relax parameter constraints to broaden query result." /> : null}

      <div className="grid gap-3 xl:grid-cols-2">
        {products.data?.map((product) => <ProductCard key={product.id} product={product} />)}
      </div>
    </div>
  );
}

function ProductCard({ product }: { product: HardwareProduct }) {
  const [open, setOpen] = useState(false);
  const specs = product.real_specs_json ?? product.specs_json ?? {};
  const socket = String(specs.socket_slot ?? specs.socket ?? specs.form_factor ?? specs.capacity ?? "No socket/slot");

  const pricingGrid = useMemo(() => {
    const mult = product.market_multiplier ?? 1.0;
    const hasShift = mult !== 1.0;

    const retail = hasShift ? product.market_adjusted_local_retail_vnd : product.latest_local_retail_vnd;
    const used = hasShift ? product.market_adjusted_used_market_vnd : product.latest_used_market_vnd;
    const supplier = hasShift ? product.market_adjusted_supplier_cost_vnd : product.latest_supplier_cost_vnd;
    const msrp = product.latest_msrp_vnd ?? product.msrp_vnd;

    return (
      <div className="flex flex-wrap gap-2 text-[9px] font-mono text-slate-400 mt-2 uppercase">
        {msrp && (
          <span className="bg-white/5 px-2 py-0.5 border border-white/10 rounded-sm">
            MSRP: <span className="text-white font-bold">{formatVnd(msrp)}</span>
          </span>
        )}
        {retail && (
          <span className="bg-primary-container/5 px-2 py-0.5 border border-primary-container/20 rounded-sm">
            Retail: <span className="text-primary-container font-bold">{formatVnd(retail)}</span>
          </span>
        )}
        {used && (
          <span className="bg-[#ffba20]/5 px-2 py-0.5 border border-[#ffba20]/20 rounded-sm">
            Used: <span className="text-[#ffba20] font-bold">{formatVnd(used)}</span>
          </span>
        )}
        {supplier && (
          <span className="bg-emerald-500/5 px-2 py-0.5 border border-emerald-500/20 rounded-sm">
            Supplier: <span className="text-emerald-400 font-bold">{formatVnd(supplier)}</span>
          </span>
        )}
      </div>
    );
  }, [product]);

  const hasMarketShift = product.market_multiplier && product.market_multiplier !== 1.0;

  const confidenceVariant =
    product.data_confidence === "OFFICIAL"
      ? "success"
      : product.data_confidence === "RETAILER"
      ? "success"
      : product.data_confidence === "MANUAL"
      ? "warning"
      : "neutral";

  return (
    <ConsolePanel variant="z-1" className="flex flex-col gap-4">
      <div className="flex gap-3 items-start justify-between">
        <div className="flex gap-3 min-w-0">
          <BrandLogo brand={product.brand_ref} logoUrl={product.effective_logo_url} name={product.brand} size="lg" />
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="truncate font-semibold text-white font-mono">{product.name}</h3>
              <StatusChip label={product.category} variant="neutral" />
              <StatusChip label={product.data_confidence ?? "UNKNOWN"} variant={confidenceVariant} />
              {hasMarketShift ? (
                <span 
                  className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-mono font-bold border ${
                    (product.market_multiplier ?? 1.0) > 1.0 
                      ? "bg-emerald-950/40 text-emerald-400 border-emerald-800/40" 
                      : "bg-rose-950/40 text-rose-400 border-rose-800/40"
                  }`}
                  title={product.active_market_event_titles?.join(", ")}
                >
                  <Activity className="h-3 w-3 text-primary-container" />
                  <span>x{(product.market_multiplier ?? 1.0).toFixed(2)}</span>
                </span>
              ) : null}
            </div>
            <p className="mt-1 text-xs text-slate-500 font-mono">
              {product.brand_ref?.name ?? product.brand} {product.chip_vendor_brand ? `/ CHIP ${product.chip_vendor_brand.name}` : ""} / {product.origin_name_vi ?? product.origin_code ?? "Unknown origin"}
            </p>
            <p className="mt-1.5 text-xs text-slate-400 font-mono uppercase">
              SOCKET: {socket} / BASE POWER: {product.base_power_watts}W
            </p>
            {pricingGrid}
          </div>
        </div>
        
        <ActionButton
          variant="secondary"
          className="!h-8 !w-8 shrink-0 flex items-center justify-center"
          onClick={() => setOpen((value) => !value)}
        >
          {open ? <ChevronDown className="h-4 w-4 text-primary-container" /> : <ChevronRight className="h-4 w-4 text-primary-container" />}
        </ActionButton>
      </div>

      {/* Metric Telemetry Specs */}
      <div className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-5 mt-2">
        <Score label="Perf" value={product.base_performance_score} />
        <Score label="Heat" value={product.base_heat_score} />
        <Score label="Reliability" value={product.base_reliability_score} />
        <Score label="Used Demand" value={product.used_demand_score} />
        <Score label="Mining" value={product.mining_popularity_score} />
      </div>

      {open ? (
        <div className="mt-2 grid gap-3 text-xs lg:grid-cols-2 pt-2 border-t border-white/5">
          <Detail title="Key Specs" value={String(specs.raw_key_specs ?? JSON.stringify(specs))} />
          <Detail title="Source Reference" value={`${product.source_name ?? "Unknown source"}${product.source_url ? ` / ${product.source_url}` : ""}`} />
          <Detail title="Normalized Json Specs" value={JSON.stringify(product.real_specs_json ?? {}, null, 2)} />
          <Detail title="Balance Coefficients" value={JSON.stringify(product.game_balance_json ?? {}, null, 2)} />
        </div>
      ) : null}
    </ConsolePanel>
  );
}

function Score({ label, value }: { label: string; value: number | null | undefined }) {
  return (
    <div className="border border-white/5 bg-[#0c0e11] p-2 font-mono text-[9px] rounded-sm">
      <div className="text-slate-500 uppercase tracking-wider truncate">{label}</div>
      <div className="mt-1 text-xs font-bold text-white">
        {value !== null && value !== undefined ? `${value}` : "?"}
      </div>
    </div>
  );
}

function Detail({ title, value }: { title: string; value: string }) {
  return (
    <div className="border border-white/5 bg-[#0c0e11] p-3 font-mono text-[10px] rounded-sm">
      <div className="mb-2 font-bold text-slate-300 uppercase tracking-wider">{title}</div>
      <pre className="whitespace-pre-wrap break-words leading-relaxed text-slate-400">{value || "None"}</pre>
    </div>
  );
}

function Select({ label, options, value, onChange }: { label: string; options: string[]; value: string; onChange: (value: string) => void }) {
  return (
    <select
      className="h-10 border border-white/10 bg-[#0c0e11] px-3 font-mono text-xs text-white uppercase outline-none focus:border-primary-container"
      onChange={(event) => onChange(event.target.value)}
      value={value}
    >
      {options.map((option) => (
        <option key={option || label} value={option}>
          {option ? labelize(option) : label}
        </option>
      ))}
    </select>
  );
}

