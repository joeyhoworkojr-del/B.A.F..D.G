import * as React from "react";
import { Info } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Legal / demonstration notice callout. Used to clearly mark sample data,
 * demonstration interfaces, and editable legal copy.
 */
export function LegalNotice({
  children,
  variant = "info",
  className,
}: {
  children: React.ReactNode;
  variant?: "info" | "sample";
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex gap-3 rounded-[var(--radius-md)] border px-4 py-3.5 text-sm leading-relaxed",
        variant === "sample"
          ? "border-amber-200 bg-amber-50/70 text-amber-900"
          : "border-[color:var(--color-border-grey)] bg-cool text-ink/70",
        className,
      )}
    >
      <Info
        className={cn(
          "mt-0.5 h-4 w-4 flex-shrink-0",
          variant === "sample" ? "text-amber-600" : "text-elysium",
        )}
        aria-hidden
      />
      <div>{children}</div>
    </div>
  );
}
