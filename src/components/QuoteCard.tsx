import { ChevronDown, ChevronRight, Check, Lock, Unlock } from "lucide-react";
import { useState } from "react";

import type { QuoteDetail } from "../types/game";
import { formatVnd, formatCurrency } from "../utils/format";
import { QuoteItemRow } from "./QuoteItemRow";
import { ScorePill } from "./ScorePill";
import { StatusChip } from "./ui/StatusChip";
import { ConsolePanel } from "./ui/ConsolePanel";
import { ActionButton } from "./ui/ActionButton";

interface QuoteCardProps {
  detail: QuoteDetail;
  onReserve: (quoteId: number) => void;
  onRelease: (quoteId: number) => void;
  onAccept: (quoteId: number) => void;
  onOpenChat?: (conversationId: number) => void;
  isBusy?: boolean;
}

export function QuoteCard({ detail, onReserve, onRelease, onAccept, onOpenChat, isBusy }: QuoteCardProps) {
  const [open, setOpen] = useState(false);
  const { quote, quote_items: items } = detail;
  const compatibility = quote.compatibility_result;
  const warningCount = compatibility?.warnings.length ?? quote.compatibility_warnings_json?.length ?? 0;
  const personaWarnings = quote.persona_warnings_json ?? [];
  const isConverted = quote.status === "CONVERTED_TO_ORDER";

  const compatibilityTone = getCompatibilityVariant(quote.compatibility_score ?? compatibility?.compatibility_score ?? null);

  function getStatusVariant(status: string): "success" | "warning" | "error" | "neutral" {
    switch (status) {
      case "CONVERTED_TO_ORDER":
        return "success";
      case "RESERVED":
        return "warning";
      default:
        return "neutral";
    }
  }

  return (
    <ConsolePanel variant="z-1" className="font-mono text-[11px]">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        {/* Left Side: Clickable Toggle Header */}
        <button
          className="flex flex-1 gap-3 text-left cursor-pointer focus:outline-none select-none"
          onClick={() => setOpen((value) => !value)}
          type="button"
        >
          <span className="mt-1 text-outline shrink-0">
            {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          </span>
          <span className="space-y-1.5 min-w-0 flex-1">
            <span className="flex flex-wrap items-center gap-2">
              <span className="font-bold text-on-surface text-xs uppercase tracking-wider">{quote.title}</span>
              <StatusChip label={quote.status} variant={getStatusVariant(quote.status)} />
              <StatusChip
                label={`WARR RISK: ${quote.warranty_risk ?? "UNKNOWN"}`}
                variant={quote.warranty_risk === "HIGH" ? "error" : "neutral"}
              />
              {quote.compatibility_score != null && (
                <StatusChip label={`COMP: ${quote.compatibility_score}`} variant={compatibilityTone} />
              )}
              {warningCount > 0 && (
                <StatusChip label={`${warningCount} WARN`} variant={warningCount > 2 ? "error" : "warning"} />
              )}
              {quote.quote_acceptance_chance != null && (
                <StatusChip
                  label={`ACCEPT: ${quote.quote_acceptance_chance}%`}
                  variant={quote.quote_acceptance_chance >= 70 ? "success" : "neutral"}
                />
              )}
            </span>
            <span className="block text-[10px] text-outline leading-relaxed">{quote.summary}</span>
            <span className="block text-[9px] text-outline/60">
              CLIENT: {quote.customer.name} // USE CASE: {quote.customer_request.request_type} // BUDGET:{" "}
              {formatVnd(quote.customer_request.budget_vnd)}
              {quote.customer_request.budget_currency && quote.customer_request.budget_currency !== "VND" && (
                ` (${formatCurrency(quote.customer_request.foreign_budget_amount, quote.customer_request.budget_currency)})`
              )}
            </span>
            {quote.customer_feedback_summary && (
              <span className="block text-[9px] text-[#ffba20] italic">&gt; {quote.customer_feedback_summary}</span>
            )}
          </span>
        </button>

        {/* Right Side: Action Buttons Desk */}
        <div className="flex flex-wrap gap-2 xl:justify-end shrink-0 select-none w-full xl:w-auto">
          {quote.customer_request.conversation_id && onOpenChat && (
            <ActionButton
              className="h-8 text-[9px] px-3 w-auto flex-1 xl:flex-none"
              variant="secondary"
              onClick={() => onOpenChat(quote.customer_request.conversation_id as number)}
            >
              COMM CHAT
            </ActionButton>
          )}
          <ActionButton
            className="h-8 text-[9px] px-3 w-auto flex-1 xl:flex-none"
            variant="secondary"
            disabled={isBusy || isConverted}
            onClick={() => onReserve(quote.id)}
          >
            <Lock className="h-3 w-3" />
            RESERVE
          </ActionButton>
          <ActionButton
            className="h-8 text-[9px] px-3 w-auto flex-1 xl:flex-none"
            variant="secondary"
            disabled={isBusy || isConverted}
            onClick={() => onRelease(quote.id)}
          >
            <Unlock className="h-3 w-3" />
            RELEASE
          </ActionButton>
          <ActionButton
            className="h-8 text-[9px] px-3 w-auto flex-1 xl:flex-none"
            variant="primary"
            disabled={isBusy || isConverted}
            onClick={() => onAccept(quote.id)}
          >
            <Check className="h-3 w-3" />
            ACCEPT
          </ActionButton>
        </div>
      </div>

      {/* Score and Pricing telemetry bars */}
      <div className="mt-3.5 grid gap-2 grid-cols-2 md:grid-cols-4 xl:grid-cols-6">
        <ScorePill label="Client Fit" value={quote.customer_fit_score} />
        <ScorePill label="Persona Fit" value={quote.persona_match_score} />
        <ScorePill label="Performance" value={quote.performance_score} />
        <ScorePill label="Thermals" value={quote.thermal_score} />
        <ScorePill label="Reliability" value={quote.reliability_score} />
        <ScorePill label="Used Match" value={quote.used_part_fit_score} />

        <div className="col-span-2 border border-emerald-500/25 bg-emerald-500/5 px-2.5 py-1.5 flex justify-between items-center text-emerald-400">
          <span className="text-[9px] text-emerald-400/70">PROPOSAL PRICE:</span>
          <span className="font-bold">
            {formatVnd(quote.quoted_price_vnd)}
            {quote.quote_currency && quote.quote_currency !== "VND" && (
              <span className="ml-1 text-[10px] font-medium">
                ({formatCurrency(quote.foreign_quoted_price, quote.quote_currency)})
              </span>
            )}
          </span>
        </div>

        <div className="col-span-2 border border-white/10 bg-white/[0.02] px-2.5 py-1.5 flex justify-between items-center text-on-surface">
          <span className="text-[9px] text-outline">ESTIMATED NET PROFIT:</span>
          <span className="font-bold text-[#00f2ff]">{formatVnd(quote.estimated_profit_vnd)}</span>
        </div>

        {quote.quote_currency && quote.quote_currency !== "VND" && (
          <div className="col-span-2 border border-white/5 bg-[#080a0d] px-2.5 py-1 text-[9px] text-outline flex items-center justify-between">
            <span>FX RATE SNAPSHOT</span>
            <span>
              1 {quote.quote_currency} = {quote.fx_rate_to_vnd?.toLocaleString()} VND ({quote.fx_provider?.toUpperCase()})
            </span>
          </div>
        )}
      </div>

      {personaWarnings.length > 0 && (
        <div className="mt-2.5 flex flex-wrap gap-1.5 select-none">
          {personaWarnings.slice(0, 4).map((warning) => (
            <span
              key={`${warning.code}-${warning.message}`}
              className={`px-1.5 py-0.5 border text-[8px] font-bold ${
                warning.severity === "CRITICAL"
                  ? "border-rose-500/20 bg-rose-500/5 text-rose-400"
                  : "border-[#ffba20]/20 bg-[#ffba20]/5 text-[#ffba20]"
              }`}
            >
              [{warning.code}]
            </span>
          ))}
        </div>
      )}

      {/* Expanded details drawers */}
      {open && (
        <div className="mt-4 space-y-3.5 border-t border-white/10 pt-4">
          {compatibility && (
            <div className="border border-white/10 bg-[#080a0d] p-3 text-xs space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2 select-none">
                <span className="font-bold text-on-surface text-[10px] tracking-wider uppercase">
                  BUILD COMPATIBILITY SCHEMATICS
                </span>
                <span className="text-[10px] text-outline">
                  QUALITY SCORE: {compatibility.build_quality_score_estimate} // RISK Δ: {compatibility.warranty_risk_delta}
                </span>
              </div>
              <div className="grid gap-2 grid-cols-2 md:grid-cols-4">
                <MiniMetric label="Compat Rating" value={compatibility.compatibility_score} />
                <MiniMetric label="Power Headroom" value={compatibility.power_headroom_score} />
                <MiniMetric label="Thermal Margin" value={compatibility.thermal_score} />
                <MiniMetric label="Balanced Load" value={compatibility.bottleneck_score} />
              </div>

              {compatibility.blocking_issues.length > 0 && (
                <div className="space-y-2 select-none">
                  <span className="text-[9px] text-rose-400 font-bold uppercase block">CRITICAL BLOCKING FAILURE LABELS:</span>
                  {compatibility.blocking_issues.map((warning) => (
                    <div key={`${warning.code}-${warning.message}`} className="border border-rose-500/25 bg-rose-500/5 px-2.5 py-1.5 text-[10px]">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-[8px] font-bold bg-rose-500 text-slate-950 px-1">BLOCKING</span>
                        <span className="font-bold text-rose-400">{warning.code}</span>
                      </div>
                      <p className="mt-1 text-outline leading-snug">{warning.message}</p>
                    </div>
                  ))}
                </div>
              )}

              {compatibility.suggestions.length > 0 && (
                <div className="space-y-1 bg-black/10 p-2 text-[10px] leading-relaxed select-none">
                  <span className="text-[9px] text-outline/50 uppercase block font-bold">ENGINEERING RECOMMENDATIONS:</span>
                  {compatibility.suggestions.map((suggestion) => (
                    <div key={suggestion} className="text-outline text-[10px]">
                      * {suggestion}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {personaWarnings.length > 0 && (
            <div className="border border-white/10 bg-[#080a0d] p-3 text-xs space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2 select-none">
                <span className="font-bold text-on-surface text-[10px] tracking-wider uppercase">
                  CLIENT PREFERENCE AUDITS
                </span>
                <span className="text-[10px] text-[#ffba20] italic">
                  {quote.customer_feedback_summary ?? "Estimating sentiment..."}
                </span>
              </div>
              <div className="space-y-2">
                {personaWarnings.map((warning) => (
                  <div key={`${warning.code}-${warning.message}`} className="border border-white/5 bg-[#090b0e] px-2.5 py-1.5 text-[10px]">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`text-[8px] font-bold px-1 ${
                        warning.severity === "CRITICAL" ? "bg-rose-500 text-slate-950" : "bg-[#ffba20] text-slate-950"
                      }`}>
                        {warning.severity}
                      </span>
                      <span className="font-bold text-on-surface">{warning.code}</span>
                    </div>
                    <p className="mt-1 text-outline leading-snug">{warning.message}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Parts items checklist list */}
          <div className="space-y-2">
            <div className="font-mono text-[9px] text-outline/50 uppercase select-none">
              PROPOSAL PARTS MANIFEST LIST
            </div>
            {items.length === 0 ? (
              <p className="text-outline/40 italic p-3 text-center bg-[#080a0d] border border-white/5">
                NO CORE SYSTEM PARTS RECORDED
              </p>
            ) : (
              <div className="space-y-1.5">
                {items.map((item) => (
                  <QuoteItemRow item={item} key={item.id} />
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </ConsolePanel>
  );
}

function MiniMetric({ label, value }: { label: string; value: number | null | undefined }) {
  return (
    <div className="border border-white/5 bg-[#0c0f13] px-2.5 py-1.5 flex justify-between items-center">
      <span className="text-[9px] text-outline uppercase">{label}</span>
      <span className="font-bold text-on-surface">{value ?? "?"}</span>
    </div>
  );
}

function getCompatibilityVariant(score: number | null | undefined): "success" | "warning" | "error" | "neutral" {
  if (score === null || score === undefined) return "neutral";
  if (score >= 90) return "success";
  if (score >= 75) return "neutral";
  if (score >= 55) return "warning";
  return "error";
}
