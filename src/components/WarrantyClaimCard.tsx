import { ChevronDown, ChevronRight } from "lucide-react";
import { useState } from "react";

import type { WarrantyClaimDetail, WarrantyResolutionType } from "../types/game";
import { formatVnd, labelize } from "../utils/format";
import { RiskBadge } from "./RiskBadge";
import { StatusChip } from "./ui/StatusChip";
import { ConsolePanel } from "./ui/ConsolePanel";
import { ActionButton } from "./ui/ActionButton";
import { WarrantyActionButtons } from "./WarrantyActionButtons";
import { WarrantyTimeline } from "./WarrantyTimeline";

interface WarrantyClaimCardProps {
  detail: WarrantyClaimDetail;
  isBusy?: boolean;
  onStartDiagnosis: (claimId: number) => void;
  onCompleteDiagnosis: (claimId: number) => void;
  onApprove: (claimId: number) => void;
  onReview: (claimId: number) => void;
  onResolve: (claimId: number, resolutionType: WarrantyResolutionType) => void;
  onReject: (claimId: number) => void;
  onRepair: (claimId: number) => void;
  onReplace: (claimId: number) => void;
  onRefund: (claimId: number) => void;
  onRma: (claimId: number) => void;
  onClose: (claimId: number) => void;
}

export function WarrantyClaimCard(props: WarrantyClaimCardProps) {
  const [open, setOpen] = useState(false);
  const { detail, isBusy } = props;
  const { claim, order } = detail;
  
  const sourceLabel = order
    ? `Order #${order.id}`
    : detail.resale_listing
      ? `Resale #${detail.resale_listing.id}`
      : claim.inventory_unit_id
        ? `Inventory #${claim.inventory_unit_id}`
        : "Unlinked claim";

  const riskLabel = order?.final_warranty_risk ?? (claim.internal_risk_score >= 70 ? "HIGH" : claim.internal_risk_score >= 35 ? "MEDIUM" : "LOW");

  const statusVariant =
    claim.status === "CLOSED" || claim.status === "RESOLVED" || claim.status === "CANCELLED"
      ? "success"
      : claim.status === "REJECTED"
      ? "error"
      : "warning";

  return (
    <ConsolePanel variant="z-1" className="flex flex-col gap-4">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <button className="flex flex-1 gap-3 text-left min-w-0" onClick={() => setOpen((value) => !value)} type="button">
          <span className="mt-1 text-slate-400 shrink-0">{open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}</span>
          <span className="min-w-0 block">
            <span className="flex flex-wrap items-center gap-2">
              <span className="font-semibold text-white font-mono text-sm">CLAIM #{claim.id}</span>
              <StatusChip label={claim.status} variant={statusVariant} />
              <StatusChip label={claim.claim_type} variant="neutral" />
              <StatusChip label={claim.claim_reason} variant="neutral" />
              <RiskBadge value={riskLabel} />
            </span>
            <span className="mt-2 block text-xs text-slate-400 font-mono uppercase truncate">
              SOURCE: {sourceLabel} // CLIENT: {claim.customer?.name ?? "No customer linked"} // SUBJECT: {claim.title || claim.complaint_summary}
            </span>
            <span className="mt-1 block text-[10px] text-slate-500 font-mono uppercase">
              VALIDITY: {claim.warranty_valid ? "VERIFIED" : "UNVERIFIED"} // SEVERITY: {claim.severity} // DUE DAY: {claim.due_on_day ?? "?"} // EST COST: {formatVnd(claim.estimated_cost_vnd)}
            </span>
          </span>
        </button>
        <div className="shrink-0 flex items-center">
          <WarrantyActionButtons
            claim={claim}
            isBusy={isBusy}
            onApprove={props.onApprove}
            onClose={props.onClose}
            onCompleteDiagnosis={props.onCompleteDiagnosis}
            onReview={props.onReview}
            onResolve={props.onResolve}
            onReject={props.onReject}
            onRepair={props.onRepair}
            onReplace={props.onReplace}
            onRefund={props.onRefund}
            onRma={props.onRma}
            onStartDiagnosis={props.onStartDiagnosis}
          />
        </div>
      </div>

      {/* 3-column stats panel */}
      <div className="mt-2 grid gap-3 text-xs lg:grid-cols-3 font-mono text-[10px] uppercase">
        <div className="border border-white/5 bg-[#0c0e11] p-3 rounded-sm">
          <div className="text-slate-500 tracking-wider">DIAGNOSTIC SUMMARY</div>
          <p className="mt-2 text-slate-300 normal-case">{claim.diagnostic_summary ?? "?"}</p>
        </div>
        <div className="border border-white/5 bg-[#0c0e11] p-3 rounded-sm">
          <div className="text-slate-500 tracking-wider">RESOLUTION ACTIONS</div>
          <p className="mt-2 text-slate-300 normal-case">{claim.resolution_summary ?? claim.notes ?? "?"}</p>
        </div>
        <div className="border border-white/5 bg-[#0c0e11] p-3 rounded-sm">
          <div className="text-slate-500 tracking-wider">REPUTATION DELTA</div>
          <p className="mt-2 text-[#00f2ff] font-bold text-xs">{claim.reputation_delta !== null && claim.reputation_delta !== undefined ? `${claim.reputation_delta}` : "?"}</p>
        </div>
      </div>

      {open ? (
        <div className="mt-4 grid gap-4 xl:grid-cols-[1.25fr_1fr] pt-3 border-t border-white/5 font-mono text-[10px] uppercase">
          <div>
            <h3 className="mb-3 font-bold text-slate-300 uppercase tracking-wider">SUSPECTED CLAIM COMPONENT ASSETS</h3>
            <div className="space-y-2">
              {detail.claim_items.map((item) => (
                <div className="border border-white/5 bg-[#0c0e11] p-3 rounded-sm space-y-1.5" key={item.id}>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-bold text-white text-xs normal-case">{item.product?.name ?? "Unknown product"}</span>
                    {item.product && <StatusChip label={item.product.category} variant="neutral" className="!text-[8px] !px-1.5" />}
                    {item.inventory_unit && <StatusChip label={item.inventory_unit.status} variant="neutral" className="!text-[8px] !px-1.5" />}
                  </div>
                  <p className="text-slate-400 normal-case">REPORTED FAULT: <span className="text-white italic">"{item.suspected_issue ?? "No suspected issue"}"</span></p>
                  <p className="text-slate-500 uppercase text-[9px]">
                    DIAGNOSED: {item.diagnosis_result ?? "?"} // ACTION RUN: {item.action_taken ? labelize(item.action_taken) : "?"}
                  </p>
                </div>
              ))}
            </div>
          </div>
          <div>
            <h3 className="mb-3 font-bold text-slate-300 uppercase tracking-wider">CLAIM TELEMETRY EVENT LOGS</h3>
            <WarrantyTimeline events={detail.events} />
          </div>
        </div>
      ) : null}
    </ConsolePanel>
  );
}
