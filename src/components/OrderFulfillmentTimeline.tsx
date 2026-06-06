import type { OrderFulfillmentEvent } from "../types/game";
import { labelize } from "../utils/format";

interface OrderFulfillmentTimelineProps {
  events: OrderFulfillmentEvent[];
}

export function OrderFulfillmentTimeline({ events }: OrderFulfillmentTimelineProps) {
  if (events.length === 0) {
    return <p className="text-[10px] text-outline/40 italic p-3 text-center">No fulfillment events logged yet.</p>;
  }

  return (
    <div className="space-y-1.5 font-mono text-[10px]">
      {events.map((event) => (
        <div key={event.id} className="border border-white/5 bg-[#090b0e] p-2 flex flex-col gap-1">
          <div className="flex justify-between items-center select-none border-b border-white/[0.02] pb-1 mb-1">
            <span className="text-[#00f2ff] font-bold">[{labelize(event.event_type)}]</span>
            <span className="text-[9px] text-outline/40">{new Date(event.created_at).toLocaleString()}</span>
          </div>
          <p className="text-on-surface leading-snug">{event.summary}</p>
        </div>
      ))}
    </div>
  );
}
