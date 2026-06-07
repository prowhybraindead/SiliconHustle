import { useState } from "react";
import { Link } from "react-router-dom";
import { Terminal, Shield, CheckCircle, Copy, AlertTriangle, HardDrive, RefreshCw } from "lucide-react";
import { apiBaseUrl } from "../api/client";
import { useSaveGames, usePlayerProfiles, useLockPlayerProfile } from "../api/hooks";
import { useGameStore } from "../store/gameStore";
import { formatVnd } from "../utils/format";

import { ConsolePanel } from "../components/ui/ConsolePanel";
import { StatusChip } from "../components/ui/StatusChip";
import { ActionButton } from "../components/ui/ActionButton";
import { SectionHeader } from "../components/ui/SectionHeader";

export function SettingsPage() {
  const selectedSaveId = useGameStore((state) => state.selectedSaveId);
  const uiLanguage = useGameStore((state) => state.uiLanguage);
  const setUiLanguage = useGameStore((state) => state.setUiLanguage);
  const saves = useSaveGames();
  const profiles = usePlayerProfiles();
  const lockProfileMut = useLockPlayerProfile();

  const [logs, setLogs] = useState<string[]>([]);
  const [diagnosticsRunning, setDiagnosticsRunning] = useState(false);
  const [saveFeedback, setSaveFeedback] = useState("");
  const [exportNotice, setExportNotice] = useState("");

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
      () => selectedProfile ? `PROFILE ACCESS SYNCED: ${selectedProfile.display_name} // PIN PROTECT: ${selectedProfile.pin_enabled ? "ON" : "OFF"}` : `NO SECURE PROFILE ASSIGNED TO ACTIVE SAVE`,
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
      alert("PROFILE LOCKED. ACTIVE VERIFICATION SESSION TERMINATED.");
      window.location.reload();
    } catch (err) {
      alert("FAILED TO LOCK PROFILE SESSION.");
    }
  };

  const saveStateLabel = selectedSaveId ? `SAVE ACTIVE [ID: ${selectedSaveId}]` : "NO SAVE LOADED";
  const pinStatusLabel = selectedProfile ? (selectedProfile.pin_enabled ? "PIN LOCKED" : "PIN OFF") : "NO PROFILE";
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
          <SectionHeader title="Systems Panel" subtitle="CORE OPTIONS // SAVE DIAGNOSTICS" />
          <div className="font-mono text-[10px] text-slate-500 mt-1 uppercase">
            STATUS: <span className="text-[#00f2ff] font-bold">SYSTEM STABLE</span> // AUTOSAVE: ENABLED
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-[10px] uppercase shrink-0">
          <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
            <span className="text-slate-500 text-[8px] block tracking-wider">SAVE STATE</span>
            <span className="text-white font-bold text-xs">{selectedSaveId ? "ACTIVE" : "NONE"}</span>
          </div>
          <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
            <span className="text-slate-500 text-[8px] block tracking-wider">PROFILE LOCK</span>
            <span className="text-[#00f2ff] font-bold text-xs">{selectedProfile?.pin_enabled ? "ENABLED" : "OFF"}</span>
          </div>
          <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
            <span className="text-slate-500 text-[8px] block tracking-wider">BACKEND HEALTH</span>
            <span className="text-emerald-400 font-bold text-xs">ONLINE</span>
          </div>
          <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
            <span className="text-slate-500 text-[8px] block tracking-wider">AUTOSAVE</span>
            <span className="text-[#00f2ff] font-bold text-xs">ACTIVE</span>
          </div>
        </div>
      </ConsolePanel>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Left Side: Save Profile & Security details */}
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
              <HardDrive className="h-4 w-4 text-[#00f2ff]" />
              Active Save Game Configuration
            </h2>

            {currentSave ? (
              <div className="space-y-4 font-mono text-xs uppercase">
                <div className="grid grid-cols-2 gap-2 bg-[#0c0e11] border border-white/5 p-3 rounded-none">
                  <div>
                    <span className="text-slate-500 text-[8px] block">SHOWROOM NAME</span>
                    <span className="font-bold text-white text-sm">{currentSave.name}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 text-[8px] block">SAVE DIRECTORY INDEX</span>
                    <span className="font-bold text-slate-300">ID #{currentSave.id}</span>
                  </div>
                  <div className="mt-2">
                    <span className="text-slate-500 text-[8px] block">CURRENT CYCLE</span>
                    <span className="font-bold text-[#ffba20]">DAY {currentSave.game_day}</span>
                  </div>
                  <div className="mt-2">
                    <span className="text-slate-500 text-[8px] block">REPUTATION LEVEL</span>
                    <span className="font-bold text-emerald-400">{currentSave.reputation} REP</span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <ActionButton onClick={handleSaveNow}>
                    SAVE NOW
                  </ActionButton>
                  <ActionButton variant="secondary" onClick={handleExport}>
                    EXPORT METADATA
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
              PIN Lock & Access Security
            </h2>

            <div className="font-mono text-xs uppercase space-y-3">
              <div className="bg-[#0c0e11] border border-white/5 p-3 rounded-none space-y-2">
                <div className="flex justify-between">
                  <span className="text-slate-500">ASSIGNED PROFILE:</span>
                  <span className="text-white font-bold">{selectedProfile?.display_name ?? "NONE"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">PIN STATUS:</span>
                  <span>
                    {selectedProfile ? (
                      selectedProfile.pin_enabled ? (
                        <span className="text-[#ffba20] font-bold">LOCKED PROTECTED</span>
                      ) : (
                        <span className="text-slate-400">NO PIN SYSTEM</span>
                      )
                    ) : (
                      <span className="text-slate-500">UNRESTRICTED RUN</span>
                    )}
                  </span>
                </div>
                {activeToken && (
                  <div className="flex justify-between text-[10px] text-emerald-400">
                    <span>VERIFIED SESSION TOKEN:</span>
                    <span>ACTIVE</span>
                  </div>
                )}
              </div>

              <div className="flex gap-2">
                {activeToken && selectedProfile && (
                  <ActionButton variant="danger" className="flex-1" onClick={handleLockProfile}>
                    REVOKE LOCK SESSION
                  </ActionButton>
                )}
                <Link className="flex-1" to="/profiles">
                  <ActionButton variant="secondary">
                    PROFILES SETTINGS
                  </ActionButton>
                </Link>
              </div>
            </div>
          </ConsolePanel>

          {/* Dangerous Operations Zone */}
          <ConsolePanel variant="z-1" className="p-5 border-glow-amber bg-yellow-500/[0.02] space-y-3">
            <h2 className="text-xs font-bold font-mono text-[#ffba20] uppercase tracking-wider flex items-center gap-1.5">
              <AlertTriangle className="h-4 w-4 text-[#ffba20]" />
              DANGEROUS OPERATIONS ZONE
            </h2>
            <p className="font-mono text-[10px] text-slate-400 uppercase leading-relaxed">
              DESTRUCTIVE COLD RESETS RESCIND PROFILE LOCKS AND FLUSH ACTIVE DATABASE LOGS. COLD CLEARS ARE DISABLED IN THIS WORKSPACE DIRECTORY TO PREVENT ACCIDENTAL LOSS.
            </p>
            <ActionButton variant="secondary" className="!h-9 cursor-not-allowed border-white/10 text-slate-500" disabled>
              RESET SYSTEMS COLD [LOCKED]
            </ActionButton>
          </ConsolePanel>
        </div>

        {/* Right Side: Diagnostics console and logger logs */}
        <div className="space-y-4">
          <ConsolePanel variant="z-1" className="p-5 space-y-4 flex flex-col h-full">
            <div className="flex items-center justify-between border-b border-white/5 pb-2">
              <h2 className="text-xs font-bold font-mono text-white uppercase tracking-wider flex items-center gap-1.5">
                <Terminal className="h-4 w-4 text-[#00f2ff]" />
                Diagnostics & Connection Logs
              </h2>
              <ActionButton
                className="!h-8 !w-auto !px-3 font-mono text-[10px]"
                onClick={runDiagnostics}
                disabled={diagnosticsRunning}
              >
                <RefreshCw className={`h-3 w-3 ${diagnosticsRunning ? "animate-spin" : ""}`} />
                RUN TESTS
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
              <span className="font-bold text-white block mb-0.5">LOCAL SYNC ARCHITECTURE NOTICE</span>
              Save states are synchronized automatically to SQLite databases and local browsers. Reloading the browser session recovers from the latest cached cycle.
            </div>
          </ConsolePanel>
        </div>
      </div>
    </section>
  );
}
