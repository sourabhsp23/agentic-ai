import { CornerDownRight, RotateCw } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Section } from "@/components/ui/section";
import { ErrorState, Skeleton } from "@/components/ui/states";
import type { Chart, TraceStep } from "@/lib/api";
import { cn } from "@/lib/cn";
import { formatCost, formatMs } from "@/lib/format";

import { ResultChart } from "./result-chart";
import { ResultTable } from "./result-table";
import { SqlBlock } from "./sql-block";
import { TraceList } from "./trace-list";

/** One shape for both live runs and runs loaded from history. */
export interface RunViewModel {
  question: string;
  dataset: string | null;
  status: "running" | "completed" | "failed";
  answer: string | null;
  insights: string[];
  followUps: string[];
  sql: string | null;
  table: { columns: string[]; rows: unknown[][]; truncated: boolean } | null;
  chart: Chart | null;
  trace: TraceStep[];
  meta: { latencyMs: number; tokens: number; costUsd: number; model: string | null } | null;
  error: string | null;
}

const statusStyle = {
  running: "text-info",
  completed: "text-success",
  failed: "text-danger",
} as const;

/** Renders **bold** from model output without pulling in a markdown library. */
function Prose({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return (
    <p className="max-w-prose whitespace-pre-line text-base text-fg">
      {parts.map((p, i) =>
        p.startsWith("**") && p.endsWith("**") ? (
          <strong key={i} className="font-semibold">
            {p.slice(2, -2)}
          </strong>
        ) : (
          p
        ),
      )}
    </p>
  );
}

function MetaItem({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-baseline gap-1">
      <dt className="text-fg-subtle">{label}</dt>
      <dd className="font-mono text-fg-muted tabular">{children}</dd>
    </div>
  );
}

interface RunViewProps {
  run: RunViewModel;
  onAsk: (question: string) => void;
  canAsk: boolean;
}

export function RunView({ run, onAsk, canAsk }: RunViewProps) {
  const running = run.status === "running";

  return (
    <article className="flex flex-col gap-6" aria-busy={running}>
      <header className="flex flex-col gap-2">
        <h1 className="break-words text-md font-medium text-fg">{run.question}</h1>
        <dl className="flex flex-wrap gap-x-4 gap-y-1 text-xs">
          <div className="flex items-baseline gap-1">
            <dt className="sr-only">Status</dt>
            <dd className={cn("font-medium", statusStyle[run.status])}>
              {run.status === "running" ? "Running" : run.status === "completed" ? "Completed" : "Failed"}
            </dd>
          </div>
          {run.dataset && <MetaItem label="Dataset">{run.dataset}</MetaItem>}
          {run.meta && (
            <>
              <MetaItem label="Latency">{formatMs(run.meta.latencyMs)}</MetaItem>
              <MetaItem label="Tokens">{run.meta.tokens.toLocaleString("en-US")}</MetaItem>
              <MetaItem label="Est. cost">{formatCost(run.meta.costUsd)}</MetaItem>
              {run.meta.model && <MetaItem label="Model">{run.meta.model}</MetaItem>}
            </>
          )}
        </dl>
      </header>

      <Section title="Answer">
        {running ? (
          <div className="flex max-w-prose flex-col gap-2">
            <Skeleton className="w-full" />
            <Skeleton className="w-full" />
            <Skeleton className="w-rail" />
          </div>
        ) : run.status === "failed" ? (
          <ErrorState
            title="The agents couldn't answer this question"
            message={run.answer || run.error || "No answer was produced."}
            onRetry={canAsk ? () => onAsk(run.question) : undefined}
          />
        ) : (
          <div className="flex flex-col gap-4">
            <Prose text={run.answer ?? ""} />
            {run.insights.length > 0 && (
              <ul className="flex max-w-prose list-disc flex-col gap-1 pl-4 text-sm text-fg-muted">
                {run.insights.map((i) => (
                  <li key={i}>{i}</li>
                ))}
              </ul>
            )}
            {run.followUps.length > 0 && canAsk && (
              <div className="flex flex-col items-start gap-1">
                <p className="text-xs text-fg-subtle">Follow-up questions</p>
                {run.followUps.map((q) => (
                  <Button key={q} variant="link" size="inline" onClick={() => onAsk(q)}>
                    <CornerDownRight className="size-4 shrink-0" aria-hidden />
                    {q}
                  </Button>
                ))}
              </div>
            )}
          </div>
        )}
      </Section>

      {(running || run.chart) && (
        <Section title="Chart">
          {running ? <Skeleton className="h-chart w-full" /> : run.chart && <ResultChart chart={run.chart} />}
        </Section>
      )}

      {(running || run.sql) && (
        <Section title="Result" meta={run.table ? `${run.table.columns.length} columns` : undefined}>
          {running ? (
            <div className="flex flex-col gap-2">
              {[0, 1, 2, 3].map((i) => (
                <Skeleton key={i} className="w-full" />
              ))}
            </div>
          ) : run.table ? (
            <ResultTable columns={run.table.columns} rows={run.table.rows} truncated={run.table.truncated} />
          ) : (
            <div className="flex flex-wrap items-center gap-3 py-2 text-sm text-fg-muted">
              History keeps the SQL and answer, not the result rows.
              {canAsk && (
                <Button size="sm" variant="secondary" onClick={() => onAsk(run.question)}>
                  <RotateCw className="size-4" aria-hidden />
                  Run again for rows
                </Button>
              )}
            </div>
          )}
        </Section>
      )}

      {run.sql && !running && <SqlBlock sql={run.sql} />}

      <Section title="Agent trace" meta={`${run.trace.length} steps`}>
        <TraceList steps={run.trace} running={running} />
      </Section>
    </article>
  );
}
