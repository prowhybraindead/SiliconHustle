import {
  useApproveWarrantyClaim,
  useCloseWarrantyClaim,
  useCompleteWarrantyDiagnosis,
  useGenerateWarrantyClaim,
  useRejectWarrantyClaim,
  useResolveWarrantyClaim,
  useReviewWarrantyClaim,
  useWarrantySummary,
  useResolveWarrantyRefund,
  useResolveWarrantyRepair,
  useResolveWarrantyReplace,
  useResolveWarrantyRma,
  useStartWarrantyDiagnosis,
  useWarrantyClaims,
} from "../api/hooks";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { WarrantyClaimCard } from "../components/WarrantyClaimCard";
import { useGameStore } from "../store/gameStore";

import { ConsolePanel } from "../components/ui/ConsolePanel";
import { StatusChip } from "../components/ui/StatusChip";
import { ActionButton } from "../components/ui/ActionButton";
import { SectionHeader } from "../components/ui/SectionHeader";

export function WarrantyPage() {
  const saveId = useGameStore((state) => state.selectedSaveId);
  const claims = useWarrantyClaims(saveId);
  const summary = useWarrantySummary(saveId);
  const generateClaim = useGenerateWarrantyClaim(saveId);
  const reviewClaim = useReviewWarrantyClaim(saveId);
  const resolveClaim = useResolveWarrantyClaim(saveId);
  const startDiagnosis = useStartWarrantyDiagnosis(saveId);
  const completeDiagnosis = useCompleteWarrantyDiagnosis(saveId);
  const approveClaim = useApproveWarrantyClaim(saveId);
  const rejectClaim = useRejectWarrantyClaim(saveId);
  const repair = useResolveWarrantyRepair(saveId);
  const replace = useResolveWarrantyReplace(saveId);
  const refund = useResolveWarrantyRefund(saveId);
  const rma = useResolveWarrantyRma(saveId);
  const closeClaim = useCloseWarrantyClaim(saveId);
  
  const actions = [generateClaim, reviewClaim, resolveClaim, startDiagnosis, completeDiagnosis, approveClaim, rejectClaim, repair, replace, refund, rma, closeClaim];
  const isBusy = actions.some((action) => action.isPending);
  const actionError = actions.find((action) => action.isError)?.error as Error | undefined;

  if (!saveId) return <EmptyState title="No save selected" body="Open a save before handling warranty claims." />;

  return (
    <section className="space-y-4">
      {/* Page Header and Telemetry */}
      <ConsolePanel variant="z-1" className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <SectionHeader title="Warranty Claims / RMA Terminal" subtitle="STATION-08 // AFTER-SALES DESK" />
          <div className="font-mono text-[10px] text-slate-500 mt-1 uppercase">
            STATUS: <span className="text-[#00f2ff] font-bold">MONITORING</span> // SYS_OP: NORMAL
          </div>
        </div>

        {summary.data ? (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-[10px] uppercase shrink-0">
            <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
              <span className="text-slate-500 text-[8px] block tracking-wider">OPEN CLAIMS</span>
              <span className="text-white font-bold text-xs">{summary.data.open_claims_count}</span>
            </div>
            <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
              <span className="text-slate-500 text-[8px] block tracking-wider">IN REVIEW</span>
              <span className="text-[#00f2ff] font-bold text-xs">{summary.data.in_review_claims_count}</span>
            </div>
            <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
              <span className="text-slate-500 text-[8px] block tracking-wider">DUE SOON</span>
              <span className="text-[#ffba20] font-bold text-xs">{summary.data.due_soon_claims_count}</span>
            </div>
            <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
              <span className="text-slate-500 text-[8px] block tracking-wider">EST EXPOSURE</span>
              <span className="text-rose-400 font-bold text-xs">{summary.data.estimated_exposure_vnd.toLocaleString("en-US")} VND</span>
            </div>
          </div>
        ) : null}
      </ConsolePanel>

      {/* Action panel to trigger test claims */}
      <ConsolePanel variant="z-1" className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xs font-bold font-mono text-white uppercase tracking-wider">Warranty Operations Console</h2>
          <p className="text-[10px] font-mono text-slate-500 uppercase mt-0.5">Diagnose and resolve customer defect claims (Repair, Refund, Replacement, RMA).</p>
        </div>
        <ActionButton
          className="!h-9 !w-auto !px-4 font-mono text-[10px]"
          disabled={isBusy}
          onClick={() => generateClaim.mutate({})}
        >
          GENERATE CLAIM
        </ActionButton>
      </ConsolePanel>

      {claims.isLoading ? <LoadingState /> : null}
      {claims.isError ? <ErrorState message={(claims.error as Error).message} /> : null}
      {actionError ? <ErrorState message={actionError.message} /> : null}
      {claims.data?.length === 0 ? <EmptyState title="No warranty claims" body="Open a claim from a delivered order when after-sales issues appear." /> : null}
      
      <div className="grid gap-3">
        {claims.data?.map((detail) => (
          <WarrantyClaimCard
            detail={detail}
            isBusy={isBusy}
            key={detail.claim.id}
            onApprove={(claimId) => approveClaim.mutate(claimId)}
            onClose={(claimId) => closeClaim.mutate(claimId)}
            onCompleteDiagnosis={(claimId) => completeDiagnosis.mutate(claimId)}
            onReview={(claimId) => reviewClaim.mutate({ claimId, payload: { notes: "Reviewed from Warranty page." } })}
            onResolve={(claimId, resolutionType) => resolveClaim.mutate({ claimId, payload: { resolution_type: resolutionType } })}
            onReject={(claimId) => rejectClaim.mutate({ claimId, reason: "No reproducible fault or invalid warranty coverage." })}
            onRepair={(claimId) => repair.mutate(claimId)}
            onReplace={(claimId) => replace.mutate(claimId)}
            onRefund={(claimId) => refund.mutate(claimId)}
            onRma={(claimId) => rma.mutate(claimId)}
            onStartDiagnosis={(claimId) => startDiagnosis.mutate(claimId)}
          />
        ))}
      </div>
    </section>
  );
}
