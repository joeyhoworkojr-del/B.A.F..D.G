/** Decorative football-pitch line-art, tuned to the light/blue theme. Purely
 *  ornamental — sits behind hero cards at low opacity. */
export function PitchBackdrop({ className = '' }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 400 200"
      className={className}
      preserveAspectRatio="xMidYMid slice"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="pitch-grad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#2563eb" stopOpacity="0.07" />
          <stop offset="100%" stopColor="#2563eb" stopOpacity="0.015" />
        </linearGradient>
      </defs>
      <rect width="400" height="200" fill="url(#pitch-grad)" />
      <g stroke="#2563eb" strokeOpacity="0.13" strokeWidth="1.5" fill="none">
        <line x1="200" y1="4" x2="200" y2="196" />
        <circle cx="200" cy="100" r="34" />
        <rect x="0" y="62" width="44" height="76" />
        <rect x="356" y="62" width="44" height="76" />
        <rect x="0" y="84" width="16" height="32" />
        <rect x="384" y="84" width="16" height="32" />
      </g>
      <circle cx="200" cy="100" r="3" fill="#2563eb" fillOpacity="0.22" />
    </svg>
  )
}

/** Inline soccer-ball glyph. */
export function SoccerBall({ className = '' }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="9.2" fill="currentColor" fillOpacity="0.1" stroke="currentColor" strokeWidth="1.4" />
      <path
        d="M12 6.6l3.2 2.3-1.2 3.7h-4L8.8 8.9 12 6.6z"
        fill="currentColor"
        fillOpacity="0.85"
      />
      <path
        d="M12 6.6V3.2M15.2 8.9l3.1-1M13.8 12.6l2 3M10.2 12.6l-2 3M8.8 8.9l-3.1-1"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
        strokeOpacity="0.5"
      />
    </svg>
  )
}
