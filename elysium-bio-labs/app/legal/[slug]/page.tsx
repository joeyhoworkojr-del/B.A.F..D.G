import * as React from "react";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import { legalPages, getLegalPage } from "@/data/legal";
import { PageHero } from "@/components/ui/page-hero";
import { LegalNotice } from "@/components/ui/legal-notice";
import { pageMetadata } from "@/lib/metadata";

export function generateStaticParams() {
  return legalPages.map((p) => ({ slug: p.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const page = getLegalPage(slug);
  if (!page) return { title: "Policy not found" };
  return pageMetadata({
    title: page.title,
    description: page.summary,
    path: `/legal/${page.slug}`,
  });
}

export default async function LegalPageRoute({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const page = getLegalPage(slug);
  if (!page) notFound();

  return (
    <>
      <PageHero
        eyebrow="Legal"
        title={page.title}
        description={page.summary}
        breadcrumbs={[
          { label: "Home", href: "/" },
          { label: "Legal" },
          { label: page.title },
        ]}
      >
        <p className="mono-label mt-6 text-ink/45">
          Last updated:{" "}
          {new Date(page.updated).toLocaleDateString("en-CA", {
            year: "numeric",
            month: "long",
            day: "numeric",
          })}
        </p>
      </PageHero>

      <div className="container-el max-w-3xl py-14 lg:py-16">
        <LegalNotice variant="sample" className="mb-10">
          This is editable placeholder legal copy. It is <strong>not legal
          advice</strong> and is not guaranteed to satisfy Canadian regulatory
          requirements. Have all legal pages reviewed by qualified Canadian
          regulatory counsel before launch.
        </LegalNotice>

        <div className="space-y-10">
          {page.sections.map((section) => (
            <section key={section.heading}>
              <h2 className="font-[family-name:var(--font-display)] text-xl font-semibold text-navy sm:text-2xl">
                {section.heading}
              </h2>
              <div className="mt-3 space-y-4">
                {section.paragraphs.map((p, i) => (
                  <p key={i} className="leading-relaxed text-ink/75">
                    {p}
                  </p>
                ))}
              </div>
            </section>
          ))}
        </div>

        {/* Other policies */}
        <nav
          aria-label="Other policies"
          className="mt-14 border-t border-[color:var(--color-border-grey)] pt-8"
        >
          <p className="mono-label mb-4 text-ink/50">Other policies</p>
          <ul className="grid gap-2 sm:grid-cols-2">
            {legalPages
              .filter((p) => p.slug !== page.slug)
              .map((p) => (
                <li key={p.slug}>
                  <Link
                    href={`/legal/${p.slug}`}
                    className="text-sm text-elysium hover:underline"
                  >
                    {p.title}
                  </Link>
                </li>
              ))}
          </ul>
        </nav>
      </div>
    </>
  );
}
