import { useNavigate } from "react-router-dom";

import {
  useCreateConversationForRequest,
  useCustomerRequests,
  useCustomers,
  useEvaluateRequestQuotes,
  useGenerateCustomer,
  useGenerateQuote,
} from "../api/hooks";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { useGameStore } from "../store/gameStore";
import { formatVnd } from "../utils/format";
import type { CustomerRequest } from "../types/game";

import { ConsolePanel } from "../components/ui/ConsolePanel";
import { StatusChip } from "../components/ui/StatusChip";
import { ActionButton } from "../components/ui/ActionButton";
import { tutorialHighlight, tutorialTooltip } from "../utils/tutorial";

export function CustomersPage() {
  const saveId = useGameStore((state) => state.selectedSaveId);
  const navigate = useNavigate();
  const customers = useCustomers(saveId);
  const requests = useCustomerRequests(saveId);
  const generateCustomer = useGenerateCustomer(saveId);
  const generateQuote = useGenerateQuote(saveId);
  const evaluateQuotes = useEvaluateRequestQuotes(saveId);
  const createConversation = useCreateConversationForRequest(saveId);
  const tutorialMode = useGameStore((state) => state.tutorialMode);
  const tutorialStep = useGameStore((state) => state.tutorialStep);

  async function handleGenerateQuote(requestId: number) {
    await generateQuote.mutateAsync(requestId);
    navigate("/quotes");
  }

  async function handleOpenChat(request: CustomerRequest) {
    const conversationId =
      request.conversation_id ?? (await createConversation.mutateAsync(request.id)).conversation.id;
    navigate(`/customer-chat?conversationId=${conversationId}`);
  }

  if (!saveId) return <EmptyState title="No save selected" body="Open a save before generating customers." />;

  return (
    <section className="space-y-4">
      {/* Header Panel */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 mb-2 select-none">
        <div>
          <span className="font-mono text-[10px] text-primary-container tracking-widest uppercase block mb-1">
            STATION_04 // SHOWROOM FRONT COUNTER
          </span>
          <h1 className="font-sans text-2xl font-black text-on-surface uppercase tracking-tighter">
            Walk-in Requests Registry
          </h1>
        </div>
        <div>
          <ActionButton
            className={`h-9 px-4 text-[11px] ${tutorialHighlight(tutorialMode && tutorialStep <= 1)}`}
            variant="primary"
            disabled={generateCustomer.isPending}
            onClick={() => generateCustomer.mutate()}
            title={tutorialTooltip(tutorialMode && tutorialStep <= 1, "Generate sample walk-in")}
          >
            GENERATE WALK-IN SAMPLE
          </ActionButton>
        </div>
      </div>

      {(customers.isLoading || requests.isLoading) && <LoadingState />}
      {(customers.isError || requests.isError || generateQuote.isError || evaluateQuotes.isError) && (
        <ErrorState
          message={((customers.error || requests.error || generateQuote.error || evaluateQuotes.error) as Error | null)?.message}
        />
      )}
      {requests.data?.length === 0 ? (
        <EmptyState title="No customer requests" body="Generate a deterministic sample customer request." />
      ) : null}

      <div className="grid gap-3">
        {requests.data?.map((request) => (
          <ConsolePanel key={request.id} variant="z-1" className="font-mono text-[11px] select-none">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div className="flex-1 space-y-3">
                {/* Dossier Header */}
                <div className="flex flex-wrap items-center gap-2 border-b border-white/5 pb-2">
                  <h3 className="text-sm font-bold text-on-surface tracking-wider uppercase">{request.customer.name}</h3>
                  <span className="border border-white/10 bg-white/[0.03] px-1.5 py-0.5 text-[9px] text-outline">
                    ARCH: {request.customer.archetype}
                  </span>
                  <StatusChip label={request.customer.persona_type ?? "GENERIC"} variant={getPersonaVariant(request.customer.persona_type)} />
                  <StatusChip label={request.status} variant={request.status === "ACCEPTED" ? "success" : "warning"} />
                  {request.conversation_status && (
                    <StatusChip label={request.conversation_status} variant="success" />
                  )}
                </div>

                {/* Details layout rows */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 bg-[#080a0d] border border-white/5 p-3">
                  <div>
                    <span className="text-[9px] text-outline block">ACQUISITION VERB // USE CASE</span>
                    <span className="text-on-surface block mt-0.5">
                      {request.request_type} // {request.use_case}
                    </span>
                  </div>
                  <div>
                    <span className="text-[9px] text-outline block">TARGET BUDGET</span>
                    <span className="text-emerald-400 font-bold block mt-0.5">
                      {formatVnd(request.budget_vnd)}
                    </span>
                  </div>
                  <div>
                    <span className="text-[9px] text-outline block">WAR ROOM DIAGNOSTICS</span>
                    <span className="text-on-surface block mt-0.5 text-[10px]">
                      KNOW: {request.customer.knowledge_level} // NEG: {request.customer.negotiation_score} // RISK: {request.customer.risk_tolerance}
                    </span>
                  </div>
                </div>

                {/* Badges strip */}
                <div className="flex flex-wrap gap-1.5 items-center">
                  <span className={`px-1.5 py-0.5 border text-[9px] ${request.accepts_used_parts ? "border-emerald-500/20 bg-emerald-500/5 text-emerald-400" : "border-white/10 text-outline"}`}>
                    {request.accepts_used_parts ? "USED_PARTS_OK" : "NEW_PARTS_ONLY"}
                  </span>
                  <span className="border border-white/10 bg-white/[0.03] px-1.5 py-0.5 text-[9px] text-outline">
                    WARRANTY: {request.warranty_expectation_days ?? 30} DAYS
                  </span>
                  <span className="border border-white/10 bg-white/[0.03] px-1.5 py-0.5 text-[9px] text-outline">
                    SENSITIVITY: Price {request.customer.price_sensitivity ?? 50} // Rel {request.customer.reliability_priority ?? 50}
                  </span>
                  {getPriorityTags(request).slice(0, 4).map((tag) => (
                    <span key={tag} className="border border-primary-container/20 bg-primary-container/5 px-1.5 py-0.5 text-[9px] text-[#00f2ff]">
                      [{tag.toUpperCase()}]
                    </span>
                  ))}
                </div>

                {getPersonaHint(request) && (
                  <p className="text-[10px] text-outline/65 italic leading-relaxed pt-1">
                    &gt; {getPersonaHint(request)}
                  </p>
                )}
              </div>

              {/* Action columns */}
              <div
                className={`flex flex-row lg:flex-col gap-2 shrink-0 w-full lg:w-[130px] pt-3 lg:pt-0 lg:border-l lg:border-white/5 lg:pl-3 select-none ${
                  tutorialMode && tutorialStep >= 2 ? tutorialHighlight(true) : ""
                }`}
              >
                <ActionButton
                  className={`h-8 text-[9px] flex-1 lg:flex-none ${tutorialHighlight(tutorialMode && tutorialStep >= 2)}`}
                  variant="primary"
                  disabled={generateQuote.isPending || request.status === "ACCEPTED" || request.status === "COMPLETED"}
                  onClick={() => handleGenerateQuote(request.id)}
                  title={tutorialTooltip(tutorialMode && tutorialStep >= 2, "Generate quote from this request")}
                >
                  SCOUT QUOTE
                </ActionButton>
                  <ActionButton
                    className={`h-8 text-[9px] flex-1 lg:flex-none ${tutorialHighlight(tutorialMode && tutorialStep >= 2)}`}
                    variant="secondary"
                    disabled={createConversation.isPending}
                    onClick={() => handleOpenChat(request)}
                    title={tutorialTooltip(tutorialMode && tutorialStep >= 2, "Open customer chat")}
                  >
                  OPEN CHAT DESK
                  </ActionButton>
                  <ActionButton
                    className={`h-8 text-[9px] flex-1 lg:flex-none ${tutorialHighlight(tutorialMode && tutorialStep >= 2)}`}
                    variant="secondary"
                    disabled={evaluateQuotes.isPending}
                    onClick={() => evaluateQuotes.mutate(request.id)}
                    title={tutorialTooltip(tutorialMode && tutorialStep >= 2, "Re-score fit")}
                  >
                  RE-SCORE FIT
                </ActionButton>
              </div>
            </div>
          </ConsolePanel>
        ))}
      </div>
    </section>
  );
}

function getPriorityTags(request: {
  priority_tags_json?: string[] | null;
  preference_json?: Record<string, unknown> | null;
}) {
  if (request.priority_tags_json?.length) return request.priority_tags_json;
  const preferenceJson = request.preference_json;
  if (!preferenceJson) return [];
  const tags = (preferenceJson as { preferred_priorities?: unknown }).preferred_priorities;
  return Array.isArray(tags) ? tags.filter((tag): tag is string => typeof tag === "string") : [];
}

function getPersonaHint(request: {
  customer: { persona_type: string | null; preference_json: Record<string, unknown> | null };
  preference_json?: Record<string, unknown> | null;
}) {
  const preferenceJson = request.preference_json ?? request.customer.preference_json;
  if (!preferenceJson) return null;
  const hints = (preferenceJson as { preference_hints?: unknown }).preference_hints;
  if (Array.isArray(hints) && hints.length > 0 && typeof hints[0] === "string") {
    return hints[0];
  }
  const sample = (preferenceJson as { sample_use_case?: unknown }).sample_use_case;
  return typeof sample === "string" ? sample : null;
}

function getPersonaVariant(personaType: string | null | undefined): "success" | "warning" | "error" | "neutral" {
  switch (personaType) {
    case "BUDGET_GAMER":
    case "STUDENT":
    case "BARGAIN_HUNTER":
      return "success";
    case "ESPORTS_PLAYER":
    case "STREAMER":
    case "PREMIUM_BUILDER":
      return "neutral";
    case "OFFICE_BUYER":
    case "QUIET_PC_LOVER":
    case "WARRANTY_SENSITIVE":
      return "warning";
    case "AI_WORKSTATION":
    case "CREATOR_EDITOR":
    case "RGB_ENTHUSIAST":
      return "error";
    default:
      return "neutral";
  }
}
