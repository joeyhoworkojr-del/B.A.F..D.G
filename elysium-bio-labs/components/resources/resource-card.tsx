"use client";

import * as React from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowUpRight, Clock } from "lucide-react";
import type { Resource } from "@/data/resources";
import { resourceText } from "@/data/resources";
import { readingTime } from "@/lib/utils";

export function ResourceCard({
  resource,
  index = 0,
}: {
  resource: Resource;
  index?: number;
}) {
  const minutes = readingTime(resourceText(resource));
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
      className="group h-full"
    >
      <Link
        href={`/resources/${resource.slug}`}
        className="flex h-full flex-col rounded-[var(--radius-lg)] border border-[color:var(--color-border-grey)] bg-white p-6 transition-all duration-300 hover:-translate-y-1 hover:border-[color:color-mix(in_srgb,var(--color-elysium)_35%,transparent)] hover:shadow-[var(--shadow-card)]"
      >
        <div className="flex items-center justify-between">
          <span className="mono-label text-elysium">{resource.category}</span>
          <ArrowUpRight className="h-4 w-4 text-ink/30 transition-all group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:text-elysium" />
        </div>
        <h3 className="mt-4 font-[family-name:var(--font-display)] text-lg font-semibold leading-snug text-navy">
          {resource.title}
        </h3>
        <p className="mt-2 flex-1 text-sm leading-relaxed text-ink/60">
          {resource.excerpt}
        </p>
        <div className="mt-5 flex items-center gap-3 border-t border-[color:var(--color-border-grey)] pt-4 text-[0.6875rem] text-ink/45">
          <span className="inline-flex items-center gap-1">
            <Clock className="h-3.5 w-3.5" aria-hidden />
            {minutes} min read
          </span>
          <span aria-hidden>·</span>
          <time dateTime={resource.publishedOn}>
            {new Date(resource.publishedOn).toLocaleDateString("en-CA", {
              year: "numeric",
              month: "short",
              day: "numeric",
            })}
          </time>
        </div>
      </Link>
    </motion.article>
  );
}
