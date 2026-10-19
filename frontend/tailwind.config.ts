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
        // Every colour here is a text or fill colour on a *light* surface, and
        // each one clears 4.5:1 against white and against its own `-dim` tint.
        // They were picked by eye before, and a contrast audit of the whole app
        // found seven distinct pairs below AA — emerald-600 text on white is
        // 3.77:1, white on emerald-600 is the same, and red-600 on red-100 is
        // 3.95:1. The deeper shades below are what those have to be. The
        // audit now runs in the e2e suite, so this cannot drift back.
        signal: {
          amber: '#b45309',        // watch / medium confidence
          // Light enough that #b45309 text on it clears 4.5:1 (amber-100 does not).
          'amber-dim': '#fffbeb',
          green: '#047857',        // brand + genuine positive value (5.5:1 on white)
          'green-dim': '#ecfdf5',
          red: '#be123c',          // negative / stale / error (5.9:1 on white)
          'red-dim': '#fff1f2',
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
          500: '#667085',   // tertiary text — 4.5:1 on `terminal.muted` too
          // Faint / disabled. It does not clear 4.5:1 on white and is not for
          // text: anything a reader has to read uses 500 or darker.
          600: '#9ca3af',
          700: '#d1d5db',
          800: '#e5e7eb',
          900: '#f3f4f6',
        },
        // Semantic aliases for new components.
        //
        // `DEFAULT` is the emerald that carries text on a light surface and
        // white text on a fill; `strong` is the step darker for a hover state;
        // `light` is for the two inverted panels, where the relationship is
        // the other way round and emerald-600 is the one that is too dark.
        brand: {
          DEFAULT: '#047857',   // 5.5:1 on white, 5.5:1 under white text
          strong: '#065f46',    // hover — 7.8:1
          soft: '#ecfdf5',
          light: '#10b981',     // on `ink` only — 7.3:1 on #0a1512
        },
        // ── Inverted surfaces ───────────────────────────────────────────────
        // The hero and the raised nav button sit on near-black rather than on
        // the page white, which is what gives the board a focal point instead
        // of a wall of equal cards. Named by role, not by colour, so a later
        // change of palette does not leave "navy" meaning charcoal.
        ink: {
          DEFAULT: '#0a1512',   // hero / inverted card
          soft: '#12201c',      // tiles inside it
          line: '#1e2f2a',      // hairlines inside it
          muted: '#8aa39b',     // secondary text on ink
        },
      },
      borderRadius: {
        // One card radius for the whole app. Before the redesign there were
        // three — `rounded-xl`, `rounded-card` and `rounded-2xl`, at 12, 14
        // and 16px — mixed across pages built at different times, which is
        // the kind of inconsistency that reads as carelessness rather than
        // as a choice. The redesign's softer 18px is now the only one.
        card: '18px',
        hero: '22px',
      },
      boxShadow: {
        card: '0 1px 2px rgba(16, 24, 40, 0.04), 0 1px 3px rgba(16, 24, 40, 0.06)',
        pop: '0 8px 24px -6px rgba(16, 24, 40, 0.12)',
        // The raised centre button in the bottom bar.
        lift: '0 6px 16px -4px rgba(5, 150, 105, 0.45)',
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
