import type { QuoteItem } from "../types/game";
import { useGameStore } from "../store/gameStore";
import { BrandLogo } from "./BrandLogo";
import { StatusChip } from "./ui/StatusChip";

interface QuoteItemRowProps {
  item: QuoteItem;
}

export function QuoteItemRow({ item }: QuoteItemRowProps) {
  const uiLanguage = useGameStore((state) => state.uiLanguage);
  const isInventory = item.source === "INVENTORY";
  const isSupplier = item.source === "SUPPLIER_NEEDED";

  return (
    <div className="font-mono text-[11px] border border-white/5 bg-[#090b0e] p-2.5 flex flex-col md:flex-row md:items-center justify-between gap-2 hover:border-white/10 transition">
      <div className="flex items-center gap-3 min-w-0">
        <BrandLogo
          brand={item.product.brand_ref}
          logoUrl={item.product.effective_logo_url}
          name={item.product.brand}
          size="sm"
        />
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="font-bold text-on-surface truncate">{item.product.name}</span>
            <span className="text-[8px] border border-white/10 bg-white/[0.02] px-1 text-outline">
              {item.product.category.toUpperCase()}
            </span>
            <StatusChip label={item.source} variant={isInventory ? "success" : isSupplier ? "warning" : "neutral"} />
          </div>
          <div className="text-[10px] text-outline mt-0.5">
            {uiLanguage === "en" ? "QTY" : "SL"}: {item.quantity} // {item.notes ?? (uiLanguage === "en" ? "NO NOTES" : "KHÔNG CÓ GHI CHÚ")}
          </div>
        </div>
      </div>

      <div className="flex flex-wrap md:flex-nowrap gap-4 items-center justify-between md:justify-end shrink-0 select-none">
        <div className="text-outline">
          {uiLanguage === "en" ? "UNIT PRICE" : "GIÁ BÁN ĐƠN VỊ"}: <span className="font-bold text-emerald-400">₫{item.unit_price_vnd.toLocaleString()}</span>
        </div>
        <div className="text-outline">
          {uiLanguage === "en" ? "UNIT COST" : "GIÁ VỐN ĐƠN VỊ"}: <span className="font-bold text-on-surface">₫{item.unit_cost_vnd.toLocaleString()}</span>
        </div>
        <div className="flex gap-1.5">
          {item.inventory_unit && (
            <StatusChip
              label={item.inventory_unit.status}
              variant={item.inventory_unit.status === "RESERVED" ? "warning" : "success"}
            />
          )}
          <StatusChip label={item.is_reserved ? "RESERVED" : "NOT_RESERVED"} variant={item.is_reserved ? "warning" : "neutral"} />
        </div>
      </div>
    </div>
  );
}
