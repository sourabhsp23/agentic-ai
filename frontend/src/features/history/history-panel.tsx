import { Section } from "@/components/ui/section";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/states";
import { cn } from "@/lib/cn";
import { formatMs, formatTime } from "@/lib/format";
import { useRuns } from "@/lib/queries";
import { useUI } from "@/lib/store";

export function HistoryPanel() {
  const { data, isPending, isError, error, refetch } = useRuns();
  const { selectedRunId, selectRun } = useUI();

  return (
    <Section title="History" meta={data ? `${data.length} recent` : undefined}>
      {isPending ? (
        <div className="flex flex-col gap-4" aria-busy>
          {[0, 1, 2, 3, 4].map((i) => (
            <div key={i} className="flex flex-col gap-2">
              <Skeleton className="w-full" />
              <Skeleton className="w-sidebar" />
            </div>
          ))}
        </div>
      ) : isError ? (
        <ErrorState title="Couldn't load history" message={error.message} onRetry={() => refetch()} />
      ) : data.length === 0 ? (
        <EmptyState title="No runs yet">Each question you ask is saved here with its SQL, answer and cost.</EmptyState>
      ) : (
        <ul className="flex flex-col">
          {data.map((r) => {
            const selected = r.id === selectedRunId;
            return (
              <li key={r.id} className="border-b border-border last:border-b-0">
                <button
                  type="button"
                  onClick={() => selectRun(r.id)}
                  aria-current={selected || undefined}
                  className={cn(
                    "flex w-full flex-col gap-1 rounded-control px-2 py-2 text-left transition-colors hover:bg-bg-subtle",
                    selected && "bg-accent-subtle hover:bg-accent-subtle",
                  )}
                >
                  <span className="line-clamp-2 break-words text-sm text-fg">{r.question}</span>
                  <span className="flex items-center gap-2 text-xs text-fg-subtle tabular">
                    <span
                      className={cn("size-2 rounded-full", r.status === "completed" ? "bg-success" : "bg-danger")}
                      aria-hidden
                    />
                    <span className="sr-only">{r.status}</span>
                    {formatTime(r.created_at)}
                    <span aria-hidden>·</span>
                    {formatMs(r.latency_ms)}
                    <span aria-hidden>·</span>
                    <span className="truncate">{r.dataset}</span>
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </Section>
  );
}
