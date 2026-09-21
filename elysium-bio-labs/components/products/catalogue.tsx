"use client";

import * as React from "react";
import { useSearchParams } from "next/navigation";
import { Search, SlidersHorizontal, X, ChevronDown } from "lucide-react";
import {
  products as allProducts,
  CATEGORIES,
  STATUS_META,
  type ProductStatus,
  type ResearchCategory,
} from "@/data/products";
import { ProductCard } from "./product-card";
import { EmptyState } from "@/components/ui/states";
import { cn } from "@/lib/utils";

type SortKey = "name" | "category" | "newest";
type DocFilter = "all" | "available" | "pending";

export function Catalogue() {
  const searchParams = useSearchParams();
  const initialCategory = searchParams.get("category") as ResearchCategory | null;

  const [query, setQuery] = React.useState("");
  const [categories, setCategories] = React.useState<Set<ResearchCategory>>(
    () => new Set(initialCategory ? [initialCategory] : []),
  );
  const [statuses, setStatuses] = React.useState<Set<ProductStatus>>(new Set());
  const [docFilter, setDocFilter] = React.useState<DocFilter>("all");
  const [sort, setSort] = React.useState<SortKey>("name");
  const [drawerOpen, setDrawerOpen] = React.useState(false);

  const toggle = <T,>(set: Set<T>, value: T): Set<T> => {
    const next = new Set(set);
    if (next.has(value)) next.delete(value);
    else next.add(value);
    return next;
  };

  const reset = () => {
    setQuery("");
    setCategories(new Set());
    setStatuses(new Set());
    setDocFilter("all");
    setSort("name");
  };

  const filtered = React.useMemo(() => {
    const q = query.trim().toLowerCase();
    const result = allProducts.filter((p) => {
      if (
        q &&
        !p.name.toLowerCase().includes(q) &&
        !p.category.toLowerCase().includes(q) &&
        !p.description.toLowerCase().includes(q)
      )
        return false;
      if (categories.size > 0 && !categories.has(p.category)) return false;
      if (statuses.size > 0 && !statuses.has(p.status)) return false;
      if (docFilter === "available" && !p.documentationAvailable) return false;
      if (docFilter === "pending" && p.documentationAvailable) return false;
      return true;
    });

    result.sort((a, b) => {
      if (sort === "name") return a.name.localeCompare(b.name);
      if (sort === "category") return a.category.localeCompare(b.category);
      return b.addedOn.localeCompare(a.addedOn);
    });
    return result;
  }, [query, categories, statuses, docFilter, sort]);

  const activeFilterCount =
    categories.size + statuses.size + (docFilter !== "all" ? 1 : 0);

  const filterPanel = (
    <FilterPanel
      categories={categories}
      statuses={statuses}
      docFilter={docFilter}
      onToggleCategory={(c) => setCategories((s) => toggle(s, c))}
      onToggleStatus={(s2) => setStatuses((s) => toggle(s, s2))}
      onDocFilter={setDocFilter}
      onReset={reset}
      activeFilterCount={activeFilterCount}
    />
  );

  return (
    <div className="container-el grid gap-10 py-12 lg:grid-cols-[16rem_1fr] lg:gap-12 lg:py-16">
      {/* Desktop sidebar */}
      <aside className="hidden lg:block">
        <div className="sticky top-[calc(var(--header-height)+1.5rem)]">
          {filterPanel}
        </div>
      </aside>

      {/* Main */}
      <div>
        {/* Controls */}
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="relative flex-1">
            <Search
              className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-ink/40"
              aria-hidden
            />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search materials, categories…"
              aria-label="Search research materials"
              className="h-11 w-full rounded-[var(--radius-sm)] border border-[color:var(--color-border-grey)] bg-white pl-10 pr-4 text-sm text-navy outline-none transition-colors placeholder:text-ink/40 focus:border-elysium"
            />
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setDrawerOpen(true)}
              className="inline-flex h-11 items-center gap-2 rounded-[var(--radius-sm)] border border-[color:var(--color-border-grey)] bg-white px-4 text-sm font-medium text-navy lg:hidden"
            >
              <SlidersHorizontal className="h-4 w-4" />
              Filters
              {activeFilterCount > 0 && (
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-elysium text-[0.625rem] text-white">
                  {activeFilterCount}
                </span>
              )}
            </button>

            <div className="relative">
              <select
                value={sort}
                onChange={(e) => setSort(e.target.value as SortKey)}
                aria-label="Sort products"
                className="h-11 appearance-none rounded-[var(--radius-sm)] border border-[color:var(--color-border-grey)] bg-white pl-4 pr-10 text-sm font-medium text-navy outline-none focus:border-elysium"
              >
                <option value="name">Sort: Name</option>
                <option value="category">Sort: Category</option>
                <option value="newest">Sort: Newest</option>
              </select>
              <ChevronDown
                className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink/40"
                aria-hidden
              />
            </div>
          </div>
        </div>

        {/* Result count */}
        <p className="mt-5 text-sm text-ink/55" aria-live="polite">
          Showing{" "}
          <span className="font-medium text-navy">{filtered.length}</span> of{" "}
          {allProducts.length} materials
        </p>

        {/* Grid */}
        <div className="mt-6 grid gap-6 sm:grid-cols-2 xl:grid-cols-3">
          {filtered.length > 0 ? (
            filtered.map((p, i) => (
              <ProductCard key={p.slug} product={p} index={i} />
            ))
          ) : (
            <EmptyState onReset={reset} />
          )}
        </div>
      </div>

      {/* Mobile drawer */}
      {drawerOpen && (
        <div className="fixed inset-0 z-[60] lg:hidden">
          <button
            className="absolute inset-0 bg-navy/40 backdrop-blur-sm"
            aria-label="Close filters"
            onClick={() => setDrawerOpen(false)}
          />
          <div className="absolute inset-y-0 right-0 w-[85%] max-w-sm overflow-y-auto bg-white p-6 shadow-2xl">
            <div className="mb-6 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-navy">Filters</h2>
              <button
                onClick={() => setDrawerOpen(false)}
                className="flex h-9 w-9 items-center justify-center rounded-[var(--radius-sm)] border border-[color:var(--color-border-grey)]"
                aria-label="Close"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            {filterPanel}
          </div>
        </div>
      )}
    </div>
  );
}

