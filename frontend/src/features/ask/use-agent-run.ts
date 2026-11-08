import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useReducer, useRef } from "react";

import { ApiError, streamAsk, type RunResult, type TraceStep } from "@/lib/api";
import { keys } from "@/lib/queries";

export type RunPhase = "idle" | "running" | "done" | "error";

export interface LiveRun {
  phase: RunPhase;
  dataset: string | null;
  question: string;
  steps: TraceStep[];
  result: RunResult | null;
  error: string | null;
}

type Action =
  | { type: "start"; dataset: string; question: string }
  | { type: "step"; step: TraceStep }
  | { type: "final"; result: RunResult }
  | { type: "error"; error: string }
  | { type: "cancel" };

const initial: LiveRun = { phase: "idle", dataset: null, question: "", steps: [], result: null, error: null };

function reducer(state: LiveRun, action: Action): LiveRun {
  switch (action.type) {
    case "start":
      return { ...initial, phase: "running", dataset: action.dataset, question: action.question };
    case "step":
      return { ...state, steps: [...state.steps, action.step] };
    case "final":
      return { ...state, phase: "done", result: action.result, steps: action.result.trace };
    case "error":
      return { ...state, phase: "error", error: action.error };
    case "cancel":
      return { ...state, phase: state.steps.length ? "error" : "idle", error: "Run cancelled." };
  }
}

/** Streams one agent run over SSE, exposing live steps and the final result. */
export function useAgentRun() {
  const [run, dispatch] = useReducer(reducer, initial);
  const controller = useRef<AbortController | null>(null);
  const qc = useQueryClient();

  const start = useCallback(
    async (dataset: string, question: string) => {
      controller.current?.abort();
      const ctrl = new AbortController();
      controller.current = ctrl;
      dispatch({ type: "start", dataset, question });
      try {
        for await (const event of streamAsk(dataset, question, ctrl.signal)) {
          if (event.type === "step") dispatch({ type: "step", step: event });
          if (event.type === "final") dispatch({ type: "final", result: event.result });
        }
        qc.invalidateQueries({ queryKey: keys.runs });
      } catch (err) {
        if (ctrl.signal.aborted) return;
        dispatch({ type: "error", error: err instanceof ApiError ? err.message : "The stream ended unexpectedly." });
      }
    },
    [qc],
  );

  const cancel = useCallback(() => {
    controller.current?.abort();
    dispatch({ type: "cancel" });
  }, []);

  useEffect(() => () => controller.current?.abort(), []);

  return { run, start, cancel };
}
