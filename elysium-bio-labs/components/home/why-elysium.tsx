import * as React from "react";
import { Crosshair, GitBranch, FileText } from "lucide-react";
import { SectionHeader } from "@/components/ui/section-header";
import { Reveal } from "@/components/ui/reveal";

const cards = [
  {
    icon: Crosshair,
    title: "Built Around Precision",
    body: "We describe materials with restraint and accuracy — specific presentations, named methods, and no unsupported claims. Precision is the product.",
  },
  {
    icon: GitBranch,
    title: "Designed for Traceability",
    body: "Every material is designed to be traceable from source evaluation through to a documented batch, so a figure on a report always maps to something real.",
  },
  {
    icon: FileText,
    title: "Supported by Documentation",
    body: "Batch-level documentation is the foundation of the catalogue, not a premium add-on. What you evaluate is what you can reference later.",
  },
];

export function WhyElysium() {
  return (
    <section className="border-y border-[color:var(--color-border-grey)] bg-cool/50 py-20 lg:py-28">
      <div className="container-el">
        <SectionHeader
          align="center"
          eyebrow="Why Elysium"
          title="Three commitments, applied consistently."
        />
        <div className="mt-14 grid gap-6 md:grid-cols-3">
          {cards.map((card, i) => (
            <Reveal
              key={card.title}
              delayIndex={i}
              className="group relative flex flex-col overflow-hidden rounded-[var(--radius-lg)] border border-[color:var(--color-border-grey)] bg-white p-8 transition-shadow duration-300 hover:shadow-[var(--shadow-card)]"
            >
              <span
                className="absolute inset-x-0 top-0 h-0.5 origin-left scale-x-0 bg-elysium transition-transform duration-500 ease-[var(--ease-out-soft)] group-hover:scale-x-100"
                aria-hidden
              />
              <div className="flex h-12 w-12 items-center justify-center rounded-[var(--radius-md)] bg-navy">
                <card.icon className="h-5 w-5 text-white" aria-hidden />
              </div>
              <h3 className="mt-6 font-[family-name:var(--font-display)] text-xl font-semibold text-navy">
                {card.title}
              </h3>
              <p className="mt-3 text-sm leading-relaxed text-ink/65">
                {card.body}
              </p>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