function FilterPanel({
  categories,
  statuses,
  docFilter,
  onToggleCategory,
  onToggleStatus,
  onDocFilter,
  onReset,
  activeFilterCount,
}: {
  categories: Set<ResearchCategory>;
  statuses: Set<ProductStatus>;
  docFilter: DocFilter;
  onToggleCategory: (c: ResearchCategory) => void;
  onToggleStatus: (s: ProductStatus) => void;
  onDocFilter: (d: DocFilter) => void;
  onReset: () => void;
  activeFilterCount: number;
}) {
  return (
    <div className="space-y-7">
      <div className="flex items-center justify-between">
        <h2 className="mono-label text-ink/50">Filters</h2>
        {activeFilterCount > 0 && (
          <button
            onClick={onReset}
            className="text-xs font-medium text-elysium hover:underline"
          >
            Clear all
          </button>
        )}
      </div>

      <FilterGroup label="Category">
        {CATEGORIES.map((c) => (
          <CheckRow
            key={c}
            checked={categories.has(c)}
            onChange={() => onToggleCategory(c)}
            label={c}
          />
        ))}
      </FilterGroup>

      <FilterGroup label="Availability">
        {(Object.keys(STATUS_META) as ProductStatus[]).map((s) => (
          <CheckRow
            key={s}
            checked={statuses.has(s)}
            onChange={() => onToggleStatus(s)}
            label={STATUS_META[s].label}
          />
        ))}
      </FilterGroup>

      <FilterGroup label="Documentation">
        {(
          [
            ["all", "All"],
            ["available", "Available"],
            ["pending", "Pending"],
          ] as [DocFilter, string][]
        ).map(([value, label]) => (
          <label
            key={value}
            className="flex cursor-pointer items-center gap-2.5 text-sm text-ink/70"
          >
            <input
              type="radio"
              name="docFilter"
              checked={docFilter === value}
              onChange={() => onDocFilter(value)}
              className="h-4 w-4 accent-[color:var(--color-elysium)]"
            />
            {label}
          </label>
        ))}
      </FilterGroup>
    </div>
  );
}

function FilterGroup({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <h3 className="mb-3 text-sm font-semibold text-navy">{label}</h3>
      <div className="space-y-2.5">{children}</div>
    </div>
  );
}

function CheckRow({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: () => void;
  label: string;
}) {
  return (
    <label className="flex cursor-pointer items-center gap-2.5 text-sm text-ink/70">
      <span
        className={cn(
          "flex h-4 w-4 items-center justify-center rounded-[3px] border transition-colors",
          checked
            ? "border-elysium bg-elysium"
            : "border-[color:var(--color-border-grey)] bg-white",
        )}
      >
        {checked && (
          <svg viewBox="0 0 12 12" className="h-3 w-3 text-white" fill="none">
            <path
              d="M2.5 6.2L4.8 8.5L9.5 3.5"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        )}
      </span>
      <input
        type="checkbox"
        checked={checked}
        onChange={onChange}
        className="sr-only"
      />
      {label}
    </label>
  );
}
