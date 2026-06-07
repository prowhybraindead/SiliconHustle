import { Link } from "react-router-dom";

import { useDashboardState, useFxRates, useProgression } from "../api/hooks";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { useGameStore } from "../store/gameStore";
import type { ExchangeRate } from "../types/game";
import { translateUiText } from "../utils/format";

import { ConsolePanel } from "../components/ui/ConsolePanel";
import { MetricPill } from "../components/ui/MetricPill";
import { StatusChip } from "../components/ui/StatusChip";
import { ActionButton } from "../components/ui/ActionButton";
import { ShowroomFloorMonitor } from "../components/ShowroomFloorMonitor";
import { LiveOpsFeed } from "../components/LiveOpsFeed";

function FxDashboardStatus() {
  const ratesQuery = useFxRates("USD", "VND");
  if (ratesQuery.isLoading || ratesQuery.isError || !ratesQuery.data) return null;

  const rawRate = ratesQuery.data;
  const rate: ExchangeRate | undefined = Array.isArray(rawRate) ? rawRate[0] : rawRate;
  if (!rate) return null;

  return (
    <Link
      to="/currency"
      className="flex items-center gap-2 border border-white/10 bg-[#090b0e] p-2 hover:border-primary-container/40 transition select-none"
    >
      <span className="font-mono text-[9px] text-outline uppercase">FX RATE:</span>
      <span className="font-mono text-[10px] font-bold text-on-surface">1 USD = {Number(rate.rate).toLocaleString()} VND</span>
      {rate.is_fallback ? (
        <span className="font-mono text-[9px] text-rose-400 bg-rose-500/10 px-1 border border-rose-500/20">OFFLINE</span>
      ) : (
        <span className="font-mono text-[9px] text-[#00f2ff] bg-[#00f2ff]/10 px-1 border border-[#00f2ff]/20">LIVE</span>
      )}
    </Link>
  );
}

