import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'url'
import path from 'path'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const webRoot = path.resolve(__dirname, 'web')

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(webRoot, 'src'),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: [path.resolve(webRoot, 'src/test/setup.ts'), path.resolve(__dirname, 'vitest.setup.ts')],
    include: ['web/src/**/*.{test,spec}.{ts,tsx}'],
    exclude: [
      'node_modules/**',
      '.sst/**',
      'web/e2e/**',
      'web/dist/**',
    ],
    env: {
      VITE_SUPABASE_URL: 'https://test.supabase.co',
      VITE_SUPABASE_ANON_KEY: 'test-anon-key',
    },
  },
})
