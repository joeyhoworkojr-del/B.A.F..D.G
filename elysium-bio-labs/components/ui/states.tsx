import * as React from "react";
import { SearchX, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "./button";

/** Empty state — used by catalogue and resource filters. */
export function EmptyState({
  title = "No matches found",
  description = "Try adjusting or clearing your filters to see more results.",
  onReset,
  className,
}: {
  title?: string;
  description?: string;
  onReset?: () => void;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "col-span-full flex flex-col items-center justify-center rounded-[var(--radius-lg)] border border-dashed border-[color:var(--color-border-grey)] bg-cool/50 px-6 py-16 text-center",
        className,
      )}
    >
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-soft">
        <SearchX className="h-5 w-5 text-elysium" aria-hidden />
      </div>
      <h3 className="text-lg font-semibold text-navy">{title}</h3>
      <p className="mt-1.5 max-w-sm text-sm text-ink/60">{description}</p>
      {onReset && (
        <Button variant="secondary" size="sm" className="mt-5" onClick={onReset}>
          Clear filters
        </Button>
      )}
    </div>
  );
}

/** Error state — used by error boundaries. */
export function ErrorState({
  reset,
  title = "Something went wrong",
  description = "An unexpected error occurred while loading this section.",
}: {
  reset?: () => void;
  title?: string;
  description?: string;
}) {
  return (
    <div className="flex min-h-[50vh] flex-col items-center justify-center px-6 text-center">
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-amber-50">
        <AlertTriangle className="h-5 w-5 text-amber-600" aria-hidden />
      </div>
      <h1 className="text-2xl font-semibold text-navy">{title}</h1>
      <p className="mt-2 max-w-md text-ink/60">{description}</p>
      <div className="mt-6 flex gap-3">
        {reset && (
          <Button variant="primary" size="sm" onClick={reset}>
            Try again
          </Button>
        )}
        <Button variant="secondary" size="sm" href="/">
          Return home
        </Button>
      </div>
    </div>
  );
}

/** Loading skeleton block. */
export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-[var(--radius-sm)] bg-[color:var(--color-border-grey)]/60",
        className,
      )}
    />
  );
}

/** Product card skeleton used by loading.tsx. */
export function ProductCardSkeleton() {
  return (
    <div className="rounded-[var(--radius-lg)] border border-[color:var(--color-border-grey)] bg-white p-5">
      <Skeleton className="mb-5 h-40 w-full" />
      <Skeleton className="mb-2 h-3 w-24" />
      <Skeleton className="mb-4 h-5 w-32" />
      <Skeleton className="h-9 w-full" />
    </div>
  );
}
