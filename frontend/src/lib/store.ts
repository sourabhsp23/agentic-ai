import { create } from "zustand";

type Theme = "light" | "dark";
export type View = "workspace" | "data" | "history";

interface UIState {
  dataset: string | null;
  /** History run being viewed; null = the live run in the workspace. */
  selectedRunId: string | null;
  /** Mobile tab. Desktop shows all panels at once. */
  view: View;
  theme: Theme;
  setDataset: (dataset: string) => void;
  selectRun: (id: string | null) => void;
  setView: (view: View) => void;
  toggleTheme: () => void;
}

const initialTheme = (): Theme =>
  document.documentElement.dataset.theme === "dark" ? "dark" : "light";

export const useUI = create<UIState>((set, get) => ({
  dataset: null,
  selectedRunId: null,
  view: "workspace",
  theme: initialTheme(),
  setDataset: (dataset) => set({ dataset }),
  selectRun: (selectedRunId) => set({ selectedRunId, view: "workspace" }),
  setView: (view) => set({ view }),
  toggleTheme: () => {
    const theme: Theme = get().theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem("ip-theme", theme);
    } catch {
      /* storage unavailable: theme still applies for this session */
    }
    set({ theme });
  },
}));
