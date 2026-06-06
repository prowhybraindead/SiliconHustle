import { useState } from "react";
import { Link } from "react-router-dom";
import { ConsolePanel } from "./ui/ConsolePanel";
import { StatusChip } from "./ui/StatusChip";
import { ActionButton } from "./ui/ActionButton";

interface ShowroomFloorMonitorProps {
  dashboardData: any;
  shopLevel: number;
}

interface EntityDot {
  type: string;
  colorClass: string;
  tooltip: string;
}

export function ShowroomFloorMonitor({ dashboardData, shopLevel }: ShowroomFloorMonitorProps) {
  const [selectedZone, setSelectedZone] = useState<string>("Entrance");

  const zones = [
    { name: "Entrance", style: { left: "0%", top: "0%", width: "22%", height: "25%" } },
    { name: "Display Area", style: { left: "24%", top: "0%", width: "52%", height: "55%" } },
    { name: "Sales Desk", style: { left: "78%", top: "0%", width: "22%", height: "25%" } },
    { name: "Expansion Wing", style: { left: "78%", top: "27%", width: "22%", height: "28%" } },
    { name: "Build Bay", style: { left: "0%", top: "27%", width: "22%", height: "28%" } },
    { name: "Test Bench", style: { left: "24%", top: "57%", width: "25%", height: "20%" } },
    { name: "Refurbish Bay", style: { left: "51%", top: "57%", width: "25%", height: "20%" } },
    { name: "Warehouse", style: { left: "0%", top: "57%", width: "22%", height: "43%" } },
    { name: "Warranty Desk", style: { left: "24%", top: "79%", width: "25%", height: "21%" } },
    { name: "Staff Room", style: { left: "51%", top: "79%", width: "25%", height: "21%" } },
    { name: "Market Terminal", style: { left: "78%", top: "57%", width: "22%", height: "43%" } },
  ];

  const zonesData: Record<
    string,
    {
      label: string;
      route: string;
      actionText: string;
      getDescription: (data: any) => string;
      getDots: (data: any) => EntityDot[];
    }
  > = {
    Entrance: {
      label: "ENTRANCE",
      route: "/customers",
      actionText: "Scout Walk-ins",
      getDescription: (data) =>
        `Showroom entrance reception. Walk-in queue has ${data.waiting_for_player_conversations_count ?? 0} customer(s) awaiting first contact.`,
      getDots: (data) => {
        const count = Math.max(0, (data.open_conversations_count ?? 0) - (data.waiting_for_player_conversations_count ?? 0));
        return Array(Math.min(6, count))
          .fill(null)
          .map((_, i) => ({
            type: "customer",
            colorClass: "bg-white shadow-[0_0_4px_#ffffff]",
            tooltip: `Walk-in Customer #${i + 1}`,
          }));
      },
    },
    "Display Area": {
      label: "DISPLAY AREA",
      route: "/catalog",
      actionText: "Manage Catalog",
      getDescription: (data) =>
        `Showroom display floor. Currently presenting catalog configurations. Staff are showcasing hardware variants.`,
      getDots: (data) => {
        const activeOrders = data.active_orders?.length ?? 0;
        return Array(Math.min(4, Math.max(1, activeOrders)))
          .fill(null)
          .map((_, i) => ({
            type: "staff-sales",
            colorClass: "bg-[#00f2ff] shadow-[0_0_4px_#00f2ff]",
            tooltip: `Staff Operator #${i + 1}`,
          }));
      },
    },
    "Sales Desk": {
      label: "SALES DESK",
      route: "/customer-chat",
      actionText: "Consult Customer",
      getDescription: (data) =>
        `Sales counter. ${data.customers_needing_consultation_count ?? 0} customer(s) waiting for active consultation. ${data.waiting_for_player_conversations_count ?? 0} awaiting quote decisions.`,
      getDots: (data) => {
        const dots: EntityDot[] = [];
        const alerts = data.customers_needing_consultation_count ?? 0;
        const waiting = data.waiting_for_player_conversations_count ?? 0;

        for (let i = 0; i < Math.min(4, alerts); i++) {
          dots.push({
            type: "customer-alert",
            colorClass: "bg-white border border-rose-500 text-rose-500 animate-pulse text-[8px] flex items-center justify-center font-black",
            tooltip: "Customer Awaiting Consultation",
          });
        }
        for (let i = 0; i < Math.min(4, waiting); i++) {
          dots.push({
            type: "customer",
            colorClass: "bg-white shadow-[0_0_4px_#ffffff]",
            tooltip: "Customer in Negotiation",
          });
        }
        return dots;
      },
    },
    "Expansion Wing": {
      label: "EXPANSION WING",
      route: "/progression",
      actionText: "Verify Upgrades",
      getDescription: () =>
        shopLevel >= 2
          ? "Showroom Expansion Wing unlocked and operating. Fitted with premium chassis frames."
          : "Locked station zone. Shop Level 2 operational license required for custom parts display slots.",
      getDots: () => [],
    },
    "Build Bay": {
      label: "BUILD BAY",
      route: "/orders",
      actionText: "Assemble Systems",
      getDescription: (data) =>
        `PC assembly lab. ${data.order_fulfillment_summary?.orders_in_progress ?? 0} active machine build(s) currently being wired by technicians.`,
      getDots: (data) => {
        const count = data.order_fulfillment_summary?.orders_in_progress ?? 0;
        return Array(Math.min(5, count))
          .fill(null)
          .map(() => ({
            type: "staff-tech",
            colorClass: "bg-[#ffba20] shadow-[0_0_4px_#ffba20]",
            tooltip: "Technician Assembling Rig",
          }));
      },
    },
    "Test Bench": {
      label: "TEST BENCH",
      route: "/orders",
      actionText: "Run Diagnostics",
      getDescription: (data) =>
        `Stress test terminal. ${data.order_fulfillment_summary?.orders_in_testing ?? 0} built rig(s) undergoing validation and stress checks.`,
      getDots: (data) => {
        const count = data.order_fulfillment_summary?.orders_in_testing ?? 0;
        return Array(Math.min(4, count))
          .fill(null)
          .map(() => ({
            type: "staff-analyst",
            colorClass: "bg-teal-400 shadow-[0_0_4px_rgba(45,212,191,0.5)]",
            tooltip: "Analyst running bench tests",
          }));
      },
    },
    "Refurbish Bay": {
      label: "REFURBISH BAY",
      route: "/refurbish",
      actionText: "Repair Components",
      getDescription: (data) =>
        `Parts repair workshop. ${data.warranty_summary?.diagnosing_warranty_claims ?? 0} warranty claims currently under repair and component cleaning.`,
      getDots: (data) => {
        const count = data.warranty_summary?.diagnosing_warranty_claims ?? 0;
        return Array(Math.min(4, count))
          .fill(null)
          .map(() => ({
            type: "staff-repair",
            colorClass: "bg-[#feb700] shadow-[0_0_4px_#feb700]",
            tooltip: "Repair technician repairing parts",
          }));
      },
    },
    Warehouse: {
      label: "WAREHOUSE",
      route: "/inventory",
      actionText: "Inspect Inventory",
      getDescription: (data) =>
        `Inventory storage facility. Total stock: ${data.inventory_summary?.total ?? 0} parts (${data.inventory_summary?.untested ?? 0} untested/raw items).`,
      getDots: (data) => {
        const untested = data.inventory_summary?.untested ?? 0;
        const dots: EntityDot[] = [];
        if (untested > 0) {
          dots.push({
            type: "staff-procurement",
            colorClass: "bg-emerald-400 shadow-[0_0_4px_rgba(52,211,153,0.5)]",
            tooltip: "Procurement clerk sorting stock",
          });
        }
        const displayCount = Math.min(6, Math.floor((data.inventory_summary?.total ?? 0) / 5));
        for (let i = 0; i < displayCount; i++) {
          dots.push({
            type: "inventory-crate",
            colorClass: "bg-gray-600 rounded-none w-1.5 h-1.5 border border-white/20",
            tooltip: "Stored parts crate",
          });
        }
        return dots;
      },
    },
    "Warranty Desk": {
      label: "WARRANTY DESK",
      route: "/warranty",
      actionText: "Open RMA Claims",
      getDescription: (data) =>
        `RMA Intake. ${data.warranty_summary?.open_warranty_claims ?? 0} active claim file(s). Warranty cost exposure: ₫${(data.warranty_summary?.warranty_cost_exposure ?? 0).toLocaleString()}.`,
      getDots: (data) => {
        const count = data.warranty_summary?.open_warranty_claims ?? 0;
        return Array(Math.min(4, count))
          .fill(null)
          .map(() => ({
            type: "staff-warranty",
            colorClass: "bg-rose-400 shadow-[0_0_4px_rgba(248,113,113,0.5)]",
            tooltip: "RMA Coordinator processing claims",
          }));
      },
    },
    "Staff Room": {
      label: "STAFF ROOM",
      route: "/staff",
      actionText: "Manage Personnel",
      getDescription: (data) =>
        `Employee room. Total headcount: ${data.staff_count ?? 0}. ${data.available_staff_count ?? 0} staff operator(s) resting or on standby.`,
      getDots: (data) => {
        const count = data.available_staff_count ?? 0;
        return Array(Math.min(6, count))
          .fill(null)
          .map(() => ({
            type: "staff-idle",
            colorClass: "bg-gray-500 shadow-[0_0_4px_rgba(156,163,175,0.5)]",
            tooltip: "Standby staff resting",
          }));
      },
    },
    "Market Terminal": {
      label: "MARKET TERMINAL",
      route: "/market",
      actionText: "Track Trends",
      getDescription: (data) =>
        `FX & Trade indices. Current active event disruptions: ${data.market_summary?.active_market_events_count ?? 0}. Pressures: ${data.market_summary?.market_pressure_summary ?? "Stable"}.`,
      getDots: (data) => {
        const events = data.market_summary?.active_market_events_count ?? 0;
        return Array(Math.min(3, events))
          .fill(null)
          .map(() => ({
            type: "staff-marketing",
            colorClass: "bg-purple-400 shadow-[0_0_4px_rgba(168,85,247,0.5)]",
            tooltip: "Marketing coordinator auditing pressures",
          }));
      },
    },
  };

  const activeZoneInfo = zonesData[selectedZone] || {
    label: "UNKNOWN STATION",
    route: "/dashboard",
    actionText: "Scan Diagnostics",
    getDescription: () => "Zone metadata corrupted.",
    getDots: () => [],
  };

  return (
    <ConsolePanel className="flex flex-col xl:flex-row gap-4 h-full min-h-[380px]" variant="z-1">
      {/* Schematic Floor Grid */}
      <div className="flex-1 relative bg-[#07090b] border border-white/10 overflow-hidden h-[300px] xl:h-auto select-none">
        <div className="absolute inset-0 blueprint-grid opacity-15 pointer-events-none" />

        {zones.map((zone) => {
          const isSelected = selectedZone === zone.name;
          const isExpansion = zone.name === "Expansion Wing";
          const isLocked = isExpansion && shopLevel < 2;
          const info = zonesData[zone.name];
          const dots = info ? info.getDots(dashboardData) : [];

          return (
            <div
              key={zone.name}
              style={zone.style}
              onClick={() => setSelectedZone(zone.name)}
              className={`absolute border transition-all duration-150 cursor-pointer flex flex-col p-1.5 justify-between group ${
                isLocked
                  ? "bg-stripes border-white/5 cursor-not-allowed opacity-40 hover:opacity-50"
                  : isSelected
                  ? "bg-primary-container/10 border-primary-container text-primary-container"
                  : "bg-[#090b0e]/85 border-white/10 hover:border-white/30 text-outline"
              }`}
            >
              <div className="flex justify-between items-start">
                <span className="font-mono text-[8px] uppercase tracking-wider font-bold">
                  {zone.name}
                </span>
                {isLocked && (
                  <span className="font-mono text-[7px] text-rose-400 border border-rose-500/20 px-1 bg-rose-500/10">
                    LOCKED
                  </span>
                )}
              </div>

              {/* Occupants Dots Display */}
              <div className="flex flex-wrap gap-1 justify-start max-w-full overflow-hidden max-h-[22px] mt-1 select-none">
                {dots.map((dot, index) => (
                  <div
                    key={index}
                    title={dot.tooltip}
                    className={`w-1.5 h-1.5 rounded-full ${dot.colorClass}`}
                  >
                    {dot.type === "customer-alert" && "!"}
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* Inspector Panel */}
      <div className="w-full xl:w-[220px] flex flex-col justify-between border-t xl:border-t-0 xl:border-l border-white/10 pt-3 xl:pt-0 xl:pl-4 font-mono select-none">
        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-[10px] text-outline uppercase">ZONE REPORT</span>
            <StatusChip
              label={selectedZone === "Expansion Wing" && shopLevel < 2 ? "LOCKED" : "ACTIVE"}
              variant={selectedZone === "Expansion Wing" && shopLevel < 2 ? "error" : "success"}
            />
          </div>
          <div>
            <h3 className="text-sm font-bold text-on-surface tracking-wider">
              {activeZoneInfo.label}
            </h3>
            <div className="h-[1px] bg-white/10 my-1.5" />
            <p className="text-[10px] text-outline leading-relaxed">
              {activeZoneInfo.getDescription(dashboardData)}
            </p>
          </div>

          {/* Dot Color Legend */}
          <div className="space-y-1.5 bg-[#090b0e] border border-white/5 p-2 text-[9px] text-outline">
            <span className="text-[8px] text-outline/50 uppercase block font-bold border-b border-white/5 pb-1 mb-1">
              OCCUPANT LEGEND
            </span>
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-white shadow-[0_0_4px_#ffffff]" />
              <span>Customer</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[#00f2ff] shadow-[0_0_4px_#00f2ff]" />
              <span>Sales Staff</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[#ffba20] shadow-[0_0_4px_#ffba20]" />
              <span>Technician</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[#feb700] shadow-[0_0_4px_#feb700]" />
              <span>Repair Operator</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />
              <span>RMA Support</span>
            </div>
          </div>
        </div>

        <div className="pt-4 mt-auto">
          {selectedZone === "Expansion Wing" && shopLevel < 2 ? (
            <div className="text-[9px] text-rose-400 italic text-center p-2 border border-rose-500/10 bg-rose-500/5">
              LICENSE REQ: LEVEL 2
            </div>
          ) : (
            <Link to={activeZoneInfo.route}>
              <ActionButton className="h-9 text-[10px]" variant="primary">
                {activeZoneInfo.actionText}
              </ActionButton>
            </Link>
          )}
        </div>
      </div>
    </ConsolePanel>
  );
}
