"use client";

import { ErrorState } from "@/components/ui/states";

export default function Error({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="pt-[var(--header-height)]">
      <ErrorState reset={reset} />
    </div>
  );
}
