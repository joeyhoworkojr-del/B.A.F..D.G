import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // ── StatEdge light theme ────────────────────────────────────────────
        // White page, very light grey secondary surfaces, charcoal text and an
        // emerald brand accent. The `terminal.*` / `signal.*` / inverted `zinc`
        // names are kept so the whole app re-skins from this one file.
        terminal: {
          bg: '#ffffff',        // page background
          surface: '#ffffff',   // cards (separated by border, not fill)
          muted: '#f5f6f8',     // secondary surface / table stripes
          border: '#e4e7ec',    // hairline borders
        },
        signal: {
          amber: '#b45309',        // watch / medium confidence (AA on white)
          'amber-dim': '#fef3c7',
          green: '#059669',        // brand + genuine positive value
          'green-dim': '#ecfdf5',
          red: '#dc2626',          // negative / stale / error
          'red-dim': '#fef2f2',
          blue: '#2563eb',         // informational (crowd / market)
          purple: '#7c3aed',
        },
        // Inverted scale: the app writes `text-zinc-100` for primary text, so
        // 100 is the darkest value here and the ramp lightens as it climbs.
        zinc: {
          50: '#ffffff',
          100: '#111827',   // primary text — charcoal
          200: '#1f2937',
          300: '#374151',
          400: '#4b5563',   // secondary text (AA on white)
          500: '#6b7280',   // tertiary text
          600: '#9ca3af',   // faint / disabled
          700: '#d1d5db',
          800: '#e5e7eb',
          900: '#f3f4f6',
        },
        // Semantic aliases for new components.
        brand: {
          DEFAULT: '#059669',
          strong: '#047857',
          soft: '#ecfdf5',
        },
      },
      borderRadius: {
        card: '14px',
      },
      boxShadow: {
        card: '0 1px 2px rgba(16, 24, 40, 0.04), 0 1px 3px rgba(16, 24, 40, 0.06)',
        pop: '0 8px 24px -6px rgba(16, 24, 40, 0.12)',
      },
      fontFamily: {
        display: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        body: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      fontSize: {
        // Body text sits at 14–16px; nothing meaningful below 12px.
        xs: ['0.75rem', { lineHeight: '1rem' }],
        sm: ['0.875rem', { lineHeight: '1.25rem' }],
        base: ['1rem', { lineHeight: '1.5rem' }],
      },
      maxWidth: {
        app: '1280px',
      },
    },
  },
  plugins: [],
} satisfies Config
