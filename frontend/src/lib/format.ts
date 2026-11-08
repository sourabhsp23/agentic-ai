const numberFmt = new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 });
const compactFmt = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 });
const timeFmt = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

export const isNumber = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);

export function formatCell(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (isNumber(v)) return numberFmt.format(v);
  return String(v);
}

export const formatCompact = (v: number) => compactFmt.format(v);

export function formatMs(ms: number): string {
  return ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(1)} s`;
}

export function formatCost(usd: number): string {
  if (usd === 0) return "$0";
  return usd < 0.01 ? `$${usd.toFixed(5)}` : `$${usd.toFixed(3)}`;
}

export const formatTime = (iso: string) => timeFmt.format(new Date(iso));

/** "sql_agent" -> "SQL agent", "retrieve_context" -> "Retrieve context" */
export function nodeLabel(node: string): string {
  const labels: Record<string, string> = {
    retrieve_context: "Retrieve context",
    planner: "Planner",
    sql_agent: "SQL agent",
    analyst: "Analyst",
    visualizer: "Visualizer",
    critic: "Critic",
    finalize: "Finalize",
  };
  return labels[node] ?? node;
}
