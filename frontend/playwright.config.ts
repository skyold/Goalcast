// Playwright config for Goalcast E2E.
// - Desktop run: signup → set leagues → see filtered Matches list
// - Mobile run: 5-surface screenshot suite at iPhone 14 viewport (390x844)
//
// Run:   npx playwright test
// Heads: npx playwright test --headed
// One:   npx playwright test mobile

import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30_000,
  expect: { timeout: 5_000 },
  fullyParallel: false,            // signup tests must serialize on a shared DB.
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'desktop',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1400, height: 900 } },
      testMatch: /desktop\.spec\.ts$/,
    },
    {
      name: 'mobile',
      use: { ...devices['iPhone 14'] },
      testMatch: /mobile\.spec\.ts$/,
    },
  ],
})
