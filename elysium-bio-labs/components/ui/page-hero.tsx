import * as React from "react";
import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { Reveal } from "./reveal";

export interface Crumb {
  label: string;
  href?: string;
}

export function Breadcrumbs({
  items,
  className,
}: {
  items: Crumb[];
  className?: string;
}) {
  return (
    <nav aria-label="Breadcrumb" className={className}>
      <ol className="flex flex-wrap items-center gap-1.5 text-[0.8125rem]">
        {items.map((item, i) => (
          <li key={i} className="flex items-center gap-1.5">
            {item.href ? (
              <Link
                href={item.href}
                className="text-ink/50 transition-colors hover:text-elysium"
              >
                {item.label}
              </Link>
            ) : (
              <span className="font-medium text-navy" aria-current="page">
                {item.label}
              </span>
            )}
            {i < items.length - 1 && (
              <ChevronRight className="h-3.5 w-3.5 text-ink/30" aria-hidden />
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}

/** Standard interior page hero with grid backdrop and optional eyebrow. */
export function PageHero({
  eyebrow,
  title,
  description,
  breadcrumbs,
  children,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  breadcrumbs?: Crumb[];
  children?: React.ReactNode;
}) {
  return (
    <section className="relative overflow-hidden border-b border-[color:var(--color-border-grey)] pt-[calc(var(--header-height)+2.5rem)]">
      <div className="grid-lines absolute inset-0 opacity-70" aria-hidden />
      <div
        className="absolute inset-x-0 top-0 h-full bg-gradient-to-b from-soft/50 to-white"
        aria-hidden
      />
      <div className="container-el relative pb-14 lg:pb-16">
        {breadcrumbs && <Breadcrumbs items={breadcrumbs} className="mb-6" />}
        <Reveal>
          {eyebrow && (
            <div className="mb-4 flex items-center gap-3">
              <span className="h-px w-8 bg-elysium" aria-hidden />
              <span className="mono-label text-elysium">{eyebrow}</span>
            </div>
          )}
          <h1
            className={cn(
              "font-[family-name:var(--font-display)] text-balance text-4xl font-semibold leading-[1.05] tracking-tight text-navy sm:text-5xl lg:text-[3.25rem]",
            )}
          >
            {title}
          </h1>
          {description && (
            <p className="mt-5 max-w-2xl text-base leading-relaxed text-ink/65 sm:text-lg">
              {description}
            </p>
          )}
          {children}
        </Reveal>
      </div>
    </section>
  );
}
