"use client";

import * as React from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

export interface ProcessStep {
  index: string;
  title: string;
  description: string;
}

/**
 * Animated process diagram. Horizontal on wide screens, vertical on mobile.
 * The connecting rule draws in as it enters the viewport.
 */
export function ProcessTimeline({
  steps,
  dark = false,
  className,
}: {
  steps: ProcessStep[];
  dark?: boolean;
  className?: string;
}) {
  return (
    <div className={cn("relative", className)}>
      {/* connector rail */}
      <div
        className={cn(
          "absolute left-[15px] top-2 bottom-2 w-px md:left-0 md:right-0 md:top-[15px] md:bottom-auto md:h-px md:w-full",
          dark ? "bg-white/15" : "bg-[color:var(--color-border-grey)]",
        )}
        aria-hidden
      />
      <motion.div
        className="absolute left-[15px] top-2 w-px origin-top bg-elysium md:left-0 md:top-[15px] md:h-px md:w-full md:origin-left"
        initial={{ scaleY: 0, scaleX: 0 }}
        whileInView={{ scaleY: 1, scaleX: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 1.1, ease: [0.22, 1, 0.36, 1] }}
        style={{ bottom: 8 }}
        aria-hidden
      />

      <ol className="relative grid gap-8 md:grid-cols-4 md:gap-6">
        {steps.map((step, i) => (
          <motion.li
            key={step.title}
            className="relative pl-11 md:pl-0 md:pt-11"
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{
              duration: 0.5,
              delay: 0.2 + i * 0.12,
              ease: [0.22, 1, 0.36, 1],
            }}
          >
            <span
              className={cn(
                "absolute left-0 top-0 flex h-8 w-8 items-center justify-center rounded-full font-[family-name:var(--font-mono)] text-[0.6875rem] font-medium md:left-0",
                dark
                  ? "bg-elysium text-white ring-4 ring-navy"
                  : "bg-elysium text-white ring-4 ring-white",
              )}
            >
              {step.index}
            </span>
            <h3
              className={cn(
                "text-base font-semibold",
                dark ? "text-white" : "text-navy",
              )}
            >
              {step.title}
            </h3>
            <p
              className={cn(
                "mt-1.5 text-sm leading-relaxed",
                dark ? "text-white/65" : "text-ink/60",
              )}
            >
              {step.description}
            </p>
          </motion.li>
        ))}
      </ol>
    </div>
  );
}
