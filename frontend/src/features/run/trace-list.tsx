import { Check } from "lucide-react";

import { Skeleton } from "@/components/ui/states";
import type { TraceStep } from "@/lib/api";
import { formatMs, nodeLabel } from "@/lib/format";

/** Ordered agent steps. While running, a placeholder row marks the step in progress. */
export function TraceList({ steps, running }: { steps: TraceStep[]; running: boolean }) {
  return (
    <ol className="flex flex-col">
      {steps.map((s, i) => (
        <li
          key={`${s.node}-${i}`}
          className="grid grid-cols-trace items-baseline gap-3 border-b border-border py-2 text-sm last:border-b-0 max-md:grid-cols-trace-sm"
        >
          <Check className="size-4 self-center text-success" aria-label="Done" />
          <span className="font-medium text-fg">{nodeLabel(s.node)}</span>
          <span className="min-w-0 break-words text-fg-muted max-md:col-span-2 max-md:col-start-2 max-md:row-start-2">
            {s.summary}
          </span>
          <span className="font-mono text-xs text-fg-subtle tabular max-md:col-start-3 max-md:row-start-1">
            {formatMs(s.ms)}
          </span>
        </li>
      ))}
      {running && (
        <li className="grid grid-cols-trace-live items-center gap-3 py-2" aria-live="polite">
          <span className="size-2 justify-self-center rounded-full bg-accent" aria-hidden />
          <span className="flex items-center gap-3 text-sm text-fg-muted">
            Working
            <Skeleton className="w-sidebar" />
          </span>
        </li>
      )}
    </ol>
  );
}
