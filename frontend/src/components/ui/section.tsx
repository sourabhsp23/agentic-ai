import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

/** Plain section with a heading row and a divider. Groups content without card chrome. */
export function Section({
  title,
  meta,
  actions,
  children,
  className,
}: {
  title: string;
  meta?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("border-t border-border pt-4 first:border-t-0 first:pt-0", className)} aria-label={title}>
      <header className="mb-3 flex min-h-control-sm items-center justify-between gap-3">
        <div className="flex min-w-0 items-baseline gap-2">
          <h2 className="text-sm font-semibold text-fg">{title}</h2>
          {meta && <span className="truncate text-xs text-fg-subtle tabular">{meta}</span>}
        </div>
        {actions && <div className="flex items-center gap-1">{actions}</div>}
      </header>
      {children}
    </section>
  );
}
