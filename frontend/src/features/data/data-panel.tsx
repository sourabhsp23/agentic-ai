import { ChevronRight } from "lucide-react";

import { Section } from "@/components/ui/section";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/states";
import { useSchema } from "@/lib/queries";
import { useUI } from "@/lib/store";

import { UploadForm } from "./upload-form";

function SchemaList({ dataset }: { dataset: string }) {
  const { data, isPending, isError, error, refetch } = useSchema(dataset);

  if (isPending) {
    return (
      <div className="flex flex-col gap-3" aria-busy>
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="w-full" />
        ))}
      </div>
    );
  }
  if (isError) return <ErrorState title="Couldn't load tables" message={error.message} onRetry={() => refetch()} />;
  if (data.length === 0) return <EmptyState title="No tables">Upload a CSV below to add one.</EmptyState>;

  return (
    <ul className="flex flex-col">
      {data.map((t) => (
        <li key={t.name} className="border-b border-border last:border-b-0">
          <details className="group">
            <summary className="flex cursor-pointer list-none items-center gap-2 rounded-control py-2 text-sm hover:bg-bg-subtle [&::-webkit-details-marker]:hidden">
              <ChevronRight className="size-4 shrink-0 text-fg-subtle transition-transform group-open:rotate-90" aria-hidden />
              <span className="min-w-0 flex-1 truncate font-mono text-fg">{t.name}</span>
              <span className="text-xs text-fg-subtle tabular">{t.row_count.toLocaleString("en-US")} rows</span>
            </summary>
            <ul className="mb-2 flex flex-col gap-1 pl-6">
              {t.columns.map(([name, type]) => (
                <li key={name} className="flex items-baseline justify-between gap-2 text-xs">
                  <span className="truncate font-mono text-fg-muted">{name}</span>
                  <span className="shrink-0 font-mono text-fg-subtle">{type.toLowerCase()}</span>
                </li>
              ))}
            </ul>
          </details>
        </li>
      ))}
    </ul>
  );
}

export function DataPanel() {
  const dataset = useUI((s) => s.dataset);
  return (
    <div className="flex flex-col gap-6">
      <Section title="Tables" meta={dataset ?? undefined}>
        {dataset ? (
          <SchemaList dataset={dataset} />
        ) : (
          <p className="text-sm text-fg-muted">Select a dataset to see its tables.</p>
        )}
      </Section>
      <Section title="Add data">
        <UploadForm />
      </Section>
    </div>
  );
}
