import { defineConfig, devices } from '@playwright/test'

/**
 * Browser tests against `vite preview` of a VITE_E2E build (exposes window.__hexmap), with the
 * API mocked in e2e/mocks.ts. Runs at 1440×900 and on an iPhone 14 viewport.
 *
 *   docker compose --profile test run --rm test-frontend-e2e
 *
 * Set CI_NETWORK=1 to load the real hosted basemap instead of a background-only stand-in.
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 45_000,
  expect: { timeout: 15_000 },
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: 'http://localhost:4173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } } },
    { name: 'phone', use: { ...devices['iPhone 14'], browserName: 'chromium' } },
  ],
  webServer: {
    command: 'npx vite build --mode e2e && npx vite preview --port 4173 --strictPort',
    url: 'http://localhost:4173',
    timeout: 180_000,
    reuseExistingServer: !process.env.CI,
  },
})
