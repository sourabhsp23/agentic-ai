import { AppHeader } from "@/components/app-header";
import { cn } from "@/lib/cn";
import { useUI, type View } from "@/lib/store";

import { Workspace } from "./features/ask/workspace";
import { DataPanel } from "./features/data/data-panel";
import { HistoryPanel } from "./features/history/history-panel";

const VIEWS: { id: View; label: string }[] = [
  { id: "workspace", label: "Analysis" },
  { id: "data", label: "Data" },
  { id: "history", label: "History" },
];

/** Below 1024px only one panel shows at a time; panels stay mounted so a live run keeps streaming. */
function MobileNav() {
  const { view, setView } = useUI();
  return (
    <nav aria-label="Panels" className="flex gap-1 border-b border-border px-4 lg:hidden">
      {VIEWS.map((v) => (
        <button
          key={v.id}
          type="button"
          onClick={() => setView(v.id)}
          aria-current={view === v.id ? "page" : undefined}
          className={cn(
            "-mb-px border-b-2 px-3 py-2 text-sm transition-colors",
            view === v.id ? "border-accent font-medium text-fg" : "border-transparent text-fg-muted hover:text-fg",
          )}
        >
          {v.label}
        </button>
      ))}
    </nav>
  );
}

export default function App() {
  const view = useUI((s) => s.view);
  const panel = (id: View) => (view === id ? "block" : "hidden");

  return (
    <div className="flex min-h-full flex-col">
      <AppHeader />
      <MobileNav />
      <div className="mx-auto grid w-full max-w-content flex-1 grid-cols-1 gap-6 px-4 py-4 lg:grid-cols-shell">
        <aside aria-label="Data" className={cn(panel("data"), "lg:block")}>
          <DataPanel />
        </aside>
        <main className={cn(panel("workspace"), "min-w-0 lg:block")}>
          <Workspace />
        </main>
        <aside aria-label="History" className={cn(panel("history"), "lg:block")}>
          <HistoryPanel />
        </aside>
      </div>
    </div>
  );
}
