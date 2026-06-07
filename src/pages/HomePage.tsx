import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { ChevronRight, HardDriveDownload, Plus, Play, Trash2 } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { useCreateSaveGame, useDeleteSaveGame, useSaveGames } from "../api/hooks";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { ActionButton } from "../components/ui/ActionButton";
import { ConsolePanel } from "../components/ui/ConsolePanel";
import { useGameStore } from "../store/gameStore";
import { formatVndCompact, pickUiText } from "../utils/format";

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

function getSaveStatus(save: { is_locked: boolean; pin_required: boolean }) {
  if (save.is_locked) return "LOCKED";
  if (save.pin_required) return "PIN";
  return "READY";
}

export function HomePage() {
  const [name, setName] = useState("My Tech Showroom");
  const navigate = useNavigate();
  const selectedSaveId = useGameStore((state) => state.selectedSaveId);
  const setSelectedSaveId = useGameStore((state) => state.setSelectedSaveId);
  const startTutorial = useGameStore((state) => state.startTutorial);
  const tutorialSeen = useGameStore((state) => state.tutorialSeen);
  const uiLanguage = useGameStore((state) => state.uiLanguage);
  const saves = useSaveGames();
  const createSave = useCreateSaveGame();
  const deleteSave = useDeleteSaveGame();
  const autoTutorialLaunched = useRef(false);

  const copy = useMemo(
    () => ({
      sessionHub: pickUiText("TRUNG TÂM PHIÊN // CHỌN SHOWROOM", "SESSION HUB // SELECT SHOWROOM", uiLanguage),
      activeSave: pickUiText("SHOWROOM ĐANG DÙNG", "ACTIVE SHOWROOM", uiLanguage),
      emptySave: pickUiText("CHƯA CÓ SHOWROOM NÀO", "NO SHOWROOM YET", uiLanguage),
      emptySaveBody: pickUiText("Tạo một bản lưu mới để bắt đầu hành trình của anh.", "Create a new save to start your run.", uiLanguage),
      lastSync: pickUiText("ĐỒNG BỘ LẦN CUỐI", "LAST SYNC", uiLanguage),
      saves: pickUiText("BẢN LƯU", "SAVE GAMES", uiLanguage),
      entries: pickUiText("BẢN GHI", "ENTRIES", uiLanguage),
      day: pickUiText("NGÀY", "DAY", uiLanguage),
      reputation: pickUiText("UY TÍN", "REP", uiLanguage),
      newShowroom: pickUiText("SHOWROOM MỚI", "NEW SHOWROOM", uiLanguage),
      showroomName: pickUiText("Tên showroom", "Showroom name", uiLanguage),
      createShowroom: pickUiText("Tạo showroom", "Create showroom", uiLanguage),
      continueSave: pickUiText("Tiếp tục bản lưu", "Continue save", uiLanguage),
      focusNew: pickUiText("Showroom mới", "New showroom", uiLanguage),
      tutorial: pickUiText("TUTORIAL HƯỚNG DẪN", "GUIDED TUTORIAL", uiLanguage),
      safeMode: pickUiText("CHẾ ĐỘ THỰC HÀNH AN TOÀN", "SAFE PRACTICE MODE", uiLanguage),
      tutorialBody: pickUiText(
        "Nếu anh muốn đi theo hướng dẫn thay vì vào thẳng bản lưu của mình, em sẽ tạo một showroom tutorial sạch và dẫn anh qua vòng khách hàng đầu tiên từng bước một.",
        "If you want a guided path before jumping into your own save, we can open a clean tutorial showroom and walk through the first customer flow step by step.",
        uiLanguage,
      ),
      tutorialNote: pickUiText(
        "Anh sẽ học dashboard, yêu cầu khách hàng, kho hàng và luồng báo giá mà không chạm vào các bản lưu hiện có.",
        "You'll learn the dashboard, customer requests, inventory, and quote flow without touching any existing saves.",
        uiLanguage,
      ),
      startTutorial: pickUiText("BẮT ĐẦU TUTORIAL", "START TUTORIAL", uiLanguage),
      preparing: pickUiText("ĐANG CHUẨN BỊ...", "PREPARING...", uiLanguage),
      deleteShowroom: pickUiText("XÓA SHOWROOM", "DELETE SHOWROOM", uiLanguage),
      deleteConfirm: pickUiText(
        "Xóa showroom này sẽ dọn sạch dữ liệu lưu của nó. Anh chắc muốn làm vậy chứ?",
        "Deleting this showroom will remove its save data. Are you sure?",
        uiLanguage,
      ),
    }),
    [uiLanguage],
  );

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
    const save = await createSave.mutateAsync(name.trim() || pickUiText("Showroom mới", "New Showroom", uiLanguage));
    openSave(save.id);
  }

  async function handleStartTutorial() {
    const tutorialSave = await createSave.mutateAsync("Tutorial Sandbox");
    setSelectedSaveId(tutorialSave.id);
    startTutorial(tutorialSave.id);
    navigate("/tutorial");
  }

  async function handleDeleteSave(saveId: number, saveName: string) {
    if (!window.confirm(`${copy.deleteConfirm}\n\n${saveName}`)) return;
    await deleteSave.mutateAsync(saveId);
    const remaining = saves.data?.filter((save) => save.id !== saveId) ?? [];
    setSelectedSaveId(remaining[0]?.id ?? null);
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
  }, [createSave.isPending, saves.data?.length, saves.isError, saves.isLoading, tutorialSeen]);

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
            {copy.sessionHub}
          </div>
        </header>

        <section className="overflow-hidden border border-white/10 bg-surface-container-high">
          <div className="flex items-center justify-between border-b border-white/10 bg-surface-container-highest px-4 py-2">
            <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-outline">{copy.activeSave}</span>
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
                      {copy.lastSync}: {formatSyncTime(selectedSave.last_autosave_at ?? selectedSave.updated_at)}
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-2 border-t border-white/10 pt-4">
                  <div className="flex flex-col gap-1">
                    <span className="font-mono text-[9px] uppercase tracking-[0.18em] text-outline">FUNDS</span>
                    <span className="font-mono text-sm font-bold text-secondary-fixed-dim">{formatVndCompact(selectedSave.cash)}</span>
                  </div>
                  <div className="flex flex-col gap-1">
                    <span className="font-mono text-[9px] uppercase tracking-[0.18em] text-outline">CYCLE</span>
                    <span className="font-mono text-sm font-bold text-on-surface">
                      {copy.day} {selectedSave.game_day}
                    </span>
                  </div>
                  <div className="flex flex-col gap-1">
                    <span className="font-mono text-[9px] uppercase tracking-[0.18em] text-outline">{copy.reputation}</span>
                    <span className="font-mono text-sm font-bold text-on-surface">{selectedSave.reputation}%</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex min-h-[148px] flex-col justify-center gap-2 text-center">
                <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-outline">{copy.emptySave}</div>
                <div className="text-sm text-on-surface-variant">{copy.emptySaveBody}</div>
              </div>
            )}
          </div>
        </section>

        <section className="grid gap-panel-gap">
          <div className="flex items-center justify-between px-1">
            <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-outline">{copy.saves}</span>
            <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-on-surface-variant">
              {saves.data?.length ?? 0} {copy.entries}
            </span>
          </div>

          <div className="grid gap-panel-gap">
            {saves.data?.map((save) => {
              const active = save.id === selectedSave?.id;

              return (
                <div
                  key={save.id}
                  onClick={() => setSelectedSaveId(save.id)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      setSelectedSaveId(save.id);
                    }
                  }}
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
                        {copy.day} {save.game_day}
                      </span>
                    </div>
                    <div className="mt-1 font-mono text-[10px] uppercase tracking-[0.18em] text-on-surface-variant">
                      {formatVndCompact(save.cash)} / {copy.reputation} {save.reputation}% / {getSaveStatus(save)}
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      void handleDeleteSave(save.id, save.name);
                    }}
                    disabled={deleteSave.isPending}
                    className="inline-flex h-10 items-center gap-2 border border-rose-500/20 bg-rose-500/10 px-3 font-mono text-[10px] font-bold uppercase tracking-[0.18em] text-rose-300 transition hover:bg-rose-500/20 disabled:cursor-wait disabled:opacity-60"
                    title={copy.deleteShowroom}
                  >
                    <Trash2 className="h-4 w-4" />
                    {copy.deleteShowroom}
                  </button>

                  <ChevronRight className={`h-4 w-4 shrink-0 ${active ? "text-primary-container" : "text-outline"}`} />
                </div>
              );
            })}
          </div>
        </section>

        <section className="overflow-hidden border border-primary-container/35 bg-surface-container-low/80 backdrop-blur-md terminal-glow">
          <div className="border-b border-white/10 px-4 py-2">
            <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-outline">{copy.newShowroom}</span>
          </div>

          <form className="flex flex-col gap-3 p-4" onSubmit={handleSubmit}>
            <label className="sr-only" htmlFor="showroom-name">
              {copy.showroomName}
            </label>
            <input
              id="showroom-name"
              className="min-h-12 border border-white/10 bg-surface-container-high px-3 font-sans text-sm text-on-surface outline-none transition placeholder:text-on-surface-variant/60 focus:border-primary-container/50"
              onChange={(event) => setName(event.target.value)}
              placeholder={copy.showroomName}
              value={name}
            />
            <button
              className="inline-flex min-h-12 items-center justify-center gap-2 border border-primary-container bg-primary-container px-4 font-mono text-[11px] font-bold uppercase tracking-[0.18em] text-on-primary-fixed transition hover:bg-primary-fixed-dim disabled:cursor-wait disabled:opacity-60"
              disabled={createSave.isPending}
              type="submit"
            >
              <Plus className="h-4 w-4" />
              {copy.createShowroom}
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
            {copy.continueSave}
          </button>
          <button
            type="button"
            onClick={() => document.getElementById("showroom-name")?.focus()}
            className="inline-flex h-12 flex-1 items-center justify-center gap-2 border border-white/10 bg-surface-container px-4 font-mono text-[11px] font-bold uppercase tracking-[0.18em] text-on-surface-variant transition hover:bg-white/5"
          >
            <HardDriveDownload className="h-4 w-4" />
            {copy.focusNew}
          </button>
        </div>

        <ConsolePanel variant="z-1" className="space-y-3">
          <div className="flex items-center justify-between gap-3 border-b border-white/10 pb-2">
            <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-outline">{copy.tutorial}</span>
            <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-primary-container">{copy.safeMode}</span>
          </div>
          <p className="text-sm leading-relaxed text-on-surface-variant">{copy.tutorialBody}</p>
          <div className="grid gap-2 sm:grid-cols-[1fr_auto]">
            <div className="rounded-none border border-white/10 bg-[#080a0d] px-3 py-2 text-[11px] leading-relaxed text-outline">
              {copy.tutorialNote}
            </div>
            <ActionButton
              className="h-11 w-full sm:w-[200px]"
              disabled={createSave.isPending}
              onClick={handleStartTutorial}
              title="Open tutorial demo"
            >
              {createSave.isPending ? copy.preparing : copy.startTutorial}
            </ActionButton>
          </div>
        </ConsolePanel>
      </main>
    </div>
  );
}
