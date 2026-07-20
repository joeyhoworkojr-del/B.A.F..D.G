import * as React from "react";
import { Suspense } from "react";
import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, Clock, Star } from "lucide-react";
import { PageHero } from "@/components/ui/page-hero";
import { SectionHeader } from "@/components/ui/section-header";
import { ResourceLibrary } from "@/components/resources/resource-library";
import { Skeleton } from "@/components/ui/states";
import { pageMetadata } from "@/lib/metadata";
import { getFeaturedResource, resourceText } from "@/data/resources";
import { readingTime } from "@/lib/utils";

export const metadata: Metadata = pageMetadata({
  title: "Resource Center",
  description:
    "Cautious, professional resources on analytical testing, quality documentation, research handling, and industry standards.",
  path: "/resources",
});

export default function ResourcesPage() {
  const featured = getFeaturedResource();
  const minutes = readingTime(resourceText(featured));

  return (
    <>
      <PageHero
        eyebrow="Resources"
        title="A resource center for research buyers."
        description="Professional, cautious explainers on documentation and analytical testing — never administration or dosing guidance."
        breadcrumbs={[{ label: "Home", href: "/" }, { label: "Resources" }]}
      />

      {/* Featured resource */}
      <section className="py-14 lg:py-20">
        <div className="container-el">
          <Link
            href={`/resources/${featured.slug}`}
            className="group grid overflow-hidden rounded-[var(--radius-lg)] border border-[color:var(--color-border-grey)] bg-white shadow-[var(--shadow-card)] transition-shadow hover:shadow-[var(--shadow-card-hover)] lg:grid-cols-2"
          >
            <div className="relative flex min-h-[220px] items-center justify-center overflow-hidden bg-navy p-10">
              <div className="grid-lines-dark absolute inset-0 opacity-50" aria-hidden />
              <div className="glow-soft absolute inset-x-0 top-0 h-32" aria-hidden />
              <span className="mono-label relative rounded-full border border-white/20 px-3 py-1 text-white/80">
                Featured Resource
              </span>
            </div>
            <div className="p-8 lg:p-10">
              <div className="flex items-center gap-2">
                <Star className="h-4 w-4 text-elysium" aria-hidden />
                <span className="mono-label text-elysium">
                  {featured.category}
                </span>
              </div>
              <h2 className="mt-4 font-[family-name:var(--font-display)] text-2xl font-semibold text-navy lg:text-3xl">
                {featured.title}
              </h2>
              <p className="mt-3 leading-relaxed text-ink/65">
                {featured.excerpt}
              </p>
              <div className="mt-6 flex items-center gap-4 text-sm">
                <span className="inline-flex items-center gap-1.5 text-ink/50">
                  <Clock className="h-4 w-4" aria-hidden />
                  {minutes} min read
                </span>
                <span className="inline-flex items-center gap-1 font-medium text-elysium">
                  Read article
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                </span>
              </div>
            </div>
          </Link>
        </div>
      </section>

      {/* Library */}
      <section className="border-t border-[color:var(--color-border-grey)] py-14 lg:py-20">
        <div className="container-el">
          <SectionHeader eyebrow="All Resources" title="Browse the library." />
          <div className="mt-10">
            <Suspense
              fallback={
                <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                  {Array.from({ length: 3 }).map((_, i) => (
                    <Skeleton key={i} className="h-56 w-full" />
                  ))}
                </div>
              }
            >
              <ResourceLibrary />
            </Suspense>
          </div>
        </div>
      </section>
    </>
  );
}
