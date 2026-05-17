// Mobile screenshot suite: 5 core surfaces at iPhone 14 viewport.
// Captures full-page screenshots into `test-results/` for manual review and
// (if you wire Lighthouse CI later) for visual regression diffing.
//
// Surfaces covered: dashboard / login / signup / matches / drawer.

import { test, expect } from '@playwright/test'

test.describe('mobile (390x844) — 5-surface screenshots', () => {
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
