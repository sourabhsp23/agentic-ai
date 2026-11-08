import { Upload } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/field";
import { useUpload } from "@/lib/queries";
import { useUI } from "@/lib/store";

const NAME_RE = /^[A-Za-z0-9_-]{1,64}$/;

export function UploadForm() {
  const { dataset: current, setDataset } = useUI();
  const [name, setName] = useState(current ?? "");
  const [nameTouched, setNameTouched] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const upload = useUpload();

  useEffect(() => {
    if (!nameTouched && current) setName(current);
  }, [current, nameTouched]);

  const nameError =
    nameTouched && !NAME_RE.test(name) ? "Use 1–64 letters, digits, hyphens or underscores." : null;
  const fileError = file && !file.name.toLowerCase().endsWith(".csv") ? "Only .csv files are supported." : null;

  const submit = (e: FormEvent) => {
    e.preventDefault();
    setNameTouched(true);
    if (!file || !NAME_RE.test(name) || fileError) return;
    upload.mutate(
      { dataset: name, file },
      {
        onSuccess: () => {
          setDataset(name);
          setFile(null);
          if (fileInput.current) fileInput.current.value = "";
        },
      },
    );
  };

  return (
    <form onSubmit={submit} className="flex flex-col gap-3" noValidate>
      <Field label="Dataset" error={nameError} helper="Existing name adds a table; a new name creates a dataset.">
        {({ id, describedBy, invalid }) => (
          <Input
            id={id}
            aria-describedby={describedBy}
            invalid={invalid}
            value={name}
            onChange={(e) => setName(e.target.value)}
            onBlur={() => setNameTouched(true)}
            placeholder="ecommerce"
          />
        )}
      </Field>
      <Field label="CSV file" error={fileError} helper="Max 20 MB. The file name becomes the table name.">
        {({ id, describedBy, invalid }) => (
          <Input
            ref={fileInput}
            id={id}
            type="file"
            accept=".csv,text/csv"
            aria-describedby={describedBy}
            invalid={invalid}
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="py-1 text-sm file:mr-3 file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-fg"
          />
        )}
      </Field>
      {upload.isError && (
        <p role="alert" className="text-xs text-danger">
          Upload failed: {upload.error.message}
        </p>
      )}
      {upload.isSuccess && (
        <p role="status" className="text-xs text-success">
          Added {upload.data.file} to {upload.data.dataset}.
        </p>
      )}
      <Button type="submit" size="sm" variant="secondary" loading={upload.isPending} disabled={!file} className="self-start">
        <Upload className="size-4" aria-hidden />
        Upload CSV
      </Button>
    </form>
  );
}
