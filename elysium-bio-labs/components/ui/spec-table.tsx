import * as React from "react";
import { cn } from "@/lib/utils";

export interface SpecRow {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
}

export function SpecTable({
  rows,
  className,
}: {
  rows: SpecRow[];
  className?: string;
}) {
  return (
    <dl
      className={cn(
        "divide-y divide-[color:var(--color-border-grey)] overflow-hidden rounded-[var(--radius-md)] border border-[color:var(--color-border-grey)] bg-white",
        className,
      )}
    >
      {rows.map((row) => (
        <div
          key={row.label}
          className="grid grid-cols-1 gap-1 px-4 py-3.5 sm:grid-cols-[minmax(0,11rem)_1fr] sm:gap-4 sm:px-5"
        >
          <dt className="mono-label text-ink/50">{row.label}</dt>
          <dd
            className={cn(
              "text-sm text-navy",
              row.mono && "font-[family-name:var(--font-mono)] text-[0.8125rem]",
            )}
          >
            {row.value}
          </dd>
        </div>
      ))}
    </dl>
  );
}
