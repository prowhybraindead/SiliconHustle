import { Search } from "lucide-react";
import { useMemo, useState } from "react";

import { useBrands } from "../api/hooks";
import { BrandLogo } from "../components/BrandLogo";
import { EmptyState } from "../components/EmptyState";
import type { BrandCategory, BrandType, MarketTier } from "../types/game";
import { labelize } from "../utils/format";

import { ConsolePanel } from "../components/ui/ConsolePanel";
import { StatusChip } from "../components/ui/StatusChip";
import { SectionHeader } from "../components/ui/SectionHeader";

const categories: Array<BrandCategory | ""> = ["", "CPU", "GPU", "MOTHERBOARD", "RAM", "STORAGE", "PSU", "CASE", "COOLER", "WATER_COOLING", "MONITOR", "OTHER"];
const marketTiers: Array<MarketTier | ""> = ["", "PREMIUM", "MAINSTREAM", "VALUE", "BUDGET", "GRAY_MARKET", "INDUSTRIAL", "UNKNOWN"];
const brandTypes: Array<BrandType | ""> = ["", "CHIP_VENDOR", "BOARD_PARTNER", "MEMORY_STORAGE", "PSU_CASE_COOLING", "CASE_COOLING", "RETAILER", "OTHER"];

export function BrandsPage() {
  const [q, setQ] = useState("");
  const [category, setCategory] = useState<BrandCategory | "">("");
  const [marketTier, setMarketTier] = useState<MarketTier | "">("");
  const [brandType, setBrandType] = useState<BrandType | "">("");
  const [originCode, setOriginCode] = useState("");
  const params = useMemo(
    () => ({
      q: q.trim() || undefined,
      category: category || undefined,
      market_tier: marketTier || undefined,
      brand_type: brandType || undefined,
      origin_code: originCode.trim().toUpperCase() || undefined,
    }),
    [brandType, category, marketTier, originCode, q],
  );
  const brands = useBrands(params);

  const totalBrandsCount = brands.data?.length ?? 0;
  const categoriesCount = useMemo(() => {
    const set = new Set<string>();
    brands.data?.forEach(b => b.categories?.forEach(c => set.add(c)));
    return set.size;
  }, [brands.data]);
  const originsCount = useMemo(() => {
    const set = new Set<string>();
    brands.data?.forEach(b => {
      if (b.origin_code) set.add(b.origin_code);
    });
    return set.size;
  }, [brands.data]);

  return (
    <section className="space-y-4">
      {/* Header and Telemetry */}
      <ConsolePanel variant="z-1" className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <SectionHeader title="Brand Registry" subtitle="STATION-12 // MANUFACTURER DIRECTORY" />
          <div className="font-mono text-[10px] text-slate-500 mt-1 uppercase">
            STATUS: <span className="text-[#00f2ff] font-bold">REGISTRY ONLINE</span> // SYSTEM: NORMAL
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 font-mono text-[10px] uppercase shrink-0">
          <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
            <span className="text-slate-500 text-[8px] block tracking-wider">TOTAL REGISTERED</span>
            <span className="text-[#00f2ff] font-bold text-xs">{totalBrandsCount} BRANDS</span>
          </div>
          <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
            <span className="text-slate-500 text-[8px] block tracking-wider">CATEGORIES MAPPED</span>
            <span className="text-white font-bold text-xs">{categoriesCount} CATEGORIES</span>
          </div>
          <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
            <span className="text-slate-500 text-[8px] block tracking-wider">ORIGIN REGIONS</span>
            <span className="text-[#ffba20] font-bold text-xs">{originsCount} REGIONS</span>
          </div>
        </div>
      </ConsolePanel>

      {/* Filter and Search Console */}
      <ConsolePanel variant="z-1" className="p-4">
        <div className="grid gap-2 grid-cols-1 sm:grid-cols-2 lg:grid-cols-[1.5fr_1fr_1fr_1fr_0.6fr] font-mono text-xs uppercase">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
            <input
              className="h-10 w-full rounded-none border border-white/10 bg-[#0c0e11] pl-9 pr-3 text-xs text-slate-100 outline-none transition focus:border-[#00f2ff]/60"
              onChange={(event) => setQ(event.target.value)}
              placeholder="QUERY NAME OR SLUG..."
              value={q}
            />
          </div>
          <FilterSelect label="All categories" onChange={(value) => setCategory(value as BrandCategory | "")} options={categories} value={category} />
          <FilterSelect label="All tiers" onChange={(value) => setMarketTier(value as MarketTier | "")} options={marketTiers} value={marketTier} />
          <FilterSelect label="All types" onChange={(value) => setBrandType(value as BrandType | "")} options={brandTypes} value={brandType} />
          <input
            className="h-10 rounded-none border border-white/10 bg-[#0c0e11] px-3 text-xs uppercase text-slate-100 outline-none transition focus:border-[#00f2ff]/60"
            maxLength={2}
            onChange={(event) => setOriginCode(event.target.value)}
            placeholder="ORIGIN..."
            value={originCode}
          />
        </div>
      </ConsolePanel>

      {brands.isLoading ? <EmptyState title="LOADING BRANDS" body="Reading brand master data from database." /> : null}
      {brands.error ? <EmptyState title="CONNECTION ERROR" body={(brands.error as Error).message} /> : null}
      {brands.data?.length === 0 ? <EmptyState title="NO RECORDS FOUND" body="No manufacturers match the current filter query." /> : null}

      {/* Brands Grid */}
      <div className="grid gap-3 xl:grid-cols-2">
        {brands.data?.map((brand) => (
          <ConsolePanel key={brand.id} variant="z-1" className="p-4 flex flex-col justify-between space-y-4">
            <div className="flex items-start gap-3">
              <BrandLogo brand={brand} size="lg" />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-1.5">
                  <h3 className="truncate font-sans text-sm font-bold text-white uppercase tracking-wider">{brand.name}</h3>
                  <StatusChip
                    label={brand.market_tier}
                    variant={brand.market_tier === "GRAY_MARKET" ? "warning" : "neutral"}
                  />
                  <StatusChip label={brand.brand_type} variant="neutral" />
                </div>
                <p className="mt-1 font-mono text-[10px] text-slate-500 uppercase">
                  SLUG: {brand.slug} / ORIGIN: {brand.origin_name_vi ?? "UNKNOWN"} {brand.origin_code ? `(${brand.origin_code})` : ""}
                </p>
              </div>
              <div className="shrink-0 text-right font-mono text-[10px] text-slate-400 uppercase">
                {brand.base_trust_score !== undefined && brand.base_trust_score !== null && (
                  <div>
                    TRUST: <span className="font-bold text-slate-100">{brand.base_trust_score}</span>
                  </div>
                )}
                {brand.used_market_risk_modifier !== undefined && brand.used_market_risk_modifier !== null && (
                  <div>
                    RISK MOD: <span className="font-bold text-[#ffba20]">{brand.used_market_risk_modifier}</span>
                  </div>
                )}
              </div>
            </div>

            <div className="flex flex-wrap gap-1.5">
              {brand.categories.length ? (
                brand.categories.map((item) => (
                  <StatusChip key={item} label={item} variant="success" />
                ))
              ) : (
                <StatusChip label="NO_CATEGORY" variant="neutral" />
              )}
            </div>

            {brand.notes && (
              <p className="font-mono text-xs text-slate-500 uppercase line-clamp-2 leading-relaxed">
                {brand.notes}
              </p>
            )}

            {brand.website_url && (
              <div className="pt-2 border-t border-white/5">
                <a
                  className="font-mono text-xs font-bold text-[#00f2ff] hover:underline uppercase"
                  href={brand.website_url}
                  rel="noreferrer"
                  target="_blank"
                >
                  LINK // WEBSITE DESK
                </a>
              </div>
            )}
          </ConsolePanel>
        ))}
      </div>
    </section>
  );
}

function FilterSelect({ label, options, value, onChange }: { label: string; options: string[]; value: string; onChange: (value: string) => void }) {
  return (
    <select
      className="h-10 rounded-none border border-white/10 bg-[#0c0e11] px-3 font-mono text-xs text-slate-100 outline-none transition focus:border-[#00f2ff]/60"
      onChange={(event) => onChange(event.target.value)}
      value={value}
    >
      {options.map((option) => (
        <option key={option || label} value={option}>
          {option ? labelize(option) : label.toUpperCase()}
        </option>
      ))}
    </select>
  );
}
