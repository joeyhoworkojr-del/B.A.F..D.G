import * as React from "react";
import type { Metadata } from "next";
import {
  Fingerprint,
  FlaskConical,
  Waves,
  LineChart,
  GitBranch,
  PackageCheck,
} from "lucide-react";
import { PageHero } from "@/components/ui/page-hero";
import { SectionHeader } from "@/components/ui/section-header";
import { ProcessTimeline } from "@/components/ui/process-timeline";
import { BatchVerifier } from "@/components/quality/batch-verifier";
import { LegalNotice } from "@/components/ui/legal-notice";
import { Reveal } from "@/components/ui/reveal";
import { CtaSection } from "@/components/ui/cta-section";
import { pageMetadata } from "@/lib/metadata";

export const metadata: Metadata = pageMetadata({
  title: "Quality Process & Documentation",
  description:
    "How Elysium Bio Labs approaches supplier qualification, identity assessment, purity analysis, batch traceability, and controlled handling.",
  path: "/quality",
});

const workflow = [
  {
    index: "01",
    title: "Supplier Qualification",
    description: "Suppliers are evaluated before any material is onboarded.",
  },
  {
    index: "02",
    title: "Material Receipt",
    description: "Incoming materials are logged and checked against records.",
  },
  {
    index: "03",
    title: "Sample Identification",
    description: "Representative samples are drawn for identity assessment.",
  },
  {
    index: "04",
    title: "Analytical Review",
    description: "Samples are reviewed using named analytical methods.",
  },
  {
    index: "05",
    title: "Purity Documentation",
    description: "Purity findings are documented against the method used.",
  },
  {
    index: "06",
    title: "Batch Assignment",
    description: "A traceable batch number is assigned to the material.",
  },
  {
    index: "07",
    title: "Controlled Storage",
    description: "Materials are stored under documented conditions.",
  },
  {
    index: "08",
    title: "Document Retention",
    description: "Records are retained and linked to the batch.",
  },
];

const capabilities = [
  {
    icon: Fingerprint,
    title: "Identity Assessment",
    body: "Establishing that a material is consistent with its reference characteristics before it enters the catalogue.",
  },
  {
    icon: FlaskConical,
    title: "Purity Analysis",
    body: "Reviewing purity against a named analytical method, reported alongside the conditions of measurement.",
  },
  {
    icon: Waves,
    title: "Mass Spectrometry",
    body: "Mass-based evidence contributing to identity and molecular-weight confirmation, where applicable.",
  },
  {
    icon: LineChart,
    title: "HPLC Documentation",
    body: "Chromatographic review supporting the reported proportion of the target compound.",
  },
  {
    icon: GitBranch,
    title: "Batch Traceability",
    body: "Linking every figure to a unique batch identifier that can be referenced later.",
  },
  {
    icon: PackageCheck,
    title: "Packaging & Handling",
    body: "Documented storage and handling procedures from receipt through dispatch.",
  },
];

export default function QualityPage() {
  return (
    <>
      <PageHero
        eyebrow="Quality"
        title="A quality process built for traceability."
        description="Our workflow is designed so that every material can be followed from supplier qualification through to a documented, traceable batch."
        breadcrumbs={[{ label: "Home", href: "/" }, { label: "Quality" }]}
      />

      {/* Full-width process timeline */}
      <section className="py-16 lg:py-24">
        <div className="container-el">
          <SectionHeader
            eyebrow="The Workflow"
            title="Eight steps, documented end to end."
            description="Each step produces records that stay attached to the material — the basis for meaningful traceability."
          />
          <div className="mt-14 grid gap-12 md:grid-cols-2">
            <ProcessTimeline steps={workflow.slice(0, 4)} />
            <ProcessTimeline steps={workflow.slice(4)} />
          </div>
          <LegalNotice className="mt-12">
            This describes our intended quality approach. We do not claim that
            every material undergoes every step unless the material&rsquo;s own
            documentation confirms it, and we do not present demonstration data
            as real testing results.
          </LegalNotice>
        </div>
      </section>

      {/* Capabilities */}
      <section
        id="documentation"
        className="border-y border-[color:var(--color-border-grey)] bg-cool/50 py-16 lg:py-24"
      >
        <div className="container-el">
          <SectionHeader
            eyebrow="Capabilities"
            title="What our documentation covers."
          />
          <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {capabilities.map((c, i) => (
              <Reveal
                key={c.title}
                delayIndex={i}
                className="rounded-[var(--radius-lg)] border border-[color:var(--color-border-grey)] bg-white p-6"
              >
                <div className="flex h-11 w-11 items-center justify-center rounded-[var(--radius-md)] bg-navy">
                  <c.icon className="h-5 w-5 text-white" aria-hidden />
                </div>
                <h3 className="mt-5 text-lg font-semibold text-navy">
                  {c.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-ink/65">
                  {c.body}
                </p>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* Verification tool */}
      <section id="verification" className="py-16 lg:py-24">
        <div className="container-el">
          <SectionHeader
            eyebrow="Batch Verification"
            title="Look up a sample batch number."
            description="Enter a batch reference to see how batch verification is presented. Results shown here are demonstrations only."
          />
          <div className="mt-10 max-w-3xl">
            <BatchVerifier />
          </div>
        </div>
      </section>

      <CtaSection
        title="Explore Our Quality Process"
        description="Browse the catalogue to see how documentation is presented at the material level, or request records for a specific batch."
        primary={{ label: "View Research Materials", href: "/research-materials" }}
        secondary={{
          label: "Request Documentation",
          href: "/contact?type=documentation",
        }}
      />
    </>
  );
}
