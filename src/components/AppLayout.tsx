import { useState, useEffect } from "react";
import { Outlet, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Lock, AlertTriangle, LogOut, Delete } from "lucide-react";

import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { EmptyState } from "./EmptyState";
import { BrandWordmark } from "./BrandWordmark";
import { useGameStore } from "../store/gameStore";
import { apiRequest, unlockPlayerProfile } from "../api/client";
import { useSaveGames } from "../api/hooks";
import type { SaveGame } from "../types/game";
import { ApiError } from "../api/client";
import { getErrorMessage } from "../utils/error";

export function AppLayout() {
  const saveId = useGameStore((state) => state.selectedSaveId);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const savesQuery = useSaveGames();

  // Query details of the active save game
  const saveDetail = useQuery({
    queryKey: ["active-save-detail", saveId],
    queryFn: () => apiRequest<SaveGame>(`/api/save-games/${saveId}`),
    enabled: Boolean(saveId),
    retry: false,
  });

  const [pin, setPin] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [lockoutTime, setLockoutTime] = useState<number | null>(null);

  const currentSave = savesQuery.data?.find((s) => s.id === saveId);
  const isLocked = saveDetail.error instanceof ApiError && saveDetail.error.status === 403;
  const profileId = currentSave?.player_profile_id;
  const profileName = currentSave?.profile_display_name ?? "Security Profile";

  // Lockout timer countdown
  useEffect(() => {
    if (lockoutTime !== null && lockoutTime > 0) {
      const timer = setTimeout(() => setLockoutTime(lockoutTime - 1), 1000);
      return () => clearTimeout(timer);
    } else if (lockoutTime === 0) {
      setLockoutTime(null);
      setErrorMsg("");
    }
  }, [lockoutTime]);

  // Extract lockout from error details
  useEffect(() => {
    if (saveDetail.error instanceof ApiError && saveDetail.error.status === 403) {
      const msg = saveDetail.error.message;
      setErrorMsg(msg);
      if (msg.includes("locked") && msg.includes("seconds")) {
        const matches = msg.match(/\d+/);
        if (matches) {
          setLockoutTime(parseInt(matches[0], 10));
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
      // Refetch detail and state
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
          setLockoutTime(parseInt(matches[0], 10));
        }
      }
    },
  });

  const handleUnlockSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
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

  const handleClear = () => {
    setErrorMsg("");
    setPin("");
  };

  const handleExitSave = () => {
    // Clear save state store
    window.localStorage.removeItem("silicon-hustle-save-id");
    // Clear token
    localStorage.removeItem("profile_unlock_token");
    queryClient.invalidateQueries();
    navigate("/");
    window.location.reload();
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

  // If save is locked, render the stunning lock screen overlay
  if (isLocked) {
    return (
      <div className="min-h-screen game-console-bg flex flex-col items-center justify-center p-4 relative overflow-hidden z-0 select-none">
        <div className="scanline-animation" />

        <main className="w-full max-w-[480px] px-margin-safe flex flex-col gap-gutter z-10 relative">
          {/* Header / Brand */}
          <header className="text-center mb-6">
            <BrandWordmark className="mx-auto max-w-[280px]" eager size="lg" />
            <div className="font-mono text-[10px] uppercase tracking-wider text-on-surface-variant mt-2 flex items-center justify-center gap-2">
              <span className="inline-block w-2 h-2 bg-secondary-fixed-dim rounded-full animate-pulse" />
              SYSTEM SECURE // AWAITING AUTHORIZATION
            </div>
          </header>

          {/* Selected Profile Card (Z-1 Panel) */}
          <div className="bg-surface-container-high border border-white/10 rounded-none overflow-hidden">
            {/* Card Header */}
            <div className="bg-surface-container-highest px-4 py-2 border-b border-white/10 flex justify-between items-center">
              <span className="font-mono text-[10px] uppercase tracking-wider text-outline">TARGET PROFILE</span>
              <span className="font-mono text-[10px] uppercase tracking-wider text-primary-container bg-primary-container/10 px-2 py-1 rounded-sm border border-primary-container/20">[LOCKED]</span>
            </div>
            {/* Card Body */}
            <div className="p-4 flex flex-col gap-4">
              <div className="flex items-center gap-4">
                <div className="w-16 h-16 bg-surface-container-lowest border border-white/10 flex items-center justify-center flex-shrink-0 font-mono text-xl text-outline font-bold">
                  {profileName.slice(0, 2).toUpperCase()}
                </div>
                <div className="flex-grow">
                  <h2 className="font-sans text-lg font-bold text-on-surface uppercase">{profileName}</h2>
                  <div className="font-mono text-[10px] text-on-surface-variant mt-1">SECURE ACCESS REQUIRED</div>
                </div>
              </div>
              {/* Stats Grid */}
              <div className="grid grid-cols-3 gap-2 border-t border-white/10 pt-4">
                <div className="flex flex-col">
                  <span className="font-mono text-[9px] uppercase tracking-wider text-outline">FUNDS</span>
                  <span className="font-mono text-xs font-bold text-secondary-fixed-dim">₫{(currentSave?.cash ?? 0).toLocaleString()}</span>
                </div>
                <div className="flex flex-col">
                  <span className="font-mono text-[9px] uppercase tracking-wider text-outline">CYCLE</span>
                  <span className="font-mono text-xs font-bold text-on-surface">DAY {currentSave?.game_day ?? 1}</span>
                </div>
                <div className="flex flex-col">
                  <span className="font-mono text-[9px] uppercase tracking-wider text-outline">REP</span>
                  <span className="font-mono text-xs font-bold text-on-surface">{currentSave?.reputation ?? 0}%</span>
                </div>
              </div>
            </div>
          </div>

          {/* PIN Input Area (Z-2 Active Modal style) */}
          <div className="bg-surface-container-low/80 backdrop-blur-md border border-primary-container/40 terminal-glow rounded-none mt-2 flex flex-col relative z-20">
            {/* Input Display */}
            <div className="p-6 border-b border-white/10 flex justify-center items-center h-20">
              <div className="flex gap-4 font-mono text-2xl text-primary-container tracking-[1em] items-center relative">
                {[...Array(4)].map((_, i) => (
                  <span
                    key={i}
                    className={`font-mono transition-all duration-150 ${
                      i < pin.length
                        ? "text-primary-container scale-110 drop-shadow-[0_0_8px_rgba(0,242,255,0.6)] font-bold"
                        : "text-on-surface-variant/30"
                    }`}
                  >
                    {i < pin.length ? "*" : "•"}
                  </span>
                ))}
                <span className="pin-cursor border-l-2 border-primary-container ml-[-0.5em] h-8 animate-pulse" />
              </div>
            </div>
            {/* Numeric Keypad */}
            <div className="grid grid-cols-3 gap-[1px] bg-white/10 p-[1px]">
              {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((num) => (
                <button
                  key={num}
                  type="button"
                  onClick={() => handleKeyPress(String(num))}
                  disabled={lockoutTime !== null}
                  className="bg-surface-container-high h-16 font-mono text-base font-bold text-on-surface hover:bg-surface-container-highest focus:outline-none flex items-center justify-center transition-all duration-100 disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  {num}
                </button>
              ))}
              <button
                type="button"
                onClick={handleClear}
                className="bg-surface-container-high h-16 font-mono text-[10px] font-bold text-outline hover:bg-surface-container-highest focus:outline-none flex items-center justify-center transition-all duration-100"
              >
                CLEAR
              </button>
              <button
                type="button"
                onClick={() => handleKeyPress("0")}
                disabled={lockoutTime !== null}
                className="bg-surface-container-high h-16 font-mono text-base font-bold text-on-surface hover:bg-surface-container-highest focus:outline-none flex items-center justify-center transition-all duration-100 disabled:opacity-30 disabled:cursor-not-allowed"
              >
                0
              </button>
              <button
                type="button"
                onClick={handleBackspace}
                className="bg-surface-container-high h-16 font-mono text-[10px] font-bold text-outline hover:bg-surface-container-highest focus:outline-none flex items-center justify-center transition-all duration-100"
              >
                BACK
              </button>
            </div>
          </div>

          {/* Error Message */}
          {errorMsg && (
            <div className="flex items-center gap-2 rounded-none border border-rose-500/20 bg-rose-500/10 p-3 text-xs text-rose-400 leading-snug mt-2">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Action buttons */}
          <div className="flex gap-3 pt-4 border-t border-white/5 mt-2">
            <button
              type="button"
              onClick={handleExitSave}
              className="flex-1 inline-flex h-12 items-center justify-center gap-1.5 border border-white/10 bg-surface text-xs font-bold text-on-surface hover:bg-white/5 transition uppercase"
            >
              <LogOut className="h-4 w-4" />
              Exit Save
            </button>
            <button
              type="button"
              onClick={() => handleUnlockSubmit()}
              disabled={unlockMutation.isPending || lockoutTime !== null}
              className="flex-1 inline-flex h-12 items-center justify-center gap-1.5 bg-primary-container text-xs font-black text-on-primary-fixed hover:bg-primary-fixed-dim transition uppercase disabled:opacity-40"
            >
              {unlockMutation.isPending ? "Unlocking..." : lockoutTime !== null ? `Locked (${lockoutTime}s)` : "Unlock"}
            </button>
          </div>
        </main>
      </div>
    );
  }

  // Standard Page Layout when unlocked (High Z-Index Locked Operations Console)
  return (
    <div className="min-h-screen game-console-bg text-on-surface flex flex-col font-sans selection:bg-primary-container selection:text-on-primary-container relative">
      <div className="scanline-animation" />
      <TopBar />
      <div className="flex flex-1 overflow-hidden relative">
        <Sidebar />
        <main className="flex-1 mt-12 md:ml-16 p-margin-safe pb-20 md:pb-margin-safe overflow-y-auto console-scrollbar">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
