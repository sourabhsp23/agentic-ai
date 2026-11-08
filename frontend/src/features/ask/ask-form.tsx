import { CornerDownLeft, Square } from "lucide-react";
import { useState, type FormEvent, type KeyboardEvent } from "react";

import { Button } from "@/components/ui/button";
import { Field, Textarea } from "@/components/ui/field";

const EXAMPLES = [
  "What was net revenue by month in 2025?",
  "Which product categories had the highest gross margin last year?",
  "Compare average order value across customer segments.",
  "What is the return rate by sales channel?",
];

const MIN_LENGTH = 6;

interface AskFormProps {
  dataset: string | null;
  running: boolean;
  question: string;
  onQuestionChange: (q: string) => void;
  onSubmit: (q: string) => void;
  onCancel: () => void;
}

export function AskForm({ dataset, running, question, onQuestionChange, onSubmit, onCancel }: AskFormProps) {
  const [touched, setTouched] = useState(false);
  const trimmed = question.trim();
  const error = touched && trimmed.length < MIN_LENGTH ? `Write at least ${MIN_LENGTH} characters.` : null;
  const canSubmit = Boolean(dataset) && trimmed.length >= MIN_LENGTH && !running;

  const submit = (e?: FormEvent) => {
    e?.preventDefault();
    setTouched(true);
    if (canSubmit) onSubmit(trimmed);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submit();
  };

  return (
    <form onSubmit={submit} className="flex flex-col gap-3" noValidate>
      <Field
        label="Question"
        error={error}
        helper={
          dataset
            ? `Plain English. The agents write SQL against “${dataset}”, check it, and chart the result.`
            : "Select a dataset in the header first."
        }
      >
        {({ id, describedBy, invalid }) => (
          <Textarea
            id={id}
            aria-describedby={describedBy}
            invalid={invalid}
            value={question}
            onChange={(e) => onQuestionChange(e.target.value)}
            onBlur={() => setTouched(true)}
            onKeyDown={onKeyDown}
            placeholder="e.g. Which 5 cities had the most completed orders in Q4 2025?"
            maxLength={1000}
            rows={3}
          />
        )}
      </Field>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div role="group" aria-labelledby="examples-label" className="flex min-w-0 flex-1 flex-col gap-1">
          <span id="examples-label" className="text-xs text-fg-subtle">
            Examples
          </span>
          <div className="flex flex-wrap gap-x-4">
            {EXAMPLES.map((q) => (
              <Button key={q} variant="link" size="inline" onClick={() => onQuestionChange(q)} disabled={running}>
                {q}
              </Button>
            ))}
          </div>
        </div>
        <div className="ml-auto flex items-center gap-2">
          {running && (
            <Button size="sm" variant="secondary" onClick={onCancel}>
              <Square className="size-4" aria-hidden />
              Stop
            </Button>
          )}
          <Button type="submit" variant="primary" size="sm" loading={running} disabled={!dataset}>
            Run analysis
            {!running && (
              <kbd className="flex items-center gap-1 text-xs opacity-80">
                Ctrl
                <CornerDownLeft className="size-4" aria-hidden />
              </kbd>
            )}
          </Button>
        </div>
      </div>
    </form>
  );
}