export function DashboardPage() {
  const saveId = useGameStore((state) => state.selectedSaveId);
  const state = useDashboardState(saveId);
  const progression = useProgression(saveId);
  
  const progressionSummary = (progression.data?.summary ?? {}) as Record<string, unknown>;
  const capacitySummary = (progression.data?.inventory_capacity_summary ?? {}) as Record<string, number>;

  if (!saveId) return <EmptyState title="No save selected" body="Open or create a save game from the home screen." />;
  if (state.isLoading) return <LoadingState />;
  if (state.isError) return <ErrorState message={(state.error as Error).message} />;
  
  const dashboard = state.data;
  if (!dashboard) return null;
  const staffSummary = dashboard.staff_summary;

  const shopLevel = progression.data?.shop_level ?? 1;

  return (
    <section className="space-y-4">
      {/* Header section */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 mb-2 select-none">
        <div>
          <span className="font-mono text-[10px] text-primary-container tracking-widest uppercase block mb-1">
            {translateUiText("SHOWROOM COMMAND CENTER // SYSTEM ONLINE")}
          </span>
          <h1 className="font-sans text-2xl font-black text-on-surface uppercase tracking-tighter">
            {dashboard.save_game.name}
          </h1>
        </div>
        <div className="flex items-center gap-3">
          <FxDashboardStatus />
        </div>
      </div>

      {/* Persistent Status Strip Telemetry */}
      <div className="grid gap-2 grid-cols-2 lg:grid-cols-4">
        <MetricPill label={translateUiText("FUNDS TELEMETRY")} value={`₫${dashboard.cash.toLocaleString()}`} />
        <MetricPill label={translateUiText("SHOWROOM REPUTATION")} value={`${dashboard.reputation}%`} />
        <MetricPill
          label={translateUiText("ESTIMATED PENDING REV")}
          value={`₫${(dashboard.order_fulfillment_summary.estimated_pending_revenue ?? 0).toLocaleString()}`}
        />
        <MetricPill label={translateUiText("ACTIVE RMA CLAIMS")} value={dashboard.warranty_summary.open_warranty_claims ?? 0} />
      </div>

      {/* Facility Progression panel */}
      {progression.data && (
        <ConsolePanel variant="z-1" className="space-y-3 font-mono text-[11px]">
          <div className="flex justify-between items-center border-b border-white/10 pb-2">
            <span className="text-[10px] uppercase text-outline">{translateUiText("FACILITY PROGRESSION LOG")}</span>
            <Link to="/progression" className="text-[10px] text-primary-container hover:underline">
              [UPGRADES]
            </Link>
          </div>
          <div className="grid gap-2 grid-cols-2 lg:grid-cols-4">
            <div className="bg-[#090b0e] border border-white/5 p-2">
              <span className="text-[9px] text-outline block">{translateUiText("OPERATIONS LEVEL")}</span>
              <span className="text-sm font-bold text-on-surface">LVL {progression.data.shop_level}</span>
            </div>
            <div className="bg-[#090b0e] border border-white/5 p-2">
              <span className="text-[9px] text-outline block">{translateUiText("ACCUMULATED XP")}</span>
              <span className="text-sm font-bold text-on-surface">{progression.data.shop_xp} XP</span>
            </div>
            <div className="bg-[#090b0e] border border-white/5 p-2">
              <span className="text-[9px] text-outline block">{translateUiText("ACQUIRED UPGRADES")}</span>
              <span className="text-sm font-bold text-[#00f2ff]">{Number(progressionSummary.purchased_upgrades_count ?? 0)} modules</span>
            </div>
            <div className="bg-[#090b0e] border border-white/5 p-2">
              <span className="text-[9px] text-outline block">{translateUiText("INVENTORY CAPACITY")}</span>
              <span className="text-sm font-bold text-[#ffba20]">
                {dashboard.inventory_summary.total ?? 0} / {capacitySummary.total_capacity ?? 50} units
              </span>
            </div>
          </div>
          <div className="bg-[#080a0d] border border-white/5 p-2 text-[10px] text-outline">
            <span className="text-outline/40">{translateUiText("RECOMMENDED FACILITY DEPLOYMENT")}: </span>
            <span className="font-bold text-on-surface uppercase">
              {String(progressionSummary.next_recommended_upgrade_title ?? "None detected")}
            </span>
          </div>
        </ConsolePanel>
      )}

      {/* Main interactive grid */}
      <div className="grid gap-4 xl:grid-cols-[1.5fr_1fr]">
        {/* Left Column: Floor Schematic and Active stats */}
        <div className="space-y-4">
          <div className="space-y-2">
            <div className="flex justify-between items-center select-none">
              <span className="font-mono text-[10px] uppercase tracking-wider text-outline">
                {translateUiText("SHOWROOM FLOORS MONITOR // TELEMETRY LINKED")}
              </span>
              <StatusChip label="ONLINE" variant="success" />
            </div>
            <ShowroomFloorMonitor dashboardData={dashboard} shopLevel={shopLevel} />
          </div>

          {/* Active Statistics grid */}
          <ConsolePanel variant="z-1" className="space-y-3 font-mono text-[11px]">
            <div className="flex justify-between items-center border-b border-white/10 pb-2">
              <span className="text-[10px] uppercase text-outline">{translateUiText("ACTIVE OPERATIONS LOG")}</span>
              <Link to="/operations" className="text-[10px] text-primary-container hover:underline">
                [WORKFLOW]
              </Link>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              <div className="bg-[#090b0e] border border-white/5 p-2">
                <span className="text-[9px] text-outline block">{translateUiText("UNTESTED STOCK")}</span>
                <span className="text-xs font-bold text-[#ffba20]">{dashboard.inventory_summary.untested ?? 0} items</span>
              </div>
              <div className="bg-[#090b0e] border border-white/5 p-2">
                <span className="text-[9px] text-outline block">{translateUiText("ACTIVE ORDERS")}</span>
                <span className="text-xs font-bold text-[#00f2ff]">{dashboard.active_orders.length} units</span>
              </div>
              <div className="bg-[#090b0e] border border-white/5 p-2">
                <span className="text-[9px] text-outline block">{translateUiText("BUILD QUEUE")}</span>
                <span className="text-xs font-bold text-on-surface">
                  {dashboard.order_fulfillment_summary.orders_in_progress ?? 0} builds
                </span>
              </div>
              <div className="bg-[#090b0e] border border-white/5 p-2">
                <span className="text-[9px] text-outline block">{translateUiText("TEST BENCH")}</span>
                <span className="text-xs font-bold text-on-surface">
                  {dashboard.order_fulfillment_summary.orders_in_testing ?? 0} rigs
                </span>
              </div>
              <div className="bg-[#090b0e] border border-white/5 p-2">
                <span className="text-[9px] text-outline block">{translateUiText("QUOTES PROPOSED")}</span>
                <span className="text-xs font-bold text-[#00f2ff]">{dashboard.quote_summary.quoted_not_accepted ?? 0} files</span>
              </div>
              <div className="bg-[#090b0e] border border-white/5 p-2">
                <span className="text-[9px] text-outline block">{translateUiText("RESERVED STOCK")}</span>
                <span className="text-xs font-bold text-on-surface">{dashboard.quote_summary.reserved_inventory ?? 0} units</span>
              </div>
              <div className="bg-[#090b0e] border border-white/5 p-2">
                <span className="text-[9px] text-outline block">{translateUiText("DIAGNOSING CLAIMS")}</span>
                <span className="text-xs font-bold text-[#ffba20]">
                  {dashboard.warranty_summary.diagnosing_warranty_claims ?? 0} claims
                </span>
              </div>
              <div className="bg-[#090b0e] border border-white/5 p-2">
                <span className="text-[9px] text-outline block">{translateUiText("WARRANTY EXPOSURE")}</span>
                <span className="text-xs font-bold text-rose-400">
                  ₫{(dashboard.warranty_summary.warranty_cost_exposure ?? 0).toLocaleString()}
                </span>
              </div>
            </div>
          </ConsolePanel>
        </div>

        {/* Right Column: Logging feed and state info cards */}
        <div className="space-y-4">
          {/* Live Ops Feed */}
          <LiveOpsFeed dashboardData={dashboard} />

          {/* Staff operations card */}
          <ConsolePanel variant="z-1" className="space-y-3 font-mono text-[11px]">
            <div className="flex justify-between items-center border-b border-white/10 pb-2">
              <span className="text-[10px] uppercase text-outline">{translateUiText("PERSONNEL ROSTER")}</span>
              <Link to="/staff" className="text-[10px] text-primary-container hover:underline">
                [MANAGE]
              </Link>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div className="bg-[#090b0e] border border-white/5 p-2">
                <span className="text-[9px] text-outline block">{translateUiText("TOTAL HEADCOUNT")}</span>
                <span className="text-sm font-bold text-on-surface">{dashboard.staff_count ?? 0} operators</span>
              </div>
              <div className="bg-[#090b0e] border border-white/5 p-2">
                <span className="text-[9px] text-outline block">{translateUiText("STANDBY / ACTIVE")}</span>
                <span className="text-sm font-bold text-on-surface">
                  {dashboard.available_staff_count ?? 0} / {Math.max(0, (dashboard.staff_count ?? 0) - (dashboard.available_staff_count ?? 0))}
                </span>
              </div>
              <div className="bg-[#090b0e] border border-white/5 p-2">
                <span className="text-[9px] text-outline block">{translateUiText("DAILY DEBIT")}</span>
                <span className="text-sm font-bold text-[#ffba20]">
                  ₫{(dashboard.daily_salary_total_vnd ?? 0).toLocaleString()}
                </span>
              </div>
              <div className="bg-[#090b0e] border border-white/5 p-2">
                <span className="text-[9px] text-outline block">{translateUiText("TEAM MORALE")}</span>
                <span className="text-sm font-bold text-[#00f2ff]">
                  {Number(staffSummary?.average_morale ?? 100).toFixed(0)}%
                </span>
              </div>
            </div>
          </ConsolePanel>

          {/* Market conditions card */}
          <ConsolePanel variant="z-1" className="space-y-3 font-mono text-[11px]">
            <div className="flex justify-between items-center border-b border-white/10 pb-2">
              <span className="text-[10px] uppercase text-outline">{translateUiText("MARKET LOG")}</span>
              <Link to="/market" className="text-[10px] text-primary-container hover:underline">
                [TERMINAL]
              </Link>
            </div>
            <div className="bg-[#080a0d] border border-white/5 p-2 flex justify-between items-center">
              <div>
                <span className="text-[9px] text-outline block">{translateUiText("ACTIVE PRESSURES")}</span>
                <span className="text-xs font-bold text-on-surface">
                  {dashboard.market_summary?.active_market_events_count ?? 0} events
                </span>
              </div>
              <div className="text-right">
                <span className="text-[9px] text-outline block">{translateUiText("PEAK COEFFICIENT")}</span>
                <span
                  className={`text-xs font-bold ${
                    (dashboard.market_summary?.strongest_market_multiplier ?? 1.0) >= 1.0
                      ? "text-[#00f2ff]"
                      : "text-rose-400"
                  }`}
                >
                  x{dashboard.market_summary?.strongest_market_multiplier?.toFixed(2) ?? "1.00"}
                </span>
              </div>
            </div>
            <p className="text-[10px] text-outline leading-relaxed bg-[#080a0d]/40 border border-white/5 p-2 italic">
              {dashboard.market_summary?.market_pressure_summary ?? "Markets stable. No disruptions detected."}
            </p>
          </ConsolePanel>
        </div>
      </div>

      {/* Bottom Ledger Sections - Mono logs replaces tables */}
      <div className="grid gap-4 lg:grid-cols-3">
        {/* Pending Sales Quotes */}
        <ConsolePanel variant="z-1" className="space-y-3 font-mono text-[11px]">
          <div className="flex justify-between items-center border-b border-white/10 pb-2">
            <span className="text-[10px] uppercase text-outline">{translateUiText("PENDING SALES QUOTES")}</span>
            <Link to="/quotes" className="text-[10px] text-primary-container hover:underline">
              [LEDGER]
            </Link>
          </div>
          {dashboard.recent_quotes.length === 0 ? (
            <div className="text-outline/40 italic p-3 text-center">NO PENDING SALES QUOTES LOGGED</div>
          ) : (
            <div className="space-y-2">
              {dashboard.recent_quotes.map((quote: any) => (
                <div
                  key={quote.id}
                  className="bg-[#090b0e] border border-white/5 p-2 flex justify-between items-center hover:border-white/20 transition"
                >
                  <div>
                    <span className="font-bold text-on-surface block">{quote.title}</span>
                    <span className="text-[9px] text-outline/50">QUOTE ID: #{quote.id}</span>
                  </div>
                  <div className="text-right">
                    <span className="font-bold text-primary-fixed-dim block">
                      ₫{Number(quote.quoted_price_vnd ?? 0).toLocaleString()}
                    </span>
                    <span className="text-[9px] text-outline/50 uppercase">STATUS: [{quote.status}]</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </ConsolePanel>

        {/* Active Assembly Queue */}
        <ConsolePanel variant="z-1" className="space-y-3 font-mono text-[11px]">
          <div className="flex justify-between items-center border-b border-white/10 pb-2">
            <span className="text-[10px] uppercase text-outline">{translateUiText("ACTIVE ASSEMBLY QUEUE")}</span>
            <Link to="/orders" className="text-[10px] text-primary-container hover:underline">
              [BUILD BAY]
            </Link>
          </div>
          {dashboard.recent_fulfillment_events.length === 0 ? (
            <div className="text-outline/40 italic p-3 text-center">NO ASSEMBLY LOGS REGISTERED</div>
          ) : (
            <div className="space-y-2">
              {dashboard.recent_fulfillment_events.slice(0, 4).map((event: any) => (
                <div
                  key={event.id}
                  className="bg-[#090b0e] border border-white/5 p-2 flex justify-between items-center hover:border-white/20 transition"
                >
                  <div>
                    <span className="font-bold text-on-surface block">{event.summary}</span>
                    <span className="text-[9px] text-[#74f5ff]">EVENT: {event.event_type}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] text-outline block">ORDER #{event.order_id}</span>
                    <span className="text-[9px] text-outline/50">PROCESSING</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </ConsolePanel>

        {/* Warranty RMA Incidents */}
        <ConsolePanel variant="z-1" className="space-y-3 font-mono text-[11px]">
          <div className="flex justify-between items-center border-b border-white/10 pb-2">
            <span className="text-[10px] uppercase text-outline">{translateUiText("WARRANTY RMA INCIDENTS")}</span>
            <Link to="/warranty" className="text-[10px] text-primary-container hover:underline">
              [RMA DESK]
            </Link>
          </div>
          {dashboard.recent_warranty_events.length === 0 ? (
            <div className="text-outline/40 italic p-3 text-center">NO ACTIVE WARRANTY CLAIMS INITIATED</div>
          ) : (
            <div className="space-y-2">
              {dashboard.recent_warranty_events.slice(0, 4).map((event: any) => (
                <div
                  key={event.id}
                  className="bg-[#090b0e] border border-white/5 p-2 flex justify-between items-center hover:border-white/20 transition"
                >
                  <div>
                    <span className="font-bold text-on-surface block">{event.summary}</span>
                    <span className="text-[9px] text-rose-400">CLAIM TYPE: {event.event_type}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] text-outline block">CLAIM #{event.claim_id}</span>
                    <span className="text-[9px] text-outline/50">AUDITING</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </ConsolePanel>
      </div>
    </section>
  );
}
