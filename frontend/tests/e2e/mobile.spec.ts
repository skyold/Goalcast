// Mobile screenshot suite at iPhone 14 viewport.
// Captures full-page screenshots into `test-results/` for manual review.
//
// Original 5 surfaces (Phase 1-4): dashboard / login / signup / matches / drawer.
// Phase 6 additions: mispricing list / league stats / alert settings + match detail
// (which embeds the time-series and H2H cards from Phase 1 + 5).

import { test, expect } from '@playwright/test'

test.describe('mobile (390x844) — core surfaces', () => {
  test('dashboard', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    await expect(page.getByRole('button', { name: /打开菜单|Open menu/ })).toBeVisible()
    await page.screenshot({ path: 'test-results/mobile-dashboard.png', fullPage: true })
  })

  test('login', async ({ page }) => {
    await page.goto('/login')
    await page.screenshot({ path: 'test-results/mobile-login.png', fullPage: true })
  })

  test('signup', async ({ page }) => {
    await page.goto('/signup')
    await page.screenshot({ path: 'test-results/mobile-signup.png', fullPage: true })
  })

  test('matches', async ({ page }) => {
    await page.goto('/matches')
    await page.waitForLoadState('networkidle')
    await page.screenshot({ path: 'test-results/mobile-matches.png', fullPage: true })
  })

  test('drawer opens on hamburger', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('button', { name: /打开菜单|Open menu/ }).click()
    await expect(page.locator('.sidebar.open')).toBeVisible()
    await page.screenshot({ path: 'test-results/mobile-drawer.png', fullPage: true })
  })
})


test.describe('mobile — analyst insights surfaces (Phase 1-5)', () => {
  test('mispricing list', async ({ page }) => {
    await page.goto('/insights/mispricing')
    await page.waitForLoadState('networkidle')
    await page.screenshot({ path: 'test-results/mobile-insights-mispricing.png', fullPage: true })
  })

  test('league stats — Serie A (499)', async ({ page }) => {
    await page.goto('/insights/leagues/499')
    await page.waitForLoadState('networkidle')
    await page.screenshot({ path: 'test-results/mobile-insights-league-stats.png', fullPage: true })
  })

  test('alert settings — anon shows must-login state', async ({ page }) => {
    await page.goto('/settings/alerts')
    await page.screenshot({ path: 'test-results/mobile-settings-alerts-anon.png', fullPage: true })
  })

  test('match detail — embeds timeseries + h2h cards', async ({ page }) => {
    // Use a recent known NS fixture id (verified in Phase 1 + 5 smoke tests).
    await page.goto('/matches/420493696')
    await page.waitForLoadState('networkidle')
    await page.screenshot({ path: 'test-results/mobile-match-detail.png', fullPage: true })
  })
})
