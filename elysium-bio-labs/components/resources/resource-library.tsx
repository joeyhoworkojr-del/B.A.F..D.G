"use client";

import * as React from "react";
import { useSearchParams } from "next/navigation";
import { Search } from "lucide-react";
import {
  resources,
  RESOURCE_CATEGORIES,
  type ResourceCategory,
} from "@/data/resources";
import { ResourceCard } from "./resource-card";
import { EmptyState } from "@/components/ui/states";
import { cn } from "@/lib/utils";

export function ResourceLibrary() {
  const params = useSearchParams();
  const initialCategory = params.get("category") as ResourceCategory | null;

  const [query, setQuery] = React.useState("");
  const [category, setCategory] = React.useState<ResourceCategory | "All">(
    initialCategory && RESOURCE_CATEGORIES.includes(initialCategory)
      ? initialCategory
      : "All",
  );

  const filtered = React.useMemo(() => {
    const q = query.trim().toLowerCase();
    return resources.filter((r) => {
      if (category !== "All" && r.category !== category) return false;
      if (
        q &&
        !r.title.toLowerCase().includes(q) &&
        !r.excerpt.toLowerCase().includes(q)
      )
        return false;
      return true;
    });
  }, [query, category]);

  const reset = () => {
    setQuery("");
    setCategory("All");
  };

  return (
    <div>
      {/* Controls */}
      <div className="flex flex-col gap-4">
        <div className="relative">
          <Search
            className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-ink/40"
            aria-hidden
          />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search resources…"
            aria-label="Search resources"
            className="h-11 w-full rounded-[var(--radius-sm)] border border-[color:var(--color-border-grey)] bg-white pl-10 pr-4 text-sm text-navy outline-none transition-colors placeholder:text-ink/40 focus:border-elysium sm:max-w-md"
          />
        </div>

        <div className="flex flex-wrap gap-2">
          {(["All", ...RESOURCE_CATEGORIES] as const).map((c) => (
            <button
              key={c}
              onClick={() => setCategory(c)}
              className={cn(
                "rounded-full border px-3.5 py-1.5 text-sm font-medium transition-colors",
                category === c
                  ? "border-elysium bg-elysium text-white"
                  : "border-[color:var(--color-border-grey)] bg-white text-ink/65 hover:border-elysium hover:text-elysium",
              )}
            >
              {c}
            </button>
          ))}
        </div>
      </div>

      {/* Grid */}
      <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {filtered.length > 0 ? (
          filtered.map((r, i) => (
            <ResourceCard key={r.slug} resource={r} index={i} />
          ))
        ) : (
          <EmptyState
            title="No resources found"
            description="Try a different search term or category."
            onReset={reset}
          />
        )}
      </div>
    </div>
  );
}
