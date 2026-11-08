import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./api";

export const keys = {
  info: ["info"] as const,
  datasets: ["datasets"] as const,
  schema: (dataset: string) => ["schema", dataset] as const,
  runs: ["runs"] as const,
  run: (id: string) => ["run", id] as const,
};

export const useInfo = () => useQuery({ queryKey: keys.info, queryFn: api.info, staleTime: Infinity });

export const useDatasets = () => useQuery({ queryKey: keys.datasets, queryFn: api.datasets });

export const useSchema = (dataset: string | null) =>
  useQuery({
    queryKey: keys.schema(dataset ?? ""),
    queryFn: () => api.schema(dataset as string),
    enabled: Boolean(dataset),
  });

export const useRuns = () => useQuery({ queryKey: keys.runs, queryFn: () => api.runs(30) });

export const useRun = (id: string | null) =>
  useQuery({ queryKey: keys.run(id ?? ""), queryFn: () => api.run(id as string), enabled: Boolean(id) });

export function useUpload() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ dataset, file }: { dataset: string; file: File }) => api.upload(dataset, file),
    onSuccess: (_data, { dataset }) => {
      qc.invalidateQueries({ queryKey: keys.datasets });
      qc.invalidateQueries({ queryKey: keys.schema(dataset) });
    },
  });
}
