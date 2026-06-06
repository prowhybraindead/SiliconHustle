import { ChevronDown, ChevronRight } from "lucide-react";
import { useState } from "react";

import { useOrderDetail } from "../api/hooks";
import type { Order, WarrantyClaimReason } from "../types/game";
import { formatVnd, labelize, formatCurrency } from "../utils/format";
import { BrandLogo } from "./BrandLogo";
import { MetricBar } from "./MetricBar";
import { OrderActionButtons } from "./OrderActionButtons";
import { OrderFulfillmentTimeline } from "./OrderFulfillmentTimeline";
import { RiskBadge } from "./RiskBadge";
import { StatusChip } from "./ui/StatusChip";
import { ConsolePanel } from "./ui/ConsolePanel";
import { ActionButton } from "./ui/ActionButton";

interface OrderCardProps {
  saveId: number;
  order: Order;
  isBusy?: boolean;
  onStartBuild: (orderId: number) => void;
  onRunBuildTest: (orderId: number) => void;
  onDeliver: (orderId: number) => void;
  onOpenWarranty: (payload: { orderId: number; claim_reason: WarrantyClaimReason; complaint_summary: string }) => void;
}

const claimReasons: WarrantyClaimReason[] = [
  "NO_DISPLAY",
  "CRASHING",
  "OVERHEATING",
  "ARTIFACTING",
  "NOISY_FAN",
  "PERFORMANCE_ISSUE",
  "RANDOM_SHUTDOWN",
  "DOA",
  "OTHER",
];

