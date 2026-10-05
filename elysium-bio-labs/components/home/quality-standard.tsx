import * as React from "react";
import { ArrowRight } from "lucide-react";
import { SectionHeader } from "@/components/ui/section-header";
import { Button } from "@/components/ui/button";
import { ProcessTimeline } from "@/components/ui/process-timeline";
import { Reveal } from "@/components/ui/reveal";

const steps = [
  {
    index: "01",
    title: "Source Evaluation",
    description: "Suppliers and materials are evaluated before onboarding.",
  },
  {
    index: "02",
    title: "Identity Assessment",
    description: "Materials are assessed against reference characteristics.",
  },
  {
    index: "03",
    title: "Purity Review",
    description: "Purity is reviewed using named analytical methods.",
  },
  {
    index: "04",
    title: "Batch Documentation",
    description: "Findings are recorded against a traceable batch number.",
  },
];

const specCards = [
  { label: "Analytical Method", value: "HPLC · MS" },
  { label: "Reported Purity", value: "≥ 98%" },
  { label: "Batch Number", value: "ELB-—-0000" },
  { label: "Documentation Status", value: "Demonstration" },
];

export function QualityStandard() {
  return (
    <section className="relative overflow-hidden bg-navy py-20 lg:py-28">
      <div className="grid-lines-dark absolute inset-0 opacity-40" aria-hidden />
      <div className="glow-soft absolute inset-x-0 top-0 h-48 opacity-70" aria-hidden />
      <div className="container-el relative">
        <SectionHeader
          dark
          eyebrow="Quality Standard"
          title="Documentation Should Never Be an Afterthought."
          description="Our quality workflow is designed so that every material can be traced from source evaluation through to a documented batch."
        />

        <div className="mt-14">
          <ProcessTimeline steps={steps} dark />
        </div>

        <Reveal className="mt-14 grid gap-px overflow-hidden rounded-[var(--radius-lg)] border border-white/10 bg-white/10 sm:grid-cols-2 lg:grid-cols-4">
          {specCards.map((card) => (
            <div key={card.label} className="bg-navy-800/80 p-5">
              <p className="mono-label text-elysium/90">{card.label}</p>
              <p className="mt-2 font-[family-name:var(--font-mono)] text-lg text-white">
                {card.value}
              </p>
            </div>
          ))}
        </Reveal>

        <Reveal className="mt-8 flex flex-col items-start gap-4 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-white/50">
            Values shown are clearly marked sample data for demonstration — not
            invented testing results.
          </p>
          <Button href="/quality">
            Explore Our Quality Process
            <ArrowRight className="h-4 w-4" />
          </Button>
        </Reveal>
      </div>
    </section>
  );
}
