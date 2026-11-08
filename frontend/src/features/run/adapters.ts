import type { RunRecord } from "@/lib/api";

import type { LiveRun } from "../ask/use-agent-run";
import type { RunViewModel } from "./run-view";

export function fromLive(run: LiveRun): RunViewModel {
  const r = run.result;
  if (!r) {
    return {
      question: run.question,
      dataset: run.dataset,
      status: run.phase === "error" ? "failed" : "running",
      answer: null,
      insights: [],
      followUps: [],
      sql: null,
      table: null,
      chart: null,
      trace: run.steps,
      meta: null,
      error: run.error,
    };
  }
  return {
    question: run.question,
    dataset: run.dataset,
    status: r.status,
    answer: r.answer,
    insights: r.insights,
    followUps: r.follow_ups,
    sql: r.sql,
    table: r.columns.length ? { columns: r.columns, rows: r.rows, truncated: r.truncated } : null,
    chart: r.chart,
    trace: r.trace,
    meta: {
      latencyMs: r.latency_ms,
      tokens: r.usage.input_tokens + r.usage.output_tokens,
      costUsd: r.usage.cost_usd,
      model: r.usage.model,
    },
    error: r.error,
  };
}

export function fromRecord(r: RunRecord): RunViewModel {
  return {
    question: r.question,
    dataset: r.dataset,
    status: r.status === "completed" ? "completed" : "failed",
    answer: r.answer,
    insights: [],
    followUps: [],
    sql: r.sql,
    table: null,
    chart: r.chart,
    trace: r.trace ?? [],
    meta: {
      latencyMs: r.latency_ms,
      tokens: r.input_tokens + r.output_tokens,
      costUsd: r.cost_usd,
      model: r.model,
    },
    error: null,
  };
}
