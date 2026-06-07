import { FormEvent, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Wrench, Search, ShieldAlert, Terminal as TermIcon } from "lucide-react";

import { useCreateInventoryUnit, useHardwareProducts, useInventory, useRunInventoryTest, useProgression } from "../api/hooks";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { InventoryUnitCard } from "../components/InventoryUnitCard";
import { LoadingState } from "../components/LoadingState";
import { useGameStore } from "../store/gameStore";

import { ConsolePanel } from "../components/ui/ConsolePanel";
import { StatusChip } from "../components/ui/StatusChip";
import { ActionButton } from "../components/ui/ActionButton";
import { SectionHeader } from "../components/ui/SectionHeader";
import { MetricPill } from "../components/ui/MetricPill";
import { tutorialHighlight, tutorialTooltip } from "../utils/tutorial";

export function InventoryPage() {
  const saveId = useGameStore((state) => state.selectedSaveId);
  const inventory = useInventory(saveId);
  const products = useHardwareProducts();
  const createUnit = useCreateInventoryUnit(saveId);
  const runTest = useRunInventoryTest(saveId);
  const progression = useProgression(saveId);
  const tutorialMode = useGameStore((state) => state.tutorialMode);
  const tutorialStep = useGameStore((state) => state.tutorialStep);

  const [productId, setProductId] = useState<number | null>(null);
  const [filter, setFilter] = useState<"ALL" | "NEW" | "USED" | "UNTESTED" | "REFURBISHED" | "DEFECTIVE">("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [logs, setLogs] = useState<string[]>([
    "SYS: Manifest initialized.",
    "INVENTORY: Connected to central storage database.",
    "SYS_OP: Active monitoring online."
  ]);

  const selectableProducts = useMemo(() => products.data ?? [], [products.data]);

  // Log function helper
  const addLog = (message: string) => {
    const time = new Date().toLocaleTimeString();
    setLogs((prev) => [...prev.slice(-15), `[${time}] ${message}`]);
  };

  async function handleCreateUsed(event: FormEvent) {
    event.preventDefault();
    const id = productId ?? selectableProducts[0]?.id;
    if (!id) return;
    const selectedProd = selectableProducts.find((p) => p.id === id);
    addLog(`PROCUREMENT: Initializing manual intake for '${selectedProd?.name}'...`);
    try {
      await createUnit.mutateAsync({
        product_id: id,
        condition_type: "USED",
        source: "USED_MARKET",
        purchase_price_vnd: 1_500_000,
        notes: "Manual used-market intake.",
      });
      addLog(`SYS: Successfully added manual intake for '${selectedProd?.name}'.`);
    } catch (err) {
      addLog(`ERROR: Intake failed: ${(err as Error).message}`);
    }
  }

  async function handleRunTest(unitId: number, action: string) {
    const unit = inventory.data?.find((u) => u.id === unitId);
    addLog(`TEST: Triggered '${action.toUpperCase()}' on #${unitId} (${unit?.product.name})...`);
    try {
      await runTest.mutateAsync({ unitId, action });
      addLog(`SYS: Passed test '${action.toUpperCase()}' on #${unitId}.`);
    } catch (err) {
      addLog(`ERROR: Test failed on #${unitId}: ${(err as Error).message}`);
    }
  }

  // Filter application
  const filteredInventory = useMemo(() => {
    if (!inventory.data) return [];
    return inventory.data.filter((unit) => {
      const matchesSearch =
        unit.product.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        unit.product.brand.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (unit.serial_number && unit.serial_number.toLowerCase().includes(searchQuery.toLowerCase()));

      if (!matchesSearch) return false;

      if (filter === "ALL") return true;
      if (filter === "NEW") return unit.condition_type === "NEW";
      if (filter === "USED") return unit.condition_type === "USED";
      if (filter === "UNTESTED") return unit.status === "UNTESTED";
      if (filter === "REFURBISHED") return unit.refurbish_count > 0 || unit.status === "REFURBISHED";
      if (filter === "DEFECTIVE") return unit.status === "DEFECTIVE";
      return true;
    });
  }, [inventory.data, filter, searchQuery]);

  // Risk and warning alerts
  const riskAlerts = useMemo(() => {
    if (!inventory.data) return [];
    return inventory.data.filter(
      (u) => u.status === "DEFECTIVE" || u.warranty_risk === "HIGH" || u.warranty_risk === "CRITICAL"
    );
  }, [inventory.data]);

  const capacitySummary = (progression.data?.inventory_capacity_summary ?? {}) as Record<string, number>;
  const totalCapacity = capacitySummary.total_capacity ?? 50;
  const currentCount = inventory.data?.length ?? 0;
  const percent = Math.min(100, Math.max(0, (currentCount / totalCapacity) * 100));
  const filledSegments = Math.round(percent / 10);

  if (!saveId) return <EmptyState title="No save selected" body="Open a save before managing inventory." />;

  return (
    <section className="space-y-4">
      {/* Top Header section */}
      <ConsolePanel variant="z-1" className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <SectionHeader title="Warehouse Manifest" subtitle="STATION-01 // WAREHOUSE" />
          <div className="font-mono text-[10px] text-slate-500 mt-1 uppercase">
            STATUS: <span className="text-[#00f2ff] font-bold">ONLINE</span> // SYS_OP: NORMAL
          </div>
        </div>

        {/* Capacity telemetry */}
        <div className={`w-full md:w-80 flex flex-col gap-1.5 ${tutorialHighlight(tutorialMode && tutorialStep >= 3)}`}>
          <div className="flex justify-between items-center font-mono text-[10px] uppercase">
            <span className="text-slate-400">Inventory Capacity</span>
            <span className="text-[#ffba20] font-bold">
              ({currentCount}/{totalCapacity}) Units
            </span>
          </div>
          <div className="flex gap-[3px] h-2 bg-[#0c0e11] p-[2px] border border-white/5 rounded-none">
            {Array.from({ length: 10 }).map((_, idx) => {
              const isFilled = idx < filledSegments;
              return (
                <div
                  key={idx}
                  className={`flex-1 h-full transition-all ${
                    isFilled ? "bg-[#00f2ff] shadow-[0_0_4px_#00f2ff]" : "bg-[#141820]"
                  }`}
                />
              );
            })}
          </div>
          <div className="font-mono text-[9px] text-[#ffba20] text-right uppercase">
            {percent >= 85 ? "Warning: Approaching Full Capacity" : "Storage Space Nominal"}
          </div>
        </div>
      </ConsolePanel>

      {/* Filter and intake desk */}
      <ConsolePanel variant="z-1" className={`flex flex-wrap items-center justify-between gap-4 ${tutorialHighlight(tutorialMode && tutorialStep >= 3)}`}>
        {/* Monospace filter chips */}
        <div className="flex flex-wrap gap-1">
          {(["ALL", "NEW", "USED", "UNTESTED", "REFURBISHED", "DEFECTIVE"] as const).map((t) => (
            <button
              key={t}
              onClick={() => {
                setFilter(t);
                addLog(`FILTER: Applied manifest filter -> ${t}`);
              }}
              className={`font-mono text-[10px] uppercase px-3 py-1 border transition-all duration-150 ${
                filter === t
                  ? "bg-primary-container/20 text-primary-container border-primary-container/50 shadow-[0_0_4px_rgba(0,242,255,0.25)]"
                  : "bg-white/5 border-white/10 text-slate-400 hover:text-white hover:border-white/20"
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        {/* Action button link and manual intake form */}
        <div className="flex flex-wrap gap-3 items-center">
          <Link
            to="/refurbish"
            className={`h-10 border border-primary-container text-primary-container bg-transparent hover:bg-primary-container/10 font-mono text-xs uppercase tracking-wider px-3 flex items-center gap-1.5 transition ${tutorialHighlight(tutorialMode && tutorialStep >= 3)}`}
            title={tutorialTooltip(tutorialMode && tutorialStep >= 3, "Open refurbish bench")}
          >
            <Wrench className="h-4 w-4 text-primary-container" /> Refurbish Bench
          </Link>
          <form className="flex gap-2" onSubmit={handleCreateUsed}>
            <select
              className="h-10 max-w-[200px] border border-white/10 bg-[#0c0e11] px-3 font-mono text-xs text-white uppercase focus:outline-none focus:border-primary-container"
              onChange={(event) => setProductId(Number(event.target.value))}
              value={productId ?? selectableProducts[0]?.id ?? ""}
            >
              {selectableProducts.map((product) => (
                <option key={product.id} value={product.id}>
                  {product.name}
                </option>
              ))}
            </select>
            <ActionButton
              disabled={createUnit.isPending}
              type="submit"
              className={`!w-auto !px-4 ${tutorialHighlight(tutorialMode && tutorialStep >= 3)}`}
              title={tutorialTooltip(tutorialMode && tutorialStep >= 3, "Add used stock")}
            >
              Add Used
            </ActionButton>
          </form>
        </div>
      </ConsolePanel>

      {/* Main layout splitting catalog cards from sidebar log panels */}
      <div className="flex flex-col lg:flex-row gap-4">
        {/* Left Column: Cards manifesting hardware units */}
        <div className="flex-1 space-y-4">
          <div className="flex items-center gap-2 mb-2">
            <Search className="h-4 w-4 text-slate-500" />
            <input
              type="text"
              placeholder="SEARCH HARDWARE DATABASE..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                if (e.target.value.length === 1) {
                  addLog("QUERY: Scanned database for matches");
                }
              }}
              className="bg-transparent border-b border-white/10 focus:border-primary-container focus:outline-none font-mono text-xs text-white placeholder-slate-600 w-full max-w-md pb-1 transition-all"
            />
          </div>

          {inventory.isLoading ? <LoadingState /> : null}
          {inventory.isError ? <ErrorState message={(inventory.error as Error).message} /> : null}
          {inventory.data && filteredInventory.length === 0 ? (
            <EmptyState title="Empty Query Response" body="No active units matching the query manifest filters." />
          ) : null}

          <div className="grid gap-4">
            {filteredInventory.map((unit) => (
              <InventoryUnitCard
                key={unit.id}
                isTesting={runTest.isPending}
                onRunTest={handleRunTest}
                unit={unit}
                tutorialActive={tutorialMode && tutorialStep >= 3}
              />
            ))}
          </div>
        </div>

        {/* Right Rail: Terminal logs and telemetry warning boards */}
        <div className="w-full lg:w-80 shrink-0 space-y-4">
          {/* Warehouse Alerts Panel */}
          <ConsolePanel variant="z-1" className="flex flex-col gap-3">
            <div className="font-mono text-xs font-bold text-slate-300 border-b border-white/5 pb-2 flex items-center gap-2">
              <ShieldAlert className="h-4 w-4 text-rose-400" />
              WAREHOUSE ALERTS
            </div>
            <div className="space-y-2 max-h-60 overflow-y-auto">
              {riskAlerts.length === 0 ? (
                <div className="text-[10px] font-mono text-slate-500 uppercase">No active hardware failures.</div>
              ) : (
                riskAlerts.map((unit) => (
                  <div key={unit.id} className="border border-rose-500/20 bg-rose-500/5 p-2 rounded-sm space-y-1">
                    <div className="flex justify-between items-start">
                      <span className="font-mono text-[10px] text-white font-bold truncate pr-1">
                        {unit.product.name}
                      </span>
                      <StatusChip label={unit.status === "DEFECTIVE" ? "FAIL" : "RISK"} variant="error" />
                    </div>
                    <div className="font-mono text-[9px] text-slate-400">
                      ID: #{unit.id} // GRADE: {unit.grade} // CONFIDENCE: {unit.inspection_confidence}%
                    </div>
                  </div>
                ))
              )}
            </div>
          </ConsolePanel>

          {/* System Operations Logs */}
          <ConsolePanel variant="z-1" className="flex flex-col gap-3">
            <div className="font-mono text-xs font-bold text-slate-300 border-b border-white/5 pb-2 flex items-center gap-2">
              <TermIcon className="h-4 w-4 text-[#00f2ff]" />
              OPERATIONS LOGGER
            </div>
            <div className="bg-[#0c0e11] p-3 font-mono text-[10px] text-slate-400 h-64 overflow-y-auto space-y-1 rounded-sm border border-white/5">
              {logs.map((log, index) => (
                <div key={index} className={log.includes("ERROR") ? "text-rose-400" : log.includes("FILTER") ? "text-[#ffba20]" : "text-[#00f2ff]/80"}>
                  {log}
                </div>
              ))}
              <div className="text-white/60 animate-pulse">_ Awaiting operator input...</div>
            </div>
          </ConsolePanel>
        </div>
      </div>
    </section>
  );
}
