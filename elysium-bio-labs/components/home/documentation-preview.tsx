import * as React from "react";
import { FileCheck2, GitBranch, QrCode } from "lucide-react";
import { SectionHeader } from "@/components/ui/section-header";
import { DocumentationCard } from "@/components/ui/documentation-card";
import { Reveal } from "@/components/ui/reveal";
import { getProduct } from "@/data/products";

const highlights = [
  {
    icon: FileCheck2,
    title: "Batch overview",
    body: "Material, batch number, formula, and molecular weight at a glance.",
  },
  {
    icon: GitBranch,
    title: "Identity & purity",
    body: "Separate identity and purity sections, each tied to a method.",
  },
  {
    icon: QrCode,
    title: "Verification field",
    body: "A verification field and QR placeholder for future document lookup.",
  },
];

export function DocumentationPreview() {
  const sample = getProduct("retatrutide");
  return (
    <section className="py-20 lg:py-28">
      <div className="container-el grid items-center gap-12 lg:grid-cols-[0.9fr_1.1fr]">
        <div>
          <SectionHeader
            eyebrow="Documentation Preview"
            title="Transparency at the Batch Level."
            description="A preview of our certificate-of-analysis interface. It demonstrates how batch documentation is organized — clearly, and always tied to a specific batch."
          />
          <ul className="mt-8 space-y-5">
            {highlights.map((h, i) => (
              <Reveal
                as="li"
                key={h.title}
                delayIndex={i}
                className="flex gap-4"
              >
                <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-[var(--radius-sm)] bg-soft">
                  <h.icon className="h-5 w-5 text-elysium" aria-hidden />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-navy">{h.title}</h3>
                  <p className="mt-0.5 text-sm text-ink/60">{h.body}</p>
                </div>
              </Reveal>
            ))}
          </ul>
        </div>

        <Reveal delayIndex={1}>
          <DocumentationCard
            product={{
              ...sample,
              reportedPurity: "≥ 98% (sample value)",
              analyticalMethod: "HPLC · MS (sample)",
              documentationStatus: "Demonstration",
            }}
          />
        </Reveal>
      </div>
    </section>
  );
}
