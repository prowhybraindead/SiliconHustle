import { Check, ClipboardCheck, Search, ShieldX, Wrench, RefreshCw, BadgeDollarSign, PackageCheck, X } from "lucide-react";
import type { WarrantyClaim, WarrantyResolutionType } from "../types/game";
import { ActionButton } from "./ui/ActionButton";

interface WarrantyActionButtonsProps {
  claim: WarrantyClaim;
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

export function WarrantyActionButtons({
  claim,
  isBusy,
  onStartDiagnosis,
  onCompleteDiagnosis,
  onApprove,
  onReview,
  onResolve,
  onReject,
  onRepair,
  onReplace,
  onRefund,
  onRma,
  onClose,
}: WarrantyActionButtonsProps) {
  if (claim.status === "OPEN") {
    return (
      <div className="flex flex-wrap gap-2">
        <ActionButton
          variant="secondary"
          className="!h-9 !w-auto !px-3 font-mono text-[10px]"
          disabled={isBusy}
          onClick={() => onReview(claim.id)}
        >
          <Check className="h-3.5 w-3.5 text-primary-container" />
          REVIEW CLAIM
        </ActionButton>
        <ActionButton
          variant="primary"
          className="!h-9 !w-auto !px-3 font-mono text-[10px]"
          disabled={isBusy}
          onClick={() => onStartDiagnosis(claim.id)}
        >
          <Search className="h-3.5 w-3.5 text-on-primary-fixed" />
          DIAGNOSE
        </ActionButton>
      </div>
    );
  }
  
  if (claim.status === "DIAGNOSING") {
    return (
      <ActionButton
        variant="primary"
        className="!h-9 !w-auto !px-3 font-mono text-[10px]"
        disabled={isBusy}
        onClick={() => onCompleteDiagnosis(claim.id)}
      >
        <ClipboardCheck className="h-3.5 w-3.5 text-on-primary-fixed" />
        COMPLETE DIAGNOSIS
      </ActionButton>
    );
  }
  
  if (claim.status === "AWAITING_DECISION") {
    return (
      <div className="flex flex-wrap gap-2">
        <ActionButton
          variant="primary"
          className="!h-9 !w-auto !px-3 font-mono text-[10px]"
          disabled={isBusy}
          onClick={() => onApprove(claim.id)}
        >
          <Check className="h-3.5 w-3.5 text-on-primary-fixed" />
          APPROVE CLAIM
        </ActionButton>
        <ActionButton
          variant="danger"
          className="!h-9 !w-auto !px-3 font-mono text-[10px]"
          disabled={isBusy}
          onClick={() => onReject(claim.id)}
        >
          <ShieldX className="h-3.5 w-3.5 text-rose-300" />
          REJECT CLAIM
        </ActionButton>
      </div>
    );
  }
  
  if (claim.status === "IN_REVIEW" || claim.status === "APPROVED") {
    return (
      <div className="flex flex-wrap gap-2">
        <ActionButton
          variant="primary"
          className="!h-9 !w-auto !px-3 font-mono text-[10px]"
          disabled={isBusy}
          onClick={() => onResolve(claim.id, "REPAIR")}
        >
          <Wrench className="h-3.5 w-3.5 text-on-primary-fixed" />
          REPAIR
        </ActionButton>
        <ActionButton
          variant="secondary"
          className="!h-9 !w-auto !px-3 font-mono text-[10px]"
          disabled={isBusy}
          onClick={() => onResolve(claim.id, "REPLACE")}
        >
          <PackageCheck className="h-3.5 w-3.5 text-primary-container" />
          REPLACE
        </ActionButton>
        <ActionButton
          variant="secondary"
          className="!h-9 !w-auto !px-3 font-mono text-[10px] hover:!bg-[#ffba20]/15 hover:!border-[#ffba20]/30 hover:!text-[#ffba20]"
          disabled={isBusy}
          onClick={() => onResolve(claim.id, "REFUND")}
        >
          <BadgeDollarSign className="h-3.5 w-3.5 text-[#ffba20]" />
          REFUND
        </ActionButton>
        <ActionButton
          variant="danger"
          className="!h-9 !w-auto !px-3 font-mono text-[10px]"
          disabled={isBusy}
          onClick={() => onResolve(claim.id, "REJECT")}
        >
          <ShieldX className="h-3.5 w-3.5 text-rose-300" />
          REJECT
        </ActionButton>
        <ActionButton
          variant="secondary"
          className="!h-9 !w-auto !px-3 font-mono text-[10px]"
          disabled={isBusy}
          onClick={() => onResolve(claim.id, "GOODWILL_CREDIT")}
        >
          <BadgeDollarSign className="h-3.5 w-3.5 text-primary-container" />
          GOODWILL
        </ActionButton>
        <ActionButton
          variant="secondary"
          className="!h-9 !w-auto !px-3 font-mono text-[10px]"
          disabled={isBusy}
          onClick={() => onRma(claim.id)}
        >
          <RefreshCw className="h-3.5 w-3.5 text-primary-container" />
          RMA
        </ActionButton>
      </div>
    );
  }
  
  if (claim.status === "RMA_SUBMITTED" || claim.status === "REJECTED") {
    return (
      <ActionButton
        variant="primary"
        className="!h-9 !w-auto !px-3 font-mono text-[10px]"
        disabled={isBusy}
        onClick={() => onClose(claim.id)}
      >
        <X className="h-3.5 w-3.5 text-on-primary-fixed" />
        CLOSE CLAIM
      </ActionButton>
    );
  }
  
  return (
    <span className="inline-flex items-center justify-center font-mono text-[10px] font-bold uppercase tracking-wider px-3 h-9 border border-white/10 bg-white/5 text-slate-400">
      [RESOLVED]
    </span>
  );
}
