import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // "Trading desk" palette — clean light surfaces, electric blue accent.
        // Token names are kept from the original dark theme so every
        // component re-skins at once: terminal.* = surfaces, signal.amber =
        // the primary accent (now blue).
        terminal: {
          bg: '#f6f8fb',
          surface: '#ffffff',
          border: '#e2e8f0',
          muted: '#eef2f7',
        },
        signal: {
          amber: '#2563eb',       // primary accent (electric blue)
          'amber-dim': '#dbeafe',
          green: '#16a34a',
          red: '#dc2626',
          blue: '#2563eb',
          purple: '#7c3aed',
        },
        // Inverted zinc scale: the app uses zinc-100 for primary text and
        // zinc-600 for faint text — remapped for light backgrounds.
        zinc: {
          50: '#f8fafc',
          100: '#0f172a',
          200: '#1e293b',
          300: '#334155',
          400: '#475569',
          500: '#64748b',
          600: '#94a3b8',
          700: '#cbd5e1',
          800: '#e2e8f0',
          900: '#f1f5f9',
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
