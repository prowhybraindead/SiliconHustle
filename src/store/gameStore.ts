import { create } from "zustand";

interface GameStore {
  selectedSaveId: number | null;
  tutorialMode: boolean;
  tutorialStep: number;
  tutorialSaveId: number | null;
  tutorialSeen: boolean;
  setSelectedSaveId: (id: number | null) => void;
  startTutorial: (saveId: number) => void;
  setTutorialStep: (step: number) => void;
  resetTutorial: () => void;
  endTutorial: () => void;
}

const storedSaveId = window.localStorage.getItem("silicon-hustle-save-id");
const storedTutorialMode = window.localStorage.getItem("silicon-hustle-tutorial-mode") === "true";
const storedTutorialStep = Number(window.localStorage.getItem("silicon-hustle-tutorial-step") ?? "0");
const storedTutorialSaveId = Number(window.localStorage.getItem("silicon-hustle-tutorial-save-id") ?? "0");
const storedTutorialSeen = window.localStorage.getItem("silicon-hustle-tutorial-seen") === "true";

export const useGameStore = create<GameStore>((set, get) => ({
  selectedSaveId: storedSaveId ? Number(storedSaveId) : null,
  tutorialMode: storedTutorialMode,
  tutorialStep: Number.isFinite(storedTutorialStep) ? storedTutorialStep : 0,
  tutorialSaveId: storedTutorialMode && Number.isFinite(storedTutorialSaveId) && storedTutorialSaveId > 0 ? storedTutorialSaveId : null,
  tutorialSeen: storedTutorialSeen,
  setSelectedSaveId: (id) => {
    if (id) {
      window.localStorage.setItem("silicon-hustle-save-id", String(id));
    } else {
      window.localStorage.removeItem("silicon-hustle-save-id");
    }
    set({
      selectedSaveId: id,
      tutorialMode: id !== null && id === get().tutorialSaveId,
    });
  },
  startTutorial: (saveId) => {
    window.localStorage.setItem("silicon-hustle-tutorial-mode", "true");
    window.localStorage.setItem("silicon-hustle-tutorial-step", "0");
    window.localStorage.setItem("silicon-hustle-tutorial-save-id", String(saveId));
    window.localStorage.setItem("silicon-hustle-tutorial-seen", "true");
    set({ tutorialMode: true, tutorialStep: 0, tutorialSaveId: saveId, tutorialSeen: true });
  },
  setTutorialStep: (step) => {
    window.localStorage.setItem("silicon-hustle-tutorial-step", String(step));
    set({ tutorialStep: step });
  },
  resetTutorial: () => {
    window.localStorage.setItem("silicon-hustle-tutorial-mode", "true");
    window.localStorage.setItem("silicon-hustle-tutorial-step", "0");
    set({ tutorialMode: true, tutorialStep: 0, tutorialSaveId: get().tutorialSaveId });
  },
  endTutorial: () => {
    window.localStorage.removeItem("silicon-hustle-tutorial-mode");
    window.localStorage.removeItem("silicon-hustle-tutorial-step");
    window.localStorage.removeItem("silicon-hustle-tutorial-save-id");
    set({ tutorialMode: false, tutorialStep: 0, tutorialSaveId: null });
  },
}));
