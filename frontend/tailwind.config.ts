import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // "Odds terminal" palette — amber signal on deep navy/black
        terminal: {
          bg: '#0a0a0f',
          surface: '#111118',
          border: '#1e1e2e',
          muted: '#2a2a3a',
        },
        signal: {
          amber: '#f59e0b',
          'amber-dim': '#78450a',
          green: '#10b981',
          red: '#ef4444',
          blue: '#3b82f6',
          purple: '#8b5cf6',
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
