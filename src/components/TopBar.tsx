import { Link } from "react-router-dom";
import { Wallet, Star, CalendarDays, ShieldCheck } from "lucide-react";

import { useGameStore } from "../store/gameStore";
import { useSaveGames } from "../api/hooks";
import { BrandWordmark } from "./BrandWordmark";
import { formatVndCompact, pickUiText } from "../utils/format";

export function TopBar() {
  const saveId = useGameStore((state) => state.selectedSaveId);
  const uiLanguage = useGameStore((state) => state.uiLanguage);
  const savesQuery = useSaveGames();
  const currentSave = savesQuery.data?.find((s) => s.id === saveId);

  return (
    <header className="fixed top-0 left-0 right-0 w-full z-50 h-12 flex justify-between items-center px-margin-safe bg-surface-container-low/80 backdrop-blur-md border-b border-white/10 transition-all select-none">
      <Link className="flex items-center gap-2 group" to="/">
        <BrandWordmark className="max-w-[140px] sm:max-w-[175px]" eager size="sm" />
        <div className="h-4 w-[1px] bg-white/20 mx-1 hidden sm:block" />
        <span className="hidden sm:inline font-mono text-[10px] text-primary-container/80 uppercase tracking-widest">
          {pickUiText("TRẠM_01_TRỰC_TUYẾN", "STATION_01_ONLINE", uiLanguage)}
        </span>
      </Link>

      {currentSave ? (
        <div className="flex gap-4 sm:gap-6 items-center">
          <div className="flex items-center gap-1.5 font-mono text-[11px] text-on-surface">
            <Wallet className="h-3.5 w-3.5 text-outline shrink-0" />
            <span>{formatVndCompact(currentSave.cash)}</span>
          </div>

          <div className="h-4 w-[1px] bg-white/20" />

          <div className="flex items-center gap-1.5 font-mono text-[11px] text-on-surface">
            <Star className="h-3.5 w-3.5 text-outline shrink-0" />
            <span>{currentSave.reputation}%</span>
          </div>

          <div className="h-4 w-[1px] bg-white/20" />

          <div className="flex items-center gap-1.5 font-mono text-[11px] text-secondary-fixed-dim">
            <CalendarDays className="h-3.5 w-3.5 text-outline shrink-0" />
            <span>{pickUiText("NGÀY", "DAY", uiLanguage)} {currentSave.game_day}</span>
          </div>

          <div className="h-4 w-[1px] bg-white/20 hidden sm:block" />

          <div className="hidden sm:flex items-center gap-1 font-mono text-[10px] bg-surface-variant/80 border border-white/10 px-2 py-0.5 text-primary-container rounded-[2px] uppercase">
            <ShieldCheck className="h-3 w-3" />
            <span>{pickUiText("An toàn", "Secure", uiLanguage)}</span>
          </div>
        </div>
      ) : (
        <div className="font-mono text-[10px] text-tech-amber/80 tracking-wider uppercase hidden sm:block">
          {pickUiText("Chưa có bản lưu // hãy giữ hệ thống ổn định", "No save loaded // keep the system stable", uiLanguage)}
        </div>
      )}
    </header>
  );
}
