import * as React from "react";
import { cn } from "@/lib/utils";
import { ShieldCheck, FileCheck2, FileX2 } from "lucide-react";
import type { ProductStatus } from "@/data/products";
import { STATUS_META } from "@/data/products";

type Tone = "positive" | "warning" | "neutral" | "brand";

const toneClasses: Record<Tone, string> = {
  positive:
    "bg-emerald-50 text-emerald-700 border-emerald-200",
  warning: "bg-amber-50 text-amber-700 border-amber-200",
  neutral: "bg-cool text-ink/70 border-[color:var(--color-border-grey)]",
  brand: "bg-soft text-elysium-700 border-[color:color-mix(in_srgb,var(--color-elysium)_25%,transparent)]",
};

export function Badge({
  tone = "neutral",
  className,
  children,
}: {
  tone?: Tone;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[0.6875rem] font-medium tracking-wide",
        toneClasses[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

/** Batch-status badge with a small live dot. */
export function StatusBadge({ status }: { status: ProductStatus }) {
  const meta = STATUS_META[status];
  const dot =
    meta.tone === "positive"
      ? "bg-emerald-500"
      : meta.tone === "warning"
        ? "bg-amber-500"
        : "bg-ink/40";
  return (
    <Badge tone={meta.tone}>
      <span className={cn("h-1.5 w-1.5 rounded-full", dot)} aria-hidden />
      {meta.label}
    </Badge>
  );
}

/** Research Use Only badge — present but restrained. */
export function RuoBadge({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "mono-label inline-flex items-center gap-1.5 rounded-[var(--radius-xs)] border border-[color:var(--color-border-grey)] bg-white/70 px-2 py-1 text-ink/60",
        className,
      )}
    >
      <ShieldCheck className="h-3 w-3 text-elysium" aria-hidden />
      Research Use Only
    </span>
  );
}

/** Documentation availability indicator. */
export function DocIndicator({
  available,
  className,
}: {
  available: boolean;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 text-[0.6875rem] font-medium",
        available ? "text-elysium-700" : "text-ink/45",
        className,
      )}
    >
      {available ? (
        <FileCheck2 className="h-3.5 w-3.5" aria-hidden />
      ) : (
        <FileX2 className="h-3.5 w-3.5" aria-hidden />
      )}
      {available ? "Documentation available" : "Documentation pending"}
    </span>
  );
}
