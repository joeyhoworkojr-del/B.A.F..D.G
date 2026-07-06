/**
 * Sports art system — clean, theme-tuned SVG field backdrops and glyphs shared
 * across every sport page so the whole app reads as one illustrated system.
 * All line-art is blue-toned (the trading-desk accent) at low opacity.
 */
import type { ReactNode } from 'react'

export type Sport = 'wc' | 'nfl' | 'cfl' | 'mlb'

const LINE = '#2563eb'

function Frame({ children }: { children: ReactNode }) {
  return (
    <defs>
      <linearGradient id="field-grad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor={LINE} stopOpacity="0.07" />
        <stop offset="100%" stopColor={LINE} stopOpacity="0.015" />
      </linearGradient>
      {children}
    </defs>
  )
}

/** Football pitch: centre circle, halfway line, penalty boxes. */
export function PitchBackdrop({ className = '' }: { className?: string }) {
  return (
    <svg viewBox="0 0 400 200" className={className} preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <Frame>{null}</Frame>
      <rect width="400" height="200" fill="url(#field-grad)" />
      <g stroke={LINE} strokeOpacity="0.13" strokeWidth="1.5" fill="none">
        <line x1="200" y1="4" x2="200" y2="196" />
        <circle cx="200" cy="100" r="34" />
        <rect x="0" y="62" width="44" height="76" />
        <rect x="356" y="62" width="44" height="76" />
        <rect x="0" y="84" width="16" height="32" />
        <rect x="384" y="84" width="16" height="32" />
      </g>
      <circle cx="200" cy="100" r="3" fill={LINE} fillOpacity="0.22" />
    </svg>
  )
}

/** Gridiron: yard lines, hash marks, two end zones. */
export function GridironBackdrop({ className = '' }: { className?: string }) {
  const yards = [40, 80, 120, 160, 200, 240, 280, 320, 360]
  return (
    <svg viewBox="0 0 400 200" className={className} preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <Frame>{null}</Frame>
      <rect width="400" height="200" fill="url(#field-grad)" />
      <g stroke={LINE} strokeOpacity="0.12" strokeWidth="1.5" fill="none">
        {yards.map(x => <line key={x} x1={x} y1="8" x2={x} y2="192" />)}
        {/* hash marks down the middle */}
        {Array.from({ length: 19 }, (_, i) => 20 + i * 20).map(x => (
          <g key={`h${x}`}>
            <line x1={x} y1="72" x2={x} y2="80" />
            <line x1={x} y1="120" x2={x} y2="128" />
          </g>
        ))}
      </g>
      {/* end zones */}
      <rect x="0" y="8" width="24" height="184" fill={LINE} fillOpacity="0.06" />
      <rect x="376" y="8" width="24" height="184" fill={LINE} fillOpacity="0.06" />
      <line x1="200" y1="8" x2="200" y2="192" stroke={LINE} strokeOpacity="0.22" strokeWidth="2" />
    </svg>
  )
}

/** Baseball diamond: infield, bases, mound, outfield arc. */
export function DiamondBackdrop({ className = '' }: { className?: string }) {
  return (
    <svg viewBox="0 0 400 200" className={className} preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <Frame>{null}</Frame>
      <rect width="400" height="200" fill="url(#field-grad)" />
      <g stroke={LINE} strokeOpacity="0.13" strokeWidth="1.5" fill="none">
        {/* outfield arc */}
        <path d="M120 176 A 110 110 0 0 1 280 176" />
        {/* infield diamond (home bottom, second top) */}
        <path d="M200 176 L246 130 L200 84 L154 130 Z" />
      </g>
      {/* bases + mound */}
      <g fill={LINE} fillOpacity="0.2">
        <rect x="196" y="172" width="8" height="8" transform="rotate(45 200 176)" />
        <rect x="242" y="126" width="8" height="8" transform="rotate(45 246 130)" />
        <rect x="196" y="80" width="8" height="8" transform="rotate(45 200 84)" />
        <rect x="150" y="126" width="8" height="8" transform="rotate(45 154 130)" />
        <circle cx="200" cy="130" r="4" />
      </g>
    </svg>
  )
}

export function fieldBackdrop(sport: Sport, className = '') {
  if (sport === 'mlb') return <DiamondBackdrop className={className} />
  if (sport === 'nfl' || sport === 'cfl') return <GridironBackdrop className={className} />
  return <PitchBackdrop className={className} />
}

// ─── Glyphs ───────────────────────────────────────────────────────────────────

/** Clean soccer ball: circle, central pentagon, seams to the edge. */
export function SoccerBall({ className = '' }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="9.3" stroke="currentColor" strokeWidth="1.4" fill="currentColor" fillOpacity="0.08" />
      <path d="M12 8 L15.8 10.76 L14.35 15.24 L9.65 15.24 L8.2 10.76 Z" fill="currentColor" fillOpacity="0.9" />
      <g stroke="currentColor" strokeWidth="1.15" strokeLinecap="round" strokeOpacity="0.55">
        <path d="M12 8 L12 2.9" />
        <path d="M15.8 10.76 L20.6 9.2" />
        <path d="M14.35 15.24 L17.3 19.4" />
        <path d="M9.65 15.24 L6.7 19.4" />
        <path d="M8.2 10.76 L3.4 9.2" />
      </g>
    </svg>
  )
}

/** American / Canadian football: prolate ball with laces. */
export function Football({ className = '' }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" aria-hidden="true">
      <ellipse cx="12" cy="12" rx="9.4" ry="5.6" transform="rotate(-32 12 12)"
        stroke="currentColor" strokeWidth="1.4" fill="currentColor" fillOpacity="0.1" />
      <g stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeOpacity="0.7">
        <path d="M8.4 15.6 L15.6 8.4" />
        <path d="M10.4 12.7 L11.6 11.5" />
        <path d="M12 14.3 L13.2 13.1" />
        <path d="M8.8 11.1 L10 9.9" />
      </g>
    </svg>
  )
}

/** Baseball: circle with two figure-eight seams. */
export function Baseball({ className = '' }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="9.3" stroke="currentColor" strokeWidth="1.4" fill="currentColor" fillOpacity="0.08" />
      <path d="M6 4.4 C 9 8, 9 16, 6 19.6" stroke="currentColor" strokeWidth="1.2" strokeOpacity="0.7" fill="none" />
      <path d="M18 4.4 C 15 8, 15 16, 18 19.6" stroke="currentColor" strokeWidth="1.2" strokeOpacity="0.7" fill="none" />
      <g stroke="currentColor" strokeWidth="0.9" strokeOpacity="0.55" strokeLinecap="round">
        <path d="M6.6 7 L8 7.3 M6.2 9.5 L7.7 9.6 M6.1 12 L7.6 12 M6.2 14.5 L7.7 14.4 M6.6 17 L8 16.7" />
        <path d="M17.4 7 L16 7.3 M17.8 9.5 L16.3 9.6 M17.9 12 L16.4 12 M17.8 14.5 L16.3 14.4 M17.4 17 L16 16.7" />
      </g>
    </svg>
  )
}

export function SportGlyph({ sport, className = '' }: { sport: Sport; className?: string }) {
  if (sport === 'mlb') return <Baseball className={className} />
  if (sport === 'nfl' || sport === 'cfl') return <Football className={className} />
  return <SoccerBall className={className} />
}
