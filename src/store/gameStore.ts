import { create } from "zustand";

interface GameStore {
  selectedSaveId: number | null;
  setSelectedSaveId: (id: number | null) => void;
}

const storedSaveId = window.localStorage.getItem("silicon-hustle-save-id");

export const useGameStore = create<GameStore>((set) => ({
  selectedSaveId: storedSaveId ? Number(storedSaveId) : null,
  setSelectedSaveId: (id) => {
    if (id) {
      window.localStorage.setItem("silicon-hustle-save-id", String(id));
    } else {
      window.localStorage.removeItem("silicon-hustle-save-id");
    }
    set({ selectedSaveId: id });
  },
}));
