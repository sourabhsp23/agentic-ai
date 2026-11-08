import { AlertCircle, RotateCw } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

import { Button } from "./button";

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("skeleton h-4", className)} aria-hidden />;
}

/** Explains what belongs here and offers the action that fills it. */
export function EmptyState({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-start gap-2 py-6">
      <p className="text-base font-medium text-fg">{title}</p>
      {children && <div className="max-w-prose text-sm text-fg-muted">{children}</div>}
      {action}
    </div>
  );
}

/** Says what failed and offers a retry. */
export function ErrorState({ title, message, onRetry }: { title: string; message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex items-start gap-3 rounded-control border border-danger/30 bg-danger-subtle p-3">
      <AlertCircle className="mt-px size-4 shrink-0 text-danger" aria-hidden />
      <div className="flex min-w-0 flex-1 flex-col gap-2">
        <div>
          <p className="text-sm font-medium text-fg">{title}</p>
          <p className="break-words text-sm text-fg-muted">{message}</p>
        </div>
        {onRetry && (
          <Button size="sm" variant="secondary" onClick={onRetry} className="self-start">
            <RotateCw className="size-4" aria-hidden />
            Retry
          </Button>
        )}
      </div>
    </div>
  );
}
