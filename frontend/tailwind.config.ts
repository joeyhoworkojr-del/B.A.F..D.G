import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Sportsbook palette — deep near-black surfaces, sportsbook green, and
        // gold "odds" highlights. Token names are shared so every component
        // re-skins at once: terminal.* = surfaces, signal.amber = the gold
        // odds/active accent, signal.green = live/positive/brand green.
        terminal: {
          bg: '#0a0e12',
          surface: '#141a20',
          border: '#28313b',
          muted: '#1b232b',
        },
        signal: {
          amber: '#f5c518',       // odds gold / active highlight
          'amber-dim': '#3a3418',
          green: '#2fd07a',       // live / positive / brand green
          red: '#f2555a',
          blue: '#4f9cf5',
          purple: '#a855f7',
        },
        // Standard dark zinc scale: zinc-100 = primary near-white text,
        // descending to muted greys and dark surfaces.
        zinc: {
          50: '#0a0e12',
          100: '#f3f6f9',
          200: '#dbe2ea',
          300: '#b7c1cc',
          400: '#8b97a5',
          500: '#6d7885',
          600: '#525c68',
          700: '#3a434e',
          800: '#28313b',
          900: '#141a20',
        },
      },
      fontFamily: {
        display: ['"Space Grotesk"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
        body: ['Inter', 'sans-serif'],
      },
    },
  },
  plugins: [],
} satisfies Config
