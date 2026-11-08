import * as RadixSelect from "@radix-ui/react-select";
import { Check, ChevronDown } from "lucide-react";

import { cn } from "@/lib/cn";

interface SelectProps {
  value: string | undefined;
  onValueChange: (value: string) => void;
  options: { value: string; label: string }[];
  placeholder: string;
  ariaLabel: string;
  disabled?: boolean;
  className?: string;
}

export function Select({ value, onValueChange, options, placeholder, ariaLabel, disabled, className }: SelectProps) {
  return (
    <RadixSelect.Root value={value} onValueChange={onValueChange} disabled={disabled}>
      <RadixSelect.Trigger
        aria-label={ariaLabel}
        className={cn(
          "inline-flex h-control-sm items-center justify-between gap-2 rounded-control border border-border bg-bg px-3 text-sm text-fg transition-colors hover:border-border-strong disabled:opacity-50 data-[placeholder]:text-fg-subtle",
          className,
        )}
      >
        <RadixSelect.Value placeholder={placeholder} />
        <RadixSelect.Icon>
          <ChevronDown className="size-4 text-fg-subtle" aria-hidden />
        </RadixSelect.Icon>
      </RadixSelect.Trigger>
      <RadixSelect.Portal>
        <RadixSelect.Content
          position="popper"
          sideOffset={4}
          className="z-50 min-w-trigger overflow-hidden rounded-control border border-border bg-bg shadow-2"
        >
          <RadixSelect.Viewport className="p-1">
            {options.map((o) => (
              <RadixSelect.Item
                key={o.value}
                value={o.value}
                className="relative flex h-control-sm cursor-default select-none items-center rounded-control pl-8 pr-3 text-sm text-fg outline-none data-[highlighted]:bg-bg-muted"
              >
                <RadixSelect.ItemIndicator className="absolute left-2">
                  <Check className="size-4 text-accent" aria-hidden />
                </RadixSelect.ItemIndicator>
                <RadixSelect.ItemText>{o.label}</RadixSelect.ItemText>
              </RadixSelect.Item>
            ))}
          </RadixSelect.Viewport>
        </RadixSelect.Content>
      </RadixSelect.Portal>
    </RadixSelect.Root>
  );
}
