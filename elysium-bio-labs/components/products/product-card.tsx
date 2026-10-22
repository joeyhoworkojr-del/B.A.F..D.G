"use client";

import * as React from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import type { Product } from "@/data/products";
import { StatusBadge, DocIndicator } from "@/components/ui/badge";
import { VialVisual } from "@/components/ui/vial-visual";

export function ProductCard({
  product,
  index = 0,
}: {
  product: Product;
  index?: number;
}) {
  const seed = product.slug.length + index;
  return (
    <motion.article
      initial={{ opacity: 0, y: 18 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-40px" }}
      transition={{
        duration: 0.5,
        delay: (index % 3) * 0.08,
        ease: [0.22, 1, 0.36, 1],
      }}
      className="group relative flex flex-col overflow-hidden rounded-[var(--radius-lg)] border border-[color:var(--color-border-grey)] bg-white shadow-[var(--shadow-card)] transition-all duration-300 ease-[var(--ease-out-soft)] hover:-translate-y-1 hover:border-[color:color-mix(in_srgb,var(--color-elysium)_35%,transparent)] hover:shadow-[var(--shadow-card-hover)]"
    >
      {/* visual */}
      <div className="relative flex h-44 items-center justify-center overflow-hidden bg-gradient-to-b from-soft/60 to-white">
        <div className="grid-lines absolute inset-0 opacity-50" aria-hidden />
        <VialVisual seed={seed} className="relative h-36 w-auto" />
        <div className="absolute right-3 top-3">
          <StatusBadge status={product.status} />
        </div>
      </div>

      {/* body */}
      <div className="flex flex-1 flex-col p-5">
        <p className="mono-label text-elysium">{product.category}</p>
        <h3 className="mt-1.5 font-[family-name:var(--font-display)] text-lg font-semibold text-navy">
          {product.name}
        </h3>
        <p className="mt-1 text-sm text-ink/60">{product.presentation}</p>

        <div className="mt-4 flex items-center justify-between border-t border-[color:var(--color-border-grey)] pt-3">
          <span className="font-[family-name:var(--font-mono)] text-[0.6875rem] text-ink/45">
            {product.batchNumber}
          </span>
          <DocIndicator available={product.documentationAvailable} />
        </div>

        <Link
          href={`/research-materials/${product.slug}`}
          className="mt-4 inline-flex items-center justify-center gap-1.5 rounded-[var(--radius-sm)] border border-[color:var(--color-border-grey)] px-4 py-2.5 text-sm font-medium text-navy transition-colors group-hover:border-elysium group-hover:bg-elysium group-hover:text-white"
        >
          View Details
          <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
        </Link>
      </div>
    </motion.article>
  );
}
