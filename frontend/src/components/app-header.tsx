import { Moon, Sun } from "lucide-react";
import { useEffect } from "react";

import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/states";
import { useDatasets, useInfo } from "@/lib/queries";
import { useUI } from "@/lib/store";

function DatasetPicker() {
  const { dataset, setDataset } = useUI();
  const { data, isPending, isError, refetch } = useDatasets();

  // Default to the first dataset once the list arrives.
  useEffect(() => {
    if (!dataset && data?.length) setDataset(data[0].name);
  }, [data, dataset, setDataset]);

  if (isPending) return <Skeleton className="h-control-sm w-sidebar" />;
  if (isError) {
    return (
      <Button size="sm" variant="danger" onClick={() => refetch()}>
        Datasets unavailable, retry
      </Button>
    );
  }
  return (
    <Select
      ariaLabel="Dataset"
      placeholder={data.length ? "Select dataset" : "No datasets, upload a CSV"}
      value={dataset ?? undefined}
      onValueChange={setDataset}
      disabled={data.length === 0}
      options={data.map((d) => ({ value: d.name, label: `${d.name} · ${d.files.length} tables` }))}
      className="w-sidebar max-sm:w-full"
    />
  );
}

export function AppHeader() {
  const { theme, toggleTheme } = useUI();
  const { data: info } = useInfo();

  return (
    <header className="sticky top-0 z-20 border-b border-border bg-bg">
      <div className="mx-auto flex h-header max-w-content items-center gap-4 px-4">
        <span className="text-base font-semibold text-fg">InsightPilot</span>
        <div className="min-w-0 flex-1 max-sm:flex-auto">
          <DatasetPicker />
        </div>
        {info && (
          <span className="truncate font-mono text-xs text-fg-subtle max-md:hidden">
            {info.model} · {info.env} · {info.git_sha.slice(0, 7)}
          </span>
        )}
        <Button
          size="icon"
          variant="ghost"
          onClick={toggleTheme}
          aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
        >
          {theme === "dark" ? <Sun className="size-4" aria-hidden /> : <Moon className="size-4" aria-hidden />}
        </Button>
      </div>
    </header>
  );
}
