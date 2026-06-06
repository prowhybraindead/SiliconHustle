import { useState } from "react";
import { ConsolePanel } from "./ui/ConsolePanel";

interface LiveOpsFeedProps {
  dashboardData: {
    recent_reviews?: any[];
    recent_conversation_messages?: any[];
    recent_fulfillment_events?: any[];
    recent_warranty_events?: any[];
    market_summary?: {
      active_market_events_count: number;
      strongest_market_multiplier: number;
      market_pressure_summary: string;
    };
  };
}

interface LogItem {
  id: string;
  type: "CHAT" | "BUILD" | "RMA" | "REVIEW" | "MARKET";
  label: string;
  text: string;
  sortKey: number;
}

export function LiveOpsFeed({ dashboardData }: LiveOpsFeedProps) {
  const [filter, setFilter] = useState<"ALL" | "CHAT" | "BUILD" | "RMA" | "REVIEW" | "MARKET">("ALL");

  const logs: LogItem[] = [];

  if (dashboardData.recent_conversation_messages) {
    dashboardData.recent_conversation_messages.forEach((msg: any) => {
      logs.push({
        id: `chat-${msg.id}`,
        type: "CHAT",
        label: `CHAT // CONV #${msg.conversation_id}`,
        text: `${msg.sender_type.toUpperCase()}: ${msg.body}`,
        sortKey: Number(msg.id) || 0,
      });
    });
  }

  if (dashboardData.recent_reviews) {
    dashboardData.recent_reviews.forEach((rev: any) => {
      logs.push({
        id: `rev-${rev.id}`,
        type: "REVIEW",
        label: `REVIEW // ${rev.sentiment}`,
        text: `(${rev.source_type.toUpperCase()}) ${rev.title} - ${rev.source_summary ?? rev.body ?? ""}`,
        sortKey: Number(rev.id) || 0,
      });
    });
  }

  if (dashboardData.recent_fulfillment_events) {
    dashboardData.recent_fulfillment_events.forEach((evt: any) => {
      logs.push({
        id: `fulfillment-${evt.id}`,
        type: "BUILD",
        label: `BUILD // ${evt.event_type}`,
        text: `ORDER #${evt.order_id}: ${evt.summary}`,
        sortKey: Number(evt.id) || 0,
      });
    });
  }

  if (dashboardData.recent_warranty_events) {
    dashboardData.recent_warranty_events.forEach((evt: any) => {
      logs.push({
        id: `warranty-${evt.id}`,
        type: "RMA",
        label: `RMA // ${evt.event_type}`,
        text: `CLAIM #${evt.claim_id}: ${evt.summary}`,
        sortKey: Number(evt.id) || 0,
      });
    });
  }

  if (dashboardData.market_summary?.market_pressure_summary) {
    logs.push({
      id: "market-pressure",
      type: "MARKET",
      label: "MARKET // PRESSURES",
      text: dashboardData.market_summary.market_pressure_summary,
      sortKey: 999999, // keep at top
    });
  }

  // Sort by sortKey descending (newest first)
  logs.sort((a, b) => b.sortKey - a.sortKey);

  const filteredLogs = filter === "ALL" ? logs : logs.filter((log) => log.type === filter);

  // Type color mappings matching console variables
  const typeColors = {
    CHAT: "text-[#00f2ff]", // Neon cyan
    BUILD: "text-[#74f5ff]", // Light blue
    RMA: "text-rose-400", // Error/Warning pink-red
    REVIEW: "text-[#ffba20]", // Warning yellow
    MARKET: "text-purple-300", // Market purple
  };

  const typeBgs = {
    CHAT: "bg-[#00f2ff]/10 border-[#00f2ff]/20",
    BUILD: "bg-[#74f5ff]/10 border-[#74f5ff]/20",
    RMA: "bg-rose-500/10 border-rose-500/20",
    REVIEW: "bg-[#ffba20]/10 border-[#ffba20]/20",
    MARKET: "bg-purple-500/10 border-purple-500/20",
  };

  return (
    <ConsolePanel className="flex flex-col h-[380px]" variant="z-1">
      {/* Header Tab Filters */}
      <div className="flex justify-between items-center border-b border-white/10 pb-2 mb-3 select-none flex-wrap gap-2">
        <span className="font-mono text-[10px] uppercase tracking-wider text-outline">
          LIVE OPERATIONS LOGGER
        </span>
        <div className="flex gap-1.5 font-mono text-[9px]">
          {(["ALL", "CHAT", "BUILD", "RMA", "REVIEW", "MARKET"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setFilter(t)}
              className={`px-1.5 py-0.5 border cursor-pointer ${
                filter === t
                  ? "bg-primary-container text-on-primary-fixed border-primary-container font-black"
                  : "bg-transparent text-outline border-white/10 hover:text-on-surface hover:bg-white/5"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Console Display Screen */}
      <div className="flex-1 overflow-y-auto bg-[#080a0d] border border-white/5 p-3 font-mono text-[11px] leading-relaxed console-scrollbar">
        {filteredLogs.length === 0 ? (
          <div className="text-outline/40 italic flex items-center justify-center h-full">
            NO LOGGED TELEMETRY FOR FILTER [{filter}]
          </div>
        ) : (
          <div className="space-y-2.5">
            {filteredLogs.map((log) => (
              <div key={log.id} className="flex gap-2 items-start border-b border-white/[0.02] pb-2">
                <span
                  className={`px-1.5 py-0.5 border text-[9px] font-bold tracking-wider shrink-0 ${typeBgs[log.type]} ${typeColors[log.type]}`}
                >
                  {log.label}
                </span>
                <span className="text-on-surface flex-1 word-break break-words">
                  {log.text}
                </span>
              </div>
            ))}
            <div className="flex items-center text-outline/30 select-none">
              AWAITING INCOMING EVENT STREAMS
              <span className="inline-block w-1.5 h-3 bg-primary-container animate-pulse ml-1 align-middle" />
            </div>
          </div>
        )}
      </div>
    </ConsolePanel>
  );
}
