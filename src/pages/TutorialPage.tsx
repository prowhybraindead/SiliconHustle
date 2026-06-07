import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowRight,
  BookOpen,
  ClipboardList,
  MessageSquareQuote,
  ShieldCheck,
  Sparkles,
  Users,
  Warehouse,
} from "lucide-react";

import { useCustomerRequests, useDashboardState, useGenerateCustomer, useProgression } from "../api/hooks";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { ActionButton } from "../components/ui/ActionButton";
import { ConsolePanel } from "../components/ui/ConsolePanel";
import { MetricPill } from "../components/ui/MetricPill";
import { SectionHeader } from "../components/ui/SectionHeader";
import { StatusChip } from "../components/ui/StatusChip";
import { useGameStore } from "../store/gameStore";
import { formatVndCompact } from "../utils/format";
import { tutorialHighlight, tutorialTooltip } from "../utils/tutorial";

type TourStep = 0 | 1 | 2 | 3;

const TOUR_STEPS: Array<{
  title: string;
  cue: string;
  body: string;
}> = [
  {
    title: "Read the command center",
    cue: "Step 1 of 4",
    body:
      "The dashboard tells you how healthy your shop is. Cash is your runway, reputation shows trust, and the day counter shows how far your shop has progressed.",
  },
  {
    title: "Generate the first customer",
    cue: "Step 2 of 4",
    body:
      "A sample walk-in request gives you a safe lead to practice on. This tutorial will create one for you automatically so you can see the flow without guessing.",
  },
  {
    title: "Inspect the live request",
    cue: "Step 3 of 4",
    body:
      "Once the request appears, use it as your first real sales opportunity. Read the budget, the use case, and the customer's preferences before moving to quotes.",
  },
  {
    title: "Practice the stations",
    cue: "Step 4 of 4",
    body:
      "After the guided intro, you can move to the dashboard, customer desk, warehouse, or quote ledger and practice the rest of the loop at your own pace.",
  },
];

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

