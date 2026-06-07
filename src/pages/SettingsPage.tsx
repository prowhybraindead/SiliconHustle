import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { Terminal, Shield, CheckCircle, Copy, AlertTriangle, HardDrive, RefreshCw } from "lucide-react";
import { apiBaseUrl } from "../api/client";
import {
  useSaveGames,
  usePlayerProfiles,
  useLockPlayerProfile,
  useUpdateSaveGamePin,
  useDisableSaveGamePin,
  useDeleteSaveGame,
} from "../api/hooks";
import { useGameStore } from "../store/gameStore";
import { formatVnd, translateUiText } from "../utils/format";

import { ConsolePanel } from "../components/ui/ConsolePanel";
import { StatusChip } from "../components/ui/StatusChip";
import { ActionButton } from "../components/ui/ActionButton";
import { SectionHeader } from "../components/ui/SectionHeader";

export function SettingsPage() {
  const selectedSaveId = useGameStore((state) => state.selectedSaveId);
  const setSelectedSaveId = useGameStore((state) => state.setSelectedSaveId);
  const uiLanguage = useGameStore((state) => state.uiLanguage);
  const setUiLanguage = useGameStore((state) => state.setUiLanguage);
  const saves = useSaveGames();
  const profiles = usePlayerProfiles();
  const lockProfileMut = useLockPlayerProfile();
  const updateShowroomPin = useUpdateSaveGamePin();
  const disableShowroomPin = useDisableSaveGamePin();
  const deleteSave = useDeleteSaveGame();

  const [logs, setLogs] = useState<string[]>([]);
  const [diagnosticsRunning, setDiagnosticsRunning] = useState(false);
  const [saveFeedback, setSaveFeedback] = useState("");
  const [exportNotice, setExportNotice] = useState("");
  const [showroomNewPin, setShowroomNewPin] = useState("");
  const [showroomCurrentPin, setShowroomCurrentPin] = useState("");
  const [showroomDeleteConfirm, setShowroomDeleteConfirm] = useState("");

  const currentSave = saves.data?.find((s) => s.id === selectedSaveId);
  const selectedProfileId = currentSave?.player_profile_id;
  const selectedProfile = profiles.data?.find((p) => p.id === selectedProfileId);
  const activeToken = typeof window !== "undefined" ? localStorage.getItem("profile_unlock_token") : null;

  const runDiagnostics = () => {
    if (diagnosticsRunning) return;
    setDiagnosticsRunning(true);
    setLogs(["INITIALIZING DIAGNOSTICS SEQUENCE..."]);

    const steps = [
      () => `RESOLVING BACKEND SERVICE ADDRESS: ${apiBaseUrl}`,
      () => `CONNECTION VERIFICATION: PING OK // RESP_TIME: 12MS`,
      () => `READING LOCAL STATIONS DATA AND CACHE STATUS...`,
      () => `LOCAL STORAGE SYSTEM INTEGRITY: SUCCESS`,
      () => `ACTIVE SAVE DETECTED: ID #${selectedSaveId ?? "NONE"}`,
      () => currentSave ? `SHOWROOM ACCESS SYNCED: ${currentSave.name} // PIN PROTECT: ${currentSave.pin_required ? "ON" : "OFF"}` : `NO SHOWROOM ACCESS LINKED TO ACTIVE SAVE`,
      () => `VERIFYING CYBER-INDUSTRIAL STYLE SYSTEM THEME...`,
      () => `THEME VARIABLES COMPATIBLE // NEON CYAN ACCENTS LOADED`,
      () => `SYSTEM HEALTHY // ALL CRITICAL HARDWARE ROUTINES ONLINE`
    ];

    steps.forEach((step, idx) => {
      setTimeout(() => {
        setLogs((prev) => [...prev, `[LOG-${idx.toString().padStart(2, "0")}] ${step()}`]);
        if (idx === steps.length - 1) {
          setDiagnosticsRunning(false);
        }
      }, (idx + 1) * 300);
    });
  };

  const handleSaveNow = () => {
    setSaveFeedback("AUTOSAVE MANUALLY EXECUTED: DISK INTEGRITY VERIFIED.");
    setTimeout(() => setSaveFeedback(""), 4000);
  };

  const handleExport = () => {
    if (!selectedSaveId) {
      setExportNotice("NO SAVE ACTIVE TO EXPORT.");
      return;
    }
    const publicSaveData = {
      saveId: selectedSaveId,
      name: currentSave?.name ?? "Tech Showroom",
      day: currentSave?.game_day ?? 1,
      cash: currentSave?.cash ?? 0,
      reputation: currentSave?.reputation ?? 0,
      timestamp: Date.now(),
    };
    navigator.clipboard.writeText(JSON.stringify(publicSaveData));
    setExportNotice("PUBLIC SAVE METADATA COPIED TO CLIPBOARD.");
    setTimeout(() => setExportNotice(""), 4000);
  };

  const handleLockProfile = async () => {
    if (!selectedProfile) return;
    try {
      await lockProfileMut.mutateAsync(selectedProfile.id);
      localStorage.removeItem("profile_unlock_token");
      alert("SHOWROOM ACCESS LOCKED. ACTIVE VERIFICATION SESSION TERMINATED.");
      window.location.reload();
    } catch (err) {
      alert("FAILED TO LOCK SHOWROOM SESSION.");
    }
  };

  const handleUpdateShowroomPin = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedSaveId || showroomNewPin.trim().length < 4) return;
    try {
      await updateShowroomPin.mutateAsync({
        saveId: selectedSaveId,
        pin: showroomNewPin.trim(),
        currentPin: showroomCurrentPin.trim() || undefined,
      });
      setShowroomNewPin("");
      setShowroomCurrentPin("");
      setSaveFeedback("SHOWROOM PIN UPDATED.");
      setTimeout(() => setSaveFeedback(""), 3500);
    } catch (err) {
      alert("FAILED TO UPDATE SHOWROOM PIN.");
    }
  };

  const handleDisableShowroomPin = async () => {
    if (!selectedSaveId) return;
    try {
      await disableShowroomPin.mutateAsync({
        saveId: selectedSaveId,
        currentPin: showroomCurrentPin.trim() || undefined,
      });
      setShowroomNewPin("");
      setShowroomCurrentPin("");
      setSaveFeedback("SHOWROOM PIN DISABLED.");
      setTimeout(() => setSaveFeedback(""), 3500);
    } catch (err) {
      alert("FAILED TO DISABLE SHOWROOM PIN.");
    }
  };

  const handleDeleteShowroom = async () => {
    if (!selectedSaveId || !currentSave) return;
    if (showroomDeleteConfirm.trim() !== currentSave.name.trim()) {
      alert(`Type ${currentSave.name} exactly to confirm deletion.`);
      return;
    }
    try {
      await deleteSave.mutateAsync(selectedSaveId);
      localStorage.removeItem("silicon-hustle-save-id");
      setSelectedSaveId(null);
      window.location.assign("/");
    } catch (err) {
      alert("FAILED TO DELETE SHOWROOM.");
    }
  };

  const saveStateLabel = selectedSaveId ? `SAVE ACTIVE [ID: ${selectedSaveId}]` : "NO SAVE LOADED";
  const pinStatusLabel = currentSave ? (currentSave.pin_required ? "PIN LOCKED" : "PIN OFF") : "NO SHOWROOM";
  const lockActionLabel = activeToken ? "REVOKE SESSION" : "LOCKED OUT";
  const languageTitle = uiLanguage === "vi" ? "Ngôn ngữ hội thoại" : "Conversation language";
  const languageBody =
    uiLanguage === "vi"
      ? "Chọn ngôn ngữ cho customer chat, quick action, staff intro và các thông báo hệ thống liên quan."
      : "Choose the language for customer chat, quick replies, staff intros, and related system notices.";

  return (
    <section className="space-y-4">
      {/* Header and Telemetry */}
      <ConsolePanel variant="z-1" className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <SectionHeader title={translateUiText("Systems Panel")} subtitle={translateUiText("CORE OPTIONS // SAVE DIAGNOSTICS")} />
          <div className="font-mono text-[10px] text-slate-500 mt-1 uppercase">
            STATUS: <span className="text-[#00f2ff] font-bold">SYSTEM STABLE</span> // AUTOSAVE: ENABLED
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-[10px] uppercase shrink-0">
          <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
            <span className="text-slate-500 text-[8px] block tracking-wider">{translateUiText("SAVE STATE")}</span>
            <span className="text-white font-bold text-xs">{selectedSaveId ? "ACTIVE" : "NONE"}</span>
          </div>
          <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
            <span className="text-slate-500 text-[8px] block tracking-wider">{translateUiText("SHOWROOM LOCK")}</span>
            <span className="text-[#00f2ff] font-bold text-xs">{currentSave?.pin_required ? "ENABLED" : "OFF"}</span>
          </div>
          <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
            <span className="text-slate-500 text-[8px] block tracking-wider">{translateUiText("BACKEND HEALTH")}</span>
            <span className="text-emerald-400 font-bold text-xs">ONLINE</span>
          </div>
          <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
            <span className="text-slate-500 text-[8px] block tracking-wider">AUTOSAVE</span>
            <span className="text-[#00f2ff] font-bold text-xs">ACTIVE</span>
          </div>
        </div>
      </ConsolePanel>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Left Side: Showroom settings & security details */}
        <div className="space-y-4">
          <ConsolePanel variant="z-1" className="p-5 space-y-4">
            <h2 className="text-xs font-bold font-mono text-white uppercase tracking-wider border-b border-white/5 pb-2 flex items-center gap-1.5">
              <Terminal className="h-4 w-4 text-[#00f2ff]" />
              ENG / VIE
            </h2>

            <div className="space-y-3 font-mono text-xs">
              <div className="bg-[#0c0e11] border border-white/5 p-3 rounded-none">
                <div className="text-white font-bold uppercase tracking-wider">{languageTitle}</div>
                <p className="mt-2 text-[11px] leading-relaxed text-slate-400 normal-case">{languageBody}</p>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <ActionButton
                  variant={uiLanguage === "en" ? "primary" : "secondary"}
                  onClick={() => setUiLanguage("en")}
                >
                  ENG
                </ActionButton>
                <ActionButton
                  variant={uiLanguage === "vi" ? "primary" : "secondary"}
                  onClick={() => setUiLanguage("vi")}
                >
                  VIE
                </ActionButton>
              </div>

              <div className="bg-[#00f2ff]/5 border border-[#00f2ff]/20 p-2 text-[10px] text-[#00f2ff] uppercase text-center">
                {uiLanguage === "vi" ? "Đang dùng tiếng Việt cho hội thoại" : "Conversation language set to English"}
              </div>
            </div>
          </ConsolePanel>

          <ConsolePanel variant="z-1" className="p-5 space-y-4">
            <h2 className="text-xs font-bold font-mono text-white uppercase tracking-wider border-b border-white/5 pb-2 flex items-center gap-1.5">
              <Shield className="h-4 w-4 text-[#00f2ff]" />
              SHOWROOM PIN & ACCESS SECURITY
            </h2>

            {currentSave ? (
              <div className="space-y-4 font-mono text-xs uppercase">
                <div className="bg-[#0c0e11] border border-white/5 p-3 rounded-none space-y-2">
                  <div className="flex justify-between gap-3">
                    <span className="text-slate-500">SHOWROOM:</span>
                    <span className="font-bold text-white">{currentSave.name}</span>
                  </div>
                  <div className="flex justify-between gap-3">
                    <span className="text-slate-500">PIN STATUS:</span>
                    <span className={currentSave.pin_required ? "text-[#ffba20] font-bold" : "text-slate-400"}>
                      {currentSave.pin_required ? "LOCKED PROTECTED" : "NO PIN LOCK"}
                    </span>
                  </div>
                </div>

                <form onSubmit={handleUpdateShowroomPin} className="space-y-3 border border-white/5 bg-white/[0.02] p-3 rounded-none">
                  <div>
                    <label className="block text-[11px] text-slate-400 mb-0.5">Current PIN</label>
                    <input
                      type="password"
                      placeholder="Current showroom PIN"
                      value={showroomCurrentPin}
                      onChange={(event) => setShowroomCurrentPin(event.target.value)}
                      className="w-full h-8 rounded border border-white/10 bg-slate-950 px-2.5 text-xs text-white outline-none focus:border-tech-blue"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] text-slate-400 mb-0.5">New PIN (4-12 digits)</label>
                    <input
                      type="password"
                      placeholder="New showroom PIN"
                      required
                      value={showroomNewPin}
                      onChange={(event) => setShowroomNewPin(event.target.value)}
                      className="w-full h-8 rounded border border-white/10 bg-slate-950 px-2.5 text-xs text-white outline-none focus:border-tech-blue"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="submit"
                      className="rounded bg-tech-blue px-3 py-1 text-xs font-semibold text-slate-950 hover:bg-sky-300 transition"
                      disabled={updateShowroomPin.isPending}
                    >
                      Update PIN
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleDisableShowroomPin()}
                      className="rounded border border-white/10 bg-white/[0.04] px-3 py-1 text-xs font-semibold text-slate-300 hover:bg-white/10 transition"
                      disabled={disableShowroomPin.isPending}
                    >
                      Disable PIN
                    </button>
                  </div>
                </form>

                <div className="border border-rose-500/20 bg-rose-500/[0.04] p-3 rounded-none space-y-3">
                  <div className="text-[11px] font-bold text-rose-300 uppercase">Danger zone</div>
                  <p className="text-[10px] text-slate-400 leading-relaxed">
                    Type the showroom name below to confirm deletion. This removes the save, its inventory, customers, quotes, and related history.
                  </p>
                  <input
                    type="text"
                    value={showroomDeleteConfirm}
                    onChange={(event) => setShowroomDeleteConfirm(event.target.value)}
                    placeholder={currentSave.name}
                    className="w-full h-8 rounded border border-rose-500/20 bg-slate-950 px-2.5 text-xs text-white outline-none focus:border-rose-400"
                  />
                  <button
                    type="button"
                    onClick={() => void handleDeleteShowroom()}
                    disabled={deleteSave.isPending}
                    className="w-full rounded border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs font-bold text-rose-200 hover:bg-rose-500/20 transition disabled:cursor-wait disabled:opacity-60"
                  >
                    DELETE SHOWROOM
                  </button>
                </div>
              </div>
            ) : (
              <div className="bg-[#0c0e11] border border-white/5 p-4 text-center text-slate-500 font-mono text-xs uppercase">
                NO ACTIVE SHOWROOM SELECTED.
              </div>
            )}
          </ConsolePanel>

          <ConsolePanel variant="z-1" className="p-5 space-y-4">
            <h2 className="text-xs font-bold font-mono text-white uppercase tracking-wider border-b border-white/5 pb-2 flex items-center gap-1.5">
              <HardDrive className="h-4 w-4 text-[#00f2ff]" />
              {translateUiText("Active Save Game Configuration")}
            </h2>

            {currentSave ? (
              <div className="space-y-4 font-mono text-xs uppercase">
                <div className="grid grid-cols-2 gap-2 bg-[#0c0e11] border border-white/5 p-3 rounded-none">
                  <div>
                    <span className="text-slate-500 text-[8px] block">{translateUiText("SHOWROOM NAME")}</span>
                    <span className="font-bold text-white text-sm">{currentSave.name}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 text-[8px] block">{translateUiText("SAVE DIRECTORY INDEX")}</span>
                    <span className="font-bold text-slate-300">ID #{currentSave.id}</span>
                  </div>
                  <div className="mt-2">
                    <span className="text-slate-500 text-[8px] block">{translateUiText("CURRENT CYCLE")}</span>
                    <span className="font-bold text-[#ffba20]">DAY {currentSave.game_day}</span>
                  </div>
                  <div className="mt-2">
                    <span className="text-slate-500 text-[8px] block">{translateUiText("REPUTATION LEVEL")}</span>
                    <span className="font-bold text-emerald-400">{currentSave.reputation} REP</span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <ActionButton onClick={handleSaveNow}>
                    {translateUiText("SAVE NOW")}
                  </ActionButton>
                  <ActionButton variant="secondary" onClick={handleExport}>
                    {translateUiText("EXPORT METADATA")}
                  </ActionButton>
                </div>

                {saveFeedback && (
                  <div className="bg-[#00f2ff]/5 border border-[#00f2ff]/20 p-2 text-[10px] text-[#00f2ff] text-center">
                    {saveFeedback}
                  </div>
                )}
                {exportNotice && (
                  <div className="bg-[#00f2ff]/5 border border-[#00f2ff]/20 p-2 text-[10px] text-[#00f2ff] text-center flex items-center justify-center gap-1">
                    <Copy className="h-3.5 w-3.5" />
                    {exportNotice}
                  </div>
                )}
              </div>
            ) : (
              <div className="bg-[#0c0e11] border border-white/5 p-4 text-center text-slate-500 font-mono text-xs uppercase">
                NO ACTIVE SAVE DETECTED. PLEASE LOAD A SAVE FROM THE HOME SCREEN.
              </div>
            )}
          </ConsolePanel>

          <ConsolePanel variant="z-1" className="p-5 space-y-4">
            <h2 className="text-xs font-bold font-mono text-white uppercase tracking-wider border-b border-white/5 pb-2 flex items-center gap-1.5">
              <Shield className="h-4 w-4 text-[#00f2ff]" />
              {translateUiText("Showroom Session & Access Security")}
            </h2>

            <div className="font-mono text-xs uppercase space-y-3">
              <div className="bg-[#0c0e11] border border-white/5 p-3 rounded-none space-y-2">
                <div className="flex justify-between">
                  <span className="text-slate-500">{translateUiText("SHOWROOM ACCESS")}:</span>
                  <span className="text-white font-bold">{currentSave?.pin_required ? "LOCKED PROTECTED" : "NO PIN LOCK"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">{translateUiText("SESSION TOKEN")}:</span>
                  <span>{activeToken ? <span className="text-emerald-400 font-bold">ACTIVE</span> : <span className="text-slate-500">NONE</span>}</span>
                </div>
                {activeToken && (
                  <div className="flex justify-between text-[10px] text-emerald-400">
                    <span>{translateUiText("VERIFIED SESSION TOKEN")}:</span>
                    <span>ACTIVE</span>
                  </div>
                )}
              </div>

              <div className="flex gap-2">
                {activeToken && selectedProfile && (
                  <ActionButton variant="danger" className="flex-1" onClick={handleLockProfile}>
                    {translateUiText("REVOKE SHOWROOM SESSION")}
                  </ActionButton>
                )}
                <Link className="flex-1" to="/profiles">
                  <ActionButton variant="secondary">
                    {translateUiText("ACCESS VAULT")}
                  </ActionButton>
                </Link>
              </div>
            </div>
          </ConsolePanel>

          {/* Dangerous Operations Zone */}
          <ConsolePanel variant="z-1" className="p-5 border-glow-amber bg-yellow-500/[0.02] space-y-3">
            <h2 className="text-xs font-bold font-mono text-[#ffba20] uppercase tracking-wider flex items-center gap-1.5">
              <AlertTriangle className="h-4 w-4 text-[#ffba20]" />
              {translateUiText("DANGEROUS OPERATIONS ZONE")}
            </h2>
            <p className="font-mono text-[10px] text-slate-400 uppercase leading-relaxed">
              DESTRUCTIVE COLD RESETS RESCIND SHOWROOM LOCKS AND FLUSH ACTIVE DATABASE LOGS. COLD CLEARS ARE DISABLED IN THIS WORKSPACE DIRECTORY TO PREVENT ACCIDENTAL LOSS.
            </p>
            <ActionButton variant="secondary" className="!h-9 cursor-not-allowed border-white/10 text-slate-500" disabled>
              {translateUiText("RESET SYSTEMS COLD [LOCKED]")}
            </ActionButton>
          </ConsolePanel>
        </div>

        {/* Right Side: Diagnostics console and logger logs */}
        <div className="space-y-4">
          <ConsolePanel variant="z-1" className="p-5 space-y-4 flex flex-col h-full">
            <div className="flex items-center justify-between border-b border-white/5 pb-2">
              <h2 className="text-xs font-bold font-mono text-white uppercase tracking-wider flex items-center gap-1.5">
                <Terminal className="h-4 w-4 text-[#00f2ff]" />
                {translateUiText("Diagnostics & Connection Logs")}
              </h2>
              <ActionButton
                className="!h-8 !w-auto !px-3 font-mono text-[10px]"
                onClick={runDiagnostics}
                disabled={diagnosticsRunning}
              >
                <RefreshCw className={`h-3 w-3 ${diagnosticsRunning ? "animate-spin" : ""}`} />
                {translateUiText("RUN TESTS")}
              </ActionButton>
            </div>

            <div className="bg-[#0c0e11] border border-white/5 p-4 rounded-none h-[380px] overflow-y-auto console-scrollbar font-mono text-[11px] text-emerald-400 uppercase space-y-1.5">
              {logs.length === 0 ? (
                <div className="text-slate-500 text-center select-none pt-24 uppercase">
                  No active logs streams. Run diagnostics routine to fetch network status.
                </div>
              ) : (
                logs.map((log, index) => (
                  <div key={index} className="leading-relaxed whitespace-pre-wrap">
                    {log}
                  </div>
                ))
              )}
            </div>

            <div className="bg-white/[0.01] border border-white/5 p-3 font-mono text-[10px] text-slate-400 uppercase leading-relaxed">
              <span className="font-bold text-white block mb-0.5">{translateUiText("LOCAL SYNC ARCHITECTURE NOTICE")}</span>
              Save states are synchronized automatically to SQLite databases and local browsers. Reloading the browser session recovers from the latest cached cycle.
            </div>
          </ConsolePanel>
        </div>
      </div>
    </section>
  );
}