export function OrderCard({
  saveId,
  order,
  isBusy,
  onStartBuild,
  onRunBuildTest,
  onDeliver,
  onOpenWarranty,
}: OrderCardProps) {
  const [open, setOpen] = useState(false);
  const [claimReason, setClaimReason] = useState<WarrantyClaimReason>("CRASHING");
  const [complaint, setComplaint] = useState("Customer reports repeat instability after delivery.");

  const detail = useOrderDetail(saveId, open ? order.id : null);
  const displayOrder = detail.data?.order ?? order;
  const events = detail.data?.fulfillment_events ?? [];
  const compatibility = displayOrder.compatibility_result;
  const warningCount = compatibility?.warnings.length ?? displayOrder.compatibility_warnings_json?.length ?? 0;

  const compatibilityTone = getCompatibilityVariant(
    displayOrder.compatibility_score ?? compatibility?.compatibility_score ?? null
  );

  function getStatusVariant(status: string): "success" | "warning" | "error" | "neutral" {
    switch (status) {
      case "DELIVERED":
        return "success";
      case "TESTING":
      case "IN_PROGRESS":
        return "warning";
      default:
        return "neutral";
    }
  }

  return (
    <ConsolePanel variant="z-1" className="font-mono text-[11px]">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        {/* Toggleable Header */}
        <button
          className="flex flex-1 gap-3 text-left cursor-pointer focus:outline-none select-none min-w-0"
          onClick={() => setOpen((value) => !value)}
          type="button"
        >
          <span className="mt-1 text-outline shrink-0">
            {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          </span>
          <span className="space-y-1.5 min-w-0 flex-1">
            <span className="flex flex-wrap items-center gap-2">
              <span className="font-bold text-on-surface text-xs uppercase tracking-wider">Order #{displayOrder.id}</span>
              <StatusChip label={displayOrder.status} variant={getStatusVariant(displayOrder.status)} />
              <RiskBadge value={displayOrder.final_warranty_risk} />
              {displayOrder.compatibility_score != null && (
                <StatusChip label={`COMP: ${displayOrder.compatibility_score}`} variant={compatibilityTone} />
              )}
              {warningCount > 0 && (
                <StatusChip label={`${warningCount} WARN`} variant={warningCount > 2 ? "error" : "warning"} />
              )}
            </span>
            <span className="block text-[10px] text-outline leading-relaxed">
              CLIENT: {displayOrder.customer.name} // QUOTE: {formatVnd(displayOrder.quoted_price_vnd)}
              {displayOrder.order_currency && displayOrder.order_currency !== "VND" && (
                ` (${formatCurrency(displayOrder.foreign_order_amount, displayOrder.order_currency)})`
              )}
              {` // COST: ${formatVnd(displayOrder.cost_vnd)} // PROFIT: ${formatVnd(displayOrder.profit_vnd)}`}
            </span>
            <span className="block text-[9px] text-outline/50">
              FIT: {displayOrder.customer_fit_score ?? "?"} // REP Δ: {displayOrder.reputation_delta ?? "?"} // DELIVERED:{" "}
              {displayOrder.delivered_at ? new Date(displayOrder.delivered_at).toLocaleDateString() : "PENDING"}
            </span>
            {displayOrder.order_currency && displayOrder.order_currency !== "VND" && (
              <span className="block text-[9px] text-outline/40">
                FX Rate: 1 {displayOrder.order_currency} = {displayOrder.fx_rate_to_vnd?.toLocaleString()} VND via{" "}
                {displayOrder.fx_provider?.toUpperCase()}
              </span>
            )}
          </span>
        </button>

        {/* Action button triggers */}
        <div className="flex flex-col items-end gap-2 shrink-0 select-none w-full xl:w-auto">
          <OrderActionButtons
            isBusy={isBusy}
            onDeliver={onDeliver}
            onRunBuildTest={onRunBuildTest}
            onStartBuild={onStartBuild}
            order={displayOrder}
          />
          {compatibility?.blocking_issues?.length ? (
            <div className="max-w-xs border border-rose-500/25 bg-rose-500/5 px-2.5 py-1.5 text-[10px] leading-relaxed">
              <span className="font-bold uppercase text-rose-400 block mb-0.5">COMPATIBILITY BLOCK:</span>
              <p className="text-outline">{compatibility.blocking_issues[0].message}</p>
            </div>
          ) : warningCount > 0 ? (
            <div className="max-w-xs border border-[#ffba20]/25 bg-[#ffba20]/5 px-2.5 py-1.5 text-[10px] leading-relaxed">
              <span className="font-bold uppercase text-[#ffba20] block mb-0.5">COMPATIBILITY CAVEATS:</span>
              <p className="text-outline">
                {compatibility?.warnings[0]?.message ?? "This build has a few compatibility warnings."}
              </p>
            </div>
          ) : null}
        </div>
      </div>

      {/* Metrics strip */}
      <div className="mt-4 grid gap-3 grid-cols-2 lg:grid-cols-4">
        <MetricBar label="Customer Fit" value={displayOrder.customer_fit_score} />
        <MetricBar label="Build Quality" value={displayOrder.build_quality_score} />
        <MetricBar label="Final Test Level" value={displayOrder.final_test_score} />
        <MetricBar label="Warranty Risk Factor" value={displayOrder.final_warranty_risk} />
      </div>

      {/* Warranty intake console */}
      {displayOrder.status === "DELIVERED" && (
        <div className="mt-4 border border-white/5 bg-[#090b0e] p-3 space-y-3">
          <div className="flex flex-wrap items-center gap-2 border-b border-white/5 pb-2 select-none">
            <span className="text-[10px] text-outline uppercase">WARRANTY INTAKE CONTROLS</span>
            <StatusChip label={displayOrder.warranty_status ?? "ELIGIBLE"} variant="warning" />
            <span className="text-[9px] text-outline/50">CLAIMS DEPOSITED: {displayOrder.warranty_claim_count}</span>
          </div>
          <div className="grid gap-2 lg:grid-cols-[180px_1fr_auto]">
            <select
              className="h-9 border border-white/10 bg-[#0c0f13] px-2 font-mono text-[10px] text-on-surface outline-none focus:border-primary-container"
              onChange={(event) => setClaimReason(event.target.value as WarrantyClaimReason)}
              value={claimReason}
            >
              {claimReasons.map((reason) => (
                <option key={reason} value={reason}>
                  {labelize(reason)}
                </option>
              ))}
            </select>
            <input
              className="h-9 border border-white/10 bg-[#0c0f13] px-3 font-mono text-[10px] text-on-surface outline-none focus:border-primary-container"
              onChange={(event) => setComplaint(event.target.value)}
              value={complaint}
            />
            <ActionButton
              className="h-9 text-[10px] px-3 shrink-0"
              variant="secondary"
              disabled={isBusy || complaint.trim().length === 0}
              onClick={() =>
                onOpenWarranty({ orderId: displayOrder.id, claim_reason: claimReason, complaint_summary: complaint })
              }
            >
              OPEN WARRANTY RMA CLAIM
            </ActionButton>
          </div>
        </div>
      )}

      {/* Expandable details */}
      {open && (
        <div className="mt-4 border-t border-white/10 pt-4 grid gap-4 xl:grid-cols-[1.3fr_1fr]">
          {/* Order Items list manifest */}
          <div className="space-y-2">
            <h3 className="text-[10px] text-outline uppercase tracking-wider select-none">Order Parts Manifest</h3>
            <div className="space-y-1.5">
              {displayOrder.items.map((item) => (
                <div
                  key={item.id}
                  className="border border-white/5 bg-[#090b0e] p-2.5 flex flex-col md:flex-row md:items-center justify-between gap-2"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <BrandLogo
                      brand={item.product.brand_ref}
                      logoUrl={item.product.effective_logo_url}
                      name={item.product.brand}
                      size="sm"
                    />
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <span className="font-bold text-on-surface truncate">{item.product.name}</span>
                        <StatusChip label={item.product.category} variant="neutral" />
                        {item.inventory_unit && (
                          <StatusChip
                            label={item.inventory_unit.status}
                            variant={item.inventory_unit.status === "SOLD" ? "success" : "neutral"}
                          />
                        )}
                      </div>
                      <p className="text-[10px] text-outline mt-0.5">
                        {item.inventory_unit
                          ? `${labelize(item.inventory_unit.condition_type)} / GRADE ${labelize(
                              item.inventory_unit.grade
                            )} / CONFIDENCE ${item.inventory_unit.inspection_confidence}%`
                          : "No linked warehouse inventory unit"}
                      </p>
                    </div>
                  </div>
                  <div className="text-[10px] text-outline select-none shrink-0 text-right">
                    QTY {item.quantity} // COST: <span className="font-bold">{formatVnd(item.cost_vnd)}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Timeline and compatibility snapshots */}
          <div className="space-y-4">
            <div className="space-y-2">
              <h3 className="text-[10px] text-outline uppercase tracking-wider select-none">Fulfillment Events</h3>
              {detail.isLoading ? (
                <p className="text-[10px] text-outline/40 italic p-3 text-center">Reading event timeline...</p>
              ) : (
                <OrderFulfillmentTimeline events={events} />
              )}
            </div>

            {compatibility && (
              <div className="border border-white/10 bg-[#080a0d] p-3 text-xs space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2 select-none">
                  <span className="font-bold text-on-surface text-[10px] tracking-wider uppercase">
                    COMPATIBILITY SNAPSHOT
                  </span>
                  <span className="text-[10px] text-outline">
                    Quality {compatibility.build_quality_score_estimate} // Risk Δ {compatibility.warranty_risk_delta}
                  </span>
                </div>
                <div className="grid gap-2 grid-cols-2">
                  <div className="border border-white/5 bg-[#0c0f13] px-2 py-1 flex justify-between items-center select-none text-[10px]">
                    <span className="text-outline uppercase">Compat</span>
                    <span className="font-bold text-on-surface">{compatibility.compatibility_score ?? "?"}</span>
                  </div>
                  <div className="border border-white/5 bg-[#0c0f13] px-2 py-1 flex justify-between items-center select-none text-[10px]">
                    <span className="text-outline uppercase">Power</span>
                    <span className="font-bold text-on-surface">{compatibility.power_headroom_score ?? "?"}</span>
                  </div>
                  <div className="border border-white/5 bg-[#0c0f13] px-2 py-1 flex justify-between items-center select-none text-[10px]">
                    <span className="text-outline uppercase">Thermal</span>
                    <span className="font-bold text-on-surface">{compatibility.thermal_score ?? "?"}</span>
                  </div>
                  <div className="border border-white/5 bg-[#0c0f13] px-2 py-1 flex justify-between items-center select-none text-[10px]">
                    <span className="text-outline uppercase">Balance</span>
                    <span className="font-bold text-on-surface">{compatibility.bottleneck_score ?? "?"}</span>
                  </div>
                </div>
                {compatibility.suggestions.length > 0 && (
                  <div className="space-y-1 bg-black/10 p-2 text-[10px] select-none leading-relaxed">
                    <span className="text-[9px] text-outline/50 uppercase block font-bold">Suggestions</span>
                    {compatibility.suggestions.map((suggestion) => (
                      <p key={suggestion} className="text-outline">
                        * {suggestion}
                      </p>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </ConsolePanel>
  );
}

function getCompatibilityVariant(score: number | null | undefined): "success" | "warning" | "error" | "neutral" {
  if (score === null || score === undefined) return "neutral";
  if (score >= 90) return "success";
  if (score >= 75) return "neutral";
  if (score >= 55) return "warning";
  return "error";
}
