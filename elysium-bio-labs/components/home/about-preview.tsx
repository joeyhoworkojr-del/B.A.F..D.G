import * as React from "react";
import { ArrowRight, Target, FileText, ShieldCheck } from "lucide-react";
import { SectionHeader } from "@/components/ui/section-header";
import { Button } from "@/components/ui/button";
import { Reveal } from "@/components/ui/reveal";
import { company } from "@/data/company";

const pillars = [
  { icon: Target, label: "Mission", body: company.mission },
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

export function AboutPreview() {
  return (
    <section className="border-y border-[color:var(--color-border-grey)] bg-cool/50 py-20 lg:py-28">
      <div className="container-el grid gap-12 lg:grid-cols-[0.85fr_1.15fr] lg:gap-16">
        <div>
          <SectionHeader
            eyebrow="About Elysium"
            title="Research Demands Better Standards."
            description="Elysium Bio Labs was developed to bring a more professional, transparent, and design-conscious standard to the research-material market."
          />
          <Button href="/about" className="mt-8">
            About Elysium
            <ArrowRight className="h-4 w-4" />
          </Button>
        </div>

        <div className="space-y-4">
          {pillars.map((p, i) => (
            <Reveal
              key={p.label}
              delayIndex={i}
              className="flex gap-5 rounded-[var(--radius-lg)] border border-[color:var(--color-border-grey)] bg-white p-6"
            >
              <div className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-[var(--radius-md)] bg-navy">
                <p.icon className="h-5 w-5 text-white" aria-hidden />
              </div>
              <div>
                <p className="mono-label text-elysium">{p.label}</p>
                <p className="mt-2 text-sm leading-relaxed text-ink/70">
                  {p.body}
                </p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
