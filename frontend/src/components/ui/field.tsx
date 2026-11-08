import { cva } from "class-variance-authority";
import { forwardRef, useId, type InputHTMLAttributes, type ReactNode, type TextareaHTMLAttributes } from "react";

import { cn } from "@/lib/cn";

const control = cva(
  "w-full rounded-control border bg-bg px-3 text-base text-fg transition-colors placeholder:text-fg-subtle hover:border-border-strong focus-visible:border-accent disabled:opacity-50",
  {
    variants: {
      invalid: { true: "border-danger hover:border-danger", false: "border-border" },
    },
    defaultVariants: { invalid: false },
  },
);

interface FieldProps {
  label: string;
  helper?: ReactNode;
  error?: string | null;
  children: (props: { id: string; describedBy: string; invalid: boolean }) => ReactNode;
}

/** Label above, control, then helper text or inline error. */
export function Field({ label, helper, error, children }: FieldProps) {
  const id = useId();
  const describedBy = `${id}-desc`;
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium text-fg">
        {label}
      </label>
      {children({ id, describedBy, invalid: Boolean(error) })}
      {(error || helper) && (
        <p id={describedBy} className={cn("text-xs", error ? "text-danger" : "text-fg-subtle")}>
          {error ?? helper}
        </p>
      )}
    </div>
  );
}

type InputProps = InputHTMLAttributes<HTMLInputElement> & { invalid?: boolean };

export const Input = forwardRef<HTMLInputElement, InputProps>(({ className, invalid, ...props }, ref) => (
  <input
    ref={ref}
    aria-invalid={invalid || undefined}
    className={cn(control({ invalid }), "h-control-sm", className)}
    {...props}
  />
));
Input.displayName = "Input";

type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement> & { invalid?: boolean };

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, invalid, ...props }, ref) => (
    <textarea
      ref={ref}
      aria-invalid={invalid || undefined}
      className={cn(control({ invalid }), "min-h-textarea resize-y py-2", className)}
      {...props}
    />
  ),
);
Textarea.displayName = "Textarea";
