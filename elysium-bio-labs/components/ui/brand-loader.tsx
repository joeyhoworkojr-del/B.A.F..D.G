"use client";

import * as React from "react";
import { motion } from "framer-motion";
import { Emblem } from "./emblem";

/** Elegant brand loader — the emblem bars draw in with a sweeping rule. */
export function BrandLoader() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-6">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4 }}
      >
        <Emblem animated className="w-16" />
      </motion.div>
      <div className="relative h-px w-40 overflow-hidden bg-[color:var(--color-border-grey)]">
        <motion.span
          className="absolute inset-y-0 left-0 w-1/2 bg-elysium"
          animate={{ x: ["-100%", "300%"] }}
          transition={{ duration: 1.1, repeat: Infinity, ease: "easeInOut" }}
        />
      </div>
      <p className="mono-label text-ink/40">Loading</p>
    </div>
  );
}
