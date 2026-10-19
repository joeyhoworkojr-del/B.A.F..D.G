"use client";

import * as React from "react";
import { motion } from "framer-motion";
import { FlaskConical, FileCheck2, ShieldCheck, Boxes } from "lucide-react";
import { Button } from "@/components/ui/button";
import { RuoBadge } from "@/components/ui/badge";
import { MolecularVisual } from "@/components/ui/molecular-visual";

const credibility = [
  { icon: FlaskConical, label: "Independent Analysis" },
  { icon: FileCheck2, label: "Batch Documentation" },
  { icon: Boxes, label: "Controlled Handling" },
  { icon: ShieldCheck, label: "Research Use Only" },
];

export function Hero() {
  return (
    <section className="relative overflow-hidden pt-[calc(var(--header-height)+2.5rem)]">
      {/* backdrop layers */}
      <div className="grid-lines absolute inset-0" aria-hidden />
      <div
        className="absolute inset-x-0 top-0 h-[520px] bg-gradient-to-b from-soft/70 via-white to-white"
        aria-hidden
      />
      <div className="glow-soft absolute inset-x-0 top-0 h-[400px]" aria-hidden />

      <div className="container-el relative grid items-center gap-12 pb-16 lg:grid-cols-[1.05fr_0.95fr] lg:gap-8 lg:pb-24 lg:pt-8">
        {/* Left column */}
        <div>
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="flex items-center gap-3"
          >
            <RuoBadge />
            <span className="mono-label text-ink/40">Est. Research Standard</span>
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.05, ease: [0.22, 1, 0.36, 1] }}
            className="mt-6 font-[family-name:var(--font-display)] text-balance text-4xl font-semibold leading-[1.05] tracking-tight text-navy sm:text-5xl lg:text-6xl"
          >
            Precision Materials for Advanced Research.
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.15, ease: [0.22, 1, 0.36, 1] }}
            className="mt-6 max-w-xl text-base leading-relaxed text-ink/65 sm:text-lg"
          >
            Elysium Bio Labs supplies carefully sourced, independently evaluated
            research materials supported by transparent documentation and
            rigorous quality standards.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.25, ease: [0.22, 1, 0.36, 1] }}
            className="mt-9 flex flex-col gap-3 sm:flex-row"
          >
            <Button href="/research-materials" size="lg">
              Explore Research Materials
            </Button>
            <Button href="/quality" variant="secondary" size="lg">
              View Quality Standards
            </Button>
          </motion.div>

          {/* credibility row */}
          <motion.ul
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.4 }}
            className="mt-12 grid grid-cols-2 gap-4 border-t border-[color:var(--color-border-grey)] pt-6 sm:grid-cols-4"
          >
            {credibility.map((item) => (
              <li key={item.label} className="flex items-center gap-2.5">
                <item.icon
                  className="h-4 w-4 flex-shrink-0 text-elysium"
                  aria-hidden
                />
                <span className="text-[0.8125rem] font-medium text-navy/80">
                  {item.label}
                </span>
              </li>
            ))}
          </motion.ul>
        </div>

        {/* Right column — visual + data card */}
        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.8, delay: 0.2, ease: [0.22, 1, 0.36, 1] }}
          className="relative"
        >
          <div className="relative overflow-hidden rounded-[var(--radius-lg)] border border-[color:var(--color-border-grey)] bg-gradient-to-br from-white to-soft/40 shadow-[var(--shadow-card)]">
            <div className="grid-lines absolute inset-0 opacity-60" aria-hidden />
            <div className="relative aspect-[4/3] p-6">
              <MolecularVisual className="h-full w-full" />
            </div>

            {/* corner mono markers */}
            <span className="mono-label absolute left-4 top-4 text-ink/35">
              LATTICE / 04
            </span>
            <span className="mono-label absolute right-4 top-4 text-ink/35">
              λ 0757F7
            </span>
          </div>

          {/* floating data card */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.55 }}
            className="absolute -bottom-6 -left-4 w-60 rounded-[var(--radius-md)] border border-[color:var(--color-border-grey)] bg-white/90 p-4 shadow-[var(--shadow-card-hover)] backdrop-blur-sm sm:-left-6"
          >
            <div className="flex items-center justify-between">
              <span className="mono-label text-elysium">SAMPLE SPEC</span>
              <span className="flex h-2 w-2">
                <span className="absolute inline-flex h-2 w-2 animate-ping rounded-full bg-elysium opacity-60" />
                <span className="inline-flex h-2 w-2 rounded-full bg-elysium" />
              </span>
            </div>
            <dl className="mt-3 space-y-2">
              {[
                ["Reported Purity", "≥ 98%"],
                ["Method", "HPLC · MS"],
                ["Batch", "ELB-—-0000"],
              ].map(([k, v]) => (
                <div key={k} className="flex justify-between text-xs">
                  <dt className="text-ink/50">{k}</dt>
                  <dd className="font-[family-name:var(--font-mono)] text-navy">
                    {v}
                  </dd>
                </div>
              ))}
            </dl>
            <p className="mt-3 border-t border-[color:var(--color-border-grey)] pt-2 text-[0.625rem] leading-tight text-ink/40">
              Sample values shown for demonstration.
            </p>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}
