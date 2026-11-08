import { ArrowLeft } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/states";
import { useRun } from "@/lib/queries";
import { useUI } from "@/lib/store";

import { fromLive, fromRecord } from "../run/adapters";
import { RunView } from "../run/run-view";
import { AskForm } from "./ask-form";
import { useAgentRun } from "./use-agent-run";

function HistoryRun({ id, onAsk, canAsk }: { id: string; onAsk: (q: string) => void; canAsk: boolean }) {
  const { data, isPending, isError, error, refetch } = useRun(id);
  if (isPending) {
    return (
      <div className="flex flex-col gap-3" aria-busy>
        <Skeleton className="h-6 w-full" />
        <Skeleton className="w-rail" />
        <Skeleton className="h-chart w-full" />
      </div>
    );
  }
  if (isError) return <ErrorState title="Couldn't load this run" message={error.message} onRetry={() => refetch()} />;
  return <RunView run={fromRecord(data)} onAsk={onAsk} canAsk={canAsk} />;
}

export function Workspace() {
  const { dataset, selectedRunId, selectRun } = useUI();
  const { run, start, cancel } = useAgentRun();
  const [question, setQuestion] = useState("");
  const running = run.phase === "running";

  const ask = (q: string) => {
    if (!dataset) return;
    setQuestion(q);
    selectRun(null);
    start(dataset, q);
  };

  return (
    <div className="flex flex-col gap-6">
      <AskForm
        dataset={dataset}
        running={running}
        question={question}
        onQuestionChange={setQuestion}
        onSubmit={ask}
        onCancel={cancel}
      />

      {selectedRunId ? (
        <div className="flex flex-col gap-3">
          <Button size="sm" variant="ghost" className="self-start" onClick={() => selectRun(null)}>
            <ArrowLeft className="size-4" aria-hidden />
            Back to current run
          </Button>
          <HistoryRun id={selectedRunId} onAsk={ask} canAsk={Boolean(dataset) && !running} />
        </div>
      ) : run.phase === "idle" ? (
        <EmptyState title="No analysis yet">
          Ask a question above. A planner breaks it down, a SQL agent queries the data and fixes its own
          errors, an analyst and a visualizer work in parallel, and a critic checks the answer against the
          numbers before you see it.
        </EmptyState>
      ) : (
        <RunView run={fromLive(run)} onAsk={ask} canAsk={Boolean(dataset) && !running} />
      )}
    </div>
  );
}
