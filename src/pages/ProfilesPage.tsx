import { useState } from "react";
import { User, Shield, ShieldOff, Lock, Unlock, Plus, Key } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";

import {
  usePlayerProfiles,
  useCreatePlayerProfile,
  useUnlockPlayerProfile,
  useLockPlayerProfile,
  useChangePlayerProfilePin,
  useDisablePlayerProfilePin,
  useSaveGames,
} from "../api/hooks";
import { PageHeader } from "../components/PageHeader";
import { EmptyState } from "../components/EmptyState";
import { LoadingState } from "../components/LoadingState";
import { formatVnd } from "../utils/format";
import { getErrorMessage } from "../utils/error";

export function ProfilesPage() {
  const queryClient = useQueryClient();
  const profiles = usePlayerProfiles();
  const saves = useSaveGames();
  
  const createProfile = useCreatePlayerProfile();
  const unlockProfile = useUnlockPlayerProfile();
  const lockProfile = useLockPlayerProfile();
  const changePin = useChangePlayerProfilePin();
  const disablePin = useDisablePlayerProfilePin();

  const [selectedProfileId, setSelectedProfileId] = useState<number | null>(null);
  
  // Creation state
  const [createName, setCreateName] = useState("");
  const [createPin, setCreatePin] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  
  // Pin Change/Setup state
  const [newPin, setNewPin] = useState("");
  const [currentPin, setCurrentPin] = useState("");
  
  // PIN Unlock state
  const [unlockPin, setUnlockPin] = useState("");
  const [unlockError, setUnlockError] = useState("");

  const selectedProfile = profiles.data?.find(p => p.id === selectedProfileId);
  const activeToken = typeof window !== "undefined" ? localStorage.getItem("profile_unlock_token") : null;

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!createName.trim()) return;
    try {
      await createProfile.mutateAsync({
        displayName: createName,
        pin: createPin || undefined,
      });
      setCreateName("");
      setCreatePin("");
      setIsCreating(false);
    } catch (err: unknown) {
      alert(getErrorMessage(err, "Failed to create profile."));
    }
  }

  async function handleUnlock(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedProfileId) return;
    setUnlockError("");
    try {
      await unlockProfile.mutateAsync({
        profileId: selectedProfileId,
        pin: unlockPin,
      });
      setUnlockPin("");
    } catch (err: unknown) {
      setUnlockError(getErrorMessage(err, "Failed to unlock profile."));
    }
  }

  async function handleLock() {
    if (!selectedProfileId) return;
    try {
      await lockProfile.mutateAsync(selectedProfileId);
    } catch (err: unknown) {
      alert(getErrorMessage(err, "Failed to revoke lock session."));
    }
  }

  async function handleChangePin(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedProfileId) return;
    try {
      await changePin.mutateAsync({
        profileId: selectedProfileId,
        pin: newPin,
        currentPin: currentPin || undefined,
      });
      setNewPin("");
      setCurrentPin("");
      alert("PIN updated successfully.");
    } catch (err: unknown) {
      alert(getErrorMessage(err, "Failed to update PIN."));
    }
  }

  async function handleDisablePin(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedProfileId) return;
    try {
      await disablePin.mutateAsync({
        profileId: selectedProfileId,
        currentPin: currentPin || undefined,
      });
      setCurrentPin("");
      alert("PIN protection disabled successfully.");
    } catch (err: unknown) {
      alert(getErrorMessage(err, "Failed to disable PIN."));
    }
  }

  // Helper for assigning profile to save game (calls API directly to support any save ID)
  async function assignProfileToSave(saveId: number, profileId: number) {
    try {
      const response = await fetch(`/api/save-games/${saveId}/assign-profile`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Profile-Unlock-Token": activeToken || ""
        },
        body: JSON.stringify({ profile_id: profileId })
      });
      if (!response.ok) {
        const data = (await response.json().catch(() => null)) as { detail?: string } | null;
        throw new Error(data?.detail || "Failed to assign profile");
      }
      queryClient.invalidateQueries({ queryKey: ["save-games"] });
      queryClient.invalidateQueries({ queryKey: ["player-profiles"] });
      alert("Assigned profile to save game successfully.");
    } catch (err: unknown) {
      alert(getErrorMessage(err, "Failed to assign profile."));
    }
  }

  return (
    <div>
      <PageHeader eyebrow="Access Control" title="Player Profiles" />

      <div className="grid gap-6 lg:grid-cols-[1fr_1.5fr]">
        {/* Left Column: List Profiles */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">Select Profile</h2>
            <button
              onClick={() => setIsCreating(!isCreating)}
              className="inline-flex items-center gap-1 rounded bg-tech-blue px-3 py-1.5 text-xs font-semibold text-slate-950 hover:bg-sky-300 transition"
            >
              <Plus className="h-3.5 w-3.5" />
              New Profile
            </button>
          </div>

          {isCreating && (
            <form onSubmit={handleCreate} className="panel rounded-lg p-4 space-y-3 border border-tech-blue/20">
              <h3 className="text-sm font-semibold text-white">Create New Profile</h3>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Display Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Gamer Pro"
                  value={createName}
                  onChange={(e) => setCreateName(e.target.value)}
                  className="w-full h-9 rounded border border-white/10 bg-slate-950 px-3 text-sm text-white outline-none focus:border-tech-blue"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Initial PIN (Optional, 4-12 digits)</label>
                <input
                  type="password"
                  placeholder="Leave empty for no PIN"
                  value={createPin}
                  onChange={(e) => setCreatePin(e.target.value)}
                  className="w-full h-9 rounded border border-white/10 bg-slate-950 px-3 text-sm text-white outline-none focus:border-tech-blue"
                />
              </div>
              <div className="flex justify-end gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => setIsCreating(false)}
                  className="rounded bg-white/10 px-3 py-1.5 text-xs font-semibold text-slate-300 hover:bg-white/20 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded bg-tech-blue px-3 py-1.5 text-xs font-semibold text-slate-950 hover:bg-sky-300 transition"
                >
                  Save Profile
                </button>
              </div>
            </form>
          )}

          {profiles.isLoading && <LoadingState />}
          {profiles.data?.length === 0 && !isCreating && (
            <EmptyState title="No Profiles" body="Create a profile to enable lock features for your showrooms." />
          )}

          <div className="space-y-2">
            {profiles.data?.map((p) => {
              const isSelected = selectedProfileId === p.id;
              const isLocked = p.pin_enabled;
              
              return (
                <button
                  key={p.id}
                  onClick={() => setSelectedProfileId(p.id)}
                  className={`w-full panel text-left rounded-lg p-4 flex items-center justify-between transition border ${
                    isSelected ? "border-tech-blue bg-tech-blue/5" : "border-white/5 hover:border-white/20"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className={`grid h-10 w-10 place-items-center rounded-lg ${
                      isSelected ? "bg-tech-blue/20 text-tech-blue" : "bg-white/[0.03] text-slate-400"
                    }`}>
                      <User className="h-5 w-5" />
                    </span>
                    <div>
                      <h3 className="font-semibold text-white text-sm">{p.display_name}</h3>
                      <p className="text-xs text-slate-500">{p.slug}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {isLocked ? (
                      <span className="inline-flex items-center gap-1 rounded bg-amber-400/10 px-2 py-0.5 text-[10px] font-semibold text-amber-400">
                        <Lock className="h-3 w-3" />
                        PIN Lock
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 rounded bg-slate-400/10 px-2 py-0.5 text-[10px] font-semibold text-slate-400">
                        <ShieldOff className="h-3 w-3" />
                        No PIN
                      </span>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Right Column: Profile Actions */}
        <div>
          {selectedProfile ? (
            <div className="panel rounded-lg p-5 space-y-6">
              <div>
                <h2 className="text-xl font-bold text-white mb-1">{selectedProfile.display_name}</h2>
                <p className="text-xs text-slate-400">Manage settings, unlock status, and lock associations for this player profile.</p>
              </div>

              {/* Status & Session controls */}
              <div className="border border-white/10 rounded-lg p-4 bg-white/[0.02] flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-white">Unlock Session</h3>
                  <p className="text-xs text-slate-500 mt-1">
                    {selectedProfile.pin_enabled 
                      ? (activeToken ? "Active session token found." : "Profile is currently locked.")
                      : "PIN verification is disabled on this profile."}
                  </p>
                  {selectedProfile.locked_until && new Date(selectedProfile.locked_until) > new Date() && (
                    <p className="text-xs text-rose-400 mt-1">
                      Locked out until {new Date(selectedProfile.locked_until).toLocaleTimeString()}
                    </p>
                  )}
                </div>

                {selectedProfile.pin_enabled && (
                  <div>
                    {activeToken ? (
                      <button
                        onClick={handleLock}
                        className="inline-flex items-center gap-1.5 rounded bg-rose-500/10 border border-rose-500/30 px-3 py-1.5 text-xs font-semibold text-rose-400 hover:bg-rose-500/20 transition"
                      >
                        <Lock className="h-3.5 w-3.5" />
                        Revoke Lock Session
                      </button>
                    ) : (
                      <button
                        onClick={() => setUnlockPin("")}
                        className="inline-flex items-center gap-1.5 rounded bg-amber-400/15 border border-amber-400/30 px-3 py-1.5 text-xs font-semibold text-amber-400 hover:bg-amber-400/25 transition"
                      >
                        <Unlock className="h-3.5 w-3.5" />
                        Enter PIN to Unlock
                      </button>
                    )}
                  </div>
                )}
              </div>

              {/* Unlock PIN Form */}
              {selectedProfile.pin_enabled && !activeToken && (
                <form onSubmit={handleUnlock} className="border border-amber-400/20 bg-amber-400/5 rounded-lg p-4 space-y-3">
                  <h3 className="text-sm font-semibold text-amber-300 flex items-center gap-1">
                    <Key className="h-4 w-4" />
                    Verify Profile Lock
                  </h3>
                  <div className="flex gap-2">
                    <input
                      type="password"
                      placeholder="Enter profile PIN"
                      value={unlockPin}
                      onChange={(e) => setUnlockPin(e.target.value)}
                      className="flex-1 h-9 rounded border border-white/10 bg-slate-950 px-3 text-sm text-white outline-none focus:border-amber-400"
                    />
                    <button
                      type="submit"
                      className="rounded bg-amber-400 px-4 text-xs font-bold text-slate-950 hover:bg-amber-300 transition"
                    >
                      Verify
                    </button>
                  </div>
                  {unlockError && <p className="text-xs text-rose-400 font-semibold">{unlockError}</p>}
                </form>
              )}

              {/* Assign Save Games */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold text-white">Showroom Save Assignment</h3>
                <p className="text-xs text-slate-400">Link this profile to a save game. Saves attached to this profile will require the PIN code if PIN Lock is enabled.</p>
                
                {saves.isLoading ? <LoadingState /> : (
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {saves.data?.map(s => {
                      const isAssigned = s.player_profile_id === selectedProfile.id;
                      
                      return (
                        <div key={s.id} className="flex items-center justify-between border border-white/5 rounded p-3 bg-white/[0.01]">
                          <div>
                            <span className="text-sm font-medium text-white">{s.name}</span>
                            <span className="block text-xs text-slate-500">
                              Day {s.game_day} / Cash {formatVnd(s.cash)}
                            </span>
                          </div>
                          <div>
                            {isAssigned ? (
                              <span className="inline-flex items-center gap-1 rounded bg-tech-blue/15 px-2.5 py-1 text-xs font-semibold text-tech-blue">
                                <Shield className="h-3.5 w-3.5" />
                                Assigned
                              </span>
                            ) : (
                              <button
                                onClick={() => assignProfileToSave(s.id, selectedProfile.id)}
                                className="rounded bg-white/5 border border-white/10 px-2.5 py-1 text-xs font-semibold text-slate-300 hover:bg-white/10 hover:text-white transition"
                              >
                                Link Profile
                              </button>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Pin update & disable panel */}
              <div className="border border-white/10 rounded-lg p-5 space-y-4">
                <h3 className="text-sm font-semibold text-white border-b border-white/10 pb-2">PIN Security Settings</h3>
                
                {/* Change PIN Form */}
                <form onSubmit={handleChangePin} className="space-y-3">
                  <h4 className="text-xs font-semibold text-slate-300">Set / Change PIN</h4>
                  {selectedProfile.pin_enabled && (
                    <div>
                      <label className="block text-[11px] text-slate-400 mb-0.5">Current PIN</label>
                      <input
                        type="password"
                        placeholder="Current PIN"
                        required
                        value={currentPin}
                        onChange={(e) => setCurrentPin(e.target.value)}
                        className="w-full h-8 rounded border border-white/10 bg-slate-950 px-2.5 text-xs text-white outline-none focus:border-tech-blue"
                      />
                    </div>
                  )}
                  <div>
                    <label className="block text-[11px] text-slate-400 mb-0.5">New PIN (4-12 digits)</label>
                    <input
                      type="password"
                      placeholder="New PIN"
                      required
                      value={newPin}
                      onChange={(e) => setNewPin(e.target.value)}
                      className="w-full h-8 rounded border border-white/10 bg-slate-950 px-2.5 text-xs text-white outline-none focus:border-tech-blue"
                    />
                  </div>
                  <button
                    type="submit"
                    className="rounded bg-tech-blue px-3 py-1 text-xs font-semibold text-slate-950 hover:bg-sky-300 transition"
                  >
                    Update PIN
                  </button>
                </form>

                {/* Disable PIN Form */}
                {selectedProfile.pin_enabled && (
                  <form onSubmit={handleDisablePin} className="space-y-3 pt-3 border-t border-white/5">
                    <h4 className="text-xs font-semibold text-rose-400">Disable PIN Lock</h4>
                    <p className="text-[11px] text-slate-500">This will remove PIN security from all assigned saves.</p>
                    <div>
                      <label className="block text-[11px] text-slate-400 mb-0.5">Current PIN</label>
                      <input
                        type="password"
                        placeholder="Confirm with PIN"
                        required
                        value={currentPin}
                        onChange={(e) => setCurrentPin(e.target.value)}
                        className="w-full h-8 rounded border border-white/10 bg-slate-950 px-2.5 text-xs text-white outline-none focus:border-rose-400"
                      />
                    </div>
                    <button
                      type="submit"
                      className="rounded bg-rose-500/10 border border-rose-500/25 px-3 py-1 text-xs font-semibold text-rose-400 hover:bg-rose-500/20 transition"
                    >
                      Disable PIN
                    </button>
                  </form>
                )}
              </div>
            </div>
          ) : (
            <div className="panel rounded-lg p-8 text-center text-slate-400">
              Select a player profile from the list to manage settings, PIN codes, and save attachments.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
