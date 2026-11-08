import { cva, type VariantProps } from "class-variance-authority";
import { Loader2 } from "lucide-react";
import { forwardRef, type ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/cn";

const buttonVariants = cva(
  "inline-flex shrink-0 items-center justify-center gap-2 whitespace-nowrap rounded-control font-medium transition-colors disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        primary: "bg-accent text-accent-fg hover:bg-accent-hover",
        secondary: "border border-border-strong bg-bg text-fg hover:bg-bg-muted",
        ghost: "text-fg-muted hover:bg-bg-muted hover:text-fg",
        danger: "border border-danger/40 text-danger hover:bg-danger-subtle",
        link: "h-auto min-w-0 max-w-full shrink whitespace-normal text-left font-normal text-fg-muted underline-offset-4 hover:text-fg hover:underline",
      },
      size: {
        sm: "h-control-sm px-3 text-sm",
        md: "h-control px-4 text-base",
        icon: "h-control-sm w-8 text-fg-muted",
        inline: "px-0 py-1 text-sm",
      },
    },
    defaultVariants: { variant: "secondary", size: "md" },
  },
);

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  loading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, loading, disabled, children, type = "button", ...props }, ref) => (
    <button
      ref={ref}
      type={type}
      className={cn(buttonVariants({ variant, size }), className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading && <Loader2 className="size-4 animate-spin motion-reduce:animate-none" aria-hidden />}
      {children}
    </button>
  ),
);
Button.displayName = "Button";
