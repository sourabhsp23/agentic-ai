import { Check, Copy } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Section } from "@/components/ui/section";

export function SqlBlock({ sql }: { sql: string }) {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!copied) return;
    const t = setTimeout(() => setCopied(false), 1500);
    return () => clearTimeout(t);
  }, [copied]);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(sql);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };

  return (
    <Section
      title="SQL"
      meta="Validated read-only, run on DuckDB"
      actions={
        <Button size="icon" variant="ghost" onClick={copy} aria-label={copied ? "SQL copied" : "Copy SQL"}>
          {copied ? <Check className="size-4 text-success" aria-hidden /> : <Copy className="size-4" aria-hidden />}
        </Button>
      }
    >
      <pre className="max-h-code overflow-auto rounded-control border border-border bg-bg-subtle p-3 text-sm text-fg">
        <code>{sql}</code>
      </pre>
    </Section>
  );
}
