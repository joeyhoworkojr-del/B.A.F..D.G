import * as React from "react";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Script from "next/script";
import { ArrowRight } from "lucide-react";
import {
  products,
  getProduct,
  getRelatedProducts,
  STATUS_META,
} from "@/data/products";
import { Breadcrumbs } from "@/components/ui/page-hero";
import { StatusBadge, DocIndicator, RuoBadge } from "@/components/ui/badge";
import { VialVisual } from "@/components/ui/vial-visual";
import { ProductCard } from "@/components/products/product-card";
import {
  ProductDetailTabs,
  ProductInquiryForm,
} from "@/components/products/product-detail";
import { Button } from "@/components/ui/button";
import { SectionHeader } from "@/components/ui/section-header";
import { SITE_URL, breadcrumbSchema } from "@/lib/metadata";

export function generateStaticParams() {
  return products.map((p) => ({ slug: p.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const product = getProduct(slug);
  if (!product) return { title: "Material not found" };
  const url = `${SITE_URL}/research-materials/${product.slug}`;
  const description = `${product.name} — ${product.category} research reference material. ${product.presentation}. Supplied for research use only with batch-level documentation.`;
  return {
    title: `${product.name} — ${product.category}`,
    description,
    alternates: { canonical: url },
    openGraph: {
      type: "website",
      title: `${product.name} | Elysium Bio Labs`,
      description,
      url,
    },
  };
}

export default async function ProductDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const product = getProduct(slug);
  if (!product) notFound();

  const related = getRelatedProducts(slug);
  const seed = product.slug.length;

  const productSchema = {
    "@context": "https://schema.org",
    "@type": "Product",
    name: product.name,
    category: product.category,
    description: product.description,
    sku: product.slug,
    brand: { "@type": "Brand", name: "Elysium Bio Labs" },
    // Availability reflects catalogue status only; no price is asserted because
    // this is an inquiry-based flow, not an unrestricted checkout.
    offers: {
      "@type": "Offer",
      availability:
        product.status === "in-stock"
          ? "https://schema.org/InStock"
          : product.status === "limited"
            ? "https://schema.org/LimitedAvailability"
            : "https://schema.org/BackOrder",
      url: `${SITE_URL}/research-materials/${product.slug}`,
      priceSpecification: {
        "@type": "PriceSpecification",
        priceCurrency: "CAD",
      },
    },
  };

  const crumbs = [
    { name: "Home", path: "/" },
    { name: "Research Materials", path: "/research-materials" },
    { name: product.name, path: `/research-materials/${product.slug}` },
  ];

  return (
    <>
      <Script
        id="product-schema"
        type="application/ld+json"
        strategy="afterInteractive"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(productSchema) }}
      />
      <Script
        id="breadcrumb-schema"
        type="application/ld+json"
        strategy="afterInteractive"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(breadcrumbSchema(crumbs)),
        }}
      />

      {/* Header region */}
      <section className="relative overflow-hidden border-b border-[color:var(--color-border-grey)] pt-[calc(var(--header-height)+2rem)]">
        <div className="grid-lines absolute inset-0 opacity-60" aria-hidden />
        <div
          className="absolute inset-x-0 top-0 h-72 bg-gradient-to-b from-soft/50 to-white"
          aria-hidden
        />
        <div className="container-el relative pb-14">
          <Breadcrumbs
            items={crumbs.map((c) => ({
              label: c.name,
              href:
                c.path === `/research-materials/${product.slug}`
                  ? undefined
                  : c.path,
            }))}
            className="mb-8"
          />

          <div className="grid items-center gap-10 lg:grid-cols-[0.9fr_1.1fr]">
            {/* Visual */}
            <div className="relative order-2 flex items-center justify-center rounded-[var(--radius-lg)] border border-[color:var(--color-border-grey)] bg-gradient-to-br from-white to-soft/40 p-10 lg:order-1">
              <div className="grid-lines absolute inset-0 opacity-50" aria-hidden />
              <VialVisual seed={seed} className="relative h-64 w-auto" />
              <span className="mono-label absolute left-4 top-4 text-ink/35">
                {product.molecularFormula}
              </span>
            </div>

            {/* Meta */}
            <div className="order-1 lg:order-2">
              <div className="flex flex-wrap items-center gap-2.5">
                <span className="mono-label text-elysium">
                  {product.category}
                </span>
                <StatusBadge status={product.status} />
                <RuoBadge />
              </div>
              <h1 className="mt-4 font-[family-name:var(--font-display)] text-4xl font-semibold tracking-tight text-navy sm:text-5xl">
                {product.name}
              </h1>
              <p className="mt-4 max-w-lg leading-relaxed text-ink/65">
                {product.description}
              </p>

              <dl className="mt-7 grid grid-cols-2 gap-px overflow-hidden rounded-[var(--radius-md)] border border-[color:var(--color-border-grey)] bg-[color:var(--color-border-grey)]">
                <MetaCell label="Presentation" value={product.presentation} />
                <MetaCell
                  label="Availability"
                  value={STATUS_META[product.status].label}
                />
                <MetaCell label="Batch" value={product.batchNumber} mono />
                <MetaCell
                  label="Documentation"
                  value={
                    <DocIndicator available={product.documentationAvailable} />
                  }
                />
              </dl>

              <div className="mt-7 flex flex-col gap-3 sm:flex-row">
                <Button href="#inquiry" size="lg">
                  Request Documentation
                </Button>
                <Button href="/contact?type=product" variant="secondary" size="lg">
                  Product Inquiry
                </Button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Tabbed detail */}
      <section className="py-14 lg:py-20">
        <div className="container-el grid gap-12 lg:grid-cols-[1.4fr_1fr] lg:gap-16">
          <div className="px-0">
            <ProductDetailTabs product={product} />
          </div>

          {/* Inquiry form */}
          <aside id="inquiry" className="scroll-mt-[calc(var(--header-height)+1rem)]">
            <div className="sticky top-[calc(var(--header-height)+1.5rem)] rounded-[var(--radius-lg)] border border-[color:var(--color-border-grey)] bg-white p-6 shadow-[var(--shadow-card)]">
              <h2 className="text-lg font-semibold text-navy">
                Request documentation
              </h2>
              <p className="mt-1.5 text-sm text-ink/60">
                Submit a documentation request for {product.name}. We respond with
                the records tied to this batch.
              </p>
              <div className="mt-6">
                <ProductInquiryForm product={product} />
              </div>
            </div>
          </aside>
        </div>
      </section>

      {/* Related */}
      <section className="border-t border-[color:var(--color-border-grey)] bg-cool/50 py-16 lg:py-20">
        <div className="container-el">
          <SectionHeader
            eyebrow="Related Materials"
            title="Explore adjacent research materials."
          />
          <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {related.map((p, i) => (
              <ProductCard key={p.slug} product={p} index={i} />
            ))}
          </div>
          <div className="mt-10">
            <Button href="/research-materials" variant="secondary">
              View Complete Catalogue
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </section>
    </>
  );
}

function MetaCell({
  label,
  value,
  mono,
}: {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
}) {
  return (
    <div className="bg-white px-4 py-3">
      <dt className="mono-label text-ink/45">{label}</dt>
      <dd
        className={
          mono
            ? "mt-1 font-[family-name:var(--font-mono)] text-xs text-navy"
            : "mt-1 text-sm font-medium text-navy"
        }
      >
        {value}
      </dd>
    </div>
  );
}
