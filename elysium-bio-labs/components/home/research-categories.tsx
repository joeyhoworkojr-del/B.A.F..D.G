"use client";

import * as React from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowUpRight, Activity, HeartPulse, Boxes, Sprout, Hourglass, Ruler } from "lucide-react";
import { SectionHeader } from "@/components/ui/section-header";

const categories = [
  {
    name: "Metabolic Research",
    icon: Activity,
    desc: "Materials studied in metabolic-pathway research contexts.",
  },
  {
    name: "Recovery Research",
    icon: HeartPulse,
    desc: "Reference materials used in recovery-pathway research.",
  },
  {
    name: "Cellular Research",
    icon: Boxes,
    desc: "Materials applied in cellular and molecular studies.",
  },
  {
    name: "Growth-Factor Research",
    icon: Sprout,
    desc: "Reference materials for growth-factor pathway research.",
  },
  {
    name: "Longevity Research",
    icon: Hourglass,
    desc: "Materials studied in longevity and cellular-aging research.",
  },
  {
    name: "Reference Materials",
    icon: Ruler,
    desc: "Characterized materials used as analytical references.",
  },
];

export function ResearchCategories() {
  return (
    <section className="py-20 lg:py-28">
      <div className="container-el">
        <SectionHeader
          eyebrow="Research Categories"
          title="Organized by research application."
          description="Categories describe the research contexts our materials are studied in — not clinical uses, and never human or veterinary consumption."
        />
      </div>

      {/* Horizontal rail on mobile, grid on larger screens */}
      <div className="container-el mt-12">
        <div className="flex snap-x snap-mandatory gap-4 overflow-x-auto rail-scroll pb-4 md:grid md:grid-cols-2 md:overflow-visible lg:grid-cols-3">
          {categories.map((cat, i) => (
            <motion.div
              key={cat.name}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-40px" }}
              transition={{
                duration: 0.5,
                delay: (i % 3) * 0.08,
                ease: [0.22, 1, 0.36, 1],
              }}
              className="min-w-[80%] snap-start sm:min-w-[60%] md:min-w-0"
            >
              <Link
                href={`/research-materials?category=${encodeURIComponent(cat.name)}`}
                className="group flex h-full flex-col rounded-[var(--radius-lg)] border border-[color:var(--color-border-grey)] bg-white p-6 transition-all duration-300 hover:-translate-y-1 hover:border-[color:color-mix(in_srgb,var(--color-elysium)_35%,transparent)] hover:shadow-[var(--shadow-card)]"
              >
                <div className="flex items-center justify-between">
                  <div className="flex h-11 w-11 items-center justify-center rounded-[var(--radius-md)] bg-soft transition-colors group-hover:bg-elysium">
                    <cat.icon
                      className="h-5 w-5 text-elysium transition-colors group-hover:text-white"
                      aria-hidden
                    />
                  </div>
                  <ArrowUpRight className="h-5 w-5 text-ink/30 transition-all group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:text-elysium" />
                </div>
                <h3 className="mt-5 font-[family-name:var(--font-display)] text-lg font-semibold text-navy">
                  {cat.name}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-ink/60">
                  {cat.desc}
                </p>
              </Link>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
