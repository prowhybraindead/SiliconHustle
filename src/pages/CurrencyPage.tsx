import React, { useState } from "react";
import { RefreshCw, Calculator, Info, AlertTriangle, Check } from "lucide-react";

import { useSupportedCurrencies, useFxRates, useRefreshFxRates, useFxAttribution } from "../api/hooks";
import { LoadingState } from "../components/LoadingState";
import { ErrorState } from "../components/ErrorState";
import { formatCurrency, formatFxRate } from "../utils/format";
import { apiRequest } from "../api/client";
import type { CurrencyConversionResult } from "../types/game";
import { getErrorMessage } from "../utils/error";

import { ConsolePanel } from "../components/ui/ConsolePanel";
import { StatusChip } from "../components/ui/StatusChip";
import { ActionButton } from "../components/ui/ActionButton";
import { SectionHeader } from "../components/ui/SectionHeader";

export function CurrencyPage() {
  const currenciesQuery = useSupportedCurrencies();
  const ratesQuery = useFxRates();
  const refreshRatesMutation = useRefreshFxRates();
  const attributionQuery = useFxAttribution();

  // State for Calculator
  const [calcAmount, setCalcAmount] = useState<string>("100");
  const [calcFrom, setCalcFrom] = useState<string>("USD");
  const [calcTo, setCalcTo] = useState<string>("VND");
  const [calcSpread, setCalcSpread] = useState<string>("1.5");
  const [calcResult, setCalcResult] = useState<CurrencyConversionResult | null>(null);
  const [calcLoading, setCalcLoading] = useState<boolean>(false);
  const [calcError, setCalcError] = useState<string | null>(null);

  const handleCalculate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCalcLoading(true);
    setCalcError(null);
    try {
      const amt = parseFloat(calcAmount) || 0;
      const spread = parseFloat(calcSpread) || 0;
      const res = await apiRequest<CurrencyConversionResult>(
        `/api/fx/convert?amount=${amt}&from_currency=${calcFrom}&to_currency=${calcTo}&spread_percent=${spread}`
      );
      setCalcResult(res);
    } catch (err: unknown) {
      setCalcError(getErrorMessage(err, "Failed to convert currency"));
    } finally {
      setCalcLoading(false);
    }
  };

  const handleRefreshRates = () => {
    refreshRatesMutation.mutate(true);
  };

  if (currenciesQuery.isLoading || ratesQuery.isLoading) return <LoadingState />;
  if (currenciesQuery.isError) return <ErrorState message={(currenciesQuery.error as Error).message} />;
  if (ratesQuery.isError) return <ErrorState message={(ratesQuery.error as Error).message} />;

  const supported = currenciesQuery.data || [];
  const rawRates = ratesQuery.data;
  const rates = Array.isArray(rawRates) ? rawRates : rawRates ? [rawRates] : [];
  const attribution = attributionQuery.data?.attribution || "Exchange rates loaded from Frankfurter / ExchangeRate-API.";

  const ratesCount = rates.length;
  const hasFallback = rates.some(r => r.is_fallback);
  const provider = rates[0]?.provider || "FRANKFURTER";

  return (
    <section className="space-y-4">
      {/* Header and Telemetry */}
      <ConsolePanel variant="z-1" className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <SectionHeader title="FX Desk" subtitle="STATION-13 // FINANCIAL CONVERSIONS" />
          <div className="font-mono text-[10px] text-slate-500 mt-1 uppercase">
            STATUS: <span className="text-[#00f2ff] font-bold">FX FEED SYNCED</span> // PROVIDER: {provider.toUpperCase()}
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-[10px] uppercase shrink-0">
          <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
            <span className="text-slate-500 text-[8px] block tracking-wider">BASE ACCOUNTING</span>
            <span className="text-[#00f2ff] font-bold text-xs">VND (₫)</span>
          </div>
          <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
            <span className="text-slate-500 text-[8px] block tracking-wider">LIVE CHANNELS</span>
            <span className="text-white font-bold text-xs">{ratesCount} FEEDS</span>
          </div>
          <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
            <span className="text-slate-500 text-[8px] block tracking-wider">FX CACHE MODE</span>
            <span className="text-[#ffba20] font-bold text-xs">{hasFallback ? "OFFLINE FX" : "LIVE FX"}</span>
          </div>
          <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
            <span className="text-slate-500 text-[8px] block tracking-wider">FEED PROTECTION</span>
            <span className="text-emerald-400 font-bold text-xs">ACTIVE</span>
          </div>
        </div>
      </ConsolePanel>

      <div className="grid gap-4 lg:grid-cols-[1.6fr_1fr]">
        {/* Left Column: Live Exchange Rates */}
        <ConsolePanel variant="z-1" className="p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-white/5 pb-3">
            <div>
              <h2 className="text-xs font-bold font-mono text-white uppercase tracking-wider">Live Exchange Rates to VND</h2>
              <p className="text-[10px] font-mono text-slate-500 uppercase mt-0.5">All internal supplier contracts and quotes calculate VND conversions at intake.</p>
            </div>
            <ActionButton
              onClick={handleRefreshRates}
              disabled={refreshRatesMutation.isPending}
              className="!h-9 !w-auto !px-4 font-mono text-[10px]"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${refreshRatesMutation.isPending ? "animate-spin" : ""}`} />
              {refreshRatesMutation.isPending ? "SYNCING..." : "SYNC RATES"}
            </ActionButton>
          </div>

          <div className="space-y-2 max-h-[500px] overflow-y-auto console-scrollbar pr-1 font-mono text-xs">
            {rates.map((rate) => {
              const currInfo = supported.find((c) => c.code === rate.base_currency);
              return (
                <div key={rate.id} className="bg-[#0c0e11] border border-white/5 p-3 flex flex-wrap items-center justify-between gap-3 uppercase">
                  <div className="flex items-center gap-2">
                    <span className="border border-white/10 bg-white/5 rounded-sm px-1.5 py-0.5 text-xs font-bold text-white">
                      {rate.base_currency}
                    </span>
                    <div>
                      <span className="block font-bold text-white">{currInfo?.name || "FOREIGN CURRENCY"}</span>
                      <span className="block text-[9px] text-slate-500">{currInfo?.country || "-"}</span>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <span className="block text-[8px] text-slate-500">EXCHANGE RATE</span>
                      <span className="block font-bold text-emerald-400">
                        {formatCurrency(rate.rate, "VND")}
                      </span>
                    </div>

                    <div className="text-center">
                      <span className="block text-[8px] text-slate-500 mb-0.5 font-mono">FEED TYPE</span>
                      {rate.is_fallback ? (
                        <StatusChip label="FALLBACK RATE" variant="warning" />
                      ) : (
                        <StatusChip label="LIVE FX" variant="success" />
                      )}
                    </div>

                    <div className="text-right hidden sm:block">
                      <span className="block text-[8px] text-slate-500">UPDATED LOG</span>
                      <span className="block text-[10px] text-slate-400">
                        {new Date(rate.fetched_at).toLocaleTimeString()}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </ConsolePanel>

        {/* Right Column: Converter and Conversion Details */}
        <div className="space-y-4">
          {/* Interactive Calculator Panel */}
          <ConsolePanel variant="z-1" className="p-5 space-y-4">
            <h2 className="text-xs font-bold font-mono text-white uppercase tracking-wider flex items-center gap-2 border-b border-white/5 pb-2">
              <Calculator className="h-4 w-4 text-[#00f2ff]" />
              FX RATE CONVERSION CALCULATOR
            </h2>
            <form onSubmit={handleCalculate} className="space-y-4 font-mono text-xs uppercase">
              <div className="space-y-1">
                <label className="block text-slate-500 text-[8px]">AMOUNT TO CONVERT</label>
                <input
                  type="number"
                  step="any"
                  value={calcAmount}
                  onChange={(e) => setCalcAmount(e.target.value)}
                  className="w-full h-10 rounded-none border border-white/10 bg-[#0c0e11] px-3 font-mono text-xs text-white focus:border-[#00f2ff] focus:outline-none"
                  placeholder="E.G. 100"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="block text-slate-500 text-[8px]">FROM CURRENCY</label>
                  <select
                    value={calcFrom}
                    onChange={(e) => setCalcFrom(e.target.value)}
                    className="w-full h-10 rounded-none border border-white/10 bg-[#0c0e11] px-3 font-mono text-xs text-white focus:border-[#00f2ff] focus:outline-none"
                  >
                    {supported.map((c) => (
                      <option key={c.code} value={c.code}>
                        {c.code} ({c.symbol})
                      </option>
                    ))}
                  </select>
                </div>
                <div className="space-y-1">
                  <label className="block text-slate-500 text-[8px]">TO CURRENCY</label>
                  <select
                    value={calcTo}
                    onChange={(e) => setCalcTo(e.target.value)}
                    className="w-full h-10 rounded-none border border-white/10 bg-[#0c0e11] px-3 font-mono text-xs text-white focus:border-[#00f2ff] focus:outline-none"
                  >
                    {supported.map((c) => (
                      <option key={c.code} value={c.code}>
                        {c.code} ({c.symbol})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="space-y-1">
                <label className="block text-slate-500 text-[8px]">MARKUP SPREAD % (SUPPLIER FEE)</label>
                <input
                  type="number"
                  step="0.01"
                  value={calcSpread}
                  onChange={(e) => setCalcSpread(e.target.value)}
                  className="w-full h-10 rounded-none border border-white/10 bg-[#0c0e11] px-3 font-mono text-xs text-white focus:border-[#00f2ff] focus:outline-none"
                  placeholder="E.G. 1.5"
                />
              </div>

              <ActionButton type="submit" disabled={calcLoading}>
                {calcLoading ? "CALCULATING RATE..." : "CONVERT CURRENCY"}
              </ActionButton>
            </form>

            {calcError && (
              <div className="bg-rose-500/10 border border-rose-500/20 p-3 font-mono text-xs text-rose-400 uppercase">
                ERROR: {calcError}
              </div>
            )}

            {calcResult && (
              <div className="border-t border-white/10 pt-4 space-y-3 font-mono text-xs uppercase">
                <div className="text-center bg-[#0c0e11] border border-white/5 p-3 rounded-none">
                  <div className="text-[8px] text-slate-500">CONVERTED TELEMETRY VALUE</div>
                  <div className="text-lg font-bold text-[#00f2ff] mt-1">
                    {formatCurrency(calcResult.converted_amount, calcResult.to_currency)}
                  </div>
                  {calcResult.to_currency !== "VND" && calcResult.final_amount_vnd !== null && (
                    <div className="text-[9px] text-slate-500 mt-1">
                      ≈ {formatCurrency(calcResult.final_amount_vnd, "VND")}
                    </div>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-y-2 text-[10px]">
                  <span className="text-slate-500">BASE CONVERSION RATE:</span>
                  <span className="text-right text-slate-300 font-bold">
                    {formatFxRate(calcResult.rate, calcResult.from_currency, calcResult.to_currency)}
                  </span>
                  <span className="text-slate-500">APPLIED DESK SPREAD:</span>
                  <span className="text-right text-slate-300 font-bold">
                    {calcResult.spread_applied}%
                  </span>
                  <span className="text-slate-500">FEED SOURCE PROVIDER:</span>
                  <span className="text-right text-slate-300 font-bold">
                    {calcResult.provider.toUpperCase()}
                  </span>
                  <span className="text-slate-500">FEED ATTRIBUTION STATUS:</span>
                  <span className="text-right font-bold">
                    {calcResult.is_fallback ? (
                      <span className="text-[#ffba20]">SNAPSHOT LOCKED</span>
                    ) : (
                      <span className="text-emerald-400">LIVE FEED</span>
                    )}
                  </span>
                </div>
              </div>
            )}
          </ConsolePanel>

          {/* Supported Currencies Quick List */}
          <ConsolePanel variant="z-1" className="p-5 space-y-4">
            <h2 className="text-xs font-bold font-mono text-white uppercase tracking-wider flex items-center gap-2 border-b border-white/5 pb-2">
              <Info className="h-4 w-4 text-[#00f2ff]" />
              SUPPORTED CURRENCIES DESK
            </h2>
            <div className="grid grid-cols-2 gap-2 text-[10px] font-mono uppercase">
              {supported.map((c) => (
                <div key={c.code} className="flex items-center justify-between bg-[#0c0e11] border border-white/5 rounded-none p-2">
                  <span className="font-bold text-white">{c.code} ({c.symbol})</span>
                  <span className="text-slate-500 text-right truncate max-w-[90px]" title={c.name}>{c.name}</span>
                </div>
              ))}
            </div>
          </ConsolePanel>
        </div>
      </div>

      <div className="flex items-start gap-3 rounded-none bg-white/[0.02] border border-white/10 p-4 text-xs text-slate-400 uppercase font-mono leading-relaxed">
        <Info className="h-4.5 w-4.5 text-[#00f2ff] shrink-0 mt-0.5" />
        <div>
          <span className="font-bold text-white block mb-0.5">FX ATTRIBUTION POLICY & SNAPSHOT VERIFICATION</span>
          <span>{attribution} historical transactions keep their original FX snapshot.</span>
        </div>
      </div>
    </section>
  );
}
