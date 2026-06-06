import { useState } from "react";
import { 
  TrendingUp, 
  TrendingDown, 
  Calendar, 
  Zap, 
  AlertCircle, 
  Activity, 
  RefreshCw 
} from "lucide-react";

import { 
  useMarketSummary, 
  useMarketEvents, 
  useGenerateMarketEvent, 
  useAdvanceMarketDay 
} from "../api/hooks";
import { PageHeader } from "../components/PageHeader";
import { useGameStore } from "../store/gameStore";

type MarketGenerationMode = "rule" | "ai" | "auto";

export function MarketPage() {
  const saveId = useGameStore((state) => state.selectedSaveId);
  
  // Queries
  const { data: summary, refetch: refetchSummary } = useMarketSummary(saveId);
  const { data: events, refetch: refetchEvents } = useMarketEvents(saveId);

  // Mutations
  const generateMutation = useGenerateMarketEvent(saveId);
  const advanceMutation = useAdvanceMarketDay(saveId);

  const [genMode, setGenMode] = useState<MarketGenerationMode>("rule");

  if (!saveId) {
    return (
      <div className="flex h-[50vh] flex-col items-center justify-center text-center">
        <AlertCircle className="mb-4 h-16 w-16 text-yellow-500/70" />
        <h2 className="text-xl font-bold text-slate-100">No Save Game Selected</h2>
        <p className="mt-2 text-sm text-slate-400">Please load or create a save game from the home page first.</p>
      </div>
    );
  }

  const handleGenerate = async () => {
    try {
      await generateMutation.mutateAsync(genMode);
      refetchEvents();
      refetchSummary();
    } catch (err) {
      console.error(err);
    }
  };

  const handleAdvanceDay = async () => {
    try {
      await advanceMutation.mutateAsync();
      refetchEvents();
      refetchSummary();
    } catch (err) {
      console.error(err);
    }
  };

  const activeEvents = events?.filter(e => e.is_active) ?? [];
  const historicalEvents = events?.filter(e => !e.is_active) ?? [];

  return (
    <section className="space-y-6">
      <PageHeader eyebrow="Economic Simulation" title="Market Dynamics Board" />

      {/* Control panel and summary statistics */}
      <div className="grid gap-4 md:grid-cols-3">
        {/* Market state card */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-5 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Market Pressure</span>
            <Activity className="h-5 w-5 text-indigo-400" />
          </div>
          <div className="mt-4">
            <div className="text-2xl font-bold text-slate-100">
              {summary?.active_market_events_count ?? 0} Active Events
            </div>
            <p className="mt-1 text-xs text-slate-400 leading-relaxed">
              {summary?.market_pressure_summary ?? "Markets are stable. No current disruptions detected."}
            </p>
          </div>
        </div>

        {/* Strongest multiplier card */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-5 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Strongest Price Shift</span>
            {summary && summary.strongest_market_multiplier >= 1.0 ? (
              <TrendingUp className="h-5 w-5 text-emerald-400" />
            ) : (
              <TrendingDown className="h-5 w-5 text-rose-400" />
            )}
          </div>
          <div className="mt-4">
            <div className="flex items-baseline space-x-2">
              <span className="text-3xl font-extrabold text-slate-100">
                x{summary?.strongest_market_multiplier?.toFixed(2) ?? "1.00"}
              </span>
              <span className={`text-xs font-semibold ${
                (summary?.strongest_market_multiplier ?? 1.0) >= 1.0 ? "text-emerald-400" : "text-rose-400"
              }`}>
                {((summary?.strongest_market_multiplier ?? 1.0) >= 1.0) ? "Upward Pressure" : "Downward Pressure"}
              </span>
            </div>
            <p className="mt-2 text-xs text-slate-500">
              Clamped within [0.35x - 3.50x] range.
            </p>
          </div>
        </div>

        {/* Action Panel */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-5 backdrop-blur-sm flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Simulator Control</span>
            <Zap className="h-5 w-5 text-yellow-400" />
          </div>
          <div className="mt-4 space-y-3">
            <div className="flex items-center space-x-2">
              <select
                value={genMode}
                onChange={(e) => setGenMode(e.target.value as MarketGenerationMode)}
                className="flex-1 rounded-lg border border-slate-800 bg-slate-950 px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              >
                <option value="rule">Rule-based Generator</option>
                <option value="ai">AI-assisted (Optional)</option>
                <option value="auto">Auto Selection</option>
              </select>
              <button
                onClick={handleGenerate}
                disabled={generateMutation.isPending}
                className="rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-800 px-3 py-1.5 text-xs font-semibold text-slate-100 transition-colors flex items-center space-x-1"
              >
                {generateMutation.isPending ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <span>Trigger</span>}
              </button>
            </div>
            <button
              onClick={handleAdvanceDay}
              disabled={advanceMutation.isPending}
              className="w-full rounded-lg bg-slate-800 hover:bg-slate-700 disabled:bg-slate-900 px-3 py-2 text-xs font-semibold text-slate-100 border border-slate-700 transition-colors flex items-center justify-center space-x-1.5"
            >
              <Calendar className="h-3.5 w-3.5" />
              <span>Advance Game Day</span>
            </button>
          </div>
          <p className="mt-2 text-[10px] text-slate-500">
            * Note: AI generator falls back to deterministic rules if AI_MARKET_EVENTS_ENABLED=false.
          </p>
        </div>
      </div>

      {/* Active Events List */}
      <div>
        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-3 flex items-center space-x-1.5">
          <Activity className="h-4 w-4 text-emerald-400" />
          <span>Active Market Shifts ({activeEvents.length})</span>
        </h3>
        
        {activeEvents.length === 0 ? (
          <div className="rounded-xl border border-slate-800 bg-slate-900/10 p-8 text-center text-slate-500">
            No active events currently impacting prices. Click "Trigger" above or advance the day to generate shifts.
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {activeEvents.map((event) => (
              <div key={event.id} className="rounded-xl border border-emerald-900/50 bg-emerald-950/10 p-5 relative overflow-hidden flex flex-col justify-between">
                <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/5 rounded-full blur-2xl -mr-16 -mt-16 pointer-events-none"></div>
                <div>
                  <div className="flex items-start justify-between">
                    <div>
                      <span className="inline-flex items-center rounded bg-emerald-950 px-2 py-0.5 text-[10px] font-medium text-emerald-400 border border-emerald-800/40">
                        {event.event_type.replace(/_/g, " ")}
                      </span>
                      <h4 className="mt-1 text-base font-bold text-slate-100">{event.title}</h4>
                    </div>
                    <div className="text-right">
                      <span className="text-xs text-slate-400 block">Severity</span>
                      <span className="text-sm font-extrabold text-emerald-400">{"★".repeat(event.severity)}{"☆".repeat(5-event.severity)}</span>
                    </div>
                  </div>

                  <p className="mt-3 text-xs text-slate-300 leading-relaxed">{event.summary}</p>
                  
                  {/* Event Details Grid */}
                  <div className="mt-4 grid grid-cols-2 gap-2 text-[11px] border-t border-slate-800/50 pt-3">
                    <div>
                      <span className="text-slate-500 block">Price Multiplier:</span>
                      <span className={`font-semibold ${event.price_multiplier >= 1.0 ? "text-emerald-400" : "text-rose-400"}`}>
                        x{event.price_multiplier.toFixed(2)}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Target Scope:</span>
                      <span className="font-semibold text-slate-300">
                        {event.affected_category && `Category: ${event.affected_category}`}
                        {event.affected_brand_slug && `Brand: ${event.affected_brand_slug}`}
                        {event.affected_origin_code && `Origin: ${event.affected_origin_code}`}
                        {event.affected_currency && `Currency: ${event.affected_currency}`}
                        {event.affected_product_id && `Product ID: ${event.affected_product_id}`}
                        {!event.affected_category && !event.affected_brand_slug && !event.affected_origin_code && !event.affected_currency && !event.affected_product_id && "Global"}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Demand Delta:</span>
                      <span className="font-semibold text-slate-300">{event.demand_delta > 0 ? `+${event.demand_delta}` : event.demand_delta}%</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Active Period:</span>
                      <span className="font-semibold text-slate-300">Day {event.starts_on_day} - {event.ends_on_day}</span>
                    </div>
                  </div>
                </div>
                
                <div className="mt-4 pt-2 border-t border-slate-800/30 flex justify-between items-center text-[10px] text-slate-500">
                  <span>Source: {event.generation_source}</span>
                  <span>Ends in {event.ends_on_day - event.starts_on_day} days</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Historical Events List */}
      <div>
        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-3 flex items-center space-x-1.5">
          <Calendar className="h-4 w-4 text-slate-400" />
          <span>Historical / Expired Events ({historicalEvents.length})</span>
        </h3>
        
        {historicalEvents.length === 0 ? (
          <div className="rounded-xl border border-slate-800 bg-slate-900/10 p-6 text-center text-slate-600 text-xs">
            No expired events recorded in log history yet.
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/20">
            <table className="w-full border-collapse text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-900/40 text-slate-400">
                  <th className="p-3 font-semibold">Title</th>
                  <th className="p-3 font-semibold">Type</th>
                  <th className="p-3 font-semibold text-center">Severity</th>
                  <th className="p-3 font-semibold text-right">Multiplier</th>
                  <th className="p-3 font-semibold text-center">Start Day</th>
                  <th className="p-3 font-semibold text-center">End Day</th>
                  <th className="p-3 font-semibold">Source</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {historicalEvents.map((event) => (
                  <tr key={event.id} className="hover:bg-slate-900/30 text-slate-300">
                    <td className="p-3 font-semibold">{event.title}</td>
                    <td className="p-3 text-slate-400">{event.event_type.replace(/_/g, " ")}</td>
                    <td className="p-3 text-center text-slate-400">★ {event.severity}</td>
                    <td className={`p-3 text-right font-mono font-semibold ${
                      event.price_multiplier >= 1.0 ? "text-emerald-500/70" : "text-rose-500/70"
                    }`}>
                      x{event.price_multiplier.toFixed(2)}
                    </td>
                    <td className="p-3 text-center text-slate-400">Day {event.starts_on_day}</td>
                    <td className="p-3 text-center text-slate-400">Day {event.ends_on_day}</td>
                    <td className="p-3 text-slate-500">{event.generation_source}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
