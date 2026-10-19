"use client";

import * as React from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

/**
 * Abstract molecular/lattice visual built purely from SVG.
 * A deterministic node-and-edge graph with layered translucent blue surfaces,
 * fine measurement markers, and a gentle drifting motion. No stock imagery,
 * no DNA helix cliché — just precise geometry.
 */

type Node = { x: number; y: number; r: number; hub?: boolean };

const NODES: Node[] = [
  { x: 50, y: 40, r: 3 },
  { x: 130, y: 70, r: 5, hub: true },
  { x: 90, y: 130, r: 3 },
  { x: 200, y: 50, r: 3 },
  { x: 250, y: 120, r: 6, hub: true },
  { x: 180, y: 160, r: 3 },
  { x: 300, y: 70, r: 3 },
  { x: 320, y: 170, r: 4 },
  { x: 150, y: 210, r: 3 },
  { x: 240, y: 220, r: 5, hub: true },
  { x: 60, y: 180, r: 4 },
  { x: 30, y: 110, r: 3 },
];

const EDGES: [number, number][] = [
  [0, 1],
  [1, 2],
  [1, 3],
  [3, 4],
  [4, 5],
  [4, 6],
  [6, 7],
  [5, 8],
  [8, 9],
  [9, 7],
  [2, 10],
  [10, 11],
  [11, 0],
  [2, 5],
  [8, 10],
  [1, 4],
];

export function MolecularVisual({ className }: { className?: string }) {
  return (
    <div className={cn("relative", className)}>
      <svg
        viewBox="0 0 360 260"
        className="h-full w-full overflow-visible"
        role="img"
        aria-label="Abstract molecular lattice diagram"
      >
        <defs>
          <linearGradient id="edgeGrad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#0757f7" stopOpacity="0.9" />
            <stop offset="100%" stopColor="#0757f7" stopOpacity="0.25" />
          </linearGradient>
          <radialGradient id="hubGlow" cx="0.5" cy="0.5" r="0.5">
            <stop offset="0%" stopColor="#0757f7" stopOpacity="0.35" />
            <stop offset="100%" stopColor="#0757f7" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* edges */}
        <g>
          {EDGES.map(([a, b], i) => (
            <motion.line
              key={i}
              x1={NODES[a].x}
              y1={NODES[a].y}
              x2={NODES[b].x}
              y2={NODES[b].y}
              stroke="url(#edgeGrad)"
              strokeWidth={1.25}
              initial={{ pathLength: 0, opacity: 0 }}
              animate={{ pathLength: 1, opacity: 1 }}
              transition={{
                duration: 1,
                delay: 0.2 + i * 0.05,
                ease: [0.22, 1, 0.36, 1],
              }}
            />
          ))}
        </g>

        {/* nodes */}
        <g>
          {NODES.map((n, i) => (
            <motion.g
              key={i}
              initial={{ opacity: 0, scale: 0 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{
                duration: 0.5,
                delay: 0.4 + i * 0.04,
                ease: [0.22, 1, 0.36, 1],
              }}
            >
              {n.hub && (
                <circle cx={n.x} cy={n.y} r={n.r * 4} fill="url(#hubGlow)" />
              )}
              <motion.circle
                cx={n.x}
                cy={n.y}
                r={n.r}
                fill={n.hub ? "#0757f7" : "#ffffff"}
                stroke="#0757f7"
                strokeWidth={n.hub ? 0 : 1.25}
                animate={{ y: [0, i % 2 === 0 ? -3 : 3, 0] }}
                transition={{
                  duration: 6 + (i % 4),
                  repeat: Infinity,
                  ease: "easeInOut",
                }}
              />
            </motion.g>
          ))}
        </g>

        {/* measurement markers */}
        <g stroke="#08152f" strokeOpacity="0.18" strokeWidth="1">
          <line x1="12" y1="20" x2="12" y2="240" />
          <line x1="8" y1="20" x2="16" y2="20" />
          <line x1="8" y1="130" x2="16" y2="130" />
          <line x1="8" y1="240" x2="16" y2="240" />
        </g>
      </svg>
    </div>
  );
}
