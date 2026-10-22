import { Hero } from "@/components/home/hero";
import { TrustStrip } from "@/components/home/trust-strip";
import { FeaturedProducts } from "@/components/home/featured-products";
import { QualityStandard } from "@/components/home/quality-standard";
import { DocumentationPreview } from "@/components/home/documentation-preview";
import { WhyElysium } from "@/components/home/why-elysium";
import { ResearchCategories } from "@/components/home/research-categories";
import { AboutPreview } from "@/components/home/about-preview";
import { ResourcesPreview } from "@/components/home/resources-preview";
import { CtaSection } from "@/components/ui/cta-section";

export default function HomePage() {
  return (
    <>
      <Hero />
      <TrustStrip />
      <FeaturedProducts />
      <QualityStandard />
      <DocumentationPreview />
      <WhyElysium />
      <ResearchCategories />
      <AboutPreview />
      <ResourcesPreview />
      <CtaSection
        eyebrow="Final Step"
        title="Build Your Research on Better Information."
        description="Explore the catalogue or request documentation for a specific material. Every figure we present is tied to a batch."
        primary={{ label: "Explore the Catalogue", href: "/research-materials" }}
        secondary={{
          label: "Request Documentation",
          href: "/contact?type=documentation",
        }}
      />
    </>
  );
}
