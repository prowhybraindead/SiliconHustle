import { useState, useMemo } from "react";
import { Wrench, ShieldAlert, DollarSign, Play, CheckCircle2, History, Sparkles, Check, AlertTriangle, ArrowRight } from "lucide-react";

import {
  useInventory,
  useStaff,
  useRefurbishActions,
  useRunRefurbishAction,
  useRefurbishEvents,
  useMarkReadyForResale,
  useUnmarkReadyForResale,
} from "../api/hooks";
import { useGameStore } from "../store/gameStore";
import { EmptyState } from "../components/EmptyState";
import { LoadingState } from "../components/LoadingState";
import { ErrorState } from "../components/ErrorState";
import { BrandLogo } from "../components/BrandLogo";
import { formatVnd, labelize } from "../utils/format";
import { MetricBar } from "../components/MetricBar";

import { ConsolePanel } from "../components/ui/ConsolePanel";
import { StatusChip } from "../components/ui/StatusChip";
import { ActionButton } from "../components/ui/ActionButton";
import { SectionHeader } from "../components/ui/SectionHeader";

export function RefurbishPage() {
  const saveId = useGameStore((state) => state.selectedSaveId);
  const inventory = useInventory(saveId);
  const staffQuery = useStaff(saveId, undefined, "AVAILABLE");
  const [selectedUnitId, setSelectedUnitId] = useState<number | null>(null);
  const [selectedStaffId, setSelectedStaffId] = useState<number | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<string>("ALL");

  // API hooks
  const actionsQuery = useRefurbishActions(saveId, selectedUnitId);
  const eventsQuery = useRefurbishEvents(saveId, selectedUnitId ?? undefined);
  const runActionMutation = useRunRefurbishAction(saveId);
  const markReadyMutation = useMarkReadyForResale(saveId);
  const unmarkReadyMutation = useUnmarkReadyForResale(saveId);

  // Filter inventory items to show only USED, UNTESTED, tested used items eligible for refurbishing
  const refurbishQueue = useMemo(() => {
    if (!inventory.data) return [];
    return inventory.data.filter((unit) => {
      // Exclude SOLD, INSTALLED_IN_BUILD, RESERVED
      const isUnavailable = ["SOLD", "INSTALLED_IN_BUILD", "RESERVED"].includes(unit.status);
      if (isUnavailable) return false;

      // Filter by category if selected
      if (categoryFilter !== "ALL" && unit.product.category !== categoryFilter) {
        return false;
      }
      return true;
    });
  }, [inventory.data, categoryFilter]);

  const selectedUnit = useMemo(() => {
    if (!inventory.data || selectedUnitId === null) return null;
    return inventory.data.find((unit) => unit.id === selectedUnitId) || null;
  }, [inventory.data, selectedUnitId]);

  // Categories list for filtering
  const categories = useMemo(() => {
    if (!inventory.data) return ["ALL"];
    const cats = new Set(inventory.data.map((u) => u.product.category));
    return ["ALL", ...Array.from(cats)];
  }, [inventory.data]);

  const stats = useMemo(() => {
    if (!inventory.data) return { queue: 0, refurbished: 0, readyResale: 0, avgRisk: 0 };
    const queue = refurbishQueue.length;
    const refurbished = inventory.data.filter((u) => u.refurbish_count > 0).length;
    const readyResale = inventory.data.filter((u) => u.ready_for_resale).length;
    const unitsWithRisk = inventory.data.filter((u) => u.repair_risk_score !== null);
    const avgRisk = unitsWithRisk.length > 0
      ? Math.round(unitsWithRisk.reduce((acc, u) => acc + (u.repair_risk_score ?? 0), 0) / unitsWithRisk.length)
      : 0;
    return { queue, refurbished, readyResale, avgRisk };
  }, [inventory.data, refurbishQueue]);

  const handleRunAction = async (actionType: string) => {
    if (selectedUnitId === null) return;
    try {
      await runActionMutation.mutateAsync({
        inventoryUnitId: selectedUnitId,
        actionType,
        staffId: selectedStaffId ?? undefined,
      });
      // Refresh available actions and events
      actionsQuery.refetch();
      eventsQuery.refetch();
    } catch (err: unknown) {
      console.error(err);
    }
  };

  const handleToggleReadyForResale = async () => {
    if (!selectedUnit) return;
    try {
      if (selectedUnit.ready_for_resale) {
        await unmarkReadyMutation.mutateAsync(selectedUnit.id);
      } else {
        await markReadyMutation.mutateAsync(selectedUnit.id);
      }
      // Refresh actions
      actionsQuery.refetch();
    } catch (err: unknown) {
      console.error(err);
    }
  };

  if (!saveId) {
    return <EmptyState title="No save selected" body="Open a save game before accessing the Refurbish workbench." />;
  }

  return (
    <section className="space-y-4">
      {/* Station Header with Telemetry */}
      <ConsolePanel variant="z-1" className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <SectionHeader title="Refurbish Bench / Repair Station" subtitle="STATION-04 // WORKBENCH" />
          <div className="font-mono text-[10px] text-slate-500 mt-1 uppercase">
            ACTIVE REPAIR PIPELINE // HARDWARE INTEGRITY RESTORATION
          </div>
        </div>
        
        {/* Telemetry panel */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-[10px] uppercase shrink-0">
          <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
            <span className="text-slate-500 text-[8px] block tracking-wider">QUEUE</span>
            <span className="text-white font-bold text-xs">{stats.queue} UNITS</span>
          </div>
          <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
            <span className="text-slate-500 text-[8px] block tracking-wider">REFURBISHED</span>
            <span className="text-[#00f2ff] font-bold text-xs">{stats.refurbished}</span>
          </div>
          <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
            <span className="text-slate-500 text-[8px] block tracking-wider">READY RESALE</span>
            <span className="text-emerald-400 font-bold text-xs">{stats.readyResale}</span>
          </div>
          <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
            <span className="text-slate-500 text-[8px] block tracking-wider">AVG RISK</span>
            <span className={`font-bold text-xs ${stats.avgRisk > 55 ? 'text-rose-400' : 'text-slate-300'}`}>{stats.avgRisk}%</span>
          </div>
        </div>
      </ConsolePanel>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        {/* Left Side: Queue List */}
        <div className="space-y-3 lg:col-span-4 flex flex-col">
          <ConsolePanel variant="z-1" className="space-y-3">
            <div className="font-mono text-xs font-bold text-slate-300 uppercase tracking-wider">Intake Queue Filter</div>
            <select
              className="w-full h-9 border border-white/10 bg-[#0c0e11] px-2 font-mono text-xs text-white uppercase focus:outline-none focus:border-primary-container"
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
            >
              {categories.map((cat) => (
                <option key={cat} value={cat}>
                  {cat === "ALL" ? "All Categories" : labelize(cat)}
                </option>
              ))}
            </select>
          </ConsolePanel>

          <div className="max-h-[600px] overflow-y-auto space-y-2 pr-1 flex-1">
            {inventory.isLoading && <LoadingState />}
            {inventory.isError && <ErrorState message={(inventory.error as Error).message} />}
            {!inventory.isLoading && refurbishQueue.length === 0 && (
              <ConsolePanel variant="z-1" className="text-center text-slate-500 font-mono text-xs">
                No items in refurbish queue matching filter.
              </ConsolePanel>
            )}

            {refurbishQueue.map((unit) => {
              const isSelected = unit.id === selectedUnitId;
              const isDefective = unit.status === "DEFECTIVE";

              return (
                <div
                  key={unit.id}
                  onClick={() => setSelectedUnitId(unit.id)}
                  className={`border transition-all duration-150 p-3 cursor-pointer flex items-center justify-between ${
                    isSelected
                      ? "border-[#00f2ff] bg-primary-container/5 shadow-[0_0_8px_rgba(0,242,255,0.15)]"
                      : "border-white/5 bg-[#0e1115]/50 hover:border-white/10 hover:bg-[#0e1115]"
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <BrandLogo
                      brand={unit.product.brand_ref}
                      logoUrl={unit.product.effective_logo_url}
                      name={unit.product.brand}
                      size="sm"
                    />
                    <div className="min-w-0">
                      <h4 className="text-xs font-semibold text-white font-mono truncate">{unit.product.name}</h4>
                      <p className="font-mono text-[9px] text-slate-400 mt-0.5 uppercase">
                        GRADE {labelize(unit.grade)} • {unit.product.category}
                      </p>
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-1.5 shrink-0">
                    <StatusChip
                      label={unit.ready_for_resale ? "READY RESALE" : unit.status}
                      variant={
                        unit.ready_for_resale
                          ? "success"
                          : isDefective
                          ? "error"
                          : unit.status === "REFURBISHED"
                          ? "success"
                          : "neutral"
                      }
                      className="!text-[8px] !px-1.5"
                    />
                    <span className="text-[10px] font-mono text-slate-400 font-bold">
                      {formatVnd(unit.resale_value_estimate_vnd ?? unit.purchase_price_vnd)}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Side: Workbench Details */}
        <div className="lg:col-span-8 space-y-4">
          {selectedUnit ? (
            <div className="space-y-4">
              {/* Item Overview & Stats */}
              <ConsolePanel variant="z-1" className="space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                  <div className="flex items-start gap-4">
                    <BrandLogo
                      brand={selectedUnit.product.brand_ref}
                      logoUrl={selectedUnit.product.effective_logo_url}
                      name={selectedUnit.product.brand}
                      size="lg"
                    />
                    <div>
                      <h2 className="text-base font-bold text-white font-mono">{selectedUnit.product.name}</h2>
                      <div className="flex flex-wrap gap-2 mt-1.5 items-center">
                        <span className="text-[10px] font-mono text-slate-400 uppercase">SN: {selectedUnit.serial_number ?? "No Serial"}</span>
                        <StatusChip label={selectedUnit.condition_type} variant={selectedUnit.condition_type === "NEW" ? "success" : "warning"} />
                        <StatusChip label={selectedUnit.status} variant={selectedUnit.status === "DEFECTIVE" ? "error" : "success"} />
                        {selectedUnit.ready_for_resale && (
                          <StatusChip label="READY FOR RESALE" variant="success" />
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-col sm:items-end gap-2 shrink-0 font-mono">
                    <div className="text-[11px] text-slate-400 uppercase">
                      Est. Resale:{" "}
                      <span className="text-xs font-bold text-[#ffba20]">
                        {formatVnd(selectedUnit.resale_value_estimate_vnd)}
                      </span>
                    </div>
                    <div className="text-[9px] text-slate-500 uppercase">
                      Intake Cost: {formatVnd(selectedUnit.purchase_price_vnd)}
                    </div>
                    <ActionButton
                      onClick={handleToggleReadyForResale}
                      disabled={markReadyMutation.isPending || unmarkReadyMutation.isPending}
                      variant={selectedUnit.ready_for_resale ? "danger" : "primary"}
                      className="!h-9 !w-auto !px-3 font-mono text-[10px]"
                      title={
                        !selectedUnit.ready_for_resale && selectedUnit.inspection_confidence < 60
                          ? "Requires at least 60% inspection confidence"
                          : ""
                      }
                    >
                      {selectedUnit.ready_for_resale ? (
                        <>Cancel Resale Ready</>
                      ) : (
                        <>
                          <CheckCircle2 className="h-4 w-4 text-on-primary-fixed" /> Set Ready for Resale
                        </>
                      )}
                    </ActionButton>
                    {!selectedUnit.ready_for_resale && selectedUnit.inspection_confidence < 60 && (
                      <span className="text-[9px] text-rose-400 uppercase">Requires ≥60% Inspection Confidence (Currently {selectedUnit.inspection_confidence}%)</span>
                    )}
                  </div>
                </div>

                <div className="border-t border-white/5 pt-4">
                  <h3 className="text-[10px] font-bold text-slate-400 font-mono uppercase tracking-wider mb-3">Known Hardware Metrics</h3>
                  <div className="grid gap-4 grid-cols-2 md:grid-cols-3">
                    <MetricBar label="Health" value={selectedUnit.health_score} />
                    <MetricBar label="Thermal" value={selectedUnit.thermal_score} />
                    <MetricBar label="Fan Score" value={selectedUnit.fan_score} />
                    <MetricBar label="VRAM Score" value={selectedUnit.vram_score} />
                    <MetricBar label="Stability" value={selectedUnit.stability_score} />
                    <div className="space-y-1 font-mono text-[10px] uppercase">
                      <div className="text-slate-500 tracking-wider">Repair Risk</div>
                      <div className="flex items-center gap-1.5 h-6">
                        <ShieldAlert className={`h-4 w-4 ${selectedUnit.repair_risk_score && selectedUnit.repair_risk_score > 50 ? 'text-rose-400' : 'text-slate-500'}`} />
                        <span className="text-xs font-bold text-white">
                          {selectedUnit.repair_risk_score !== null ? `${selectedUnit.repair_risk_score}%` : "UNKNOWN"}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="mt-4 flex gap-4 text-[10px] font-mono text-slate-500 bg-[#0c0e11] rounded-none p-2.5 border border-white/5 uppercase">
                    <div>Refurbish Count: <span className="font-semibold text-slate-300">{selectedUnit.refurbish_count}</span></div>
                    <div>Inspection Confidence: <span className="font-semibold text-slate-300">{selectedUnit.inspection_confidence}%</span></div>
                    <div>Visual Grade: <span className="font-semibold text-[#ffba20]">{labelize(selectedUnit.grade)}</span></div>
                  </div>
                </div>
              </ConsolePanel>

              {/* Action Selection Board */}
              <ConsolePanel variant="z-1" className="space-y-4">
                <h3 className="text-xs font-bold text-white font-mono flex items-center gap-2 uppercase">
                  <Wrench className="h-4 w-4 text-[#ffba20]" /> Select Refurbish Repair Verb
                </h3>

                <div className="grid gap-2 sm:grid-cols-[1fr_auto] sm:items-center border border-white/5 bg-[#0c0e11] p-3">
                  <label className="text-[10px] font-mono uppercase text-slate-400">Optional Support Tech Assignment</label>
                  <select
                    className="h-9 border border-white/10 bg-[#0c0e11] px-2 font-mono text-xs text-white focus:outline-none focus:border-primary-container"
                    value={selectedStaffId ?? ""}
                    onChange={(event) => setSelectedStaffId(event.target.value ? Number(event.target.value) : null)}
                  >
                    <option value="">No Technician support</option>
                    {(staffQuery.data ?? []).map((member) => (
                      <option key={member.id} value={member.id}>
                        {member.name} · {member.role}
                      </option>
                    ))}
                  </select>
                </div>

                {actionsQuery.isLoading && <div className="text-xs font-mono text-slate-400">Loading actions...</div>}
                {actionsQuery.isError && <div className="text-xs font-mono text-rose-400">Error loading repair verbs.</div>}

                {actionsQuery.data && (
                  <div className="grid gap-3 grid-cols-1 md:grid-cols-2">
                    {actionsQuery.data.map((action) => {
                      const isPending = runActionMutation.isPending;
                      return (
                        <div
                          key={action.action_type}
                          className={`flex flex-col justify-between border p-3 bg-[#0c0e11]/30 transition ${
                            action.applicable
                              ? "border-white/5 hover:border-white/10 hover:bg-[#0c0e11]"
                              : "border-white/5 opacity-40"
                          }`}
                        >
                          <div>
                            <div className="flex items-center justify-between">
                              <h4 className="text-xs font-bold text-white font-mono uppercase">{labelize(action.action_type)}</h4>
                              <StatusChip
                                label={action.applicable ? "APPLICABLE" : "BLOCKED"}
                                variant={action.applicable ? "success" : "neutral"}
                                className="!text-[8px] !px-1.5"
                              />
                            </div>
                            <p className="text-[10px] font-mono text-slate-400 mt-1 uppercase">
                              COST: <span className="font-semibold text-slate-300">{formatVnd(action.cost_vnd)}</span>
                              {action.duration_days > 0 && ` • TIME: ${action.duration_days} DAY(S)`}
                            </p>
                            {!action.applicable && action.unavailable_reason && (
                              <div className="mt-2 text-[9px] font-mono text-rose-400 flex items-center gap-1">
                                <AlertTriangle className="h-3 w-3 shrink-0 text-rose-400" />
                                <span>{action.unavailable_reason}</span>
                              </div>
                            )}
                          </div>
                          <div className="mt-3 flex justify-end">
                            <ActionButton
                              disabled={!action.applicable || isPending}
                              onClick={() => handleRunAction(action.action_type)}
                              className="!h-8 !w-auto !px-3 font-mono text-[10px]"
                            >
                              <Play className="h-3 w-3 text-on-primary-fixed" /> EXECUTE
                            </ActionButton>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </ConsolePanel>

              {/* Event History Logs */}
              <ConsolePanel variant="z-1" className="space-y-4">
                <h3 className="text-xs font-bold text-white font-mono flex items-center gap-2 uppercase">
                  <History className="h-4 w-4 text-primary-container" /> Workbench Operations Log
                </h3>

                {eventsQuery.isLoading && <div className="text-xs font-mono text-slate-400">Loading history logs...</div>}
                {eventsQuery.data && eventsQuery.data.length === 0 && (
                  <div className="text-xs font-mono text-slate-500 py-3 text-center uppercase">No operations history recorded for this unit.</div>
                )}

                {eventsQuery.data && eventsQuery.data.length > 0 && (
                  <div className="bg-[#0c0e11] p-3 font-mono text-[10px] text-slate-400 max-h-60 overflow-y-auto space-y-2 rounded-sm border border-white/5">
                    {eventsQuery.data.map((event) => (
                      <div key={event.id} className="border-b border-white/5 pb-2 last:border-0 last:pb-0 space-y-1">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Sparkles className="h-3 w-3 text-primary-container" />
                            <h4 className="font-bold text-white uppercase">{labelize(event.action_type)}</h4>
                          </div>
                          <div className="flex items-center gap-2 text-[9px]">
                            <span>
                              {new Date(event.created_at).toLocaleDateString()}
                            </span>
                            <StatusChip label={event.status} variant={event.status === "COMPLETED" ? "success" : "error"} className="!text-[8px]" />
                          </div>
                        </div>
                        <p className="text-slate-300 italic">"{event.summary}"</p>
                        <div className="flex flex-wrap gap-2 text-[8px] text-slate-500 pt-1">
                          <div>COST: {formatVnd(event.cost_vnd)}</div>
                          <div>GRADE: {event.before_grade} → {event.after_grade}</div>
                          {event.health_delta !== 0 && (
                            <div className="text-primary-container">HEALTH: +{event.health_delta}</div>
                          )}
                          {event.thermal_delta !== 0 && (
                            <div className="text-primary-container">THERMAL: +{event.thermal_delta}</div>
                          )}
                          {event.fan_delta !== 0 && (
                            <div className="text-primary-container">FAN: +{event.fan_delta}</div>
                          )}
                          {event.resale_value_delta_vnd !== null && event.resale_value_delta_vnd !== 0 && (
                            <div className="text-emerald-400">
                              VALUE: +{formatVnd(event.resale_value_delta_vnd)}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </ConsolePanel>
            </div>
          ) : (
            <div className="panel p-10 text-center flex flex-col items-center justify-center min-h-[400px] border border-dashed border-white/10 bg-[#0e1115]/20">
              <Wrench className="h-12 w-12 text-slate-600 mb-4 animate-pulse" />
              <h3 className="text-sm font-semibold text-slate-300 font-mono uppercase mb-1">No Unit Selected</h3>
              <p className="text-xs text-slate-500 max-w-sm font-mono uppercase">
                Select an intake part from the queue list on the left to begin cleaning, inspection, parts replacement, or stress testing.
              </p>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
