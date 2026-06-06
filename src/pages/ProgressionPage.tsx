import { useMemo, useState } from "react";
import { BadgeCheck, BadgeDollarSign, Lock, Sparkles, Unlock } from "lucide-react";

import { useProgression, usePurchaseShopUpgrade, useShopUpgrades } from "../api/hooks";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { useGameStore } from "../store/gameStore";
import { formatVnd } from "../utils/format";
import type { ShopUpgradeCategory, ShopUpgradeDefinition } from "../types/game";

import { ConsolePanel } from "../components/ui/ConsolePanel";
import { StatusChip } from "../components/ui/StatusChip";
import { ActionButton } from "../components/ui/ActionButton";
import { SectionHeader } from "../components/ui/SectionHeader";

const CATEGORY_ORDER: Array<ShopUpgradeCategory | "ALL"> = [
  "ALL",
  "STORAGE",
  "TEST_BENCH",
  "REFURBISH",
  "SUPPLIER",
  "RESALE",
  "WARRANTY",
  "STAFF",
  "CUSTOMER",
  "MARKET",
  "OPERATIONS",
];

function prettyKey(value: string) {
  return value
    .replace(/_/g, " ")
    .toLowerCase()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function UpgradeCard({
  upgrade,
  cash,
  onPurchase,
  busy,
}: {
  upgrade: ShopUpgradeDefinition;
  cash: number;
  onPurchase: (upgradeKey: string) => void;
  busy: boolean;
}) {
  const affordable = cash >= upgrade.cost_vnd;
  const isAvailable = upgrade.status === "AVAILABLE";
  const canPurchase = isAvailable && affordable && !busy;
  const buttonLabel =
    upgrade.status === "PURCHASED"
      ? "PURCHASED"
      : upgrade.status === "LOCKED"
        ? "LOCKED"
        : affordable
          ? "INSTALL UPGRADE"
          : "INSUFFICIENT FUNDS";
  const effectEntries = Object.entries(upgrade.effects_json).filter(([, value]) => value !== 0 && value !== false && value !== null && value !== undefined);

  return (
    <ConsolePanel
      variant={upgrade.status === "PURCHASED" ? "z-1" : upgrade.status === "LOCKED" ? "z-1" : "z-2"}
      className="flex flex-col h-full space-y-4"
    >
      <div className="flex items-start justify-between gap-3 border-b border-white/5 pb-2">
        <div>
          <div className="mb-1 flex items-center gap-2 font-mono text-[9px] uppercase tracking-wider text-slate-500">
            <span className="border border-white/10 bg-white/[0.04] px-1.5 py-0.5">{upgrade.category}</span>
            <span>TIER {upgrade.level}</span>
          </div>
          <h3 className="font-sans text-sm font-bold text-white uppercase tracking-wider">{upgrade.title}</h3>
        </div>
        <StatusChip
          label={upgrade.status}
          variant={
            upgrade.status === "PURCHASED"
              ? "success"
              : upgrade.status === "LOCKED"
                ? "warning"
                : "neutral"
          }
        />
      </div>

      <p className="font-mono text-xs text-slate-400 leading-relaxed uppercase">{upgrade.description}</p>

      <div className="grid grid-cols-2 gap-2 font-mono text-[10px] uppercase">
        <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm">
          <span className="block text-slate-500 text-[8px]">EST COST</span>
          <span className="mt-1 block font-bold text-[#00f2ff]">{formatVnd(upgrade.cost_vnd)}</span>
        </div>
        <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm">
          <span className="block text-slate-500 text-[8px]">LEVEL SCALE</span>
          <span className="mt-1 block font-bold text-white">
            {upgrade.level} / {upgrade.max_level}
          </span>
        </div>
      </div>

      {upgrade.requirements.length > 0 && (
        <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm font-mono text-[10px] uppercase">
          <div className="mb-1 text-slate-500 text-[8px]">PREREQ REQUIRED</div>
          <div className="flex flex-wrap gap-1.5">
            {upgrade.requirements.map((requirement) => (
              <span key={requirement} className="border border-white/10 bg-white/5 px-1.5 py-0.5 text-[9px] text-slate-300">
                [{requirement}]
              </span>
            ))}
          </div>
        </div>
      )}

      {effectEntries.length > 0 && (
        <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm font-mono text-[10px] uppercase">
          <div className="mb-1 flex items-center gap-1 text-slate-500 text-[8px]">
            <Sparkles className="h-3 w-3 text-[#00f2ff]" />
            EFFECT MODIFIERS
          </div>
          <div className="flex flex-wrap gap-1.5">
            {effectEntries.map(([key, value]) => (
              <span key={key} className="border border-[#00f2ff]/20 bg-[#00f2ff]/5 px-1.5 py-0.5 text-[9px] text-[#00f2ff]">
                {prettyKey(key)}: {String(value)}
              </span>
            ))}
          </div>
        </div>
      )}

      {upgrade.locked_reason && (
        <div className="bg-rose-500/10 border border-rose-500/20 p-2 font-mono text-[10px] text-rose-400 uppercase">
          ERROR: {upgrade.locked_reason}
        </div>
      )}

      <div className="mt-auto pt-2">
        <ActionButton
          variant={upgrade.status === "PURCHASED" ? "secondary" : canPurchase ? "primary" : "secondary"}
          disabled={!canPurchase}
          onClick={() => onPurchase(upgrade.key)}
        >
          <BadgeDollarSign className="h-4 w-4" />
          {buttonLabel}
        </ActionButton>
      </div>
    </ConsolePanel>
  );
}

export function ProgressionPage() {
  const saveId = useGameStore((state) => state.selectedSaveId);
  const progressionQuery = useProgression(saveId);
  const upgradesQuery = useShopUpgrades(saveId);
  const purchaseMutation = usePurchaseShopUpgrade(saveId);
  const [selectedCategory, setSelectedCategory] = useState<ShopUpgradeCategory | "ALL">("ALL");
  const [feedback, setFeedback] = useState<string | null>(null);

  const categories = useMemo(() => {
    const raw = upgradesQuery.data?.map((upgrade) => upgrade.category) ?? [];
    return CATEGORY_ORDER.filter((category) => category === "ALL" || raw.includes(category));
  }, [upgradesQuery.data]);

  const filteredUpgrades = (upgradesQuery.data ?? []).filter(
    (upgrade) => selectedCategory === "ALL" || upgrade.category === selectedCategory,
  );

  const effectSummary = progressionQuery.data?.upgrade_effect_summary;
  const effectEntries = effectSummary ? Object.entries(effectSummary).filter(([, value]) => value !== 0 && value !== false && value !== null && value !== undefined) : [];
  const summary = (progressionQuery.data?.summary ?? {}) as Record<string, unknown>;
  const capacitySummary = (progressionQuery.data?.inventory_capacity_summary ?? {}) as Record<string, number>;
  const purchasedCount = Number(summary.purchased_upgrades_count ?? 0);

  if (!saveId) return <EmptyState title="No save selected" body="Open or create a save game before using shop upgrades." />;
  if (progressionQuery.isLoading || upgradesQuery.isLoading) return <LoadingState />;
  if (progressionQuery.isError) return <ErrorState message={(progressionQuery.error as Error).message} />;
  if (upgradesQuery.isError) return <ErrorState message={(upgradesQuery.error as Error).message} />;
  if (!progressionQuery.data || !upgradesQuery.data) return null;

  const handlePurchase = async (upgradeKey: string) => {
    const upgrade = upgradesQuery.data?.find((item) => item.key === upgradeKey);
    if (!upgrade) return;
    const confirmed = window.confirm(`Confirm blueprint purchase: ${upgrade.title} for ${formatVnd(upgrade.cost_vnd)}?`);
    if (!confirmed) return;
    try {
      const response = await purchaseMutation.mutateAsync(upgradeKey);
      setFeedback(`UPGRADE INSTALLED: ${response.upgrade.upgrade_key}. FUNDS SECURED: -${formatVnd(Math.abs(response.cash_delta))}.`);
    } catch (error) {
      setFeedback(`ERROR EXECUTING PURCHASE: ${(error as Error).message}`);
    }
  };

  return (
    <section className="space-y-4">
      {/* Header and Telemetry */}
      <ConsolePanel variant="z-1" className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <SectionHeader title="Upgrade Board" subtitle="STATION-10 // FACILITY BLUEPRINTS" />
          <div className="font-mono text-[10px] text-slate-500 mt-1 uppercase">
            STATUS: <span className="text-[#00f2ff] font-bold">SCHEMATICS LOADED</span> // REVISION: v4.8
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-[10px] uppercase shrink-0">
          <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
            <span className="text-slate-500 text-[8px] block tracking-wider">SHOP LEVEL</span>
            <span className="text-emerald-400 font-bold text-xs">{progressionQuery.data.shop_level}</span>
          </div>
          <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
            <span className="text-slate-500 text-[8px] block tracking-wider">AVAILABLE FUNDS</span>
            <span className="text-[#00f2ff] font-bold text-xs">{formatVnd(progressionQuery.data.cash)}</span>
          </div>
          <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
            <span className="text-slate-500 text-[8px] block tracking-wider">INSTALLED BLUEPRINTS</span>
            <span className="text-[#ffba20] font-bold text-xs">{purchasedCount}</span>
          </div>
          <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
            <span className="text-slate-500 text-[8px] block tracking-wider">STORAGE CAPACITY</span>
            <span className="text-white font-bold text-xs">{capacitySummary.total_capacity ?? 50} UNITS</span>
          </div>
        </div>
      </ConsolePanel>

      {feedback && (
        <div className="border border-[#00f2ff]/20 bg-[#00f2ff]/5 p-3 font-mono text-xs text-[#00f2ff] uppercase">
          {feedback}
        </div>
      )}

      <div className="grid gap-4 xl:grid-cols-[1.4fr_0.9fr]">
        <div className="space-y-4">
          <ConsolePanel variant="z-1" className="p-4 space-y-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-white/5 pb-3">
              <h2 className="text-xs font-bold font-mono text-white uppercase tracking-wider">Upgrade schematics Catalog</h2>
              <div className="flex flex-wrap gap-1.5">
                {categories.map((category) => (
                  <button
                    key={category}
                    className={`border px-2.5 py-1 font-mono text-[9px] uppercase tracking-wider transition ${
                      selectedCategory === category
                        ? "bg-[#00f2ff] border-[#00f2ff] text-slate-950 font-bold"
                        : "bg-white/5 border-white/10 text-slate-400 hover:bg-white/10 hover:text-white"
                    }`}
                    onClick={() => setSelectedCategory(category)}
                    type="button"
                  >
                    {category}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-2 max-h-[650px] overflow-y-auto console-scrollbar pr-1">
              {filteredUpgrades.map((upgrade) => (
                <UpgradeCard
                  key={upgrade.key}
                  busy={purchaseMutation.isPending}
                  cash={progressionQuery.data.cash}
                  onPurchase={handlePurchase}
                  upgrade={upgrade}
                />
              ))}
            </div>
          </ConsolePanel>
        </div>

        <div className="space-y-4">
          <ConsolePanel variant="z-1" className="p-4 space-y-3">
            <h2 className="text-xs font-bold font-mono text-white uppercase tracking-wider border-b border-white/5 pb-2">Active Effect Modifiers</h2>
            {effectEntries.length === 0 ? (
              <p className="font-mono text-xs text-slate-500 uppercase">No active upgrades detected.</p>
            ) : (
              <div className="flex flex-wrap gap-1.5">
                {effectEntries.map(([key, value]) => (
                  <span key={key} className="border border-[#00f2ff]/20 bg-[#00f2ff]/5 px-2 py-1 text-[10px] font-mono text-sky-200">
                    [{prettyKey(key)}: {String(value)}]
                  </span>
                ))}
              </div>
            )}
          </ConsolePanel>

          <ConsolePanel variant="z-1" className="p-4 space-y-3">
            <h2 className="text-xs font-bold font-mono text-white uppercase tracking-wider border-b border-white/5 pb-2">Target Recommendations</h2>
            <div className="bg-[#0c0e11] border border-white/5 p-3 rounded-none font-mono text-xs text-[#ffba20]">
              <span className="text-slate-500 block text-[8px] mb-1">RECOMMENDED ACQUISITION</span>
              {String(summary.next_recommended_upgrade_title ?? "Buy the cheapest available upgrade that fits your current shop level.")}
            </div>
          </ConsolePanel>

          <ConsolePanel variant="z-1" className="p-4 space-y-3">
            <h2 className="text-xs font-bold font-mono text-white uppercase tracking-wider border-b border-white/5 pb-2">Blueprint Install History</h2>
            {progressionQuery.data.purchased_upgrades.length === 0 ? (
              <p className="font-mono text-xs text-slate-500 uppercase">Nothing installed yet.</p>
            ) : (
              <div className="space-y-2 max-h-[300px] overflow-y-auto console-scrollbar pr-1">
                {progressionQuery.data.purchased_upgrades.map((upgrade) => (
                  <div key={upgrade.id} className="bg-[#0c0e11]/80 border border-white/5 p-3 rounded-none font-mono text-xs">
                    <div className="flex items-center justify-between gap-3">
                      <span className="font-bold text-white uppercase">{upgrade.upgrade_key}</span>
                      <span className="text-[#00f2ff] font-bold">LVL {upgrade.level}</span>
                    </div>
                    <div className="mt-2 flex items-center justify-between text-[9px] text-slate-500">
                      <span>COST RECONCILED</span>
                      <span>{formatVnd(upgrade.cost_paid_vnd)}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </ConsolePanel>
        </div>
      </div>
    </section>
  );
}
