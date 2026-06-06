import { Link } from "react-router-dom";
import { useDashboardState, useProgression } from "../api/hooks";
import { useGameStore } from "../store/gameStore";
import { EmptyState } from "../components/EmptyState";
import { LoadingState } from "../components/LoadingState";
import { ErrorState } from "../components/ErrorState";

import { ConsolePanel } from "../components/ui/ConsolePanel";
import { SectionHeader } from "../components/ui/SectionHeader";
import { StatusChip } from "../components/ui/StatusChip";
import { ActionButton } from "../components/ui/ActionButton";

export function OperationsPage() {
  const saveId = useGameStore((state) => state.selectedSaveId);
  const state = useDashboardState(saveId);
  const progression = useProgression(saveId);

  if (!saveId) return <EmptyState title="No save selected" body="Open or create a save game from the home screen." />;
  if (state.isLoading || progression.isLoading) return <LoadingState />;
  if (state.isError) return <ErrorState message={(state.error as Error).message} />;

  const dashboard = state.data;
  if (!dashboard) return null;

  const shopLevel = progression.data?.shop_level ?? 1;
  const progressionSummary = (progression.data?.summary ?? {}) as Record<string, unknown>;

  const workflowLanes = [
    {
      title: "1. ACQUISITION & FULFILLMENT PIPELINE",
      description: "Convert customer walk-ins into completed, warrantied PC builds.",
      nodes: [
        { label: "CUSTOMERS", route: "/customers", count: dashboard.open_conversations_count ?? 0, status: "READY" },
        {
          label: "SALES CHAT",
          route: "/customer-chat",
          count: dashboard.waiting_for_player_conversations_count ?? 0,
          status: (dashboard.waiting_for_player_conversations_count ?? 0) > 0 ? "URGENT" : "STABLE",
        },
        { label: "QUOTES", route: "/quotes", count: dashboard.quote_summary?.quoted_not_accepted ?? 0, status: "PENDING" },
        {
          label: "ASSEMBLY",
          route: "/orders",
          count: dashboard.order_fulfillment_summary?.orders_in_progress ?? 0,
          status: "BUILDING",
        },
        {
          label: "DISPATCH",
          route: "/orders",
          count: dashboard.order_fulfillment_summary?.delivered_orders ?? 0,
          status: "LOGGED",
        },
      ],
    },
    {
      title: "2. PARTS PROCUREMENT & SUPPLY LINE",
      description: "Purchase raw hardware stock from wholesale supplier desks.",
      nodes: [
        { label: "SUPPLIERS", route: "/suppliers", count: null, status: "OFFERS" },
        { label: "EXCHANGE", route: "/currency", count: null, status: "FX RATE" },
        { label: "WAREHOUSE", route: "/inventory", count: dashboard.inventory_summary?.total ?? 0, status: "MANIFEST" },
        {
          label: "ASSEMBLY",
          route: "/orders",
          count: dashboard.order_fulfillment_summary?.orders_in_progress ?? 0,
          status: "BUILDING",
        },
      ],
    },
    {
      title: "3. USED MARKET RECYCLING & RESALE",
      description: "Acquire used parts, run bench diagnostics, repaste, and resell.",
      nodes: [
        { label: "USED MARKET", route: "/used-market", count: null, status: "BARGAIN" },
        {
          label: "TEST BENCH",
          route: "/orders",
          count: dashboard.order_fulfillment_summary?.orders_in_testing ?? 0,
          status: "STRESS",
        },
        {
          label: "REFURBISH",
          route: "/refurbish",
          count: dashboard.warranty_summary?.diagnosing_warranty_claims ?? 0,
          status: "REPAIR",
        },
        { label: "RESALE", route: "/resale", count: null, status: "LISTINGS" },
      ],
    },
    {
      title: "4. STAFF SCHEDULING & REST ROTATION",
      description: "Assign operator tasks and balance mental fatigue constraints.",
      nodes: [
        { label: "STAFF ROOM", route: "/staff", count: dashboard.staff_count ?? 0, status: "ROSTER" },
        { label: "STANDBY", route: "/staff", count: dashboard.available_staff_count ?? 0, status: "STANDBY" },
        {
          label: "ASSIGNED",
          route: "/staff",
          count: Math.max(0, (dashboard.staff_count ?? 0) - (dashboard.available_staff_count ?? 0)),
          status: "ON-TASK",
        },
      ],
    },
    {
      title: "5. CAPITAL DEPLOYMENT & UPGRADE BLUEPRINTS",
      description: "Expand physical square footage and procure high-tier workbench licenses.",
      nodes: [
        { label: "SHOP LEVEL", route: "/progression", count: shopLevel, status: "LICENSED" },
        { label: "UPGRADES", route: "/progression", count: Number(progressionSummary.purchased_upgrades_count ?? 0), status: "DEPLOYED" },
      ],
    },
    {
      title: "6. GLOBAL MACRO EVENTS & MARKET LOGS",
      description: "Audit supply multipliers and customer pricing category pressures.",
      nodes: [
        { label: "EVENTS", route: "/market", count: dashboard.market_summary?.active_market_events_count ?? 0, status: "ACTIVE" },
        { label: "FX MARKET", route: "/currency", count: null, status: "INDEX" },
      ],
    },
  ];

  // Derive recommended next action
  let recommendedAction = "Scout used components on the used market desk.";
  if ((dashboard.waiting_for_player_conversations_count ?? 0) > 0) {
    recommendedAction = "Address pending walk-ins awaiting sales chat consultation.";
  } else if (dashboard.order_fulfillment_summary?.orders_in_progress > 0) {
    recommendedAction = "Verify and wiring assembly logs in the Build Bay.";
  } else if (dashboard.warranty_summary?.open_warranty_claims > 0) {
    recommendedAction = "Review and clean returned parts under Warranty RMA Desk.";
  }

  // Derive bottlenecks
  let bottleneckLabel = "NOMINAL OPERATIONS";
  let bottleneckDesc = "All pipelines operating within safe parameters.";
  if (dashboard.inventory_summary?.untested > 0) {
    bottleneckLabel = "WAREHOUSE BACKLOG";
    bottleneckDesc = `There are ${dashboard.inventory_summary.untested} untested units in inventory storage queue.`;
  } else if ((dashboard.waiting_for_player_conversations_count ?? 0) > 0) {
    bottleneckLabel = "SALES DESK CONGESTION";
    bottleneckDesc = "Walk-in customers are stalling waiting for quote options.";
  } else if (dashboard.warranty_summary?.open_warranty_claims > 2) {
    bottleneckLabel = "RMA LOGJAM";
    bottleneckDesc = "High count of claims pending manual repair/refund resolutions.";
  }

  return (
    <section className="space-y-4">
      <SectionHeader title="Operations Board" subtitle="TACTICAL STATION SCHEMATICS // PIPELINE CONTROL MAP" />

      <div className="grid gap-4 xl:grid-cols-[1.5fr_1fr]">
        {/* Left Column: Visual workflow lanes */}
        <div className="space-y-4">
          {workflowLanes.map((lane, index) => (
            <ConsolePanel key={index} variant="z-1" className="space-y-2.5 font-mono text-[11px]">
              <div>
                <h3 className="text-xs font-bold text-on-surface tracking-wider uppercase">
                  {lane.title}
                </h3>
                <p className="text-[10px] text-outline mt-0.5">
                  {lane.description}
                </p>
              </div>

              {/* Lane Nodes Flow */}
              <div className="flex flex-wrap items-center gap-2 bg-[#080a0d] border border-white/5 p-3 select-none">
                {lane.nodes.map((node, nodeIdx) => (
                  <div key={nodeIdx} className="flex items-center gap-2">
                    <Link to={node.route}>
                      <div className="border border-white/10 bg-[#0c0f13] hover:border-primary-container hover:bg-primary-container/[0.04] p-2 text-center w-[115px] transition-all cursor-pointer">
                        <span className="text-[9px] text-outline block truncate">
                          {node.label}
                        </span>
                        <span className="text-[10px] font-bold text-on-surface block mt-1">
                          {node.count !== null ? `[QTY: ${node.count}]` : `[${node.status}]`}
                        </span>
                      </div>
                    </Link>
                    {nodeIdx < lane.nodes.length - 1 && (
                      <span className="text-outline/40 font-bold shrink-0">→</span>
                    )}
                  </div>
                ))}
              </div>
            </ConsolePanel>
          ))}
        </div>

        {/* Right Column: Bottlenecks, Actions, and Quick Verbs */}
        <div className="space-y-4">
          {/* Bottleneck log panel */}
          <ConsolePanel variant="z-1" className="space-y-3 font-mono text-[11px] select-none">
            <div className="flex justify-between items-center border-b border-white/10 pb-2">
              <span className="text-[10px] text-outline uppercase">DIAGNOSTIC REPORT</span>
              <StatusChip
                label={bottleneckLabel === "NOMINAL OPERATIONS" ? "NOMINAL" : "WARNING"}
                variant={bottleneckLabel === "NOMINAL OPERATIONS" ? "success" : "warning"}
              />
            </div>
            <div>
              <span className="text-[9px] text-outline/50 block">CRITICAL CONSTRAINTS</span>
              <span className="text-xs font-bold text-on-surface uppercase block mt-1">
                {bottleneckLabel}
              </span>
              <p className="text-[10px] text-outline mt-1 leading-relaxed">
                {bottleneckDesc}
              </p>
            </div>
          </ConsolePanel>

          {/* Recommended next action panel */}
          <ConsolePanel variant="z-1" className="space-y-3 font-mono text-[11px] select-none">
            <div className="flex justify-between items-center border-b border-white/10 pb-2">
              <span className="text-[10px] text-outline uppercase">REC DECISION LOG</span>
              <span className="text-[9px] text-[#00f2ff]">[EXECUTION]</span>
            </div>
            <div>
              <p className="text-[10px] text-[#00f2ff] leading-relaxed border-l-2 border-primary-container pl-2 py-0.5">
                {recommendedAction}
              </p>
            </div>
          </ConsolePanel>

          {/* Urgent Alerts panel */}
          <ConsolePanel variant="z-1" className="space-y-3 font-mono text-[11px] select-none">
            <div className="flex justify-between items-center border-b border-white/10 pb-2">
              <span className="text-[10px] text-outline uppercase">TELEMETRY THRESHOLDS</span>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between bg-[#080a0d] border border-white/5 p-2 items-center">
                <span className="text-[9px] text-outline">LIQUID FUNDS</span>
                <span className={`text-xs font-bold ${dashboard.cash < 500000 ? "text-[#ffba20]" : "text-on-surface"}`}>
                  ₫{dashboard.cash.toLocaleString()}
                </span>
              </div>
              <div className="flex justify-between bg-[#080a0d] border border-white/5 p-2 items-center">
                <span className="text-[9px] text-outline">RMA COST LIABILITY</span>
                <span
                  className={`text-xs font-bold ${
                    (dashboard.warranty_summary?.warranty_cost_exposure ?? 0) > 1000000 ? "text-rose-400" : "text-on-surface"
                  }`}
                >
                  ₫{(dashboard.warranty_summary?.warranty_cost_exposure ?? 0).toLocaleString()}
                </span>
              </div>
            </div>
          </ConsolePanel>

          {/* Quick actions desk redirect triggers */}
          <ConsolePanel variant="z-1" className="space-y-3 font-mono text-[11px]">
            <div className="flex justify-between items-center border-b border-white/10 pb-2 select-none">
              <span className="text-[10px] text-outline uppercase">QUICK OPERATIONS DESKS</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <Link to="/customers">
                <ActionButton variant="secondary" className="h-9 text-[9px]">
                  CUSTOMER DESK
                </ActionButton>
              </Link>
              <Link to="/customer-chat">
                <ActionButton variant="secondary" className="h-9 text-[9px]">
                  SALES CHAT
                </ActionButton>
              </Link>
              <Link to="/orders">
                <ActionButton variant="secondary" className="h-9 text-[9px]">
                  BUILD BAY
                </ActionButton>
              </Link>
              <Link to="/used-market">
                <ActionButton variant="secondary" className="h-9 text-[9px]">
                  USED MARKET
                </ActionButton>
              </Link>
              <Link to="/warranty">
                <ActionButton variant="secondary" className="h-9 text-[9px]">
                  RMA DESK
                </ActionButton>
              </Link>
              <Link to="/progression">
                <ActionButton variant="secondary" className="h-9 text-[9px]">
                  UPGRADE SHOP
                </ActionButton>
              </Link>
            </div>
          </ConsolePanel>
        </div>
      </div>
    </section>
  );
}
