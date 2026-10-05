import * as React from "react";
import { Fingerprint, FileCheck2, GitBranch, Lock } from "lucide-react";
import { Reveal } from "@/components/ui/reveal";

const items = [
  {
    num: "01",
    icon: Fingerprint,
    title: "Verified Identity",
    body: "Materials are assessed for identity before they enter the catalogue.",
  },
  {
    num: "02",
    icon: FileCheck2,
    title: "Purity Documentation",
    body: "Purity is reported against a named analytical method, not asserted.",
  },
  {
    num: "03",
    icon: GitBranch,
    title: "Batch Traceability",
    body: "Every figure is tied to a specific batch you can reference later.",
  },
  {
    num: "04",
    icon: Lock,
    title: "Secure Handling",
    body: "Storage and handling follow controlled, documented procedures.",
  },
];

export function TrustStrip() {
  return (
    <section className="border-y border-[color:var(--color-border-grey)] bg-cool/60">
      <div className="container-el">
        <div className="grid divide-y divide-[color:var(--color-border-grey)] sm:grid-cols-2 sm:divide-y-0 lg:grid-cols-4 lg:divide-x">
          {items.map((item, i) => (
            <Reveal
              key={item.num}
              delayIndex={i}
              className="flex flex-col gap-3 px-2 py-8 sm:px-6 lg:px-6"
            >
              <div className="flex items-center justify-between">
                <item.icon className="h-5 w-5 text-elysium" aria-hidden />
                <span className="mono-label text-ink/30">{item.num}</span>
              </div>
              <h3 className="text-base font-semibold text-navy">{item.title}</h3>
              <p className="text-sm leading-relaxed text-ink/60">{item.body}</p>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
