import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

const here = dirname(fileURLToPath(import.meta.url))

export default defineConfig({
  plugins: [react()],
  root: here,
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: [resolve(here, 'src/test/setup.ts')],
    include: ['src/**/*.test.{ts,tsx}'],
  },
})