export function TutorialPage() {
  const saveId = useGameStore((state) => state.selectedSaveId);
  const tutorialMode = useGameStore((state) => state.tutorialMode);
  const tutorialStep = useGameStore((state) => state.tutorialStep);
  const setTutorialStep = useGameStore((state) => state.setTutorialStep);
  const resetTutorial = useGameStore((state) => state.resetTutorial);
  const navigate = useNavigate();

  const dashboard = useDashboardState(saveId);
  const progression = useProgression(saveId);
  const requests = useCustomerRequests(saveId);
  const generateCustomer = useGenerateCustomer(saveId);

  const [sampleRequested, setSampleRequested] = useState(false);

  const overviewRef = useRef<HTMLDivElement | null>(null);
  const generatorRef = useRef<HTMLDivElement | null>(null);
  const sampleRef = useRef<HTMLDivElement | null>(null);
  const practiceRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!saveId || !tutorialMode) return;

    const currentStep = tutorialStep as TourStep;

    if (currentStep === 0 && overviewRef.current) {
      overviewRef.current.scrollIntoView({ behavior: "smooth", block: "center" });
    }
    if (currentStep === 1 && generatorRef.current) {
      generatorRef.current.scrollIntoView({ behavior: "smooth", block: "center" });
    }
    if (currentStep === 2 && sampleRef.current) {
      sampleRef.current.scrollIntoView({ behavior: "smooth", block: "center" });
    }
    if (currentStep === 3 && practiceRef.current) {
      practiceRef.current.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [saveId, tutorialMode, tutorialStep]);

  const state = dashboard.data;
  const existingRequest = requests.data?.[0];
  const currentTour = TOUR_STEPS[Math.min(tutorialStep, 3) as TourStep] ?? TOUR_STEPS[0];

  useEffect(() => {
    if (!saveId || !tutorialMode) return;
    if (tutorialStep !== 0) return;

    const timer = window.setTimeout(() => setTutorialStep(1), 1800);
    return () => window.clearTimeout(timer);
  }, [saveId, tutorialMode, tutorialStep, setTutorialStep]);

  useEffect(() => {
    if (!saveId || !tutorialMode) return;
    if (tutorialStep !== 1) return;
    if (existingRequest) {
      setTutorialStep(2);
      return;
    }
    if (sampleRequested || generateCustomer.isPending) return;

    const timer = window.setTimeout(() => {
      setSampleRequested(true);
      void generateCustomer.mutateAsync().catch(() => {
        setSampleRequested(false);
      });
    }, 1000);

    return () => window.clearTimeout(timer);
  }, [saveId, tutorialMode, tutorialStep, existingRequest, sampleRequested, generateCustomer, setTutorialStep]);

  useEffect(() => {
    if (!saveId || !tutorialMode) return;
    if (tutorialStep === 1 && existingRequest) {
      setTutorialStep(2);
    }
  }, [saveId, tutorialMode, tutorialStep, existingRequest, setTutorialStep]);

  if (!saveId) {
    return <EmptyState title="No tutorial save selected" body="Start the guided tutorial from the home screen." />;
  }

  if (dashboard.isLoading || progression.isLoading || requests.isLoading) {
    return <LoadingState />;
  }

  if (dashboard.isError || progression.isError || requests.isError) {
    return <ErrorState message={((dashboard.error || progression.error || requests.error) as Error).message} />;
  }

  if (!state) return null;

  function handleGenerateSampleCustomer() {
    setSampleRequested(true);
    void generateCustomer.mutateAsync().catch(() => {
      setSampleRequested(false);
    });
  }

  function handleRestartTutorial() {
    resetTutorial();
    setSampleRequested(false);
    window.requestAnimationFrame(() => {
      overviewRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    });
  }

  const quickSteps = [
    {
      title: "Read the command center",
      description:
        "Your dashboard is the executive panel. Cash tells you how much runway you have, reputation changes how customers trust you, and the day counter shows how far your shop has progressed.",
      icon: ClipboardList,
    },
    {
      title: "Create the first customer",
      description:
        "This generates a deterministic walk-in request. The request will tell you what the customer wants, how much they can spend, and whether they accept used parts.",
      icon: Users,
    },
    {
      title: "Build a quote",
      description:
        "Open Quotes after you generate a request. A quote is your pitch: the parts, price, and confidence all need to line up before a customer accepts it.",
      icon: MessageSquareQuote,
    },
    {
      title: "Use the warehouse",
      description:
        "Inventory is where you intake parts, inspect them, and prepare stock. A healthy warehouse keeps quotes fast and profitable.",
      icon: Warehouse,
    },
  ];

  const stationCards = [
    {
      title: "COMMAND CENTER",
      body: "This is the big picture view. Watch cash, reputation, active orders, and warranty risk here.",
      link: "/dashboard",
      icon: ShieldCheck,
      label: "OPEN DASHBOARD",
    },
    {
      title: "CUSTOMER DESK",
      body: "Generate walk-ins, inspect requests, and move them into chat or quote workflows.",
      link: "/customers",
      icon: Users,
      label: "OPEN CUSTOMERS",
    },
    {
      title: "WAREHOUSE",
      body: "Add hardware, test units, and prepare inventory for sale or refurbishment.",
      link: "/inventory",
      icon: Warehouse,
      label: "OPEN INVENTORY",
    },
    {
      title: "SALES LEDGER",
      body: "Quotes become orders when the customer accepts. This is where your sales pipeline turns into revenue.",
      link: "/quotes",
      icon: MessageSquareQuote,
      label: "OPEN QUOTES",
    },
  ];

  const currentStep = Math.min(tutorialStep, 3) as TourStep;

  return (
    <section className="space-y-4">
      <SectionHeader subtitle="TUTORIAL_00 // SAFE PRACTICE RUN" title="Guided Tutorial" />

      <div ref={overviewRef} className={tutorialHighlight(tutorialMode && currentStep === 0)}>
        <ConsolePanel variant="z-1" className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <StatusChip label="BEGINNER MODE" variant="success" />
              <StatusChip label={currentTour.cue} variant="neutral" />
              <StatusChip label={`${state.reputation}% REP`} variant="warning" />
              <StatusChip label={formatVndCompact(state.cash)} variant="success" />
            </div>
            <div className="flex flex-wrap gap-2">
              <ActionButton
                className="h-9 w-auto px-3"
                variant="secondary"
                onClick={handleRestartTutorial}
                title="Restart tutorial"
              >
                Restart Tutorial
              </ActionButton>
            </div>
          </div>
          <p className="max-w-4xl font-mono text-[11px] leading-relaxed text-on-surface-variant">
            This tutorial uses a fresh practice save, so you can click around safely. I will walk you through the core
            loop: understand the dashboard, create a customer request, build a quote, manage inventory, and learn
            where the rest of the systems fit.
          </p>
        </ConsolePanel>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.35fr_0.85fr]">
        <div className="space-y-4">
          <div ref={practiceRef} className={tutorialHighlight(tutorialMode && currentStep === 3)}>
            <ConsolePanel variant="z-1" className="space-y-3">
              <div className="flex items-center gap-2 border-b border-white/10 pb-2">
                <ArrowRight className="h-4 w-4 text-primary-container" />
                <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-outline">
                  PRACTICE ACTIONS
                </span>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                {stationCards.map((station) => {
                  const Icon = station.icon;
                  return (
                    <div key={station.title} className="border border-white/10 bg-[#080a0d] p-3">
                      <div className="flex items-center gap-2">
                        <div className="flex h-8 w-8 items-center justify-center border border-white/10 bg-white/[0.03] text-outline">
                          <Icon className="h-4 w-4" />
                        </div>
                        <h3 className="text-sm font-bold uppercase text-on-surface">{station.title}</h3>
                      </div>
                      <p className="mt-2 text-[11px] leading-relaxed text-on-surface-variant">{station.body}</p>
                      <ActionButton
                        className="mt-3 h-9"
                        variant="secondary"
                        onClick={() => navigate(station.link)}
                        title={`Open ${station.title.toLowerCase()}`}
                      >
                        {station.label}
                      </ActionButton>
                    </div>
                  );
                })}
              </div>
            </ConsolePanel>
          </div>

          <ConsolePanel variant="z-1" className="space-y-3">
            <div className="flex items-center gap-2 border-b border-white/10 pb-2">
              <BookOpen className="h-4 w-4 text-primary-container" />
              <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-outline">
                HOW TO READ THE GAME
              </span>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              {quickSteps.map((step, index) => {
                const Icon = step.icon;
                const active = tutorialMode && currentStep === 0 && index === 0;
                return (
                  <div
                    key={step.title}
                    className={`border bg-[#080a0d] p-3 transition-all ${active ? tutorialHighlight(true) : "border-white/10"}`}
                  >
                    <div className="flex items-center gap-2">
                      <div className="flex h-8 w-8 items-center justify-center border border-primary-container/30 bg-primary-container/10 text-primary-container">
                        <Icon className="h-4 w-4" />
                      </div>
                      <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-outline">
                        STEP {index + 1}
                      </div>
                    </div>
                    <h3 className="mt-3 text-sm font-bold uppercase text-on-surface">{step.title}</h3>
                    <p className="mt-2 text-[11px] leading-relaxed text-on-surface-variant">{step.description}</p>
                  </div>
                );
              })}
            </div>
          </ConsolePanel>
        </div>

        <div className="space-y-4">
          <div ref={generatorRef} className={tutorialHighlight(tutorialMode && currentStep === 1)}>
            <ConsolePanel variant="z-1" className="space-y-3">
              <div className="flex items-center gap-2 border-b border-white/10 pb-2">
                <Sparkles className="h-4 w-4 text-secondary-fixed-dim" />
                <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-outline">
                  WHAT TO DO FIRST
                </span>
              </div>

              <div className="grid gap-3">
                <div className="border border-white/10 bg-[#080a0d] p-3">
                  <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-primary-container">
                    01 // GENERATE A CUSTOMER
                  </div>
                  <p className="mt-2 text-[11px] leading-relaxed text-on-surface-variant">
                    Click the button below to create a sample walk-in request. That request is your first real lead.
                    Once it exists, open the customer desk and start a conversation or build a quote.
                  </p>
                </div>
                <div className="border border-white/10 bg-[#080a0d] p-3">
                  <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-primary-container">
                    02 // LEARN THE DASHBOARD
                  </div>
                  <p className="mt-2 text-[11px] leading-relaxed text-on-surface-variant">
                    Cash is your working capital. Reputation affects trust. Orders and warranty claims are the two
                    fastest ways to make or lose momentum.
                  </p>
                </div>
                <div className="border border-white/10 bg-[#080a0d] p-3">
                  <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-primary-container">
                    03 // MATCH THE RIGHT PARTS
                  </div>
                  <p className="mt-2 text-[11px] leading-relaxed text-on-surface-variant">
                    Inventory is the source of truth for what you can sell. If you need stock, go to Warehouse and add
                    units before trying to close a quote.
                  </p>
                </div>
              </div>
            </ConsolePanel>
          </div>

          <div ref={sampleRef} className={tutorialHighlight(tutorialMode && currentStep === 2)}>
            <ConsolePanel variant="z-1" className="space-y-3">
              <div className="flex items-center gap-2 border-b border-white/10 pb-2">
                <ClipboardList className="h-4 w-4 text-secondary-fixed-dim" />
                <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-outline">
                  LIVE TUTORIAL SAVE
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <MetricPill label="DAY" value={state.game_day} />
                <MetricPill label="CASH" value={formatVndCompact(state.cash)} />
                <MetricPill label="REP" value={`${state.reputation}%`} />
                <MetricPill label="REQUESTS" value={requests.data?.length ?? 0} />
              </div>

              {existingRequest ? (
                <div className="border border-white/10 bg-[#080a0d] p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-bold uppercase text-on-surface">{existingRequest.customer.name}</span>
                    <StatusChip
                      label={existingRequest.persona_type ?? "GENERIC"}
                      variant={getPersonaVariant(existingRequest.persona_type)}
                    />
                    <StatusChip label={existingRequest.status} variant="warning" />
                  </div>
                  <p className="mt-2 text-[11px] leading-relaxed text-on-surface-variant">
                    {existingRequest.request_type} // {existingRequest.use_case}
                  </p>
                  <div className="mt-3 grid gap-2 text-[10px] uppercase tracking-[0.18em] text-outline md:grid-cols-2">
                    <div className="border border-white/10 bg-white/[0.03] p-2">
                      Budget
                      <div className="mt-1 font-mono text-[11px] text-secondary-fixed-dim">
                        {formatVndCompact(existingRequest.budget_vnd)}
                      </div>
                    </div>
                    <div className="border border-white/10 bg-white/[0.03] p-2">
                      Used parts
                      <div className="mt-1 font-mono text-[11px] text-on-surface">
                        {existingRequest.accepts_used_parts ? "Allowed" : "Not preferred"}
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="border border-dashed border-white/10 bg-[#080a0d] p-4 text-[11px] leading-relaxed text-on-surface-variant">
                  No sample customer yet. The tutorial will generate one automatically. When it appears, you can use it
                  as your first real lead and follow the quote workflow from there.
                </div>
              )}

              <ActionButton
                disabled={generateCustomer.isPending}
                onClick={handleGenerateSampleCustomer}
                variant="primary"
                title={tutorialTooltip(tutorialMode && currentStep >= 1, "Generate the sample customer")}
              >
                {generateCustomer.isPending ? "GENERATING SAMPLE..." : "GENERATE FIRST WALK-IN"}
              </ActionButton>

              <div className="grid grid-cols-2 gap-2">
                <ActionButton
                  variant="secondary"
                  onClick={() => navigate("/customers")}
                  title={tutorialTooltip(tutorialMode && currentStep >= 2, "Open the customer desk")}
                >
                  Open Customer Desk
                </ActionButton>
                <ActionButton
                  variant="secondary"
                  onClick={() => setTutorialStep(3)}
                  title={tutorialTooltip(tutorialMode && currentStep >= 2, "Continue to practice")}
                >
                  Continue To Practice
                </ActionButton>
              </div>
            </ConsolePanel>
          </div>

          <ConsolePanel variant="z-1" className="space-y-3 bg-surface-container-high">
            <div className="flex items-center justify-between gap-3 border-b border-white/10 pb-2">
              <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-outline">
                TUTORIAL RUNNER
              </span>
              <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-primary-container">
                {tutorialMode ? "AUTO TOUR ACTIVE" : "MANUAL MODE"}
              </span>
            </div>
            <div className="grid grid-cols-4 gap-2">
              {TOUR_STEPS.map((step, index) => {
                const active = index === currentStep;
                return (
                  <div
                    key={step.title}
                    className={`border px-2 py-2 text-[10px] uppercase tracking-[0.16em] transition-all ${
                      active
                        ? "border-primary-container/60 bg-primary-container/10 text-primary-container"
                        : "border-white/10 bg-[#080a0d] text-on-surface-variant"
                    }`}
                  >
                    <div className="font-mono text-[9px]">{step.cue}</div>
                    <div className="mt-1 font-semibold leading-tight">{step.title}</div>
                  </div>
                );
              })}
            </div>
            <p className="text-[11px] leading-relaxed text-on-surface-variant">{currentTour.body}</p>
          </ConsolePanel>
        </div>
      </div>
    </section>
  );
}
