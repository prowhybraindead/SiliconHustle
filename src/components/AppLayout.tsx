import { useEffect, useState, type FormEvent } from "react";
import { Outlet, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Delete, LogIn } from "lucide-react";

import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { EmptyState } from "./EmptyState";
import { useGameStore } from "../store/gameStore";
import { ApiError, apiRequest, unlockPlayerProfile } from "../api/client";
import { useCreateSaveGame, useSaveGames } from "../api/hooks";
import type { SaveGame } from "../types/game";
import { getErrorMessage } from "../utils/error";
import { formatVndCompact } from "../utils/format";

function getInitials(name: string) {
  return (
    name
      .split(/[\s_-]+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase() ?? "")
      .join("")
      .slice(0, 2) || "SH"
  );
}

function formatSyncTime(value: string | null | undefined) {
  if (!value) return "UNKNOWN";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "UNKNOWN";
  return `${date.toLocaleTimeString("en-GB", {
    hour12: false,
    timeZone: "UTC",
  })} UTC`;
}

export function AppLayout() {
  const saveId = useGameStore((state) => state.selectedSaveId);
  const setSelectedSaveId = useGameStore((state) => state.setSelectedSaveId);
  const startTutorial = useGameStore((state) => state.startTutorial);
  const endTutorial = useGameStore((state) => state.endTutorial);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const savesQuery = useSaveGames();
  const createSave = useCreateSaveGame();

  const saveDetail = useQuery({
    queryKey: ["active-save-detail", saveId],
    queryFn: () => apiRequest<SaveGame>(`/api/save-games/${saveId}`),
    enabled: Boolean(saveId),
    retry: false,
  });

  const [pin, setPin] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [lockoutTime, setLockoutTime] = useState<number | null>(null);

  const currentSave = savesQuery.data?.find((save) => save.id === saveId);
  const isLocked = saveDetail.error instanceof ApiError && saveDetail.error.status === 403;
  const profileId = currentSave?.player_profile_id;
  const profileName = currentSave?.profile_display_name ?? currentSave?.name ?? "Security Profile";
  const profileSync = formatSyncTime(currentSave?.last_autosave_at ?? currentSave?.updated_at);

  useEffect(() => {
    if (lockoutTime !== null && lockoutTime > 0) {
      const timer = setTimeout(() => setLockoutTime(lockoutTime - 1), 1000);
      return () => clearTimeout(timer);
    }

    if (lockoutTime === 0) {
      setLockoutTime(null);
      setErrorMsg("");
    }
  }, [lockoutTime]);

  useEffect(() => {
    if (saveDetail.error instanceof ApiError && saveDetail.error.status === 403) {
      const msg = saveDetail.error.message;
      setErrorMsg(msg);

      if (msg.includes("locked") && msg.includes("seconds")) {
        const matches = msg.match(/\d+/);
        if (matches) {
          setLockoutTime(Number.parseInt(matches[0], 10));
        }
      }
    }
  }, [saveDetail.error]);

  const unlockMutation = useMutation({
    mutationFn: (verifyPin: string) => {
      if (!profileId) throw new Error("No profile linked to this save.");
      return unlockPlayerProfile(profileId, verifyPin);
    },
    onSuccess: (data) => {
      localStorage.setItem("profile_unlock_token", data.token);
      setErrorMsg("");
      setPin("");
      queryClient.invalidateQueries({ queryKey: ["active-save-detail", saveId] });
      queryClient.invalidateQueries({ queryKey: ["save-state", saveId] });
      queryClient.invalidateQueries({ queryKey: ["save-games"] });
    },
    onError: (err: unknown) => {
      const message = getErrorMessage(err, "Unable to unlock the save.");
      setErrorMsg(message);
      setPin("");

      if (message.includes("locked") && message.includes("seconds")) {
        const matches = message.match(/\d+/);
        if (matches) {
          setLockoutTime(Number.parseInt(matches[0], 10));
        }
      }
    },
  });

  const handleUnlockSubmit = (event?: FormEvent) => {
    if (event) event.preventDefault();
    if (lockoutTime !== null) return;

    if (pin.length < 4) {
      setErrorMsg("PIN must be at least 4 digits.");
      return;
    }

    unlockMutation.mutate(pin);
  };

  const handleKeyPress = (num: string) => {
    if (lockoutTime !== null) return;
    setErrorMsg("");

    if (pin.length < 12) {
      setPin((prev) => prev + num);
    }
  };

  const handleBackspace = () => {
    setErrorMsg("");
    setPin((prev) => prev.slice(0, -1));
  };

  const handleExitSave = () => {
    window.localStorage.removeItem("silicon-hustle-save-id");
    localStorage.removeItem("profile_unlock_token");
    endTutorial();
    queryClient.invalidateQueries();
    navigate("/");
    window.location.reload();
  };

  const handleStartTutorial = async () => {
    const tutorialSave = await createSave.mutateAsync("Tutorial Sandbox");
    setSelectedSaveId(tutorialSave.id);
    startTutorial(tutorialSave.id);
    navigate("/tutorial");
  };

  if (!saveId) {
    return (
      <div className="min-h-screen">
        <TopBar />
        <main className="p-6">
          <EmptyState title="No command center selected" body="Open or create a showroom save from the home screen." />
        </main>
      </div>
    );
  }

  if (isLocked) {
    return (
      <div className="game-console-bg relative z-0 flex min-h-screen select-none flex-col items-center justify-center overflow-hidden p-4 text-on-surface">
        <div className="scanline-animation" />

        <main className="relative z-10 flex w-full max-w-[480px] flex-col gap-gutter px-margin-safe py-12">
          <header className="mb-2 text-center">
            <h1 className="text-[2rem] font-black uppercase tracking-tighter text-primary-container sm:text-[2.25rem]">
              SILICON HUSTLE
            </h1>
            <div className="mt-2 flex items-center justify-center gap-2 font-mono text-[10px] uppercase tracking-[0.18em] text-on-surface-variant">
              <span className="inline-block h-2 w-2 rounded-full bg-secondary-fixed-dim animate-pulse" />
              HỆ THỐNG AN TOÀN // ĐANG CHỜ XÁC THỰC
            </div>
          </header>

          <section className="overflow-hidden border border-white/10 bg-surface-container-high">
            <div className="flex items-center justify-between border-b border-white/10 bg-surface-container-highest px-4 py-2">
              <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-outline">
                HỒ SƠ MỤC TIÊU
              </span>
              <span className="rounded-sm border border-primary-container/30 bg-primary-container/10 px-2 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-primary-container">
                [ĐÃ KHÓA]
              </span>
            </div>

            <div className="p-4">
              <div className="flex items-center gap-4">
                <div className="flex h-16 w-16 shrink-0 items-center justify-center border border-white/10 bg-surface-container-lowest text-lg font-bold text-outline">
                  {getInitials(profileName)}
                </div>
                <div className="min-w-0 flex-1">
                  <h2 className="truncate text-lg font-bold uppercase text-on-surface">{profileName}</h2>
                  <div className="mt-1 font-mono text-[10px] uppercase tracking-[0.18em] text-on-surface-variant">
                    LAST SYNC: {profileSync}
                  </div>
                </div>
              </div>

              <div className="mt-4 border-t border-white/10 pt-4">
                <div className="grid grid-cols-3 gap-2">
                  <div className="flex flex-col gap-1">
                    <span className="font-mono text-[9px] uppercase tracking-[0.18em] text-outline">
                      FUNDS
                    </span>
                    <span className="font-mono text-sm font-bold text-secondary-fixed-dim">
                      {formatVndCompact(currentSave?.cash)}
                    </span>
                  </div>
                  <div className="flex flex-col gap-1">
                    <span className="font-mono text-[9px] uppercase tracking-[0.18em] text-outline">
                      CYCLE
                    </span>
                    <span className="font-mono text-sm font-bold text-on-surface">
                      DAY {currentSave?.game_day ?? 1}
                    </span>
                  </div>
                  <div className="flex flex-col gap-1">
                    <span className="font-mono text-[9px] uppercase tracking-[0.18em] text-outline">
                      REP
                    </span>
                    <span className="font-mono text-sm font-bold text-on-surface">
                      {currentSave?.reputation ?? 0}%
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section className="relative z-20 overflow-hidden border border-primary-container/40 bg-surface-container-low/80 backdrop-blur-md terminal-glow">
            <div className="flex h-20 items-center justify-center border-b border-white/10 p-6">
              <div className="flex items-center gap-4 font-mono text-2xl tracking-[1em] text-primary-container">
                {[0, 1, 2, 3].map((index) => (
                  <span
                    key={index}
                    className={`transition-all duration-150 ${
                      index < pin.length
                        ? "scale-110 font-bold text-primary-container drop-shadow-[0_0_8px_rgba(0,242,255,0.6)]"
                        : "text-on-surface-variant/30"
                    }`}
                  >
                    {index < pin.length ? "*" : "•"}
                  </span>
                ))}
                <span className="pin-cursor ml-[-0.5em] h-8 border-l-2 border-primary-container animate-pulse" />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-[1px] bg-white/10 p-[1px]">
              {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((num) => (
                <button
                  key={num}
                  type="button"
                  onClick={() => handleKeyPress(String(num))}
                  disabled={lockoutTime !== null}
                  className="flex h-16 items-center justify-center bg-surface-container-high font-mono text-base font-bold text-on-surface transition-colors hover:bg-surface-container-highest disabled:cursor-not-allowed disabled:opacity-30"
                  >
                    {num}
                  </button>
              ))}

              <button
                type="button"
                onClick={handleBackspace}
                className="flex h-16 items-center justify-center bg-surface-container-high font-mono text-outline transition-colors hover:bg-surface-container-highest"
              >
                <Delete className="h-4 w-4" />
              </button>
              <button
                type="button"
                onClick={() => handleKeyPress("0")}
                disabled={lockoutTime !== null}
                className="flex h-16 items-center justify-center bg-surface-container-high font-mono text-base font-bold text-on-surface transition-colors hover:bg-surface-container-highest disabled:cursor-not-allowed disabled:opacity-30"
              >
                0
              </button>
              <button
                type="button"
                onClick={() => handleUnlockSubmit()}
                disabled={unlockMutation.isPending || lockoutTime !== null}
                className="flex h-16 items-center justify-center bg-primary-container font-mono text-lg text-on-primary-fixed transition-colors hover:bg-primary-fixed-dim disabled:cursor-not-allowed disabled:opacity-70"
              >
                <LogIn className="h-5 w-5" />
              </button>
            </div>
          </section>

          {errorMsg ? (
            <div className="mt-1 flex items-center gap-2 border border-rose-500/20 bg-rose-500/10 p-3 text-xs leading-snug text-rose-400">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          ) : null}

          <div className="flex gap-3 pt-1">
            <button
              type="button"
              onClick={() => handleUnlockSubmit()}
              disabled={unlockMutation.isPending || lockoutTime !== null}
              className="inline-flex h-12 flex-1 items-center justify-center border border-primary-container bg-surface px-4 font-mono text-[11px] font-bold uppercase tracking-[0.18em] text-primary-container transition hover:bg-primary-container/10 disabled:cursor-not-allowed disabled:border-white/10 disabled:text-on-surface-variant"
            >
              {unlockMutation.isPending ? "ĐANG TIẾP TỤC..." : lockoutTime !== null ? `ĐÃ KHÓA (${lockoutTime}s)` : "TIẾP TỤC BẢN LƯU"}
            </button>
            <button
              type="button"
              onClick={handleExitSave}
              className="inline-flex h-12 flex-1 items-center justify-center border border-white/10 bg-surface-container px-4 font-mono text-[11px] font-bold uppercase tracking-[0.18em] text-on-surface-variant transition hover:bg-white/5"
            >
              SHOWROOM MỚI
            </button>
          </div>

          <button
            type="button"
            onClick={handleStartTutorial}
            disabled={createSave.isPending}
            title="Open tutorial demo"
            className="inline-flex h-12 w-full items-center justify-center gap-2 border border-primary-container bg-surface px-4 font-mono text-[11px] font-bold uppercase tracking-[0.18em] text-primary-container transition hover:bg-primary-container/10 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {createSave.isPending ? "ĐANG CHUẨN BỊ TUTORIAL..." : "TUTORIAL HƯỚNG DẪN"}
          </button>
        </main>
      </div>
    );
  }

  return (
    <div className="game-console-bg relative min-h-screen font-sans text-on-surface selection:bg-primary-container selection:text-on-primary-container">
      <div className="scanline-animation" />
      <TopBar />
      <div className="relative flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="console-scrollbar mt-12 flex-1 overflow-y-auto p-margin-safe pb-20 md:ml-16 md:pb-margin-safe">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
