import * as React from "react";
import { Suspense } from "react";
import type { Metadata } from "next";
import { PageHero } from "@/components/ui/page-hero";
import { Catalogue } from "@/components/products/catalogue";
import { CtaSection } from "@/components/ui/cta-section";
import { ProductCardSkeleton } from "@/components/ui/states";
import { pageMetadata } from "@/lib/metadata";
import { RuoBadge } from "@/components/ui/badge";

export const metadata: Metadata = pageMetadata({
  title: "Research Materials Catalogue",
  description:
    "Browse Elysium Bio Labs research materials by category, availability, and documentation status. Every material is presented with batch-level detail.",
  path: "/research-materials",
});

export default function ResearchMaterialsPage() {
  return (
    <>
      <PageHero
        eyebrow="Catalogue"
        title="Research Materials"
        description="Carefully sourced, independently evaluated research materials — filterable by category, availability, and documentation status."
        breadcrumbs={[
          { label: "Home", href: "/" },
          { label: "Research Materials" },
        ]}
      >
        <div className="mt-6">
          <RuoBadge />
        </div>
      </PageHero>

      <Suspense
        fallback={
          <div className="container-el grid gap-6 py-16 sm:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <ProductCardSkeleton key={i} />
            ))}
          </div>
        }
      >
        <Catalogue />
      </Suspense>

      <CtaSection
        title="Need documentation for a specific material?"
        description="Request batch documentation or submit a product inquiry — our team responds with the records tied to that batch."
        primary={{
          label: "Request Documentation",
          href: "/contact?type=documentation",
        }}
        secondary={{ label: "Contact the Team", href: "/contact" }}
      />
    </>
  );
}
