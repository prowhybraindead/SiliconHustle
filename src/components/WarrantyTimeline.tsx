import type { WarrantyEvent } from "../types/game";
import { labelize } from "../utils/format";
import { StatusChip } from "./ui/StatusChip";

interface WarrantyTimelineProps {
  events: WarrantyEvent[];
}

export function WarrantyTimeline({ events }: WarrantyTimelineProps) {
  if (events.length === 0) {
    return <p className="text-xs font-mono text-slate-500 uppercase">No warranty events logged.</p>;
  }

  return (
    <div className="bg-[#0c0e11] p-3 font-mono text-[10px] text-slate-400 max-h-60 overflow-y-auto space-y-2 rounded-sm border border-white/5">
      {events.map((event) => (
        <div className="border-b border-white/5 pb-2 last:border-0 last:pb-0 space-y-1" key={event.id}>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="font-mono text-[10px] text-[#00f2ff] font-bold uppercase">{labelize(event.event_type)}</span>
            <span className="font-mono text-[9px] text-slate-600">
              {new Date(event.created_at).toLocaleString()}
            </span>
          </div>
          <p className="text-slate-300 italic normal-case">"{event.summary}"</p>
        </div>
      ))}
    </div>
  );
}
