import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * Abstract "vial" product visual — a refined geometric composition, not a
 * literal medical vial. A tall rounded capsule of layered translucent blue
 * with a fine measurement scale and a floating molecular node. Deterministic
 * per product via `seed` so each card feels distinct but on-brand.
 */
export function VialVisual({
  seed = 0,
  className,
}: {
  seed?: number;
  className?: string;
}) {
  const id = `vial-${seed}`;
  const fillLevel = 40 + (seed % 5) * 10; // 40–80
  const nodeCount = 3 + (seed % 3);
  const nodes = Array.from({ length: nodeCount }, (_, i) => ({
    x: 60 + ((i * 37 + seed * 11) % 40),
    y: 60 + ((i * 53 + seed * 17) % 120),
    r: 2 + ((i + seed) % 3),
  }));

  return (
    <svg
      viewBox="0 0 160 220"
      className={cn("h-full w-full", className)}
      role="img"
      aria-label="Abstract research-material visual"
    >
      <defs>
        <linearGradient id={`${id}-body`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#eaf2ff" stopOpacity="0.9" />
          <stop offset="100%" stopColor="#c9def8" stopOpacity="0.5" />
        </linearGradient>
        <linearGradient id={`${id}-fill`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#0757f7" stopOpacity="0.28" />
          <stop offset="100%" stopColor="#0757f7" stopOpacity="0.55" />
        </linearGradient>
        <clipPath id={`${id}-clip`}>
          <rect x="52" y="34" width="56" height="150" rx="16" />
        </clipPath>
      </defs>

      {/* soft ground shadow */}
      <ellipse cx="80" cy="196" rx="42" ry="7" fill="#08152f" opacity="0.06" />

      {/* neck */}
      <rect x="66" y="16" width="28" height="18" rx="4" fill="#dde4ee" />
      <rect x="63" y="12" width="34" height="8" rx="4" fill="#c3cede" />

      {/* body */}
      <rect
        x="52"
        y="34"
        width="56"
        height="150"
        rx="16"
        fill={`url(#${id}-body)`}
        stroke="#b7d0f2"
        strokeWidth="1"
      />

      {/* liquid fill */}
      <g clipPath={`url(#${id}-clip)`}>
        <rect
          x="52"
          y={184 - fillLevel * 1.5}
          width="56"
          height={fillLevel * 1.5}
          fill={`url(#${id}-fill)`}
        />
        {/* meniscus line */}
        <rect
          x="52"
          y={184 - fillLevel * 1.5}
          width="56"
          height="2"
          fill="#0757f7"
          opacity="0.5"
        />
        {/* floating nodes */}
        {nodes.map((n, i) => (
          <g key={i}>
            <circle cx={n.x} cy={n.y} r={n.r} fill="#0757f7" opacity="0.7" />
          </g>
        ))}
      </g>

      {/* highlight */}
      <rect
        x="60"
        y="44"
        width="6"
        height="120"
        rx="3"
        fill="#ffffff"
        opacity="0.55"
      />

      {/* measurement ticks */}
      <g stroke="#08152f" strokeOpacity="0.22" strokeWidth="1">
        {Array.from({ length: 6 }, (_, i) => (
          <line
            key={i}
            x1="112"
            x2={i % 2 === 0 ? 122 : 118}
            y1={54 + i * 22}
            y2={54 + i * 22}
          />
        ))}
      </g>
    </svg>
  );
}
