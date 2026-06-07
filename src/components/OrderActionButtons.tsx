import { PackageCheck, Play, TestTube2 } from "lucide-react";

import type { Order } from "../types/game";
import { useGameStore } from "../store/gameStore";
import { ActionButton } from "./ui/ActionButton";

interface OrderActionButtonsProps {
  order: Order;
  isBusy?: boolean;
  onStartBuild: (orderId: number) => void;
  onRunBuildTest: (orderId: number) => void;
  onDeliver: (orderId: number) => void;
}

export function OrderActionButtons({ order, isBusy, onStartBuild, onRunBuildTest, onDeliver }: OrderActionButtonsProps) {
  const uiLanguage = useGameStore((state) => state.uiLanguage);

  if (order.status === "DELIVERED") {
    return (
      <div className="font-mono text-[9px] text-[#00f2ff] border border-[#00f2ff]/20 bg-[#00f2ff]/5 px-2.5 py-1 uppercase font-bold tracking-wider select-none">
        {uiLanguage === "en" ? "DELIVERED" : "ĐÃ GIAO"}
      </div>
    );
  }

  if (order.status === "ACCEPTED") {
    return (
      <ActionButton
        variant="primary"
        className="h-8 text-[9px] px-3 w-auto shrink-0"
        disabled={isBusy}
        onClick={() => onStartBuild(order.id)}
      >
        <Play className="h-3 w-3" />
        {uiLanguage === "en" ? "START BUILD" : "BẮT ĐẦU LẮP RÁP"}
      </ActionButton>
    );
  }

  if (order.status === "IN_PROGRESS") {
    return (
      <ActionButton
        variant="secondary"
        className="h-8 text-[9px] px-3 w-auto shrink-0"
        disabled={isBusy}
        onClick={() => onRunBuildTest(order.id)}
      >
        <TestTube2 className="h-3 w-3" />
        {uiLanguage === "en" ? "RUN BUILD TEST" : "CHẠY KIỂM TRA LẮP RÁP"}
      </ActionButton>
    );
  }

  if (order.status === "TESTING") {
    return (
      <ActionButton
        variant="primary"
        className="h-8 text-[9px] px-3 w-auto shrink-0"
        disabled={isBusy}
        onClick={() => onDeliver(order.id)}
      >
        <PackageCheck className="h-3 w-3" />
        {uiLanguage === "en" ? "DELIVER ORDER" : "GIAO HÀNG"}
      </ActionButton>
    );
  }

  return <span className="font-mono text-[9px] text-outline/30 uppercase select-none">{uiLanguage === "en" ? "NO ACTION" : "KHÔNG CÓ HÀNH ĐỘNG"}</span>;
}
