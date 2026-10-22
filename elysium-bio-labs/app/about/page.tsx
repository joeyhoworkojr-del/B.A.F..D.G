import * as React from "react";
import type { Metadata } from "next";
import { Target, FileText, ShieldCheck, Compass } from "lucide-react";
import { PageHero } from "@/components/ui/page-hero";
import { SectionHeader } from "@/components/ui/section-header";
import { Reveal } from "@/components/ui/reveal";
import { LegalNotice } from "@/components/ui/legal-notice";
import { CtaSection } from "@/components/ui/cta-section";
import { Emblem } from "@/components/ui/emblem";
import { pageMetadata } from "@/lib/metadata";
import { company } from "@/data/company";

export const metadata: Metadata = pageMetadata({
  title: "About Elysium Bio Labs",
  description:
    "Elysium Bio Labs was developed to bring a more professional, transparent, and design-conscious standard to the research-material market.",
  path: "/about",
});

const philosophies = [
  {
    icon: Target,
    label: "Mission",
    body: company.mission,
  },
  {
    icon: FileText,
    label: "Documentation philosophy",
    body: company.documentationPhilosophy,
  },
  {
    icon: ShieldCheck,
    label: "Quality philosophy",
    body: company.qualityPhilosophy,
  },
];

export default function AboutPage() {
  return (
    <>
      <PageHero
        eyebrow="About"
        title="Research Demands Better Standards."
        description="Elysium Bio Labs was developed to bring a more professional, transparent, and design-conscious standard to the research-material market."
        breadcrumbs={[{ label: "Home", href: "/" }, { label: "About" }]}
      />

      {/* Brand story */}
      <section id="mission" className="py-16 lg:py-24">
        <div className="container-el grid gap-12 lg:grid-cols-[1.2fr_0.8fr] lg:gap-16">
          <div>
            <SectionHeader eyebrow="Our Story" title="Why we exist." />
            <div className="mt-6 space-y-4 text-base leading-relaxed text-ink/70">
              <p>
                The research-material market is full of bold claims and thin
                documentation. Elysium Bio Labs takes the opposite position:
                describe materials accurately, tie every figure to a batch, and
                let disciplined records — not marketing language — carry the
                credibility.
              </p>
              <p>
                We treat presentation as part of quality. A clear catalogue,
                honest labelling, and considered design are not decoration; they
                are how a professional research supplier signals that the details
                have been taken seriously.
              </p>
              <p>
                Our commitment is simple and specific: elevate the standard of
                sourcing through documentation, considered presentation, and
                transparency — and never present demonstration data as if it were
                verified fact.
              </p>
            </div>
          </div>

          <Reveal className="relative flex items-center justify-center rounded-[var(--radius-lg)] border border-[color:var(--color-border-grey)] bg-gradient-to-br from-soft/50 to-white p-10">
            <div className="grid-lines absolute inset-0 opacity-50" aria-hidden />
            <Emblem className="relative w-40" animated />
            <span className="mono-label absolute bottom-4 left-4 text-ink/35">
              ELYSIUM / STANDARD
            </span>
          </Reveal>
        </div>
      </section>

      {/* Philosophies */}
      <section className="border-y border-[color:var(--color-border-grey)] bg-cool/50 py-16 lg:py-24">
        <div className="container-el">
          <SectionHeader
            eyebrow="Principles"
            title="What guides our decisions."
          />
          <div className="mt-12 grid gap-6 md:grid-cols-3">
            {philosophies.map((p, i) => (
              <Reveal
                key={p.label}
                delayIndex={i}
                className="rounded-[var(--radius-lg)] border border-[color:var(--color-border-grey)] bg-white p-7"
              >
                <div className="flex h-11 w-11 items-center justify-center rounded-[var(--radius-md)] bg-navy">
                  <p.icon className="h-5 w-5 text-white" aria-hidden />
                </div>
                <p className="mono-label mt-5 text-elysium">{p.label}</p>
                <p className="mt-2 text-sm leading-relaxed text-ink/70">
                  {p.body}
                </p>
              </Reveal>
            ))}
          </div>

          {/* Operating principles list */}
          <div className="mt-10 grid gap-4 sm:grid-cols-2">
            {company.principles.map((pr, i) => (
              <Reveal
                key={pr.title}
                delayIndex={i}
                className="flex gap-4 rounded-[var(--radius-md)] border border-[color:var(--color-border-grey)] bg-white p-5"
              >
                <Compass
                  className="mt-0.5 h-5 w-5 flex-shrink-0 text-elysium"
                  aria-hidden
                />
                <div>
                  <h3 className="text-sm font-semibold text-navy">{pr.title}</h3>
                  <p className="mt-1 text-sm text-ink/60">{pr.body}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* Company facts placeholder */}
      <section className="py-16 lg:py-24">
        <div className="container-el max-w-3xl">
          <SectionHeader
            eyebrow="Company Information"
            title="Factual details, kept honest."
            description="We publish company facts only once they are confirmed. The fields below are editable placeholders — not fabricated history, staff, ownership, certifications, or partnerships."
          />
          <dl className="mt-8 divide-y divide-[color:var(--color-border-grey)] overflow-hidden rounded-[var(--radius-md)] border border-[color:var(--color-border-grey)] bg-white">
            {[
              ["Legal entity", "[TO BE CONFIRMED]"],
              ["Jurisdiction", company.region],
              ["Registered address", company.addressLine],
              ["Established", "[TO BE CONFIRMED]"],
              ["Certifications", "[Only if genuinely held — TO BE CONFIRMED]"],
            ].map(([k, v]) => (
              <div
                key={k}
                className="grid grid-cols-1 gap-1 px-5 py-4 sm:grid-cols-[12rem_1fr] sm:gap-4"
              >
                <dt className="mono-label text-ink/50">{k}</dt>
                <dd className="text-sm text-navy">{v}</dd>
              </div>
            ))}
          </dl>
          <LegalNotice className="mt-6">
            These fields are intentionally unfilled. Replace them with verified
            information in <code className="text-elysium">data/company.ts</code>{" "}
            before launch. Do not publish claims about history, staff, ownership,
            certifications, or partnerships that cannot be substantiated.
          </LegalNotice>
        </div>
      </section>

      <CtaSection
        title="Built on standards, not slogans."
        description="See how our approach shows up in the catalogue and quality documentation."
        primary={{ label: "Explore the Catalogue", href: "/research-materials" }}
        secondary={{ label: "View Quality Process", href: "/quality" }}
      />
    </>
  );
}
