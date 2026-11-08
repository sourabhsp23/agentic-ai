import { ArrowDown, ArrowUp, ChevronLeft, ChevronRight } from "lucide-react";
import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Tooltip } from "@/components/ui/tooltip";
import { cn } from "@/lib/cn";
import { formatCell, isNumber } from "@/lib/format";

const PAGE_SIZE = 50;
const TRUNCATE_AT = 48;

type Sort = { col: number; dir: "asc" | "desc" } | null;

function compare(a: unknown, b: unknown): number {
  if (a === b) return 0;
  if (a === null || a === undefined) return 1;
  if (b === null || b === undefined) return -1;
  if (isNumber(a) && isNumber(b)) return a - b;
  return String(a).localeCompare(String(b), undefined, { numeric: true });
}

function Cell({ value }: { value: unknown }) {
  const text = formatCell(value);
  if (text.length <= TRUNCATE_AT) return <>{text}</>;
  return (
    <Tooltip content={text}>
      <span tabIndex={0} className="block max-w-cell truncate">
        {text}
      </span>
    </Tooltip>
  );
}

export function ResultTable({ columns, rows, truncated }: { columns: string[]; rows: unknown[][]; truncated: boolean }) {
  const [sort, setSort] = useState<Sort>(null);
  const [page, setPage] = useState(0);

  const numeric = useMemo(
    () => columns.map((_, i) => rows.some((r) => isNumber(r[i])) && rows.every((r) => r[i] == null || isNumber(r[i]))),
    [columns, rows],
  );

  const sorted = useMemo(() => {
    if (!sort) return rows;
    const factor = sort.dir === "asc" ? 1 : -1;
    return [...rows].sort((a, b) => compare(a[sort.col], b[sort.col]) * factor);
  }, [rows, sort]);

  const pages = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE));
  const visible = sorted.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  const toggleSort = (col: number) => {
    setPage(0);
    setSort((s) => (s?.col !== col ? { col, dir: "desc" } : s.dir === "desc" ? { col, dir: "asc" } : null));
  };

  if (rows.length === 0) {
    return <p className="py-3 text-sm text-fg-muted">The query ran but returned 0 rows. Try widening the filters.</p>;
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="max-h-table overflow-auto rounded-control border border-border">
        <table className="w-full border-collapse text-sm tabular">
          <thead className="sticky top-0 z-10 bg-bg-subtle">
            <tr>
              {columns.map((c, i) => {
                const active = sort?.col === i;
                return (
                  <th
                    key={c}
                    scope="col"
                    aria-sort={active ? (sort.dir === "asc" ? "ascending" : "descending") : "none"}
                    className={cn("border-b border-border p-0 font-medium", numeric[i] ? "text-right" : "text-left")}
                  >
                    <button
                      type="button"
                      onClick={() => toggleSort(i)}
                      className={cn(
                        "flex w-full items-center gap-1 whitespace-nowrap px-3 py-2 text-fg-muted transition-colors hover:text-fg",
                        numeric[i] && "flex-row-reverse",
                        active && "text-fg",
                      )}
                    >
                      {c}
                      {active &&
                        (sort.dir === "asc" ? (
                          <ArrowUp className="size-4" aria-hidden />
                        ) : (
                          <ArrowDown className="size-4" aria-hidden />
                        ))}
                    </button>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {visible.map((row, ri) => (
              <tr key={ri} className="transition-colors hover:bg-bg-subtle">
                {row.map((v, ci) => (
                  <td
                    key={ci}
                    className={cn(
                      "whitespace-nowrap border-b border-border px-3 py-2 text-fg",
                      numeric[ci] && "text-right font-mono text-xs",
                    )}
                  >
                    <Cell value={v} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex items-center justify-between gap-2 text-xs text-fg-subtle tabular">
        <span>
          {sorted.length} rows{truncated && " (limited by the API row cap)"}
        </span>
        {pages > 1 && (
          <div className="flex items-center gap-1">
            <Button size="icon" variant="ghost" aria-label="Previous page" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
              <ChevronLeft className="size-4" aria-hidden />
            </Button>
            <span>
              Page {page + 1} of {pages}
            </span>
            <Button
              size="icon"
              variant="ghost"
              aria-label="Next page"
              disabled={page >= pages - 1}
              onClick={() => setPage((p) => p + 1)}
            >
              <ChevronRight className="size-4" aria-hidden />
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
