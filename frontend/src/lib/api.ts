/** Typed client for the InsightPilot FastAPI backend. */

export interface AppInfo {
  name: string;
  version: string;
  env: string;
  git_sha: string;
  llm_provider: string;
  model: string;
  storage: string;
}

export interface Dataset {
  name: string;
  files: string[];
}

export interface TableSchema {
  name: string;
  row_count: number;
  columns: [string, string][];
}

export interface TraceStep {
  node: string;
  ms: number;
  summary: string;
}

export interface Chart {
  type: "bar" | "line" | "pie" | "scatter";
  x: string;
  y: string;
  title: string;
  labels: (string | number)[];
  values: number[];
}

export interface Usage {
  model: string | null;
  llm_calls: number;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
}

export interface RunResult {
  run_id: string;
  status: "completed" | "failed";
  answer: string;
  insights: string[];
  follow_ups: string[];
  sql: string | null;
  columns: string[];
  rows: unknown[][];
  truncated: boolean;
  chart: Chart | null;
  sources: string[];
  trace: TraceStep[];
  usage: Usage;
  latency_ms: number;
  error: string | null;
}

export interface RunRecord {
  id: string;
  created_at: string;
  dataset: string;
  question: string;
  status: string;
  answer: string | null;
  sql: string | null;
  chart: Chart | null;
  trace: TraceStep[] | null;
  model: string | null;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  latency_ms: number;
}

export type StreamEvent =
  | { type: "start"; run_id: string }
  | ({ type: "step" } & TraceStep)
  | { type: "final"; result: RunResult };

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

const API_KEY = import.meta.env.VITE_API_KEY as string | undefined;

function headers(extra: Record<string, string> = {}): HeadersInit {
  return API_KEY ? { "X-API-Key": API_KEY, ...extra } : extra;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`/api${path}`, { ...init, headers: headers(init.headers as Record<string, string>) });
  } catch {
    throw new ApiError("Can't reach the API. Check that the backend is running on port 8000.", 0);
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = typeof body.detail === "string" ? body.detail : `Request failed with status ${res.status}.`;
    throw new ApiError(detail, res.status);
  }
  return res.json() as Promise<T>;
}

export const api = {
  info: () => request<AppInfo>("/info"),
  datasets: () => request<Dataset[]>("/datasets"),
  schema: (dataset: string) => request<TableSchema[]>(`/datasets/${encodeURIComponent(dataset)}/schema`),
  runs: (limit = 30) => request<RunRecord[]>(`/runs?limit=${limit}`),
  run: (id: string) => request<RunRecord>(`/runs/${encodeURIComponent(id)}`),
  upload: (dataset: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<{ dataset: string; file: string; bytes: number }>(
      `/datasets/${encodeURIComponent(dataset)}/upload`,
      { method: "POST", body: form },
    );
  },
};

/** POST /ask/stream and yield Server-Sent Events as they arrive. */
export async function* streamAsk(
  dataset: string,
  question: string,
  signal: AbortSignal,
): AsyncGenerator<StreamEvent> {
  let res: Response;
  try {
    res = await fetch("/api/ask/stream", {
      method: "POST",
      headers: headers({ "Content-Type": "application/json" }),
      body: JSON.stringify({ dataset, question }),
      signal,
    });
  } catch (err) {
    if (signal.aborted) throw err;
    throw new ApiError("Can't reach the API. Check that the backend is running on port 8000.", 0);
  }
  if (!res.ok || !res.body) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(typeof body.detail === "string" ? body.detail : "The run could not start.", res.status);
  }

  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += value;
    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      const chunk = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      const data = chunk
        .split("\n")
        .filter((line) => line.startsWith("data: "))
        .map((line) => line.slice(6))
        .join("");
      if (data) yield JSON.parse(data) as StreamEvent;
      boundary = buffer.indexOf("\n\n");
    }
  }
}
