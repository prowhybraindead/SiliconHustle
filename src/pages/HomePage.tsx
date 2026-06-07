import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { ChevronRight, HardDriveDownload, Plus, Play } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { useCreateSaveGame, useSaveGames } from "../api/hooks";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { ActionButton } from "../components/ui/ActionButton";
import { ConsolePanel } from "../components/ui/ConsolePanel";
import { useGameStore } from "../store/gameStore";
import { formatVndCompact } from "../utils/format";

function getInitials(name: string) {
  return name
    .split(/[\s_-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("")
    .slice(0, 2) || "SH";
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

function getSaveStatus(save: { is_locked: boolean; pin_required: boolean }) {
  if (save.is_locked) return "LOCKED";
  if (save.pin_required) return "PIN";
  return "READY";
}

export function HomePage() {
  const [name, setName] = useState("My Tech Showroom");
  const navigate = useNavigate();
  const { selectedSaveId, setSelectedSaveId, startTutorial } = useGameStore();
  const tutorialSeen = useGameStore((state) => state.tutorialSeen);
  const saves = useSaveGames();
  const createSave = useCreateSaveGame();
  const autoTutorialLaunched = useRef(false);

  const selectedSave = useMemo(() => {
    if (!saves.data?.length) return null;
    return saves.data.find((save) => save.id === selectedSaveId) ?? saves.data[0];
  }, [saves.data, selectedSaveId]);

  function openSave(id: number) {
    setSelectedSaveId(id);
    navigate("/dashboard");
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const save = await createSave.mutateAsync(name.trim() || "New Showroom");
    openSave(save.id);
  }

  async function handleStartTutorial() {
    const tutorialSave = await createSave.mutateAsync("Tutorial Sandbox");
    setSelectedSaveId(tutorialSave.id);
    startTutorial(tutorialSave.id);
    navigate("/tutorial");
  }

  useEffect(() => {
    if (autoTutorialLaunched.current) return;
    if (tutorialSeen) return;
    if (saves.isLoading || saves.isError || createSave.isPending) return;
    if ((saves.data?.length ?? 0) > 0) return;

    autoTutorialLaunched.current = true;
    void handleStartTutorial().catch(() => {
      autoTutorialLaunched.current = false;
    });
  }, [createSave.isPending, handleStartTutorial, saves.data?.length, saves.isError, saves.isLoading, tutorialSeen]);

  return (
    <div className="game-console-bg relative min-h-screen overflow-hidden text-on-surface">
      <div className="scanline-animation" />

      <main className="relative z-10 mx-auto flex min-h-screen w-full max-w-[480px] flex-col gap-gutter px-margin-safe py-12">
        <header className="mb-2 text-center">
          <h1 className="text-[2rem] font-black uppercase tracking-tighter text-primary-container sm:text-[2.25rem]">
            SILICON HUSTLE
          </h1>
          <div className="mt-2 flex items-center justify-center gap-2 font-mono text-[10px] uppercase tracking-[0.18em] text-on-surface-variant">
            <span className="inline-block h-2 w-2 rounded-full bg-secondary-fixed-dim animate-pulse" />
            SESSION CONTROL // SELECT SHOWROOM
          </div>
        </header>

        <section className="overflow-hidden border border-white/10 bg-surface-container-high">
          <div className="flex items-center justify-between border-b border-white/10 bg-surface-container-highest px-4 py-2">
            <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-outline">
              ACTIVE SHOWROOM
            </span>
            <span className="rounded-sm border border-primary-container/30 bg-primary-container/10 px-2 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-primary-container">
              {selectedSave ? `[${getSaveStatus(selectedSave)}]` : "[EMPTY]"}
            </span>
          </div>

          <div className="p-4">
            {saves.isLoading ? (
              <LoadingState />
            ) : saves.isError ? (
              <ErrorState message={(saves.error as Error).message} />
            ) : selectedSave ? (
              <div className="flex flex-col gap-4">
                <div className="flex items-center gap-4">
                  <div className="flex h-16 w-16 shrink-0 items-center justify-center border border-white/10 bg-surface-container-lowest text-lg font-bold text-outline">
                    {getInitials(selectedSave.name)}
                  </div>
                  <div className="min-w-0 flex-1">
                    <h2 className="truncate text-lg font-bold uppercase text-on-surface">{selectedSave.name}</h2>
                    <div className="mt-1 font-mono text-[10px] uppercase tracking-[0.18em] text-on-surface-variant">
                      LAST SYNC: {formatSyncTime(selectedSave.last_autosave_at ?? selectedSave.updated_at)}
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-2 border-t border-white/10 pt-4">
                  <div className="flex flex-col gap-1">
                    <span className="font-mono text-[9px] uppercase tracking-[0.18em] text-outline">
                      FUNDS
                    </span>
                    <span className="font-mono text-sm font-bold text-secondary-fixed-dim">
                      {formatVndCompact(selectedSave.cash)}
                    </span>
                  </div>
                  <div className="flex flex-col gap-1">
                    <span className="font-mono text-[9px] uppercase tracking-[0.18em] text-outline">
                      CYCLE
                    </span>
                    <span className="font-mono text-sm font-bold text-on-surface">
                      DAY {selectedSave.game_day}
                    </span>
                  </div>
                  <div className="flex flex-col gap-1">
                    <span className="font-mono text-[9px] uppercase tracking-[0.18em] text-outline">
                      REP
                    </span>
                    <span className="font-mono text-sm font-bold text-on-surface">
                      {selectedSave.reputation}%
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex min-h-[148px] flex-col justify-center gap-2 text-center">
                <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-outline">
                  NO SHOWROOMS FOUND
                </div>
                <div className="text-sm text-on-surface-variant">
                  Create a new save to start your run.
                </div>
              </div>
            )}
          </div>
        </section>

        <section className="grid gap-panel-gap">
          <div className="flex items-center justify-between px-1">
            <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-outline">
              SAVES
            </span>
            <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-on-surface-variant">
              {saves.data?.length ?? 0} RECORDS
            </span>
          </div>

          <div className="grid gap-panel-gap">
            {saves.data?.map((save) => {
              const active = save.id === selectedSave?.id;

              return (
                <button
                  key={save.id}
                  type="button"
                  onClick={() => setSelectedSaveId(save.id)}
                  className={`flex items-center gap-4 border px-4 py-3 text-left transition-colors ${
                    active
                      ? "border-primary-container/50 bg-surface-container-highest shadow-console"
                      : "border-white/10 bg-surface-container hover:border-white/20 hover:bg-surface-container-highest"
                  }`}
                >
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center border border-white/10 bg-surface-container-lowest text-sm font-bold text-outline">
                    {getInitials(save.name)}
                  </div>

                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <div className="truncate font-semibold uppercase text-on-surface">{save.name}</div>
                      <span className="rounded-sm border border-white/10 bg-white/5 px-2 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-on-surface-variant">
                        DAY {save.game_day}
                      </span>
                    </div>
                    <div className="mt-1 font-mono text-[10px] uppercase tracking-[0.18em] text-on-surface-variant">
                      {formatVndCompact(save.cash)} / REP {save.reputation}% / {getSaveStatus(save)}
                    </div>
                  </div>

                  <ChevronRight className={`h-4 w-4 shrink-0 ${active ? "text-primary-container" : "text-outline"}`} />
                </button>
              );
            })}
          </div>
        </section>

        <section className="overflow-hidden border border-primary-container/35 bg-surface-container-low/80 backdrop-blur-md terminal-glow">
          <div className="border-b border-white/10 px-4 py-2">
            <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-outline">
              NEW SHOWROOM
            </span>
          </div>

          <form className="flex flex-col gap-3 p-4" onSubmit={handleSubmit}>
            <label className="sr-only" htmlFor="showroom-name">
              Showroom name
            </label>
            <input
              id="showroom-name"
              className="min-h-12 border border-white/10 bg-surface-container-high px-3 font-sans text-sm text-on-surface outline-none transition placeholder:text-on-surface-variant/60 focus:border-primary-container/50"
              onChange={(event) => setName(event.target.value)}
              placeholder="Showroom name"
              value={name}
            />
            <button
              className="inline-flex min-h-12 items-center justify-center gap-2 border border-primary-container bg-primary-container px-4 font-mono text-[11px] font-bold uppercase tracking-[0.18em] text-on-primary-fixed transition hover:bg-primary-fixed-dim disabled:cursor-wait disabled:opacity-60"
              disabled={createSave.isPending}
              type="submit"
            >
              <Plus className="h-4 w-4" />
              Create Showroom
            </button>
          </form>
        </section>

        <div className="flex gap-3 pt-1">
          <button
            type="button"
            onClick={() => selectedSave && openSave(selectedSave.id)}
            disabled={!selectedSave}
            className="inline-flex h-12 flex-1 items-center justify-center gap-2 border border-primary-container bg-surface px-4 font-mono text-[11px] font-bold uppercase tracking-[0.18em] text-primary-container transition hover:bg-primary-container/10 disabled:cursor-not-allowed disabled:border-white/10 disabled:text-on-surface-variant"
          >
            <Play className="h-4 w-4" />
            Resume Save
          </button>
          <button
            type="button"
            onClick={() => document.getElementById("showroom-name")?.focus()}
            className="inline-flex h-12 flex-1 items-center justify-center gap-2 border border-white/10 bg-surface-container px-4 font-mono text-[11px] font-bold uppercase tracking-[0.18em] text-on-surface-variant transition hover:bg-white/5"
          >
            <HardDriveDownload className="h-4 w-4" />
            New Showroom
          </button>
        </div>

        <ConsolePanel variant="z-1" className="space-y-3">
          <div className="flex items-center justify-between gap-3 border-b border-white/10 pb-2">
            <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-outline">
              GUIDED TUTORIAL
            </span>
            <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-primary-container">
              SAFE PRACTICE MODE
            </span>
          </div>
          <p className="text-sm leading-relaxed text-on-surface-variant">
            If you want a walk-through instead of jumping straight into your own save, I can create a clean tutorial
            showroom and guide you through the first customer loop step by step.
          </p>
          <div className="grid gap-2 sm:grid-cols-[1fr_auto]">
            <div className="rounded-none border border-white/10 bg-[#080a0d] px-3 py-2 text-[11px] leading-relaxed text-outline">
              You&apos;ll learn the dashboard, customer requests, inventory, and quote flow without touching your
              existing saves.
            </div>
            <ActionButton
              className="h-11 w-full sm:w-[200px]"
              disabled={createSave.isPending}
              onClick={handleStartTutorial}
              title="Open tutorial demo"
            >
              {createSave.isPending ? "PREPARING..." : "START TUTORIAL"}
            </ActionButton>
          </div>
        </ConsolePanel>
      </main>
    </div>
  );
}
