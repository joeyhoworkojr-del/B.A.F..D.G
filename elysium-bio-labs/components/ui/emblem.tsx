"use client";

import * as React from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

/**
 * Elysium emblem — three offset parallelogram bars echoing the logo mark.
 * Rendered as SVG so it scales crisply and animates cheaply.
 */
export function Emblem({
  className,
  animated = false,
  tone = "brand",
}: {
  className?: string;
  animated?: boolean;
  tone?: "brand" | "white" | "muted";
}) {
  const fill =
    tone === "white"
      ? "#ffffff"
      : tone === "muted"
        ? "rgba(255,255,255,0.14)"
        : "#0757f7";

  const bars = [
    { y: 4, skew: 0 },
    { y: 22, skew: 0 },
    { y: 40, skew: 0 },
  ];

  return (
    <svg
      viewBox="0 0 72 56"
      className={cn("block", className)}
      role="img"
      aria-label="Elysium Bio Labs emblem"
    >
      {bars.map((bar, i) =>
        animated ? (
          <motion.polygon
            key={i}
            points={parallelogram(bar.y)}
            fill={fill}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{
              duration: 0.5,
              delay: i * 0.12,
              ease: [0.22, 1, 0.36, 1],
            }}
          />
        ) : (
          <polygon key={i} points={parallelogram(bar.y)} fill={fill} />
        ),
      )}
    </svg>
  );
}

/** A slanted bar: 60 wide, 10 tall, sheared right. */
function parallelogram(y: number): string {
  const h = 10;
  const shear = 8;
  const x = 6;
  const w = 60;
  return [
    `${x + shear},${y}`,
    `${x + w},${y}`,
    `${x + w - shear},${y + h}`,
    `${x},${y + h}`,
  ].join(" ");
}

/**
 * Ambient background emblem used in dark CTA sections — large, faint,
 * with a slow, subtle breathing motion that respects reduced motion.
 */
export function AmbientEmblem({ className }: { className?: string }) {
  return (
    <motion.div
      className={cn("pointer-events-none absolute", className)}
      aria-hidden
      initial={{ opacity: 0.05, scale: 0.98 }}
      animate={{ opacity: [0.05, 0.1, 0.05], scale: [0.98, 1, 0.98] }}
      transition={{ duration: 9, repeat: Infinity, ease: "easeInOut" }}
    >
      <Emblem tone="muted" className="w-[min(60vw,640px)]" />
    </motion.div>
  );
}
