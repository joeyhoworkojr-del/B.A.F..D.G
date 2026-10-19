/**
 * The nav icon set.
 *
 * One file so the header chips and the bottom bar cannot drift into using two
 * different footballs for the same destination. All are 24-viewBox strokes
 * that inherit `currentColor`, so a chip only has to set text colour.
 */
type IconProps = { size?: number }

const base = (size: number) => ({
  width: size, height: size, viewBox: '0 0 24 24', fill: 'none',
  stroke: 'currentColor', strokeWidth: 2,
  strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const,
  'aria-hidden': true,
})

export const Football = ({ size = 20 }: IconProps) => (
  <svg {...base(size)}>
    <path d="M3 21c4-.5 14-2.5 18-18C8 3.5 3.5 8 3 21Z" />
    <path d="M8.5 15.5 15.5 8.5M10 12l2 2M12 10l2 2" />
  </svg>
)

export const Bars = ({ size = 20 }: IconProps) => (
  <svg {...base(size)}>
    <line x1="6" y1="20" x2="6" y2="12" />
    <line x1="12" y1="20" x2="12" y2="4" />
    <line x1="18" y1="20" x2="18" y2="9" />
  </svg>
)

export const Trend = ({ size = 20 }: IconProps) => (
  <svg {...base(size)}>
    <polyline points="3 17 9 11 13 15 21 7" />
    <polyline points="15 7 21 7 21 13" />
  </svg>
)

export const Paper = ({ size = 20 }: IconProps) => (
  <svg {...base(size)}>
    <rect x="4" y="3" width="16" height="18" rx="2" />
    <path d="M8 8h8M8 12h8M8 16h5" />
  </svg>
)

export const Layers = ({ size = 20 }: IconProps) => (
  <svg {...base(size)}>
    <path d="m12 3 9 5-9 5-9-5 9-5Z" />
    <path d="m3 13 9 5 9-5" />
  </svg>
)

export const Ticked = ({ size = 20 }: IconProps) => (
  <svg {...base(size)}>
    <path d="M9 11l2.5 2.5L16 8" />
    <circle cx="12" cy="12" r="9" />
  </svg>
)

export const Person = ({ size = 20 }: IconProps) => (
  <svg {...base(size)}>
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
    <circle cx="12" cy="7" r="4" />
  </svg>
)

export const Spark = ({ size = 20 }: IconProps) => (
  <svg {...base(size)}>
    <path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9L12 3Z" />
    <path d="M18.5 16.5l.7 1.8 1.8.7-1.8.7-.7 1.8-.7-1.8-1.8-.7 1.8-.7.7-1.8Z" />
  </svg>
)

export const Search = ({ size = 20 }: IconProps) => (
  <svg {...base(size)}>
    <circle cx="11" cy="11" r="7" />
    <path d="m20 20-3.5-3.5" />
  </svg>
)
