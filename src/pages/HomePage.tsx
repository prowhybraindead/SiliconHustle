import { FormEvent, useState } from "react";
import { HardDriveDownload, Play, Plus } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { useCreateSaveGame, useSaveGames } from "../api/hooks";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { StatusBadge } from "../components/StatusBadge";
import { BrandWordmark } from "../components/BrandWordmark";
import { useGameStore } from "../store/gameStore";
import { formatVnd } from "../utils/format";

export function HomePage() {
  const [name, setName] = useState("My Tech Showroom");
  const navigate = useNavigate();
  const { setSelectedSaveId } = useGameStore();
  const saves = useSaveGames();
  const createSave = useCreateSaveGame();

  function openSave(id: number) {
    setSelectedSaveId(id);
    navigate("/dashboard");
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const save = await createSave.mutateAsync(name);
    openSave(save.id);
  }

  return (
    <main className="mx-auto min-h-screen max-w-6xl px-4 py-8">
      <section className="mb-8">
        <div className="flex items-center gap-3">
          <span className="grid h-12 w-12 place-items-center rounded-lg border border-tech-blue/30 bg-tech-blue/10 text-tech-blue">
            <HardDriveDownload className="h-6 w-6" />
          </span>
          <div className="min-w-0">
            <BrandWordmark className="max-w-[280px] sm:max-w-[360px]" eager size="xl" />
            <p className="mt-2 text-slate-400">Tech Shop Simulator / Buy low. Test hard. Sell smart.</p>
          </div>
        </div>
      </section>

      <form className="panel mb-6 flex flex-col gap-3 rounded-lg p-4 sm:flex-row" onSubmit={handleSubmit}>
        <input
          className="min-h-11 flex-1 rounded border border-white/10 bg-slate-950 px-3 text-sm text-white outline-none transition focus:border-tech-blue"
          onChange={(event) => setName(event.target.value)}
          placeholder="Save game name"
          value={name}
        />
        <button
          className="inline-flex min-h-11 items-center justify-center gap-2 rounded bg-tech-blue px-4 text-sm font-semibold text-slate-950 transition hover:bg-sky-300 disabled:cursor-wait disabled:opacity-60"
          disabled={createSave.isPending}
          type="submit"
        >
          <Plus className="h-4 w-4" />
          Create Save
        </button>
      </form>

      {saves.isLoading ? <LoadingState /> : null}
      {saves.isError ? <ErrorState message={(saves.error as Error).message} /> : null}
      {saves.data?.length === 0 ? <EmptyState title="No save games yet" body="Create a showroom save to begin your private run." /> : null}

      <div className="grid gap-3">
        {saves.data?.map((save) => (
          <button
            key={save.id}
            className="panel flex flex-col gap-4 rounded-lg p-4 text-left transition hover:border-tech-blue/40 sm:flex-row sm:items-center sm:justify-between"
            onClick={() => openSave(save.id)}
            type="button"
          >
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="font-semibold text-white">{save.name}</h2>
                <StatusBadge value={`Day ${save.game_day}`} tone="blue" />
              </div>
              <p className="mt-2 text-sm text-slate-400">
                Cash {formatVnd(save.cash)} / Reputation {save.reputation}
              </p>
            </div>
            <span className="inline-flex items-center gap-2 text-sm font-semibold text-tech-blue">
              <Play className="h-4 w-4" />
              Open Save
            </span>
          </button>
        ))}
      </div>
    </main>
  );
}
