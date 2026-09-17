import * as React from "react";
import type { Metadata } from "next";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { legalPages } from "@/data/legal";
import { PageHero } from "@/components/ui/page-hero";
import { LegalNotice } from "@/components/ui/legal-notice";
import { pageMetadata } from "@/lib/metadata";

export const metadata: Metadata = pageMetadata({
  title: "Legal & Policies",
  description:
    "Elysium Bio Labs policies: Research Use Only, Privacy, Terms, Shipping, Refund, and Documentation.",
  path: "/legal",
});

export default function LegalIndexPage() {
  return (
    <>
      <PageHero
        eyebrow="Legal"
        title="Policies & Legal Information"
        description="Our policies in one place. All copy is editable and pending review by qualified counsel before launch."
        breadcrumbs={[{ label: "Home", href: "/" }, { label: "Legal" }]}
      />

      <div className="container-el max-w-3xl py-14 lg:py-16">
        <ul className="grid gap-4 sm:grid-cols-2">
          {legalPages.map((p) => (
            <li key={p.slug}>
              <Link
                href={`/legal/${p.slug}`}
                className="group flex h-full flex-col rounded-[var(--radius-lg)] border border-[color:var(--color-border-grey)] bg-white p-6 transition-all duration-300 hover:-translate-y-0.5 hover:border-[color:color-mix(in_srgb,var(--color-elysium)_35%,transparent)] hover:shadow-[var(--shadow-card)]"
              >
                <div className="flex items-start justify-between gap-3">
                  <h2 className="text-base font-semibold text-navy">
                    {p.title}
                  </h2>
                  <ArrowUpRight className="h-4 w-4 flex-shrink-0 text-ink/30 transition-colors group-hover:text-elysium" />
                </div>
                <p className="mt-2 text-sm text-ink/60">{p.summary}</p>
              </Link>
            </li>
          ))}
        </ul>

        <LegalNotice variant="sample" className="mt-10">
          This legal content is placeholder copy and <strong>not legal
          advice</strong>. Have all policies reviewed by qualified Canadian
          regulatory counsel before launch.
        </LegalNotice>
      </div>
    </>
  );
}
