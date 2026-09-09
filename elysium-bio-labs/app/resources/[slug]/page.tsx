import * as React from "react";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Script from "next/script";
import { Clock, ArrowLeft } from "lucide-react";
import {
  resources,
  getResource,
  getRelatedResources,
  resourceText,
} from "@/data/resources";
import { Breadcrumbs } from "@/components/ui/page-hero";
import { ResourceCard } from "@/components/resources/resource-card";
import { LegalNotice } from "@/components/ui/legal-notice";
import { Button } from "@/components/ui/button";
import { SectionHeader } from "@/components/ui/section-header";
import { readingTime } from "@/lib/utils";
import { SITE_URL, breadcrumbSchema } from "@/lib/metadata";
import { company } from "@/data/company";

export function generateStaticParams() {
  return resources.map((r) => ({ slug: r.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const resource = getResource(slug);
  if (!resource) return { title: "Resource not found" };
  const url = `${SITE_URL}/resources/${resource.slug}`;
  return {
    title: resource.title,
    description: resource.excerpt,
    alternates: { canonical: url },
    openGraph: {
      type: "article",
      title: resource.title,
      description: resource.excerpt,
      url,
      publishedTime: resource.publishedOn,
    },
  };
}

export default async function ResourceArticlePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const resource = getResource(slug);
  if (!resource) notFound();

  const minutes = readingTime(resourceText(resource));
  const related = getRelatedResources(slug);

  const crumbs = [
    { name: "Home", path: "/" },
    { name: "Resources", path: "/resources" },
    { name: resource.title, path: `/resources/${resource.slug}` },
  ];

  const articleSchema = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: resource.title,
    description: resource.excerpt,
    datePublished: resource.publishedOn,
    author: { "@type": "Organization", name: resource.author },
    publisher: {
      "@type": "Organization",
      name: company.name,
      logo: {
        "@type": "ImageObject",
        url: `${SITE_URL}/elysium-logo.png`,
      },
    },
    mainEntityOfPage: `${SITE_URL}/resources/${resource.slug}`,
  };

  return (
    <>
      <Script
        id="article-schema"
        type="application/ld+json"
        strategy="afterInteractive"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(articleSchema) }}
      />
      <Script
        id="breadcrumb-schema"
        type="application/ld+json"
        strategy="afterInteractive"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(breadcrumbSchema(crumbs)),
        }}
      />

      <article>
        {/* Header */}
        <header className="relative overflow-hidden border-b border-[color:var(--color-border-grey)] pt-[calc(var(--header-height)+2rem)]">
          <div className="grid-lines absolute inset-0 opacity-60" aria-hidden />
          <div
            className="absolute inset-x-0 top-0 h-full bg-gradient-to-b from-soft/50 to-white"
            aria-hidden
          />
          <div className="container-el relative max-w-3xl pb-12">
            <Breadcrumbs
              items={crumbs.map((c) => ({
                label: c.name,
                href:
                  c.path === `/resources/${resource.slug}` ? undefined : c.path,
              }))}
              className="mb-6"
            />
            <span className="mono-label text-elysium">{resource.category}</span>
            <h1 className="mt-4 font-[family-name:var(--font-display)] text-3xl font-semibold leading-tight tracking-tight text-navy sm:text-4xl lg:text-[2.75rem]">
              {resource.title}
            </h1>
            <div className="mt-5 flex flex-wrap items-center gap-4 text-sm text-ink/55">
              <span>{resource.author}</span>
              <span aria-hidden>·</span>
              <time dateTime={resource.publishedOn}>
                {new Date(resource.publishedOn).toLocaleDateString("en-CA", {
                  year: "numeric",
                  month: "long",
                  day: "numeric",
                })}
              </time>
              <span aria-hidden>·</span>
              <span className="inline-flex items-center gap-1.5">
                <Clock className="h-4 w-4" aria-hidden />
                {minutes} min read
              </span>
            </div>
          </div>
        </header>

        {/* Body */}
        <div className="container-el max-w-3xl py-14 lg:py-16">
          <div className="space-y-10">
            {resource.sections.map((section) => (
              <section key={section.heading}>
                <h2 className="font-[family-name:var(--font-display)] text-xl font-semibold text-navy sm:text-2xl">
                  {section.heading}
                </h2>
                <div className="mt-4 space-y-4">
                  {section.paragraphs.map((p, i) => (
                    <p
                      key={i}
                      className="text-base leading-relaxed text-ink/75"
                    >
                      {p}
                    </p>
                  ))}
                </div>
              </section>
            ))}
          </div>

          <LegalNotice className="mt-12">
            This article is educational and general in nature. It does not provide
            administration, dosing, or clinical guidance, and it is not a
            substitute for professional or regulatory advice.
          </LegalNotice>

          <div className="mt-10">
            <Button href="/resources" variant="secondary">
              <ArrowLeft className="h-4 w-4" />
              Back to Resources
            </Button>
          </div>
        </div>
      </article>

      {/* Related */}
      {related.length > 0 && (
        <section className="border-t border-[color:var(--color-border-grey)] bg-cool/50 py-16">
          <div className="container-el">
            <SectionHeader eyebrow="Related" title="Continue reading." />
            <div className="mt-10 grid gap-6 sm:grid-cols-2">
              {related.map((r, i) => (
                <ResourceCard key={r.slug} resource={r} index={i} />
              ))}
            </div>
          </div>
        </section>
      )}
    </>
  );
}
