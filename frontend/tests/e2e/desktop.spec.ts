// Desktop E2E: full personalization flow (Phase 2-4 acceptance).
// - signup with a fresh email each run
// - navigate to /settings/leagues, pick 2 popular leagues, save
// - back on /matches after save
// - toggle EN locale, sidebar nav reads in English
//
// Pre-req: dev server up on :5173 and backend on whatever vite.config proxies to.

import { test, expect } from '@playwright/test'

const stamp = () => Date.now().toString(36)

// Playwright defaults `navigator.language` to en-US in headless Chromium, so
// the app's detect() lands on 'en' on a fresh visit. We force zh by setting
// localStorage before any page navigation so the rest of the test can assume
// Chinese-language selectors.
async function forceZh(page: import('@playwright/test').Page) {
  await page.addInitScript(() => {
    try { window.localStorage.setItem('goalcast-locale', 'zh') } catch {}
  })
}

test('signup → set leagues → matches respect whitelist → toggle EN', async ({ page }) => {
  await forceZh(page)
  const email = `e2e+desktop-${stamp()}@goalcast.dev`
  const password = 'desktop-test-pwd-1'

  // 1. Sign up
  await page.goto('/signup')
  await page.getByLabel('邮箱').fill(email)
  await page.getByLabel('密码').fill(password)
  await page.getByRole('button', { name: /^注册$/ }).click()
  await expect(page).toHaveURL('/')
  await expect(page.getByText(email)).toBeVisible()

  // 2. Manage leagues
  await page.getByRole('link', { name: '我的联赛' }).click()
  await expect(page).toHaveURL('/settings/leagues')
  const popular = page.locator('.card').filter({ hasText: '主流联赛' }).locator('.league-chk')
  await popular.nth(0).click()
  await popular.nth(1).click()
  await page.getByRole('button', { name: /^保存/ }).click()
  await expect(page).toHaveURL('/matches')

  // 3. Toggle EN and confirm nav text changes.
  await page.getByRole('button', { name: 'EN' }).click()
  await expect(page.getByRole('link', { name: 'Overview' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Matches' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'My leagues' })).toBeVisible()
})


// Phase 6 — analyst insights surfaces.
test('signup → mispricing list → league stats → alert settings + scan', async ({ page }) => {
  await forceZh(page)
  const email = `e2e+insights-${stamp()}@goalcast.dev`
  const password = 'insights-test-1'

  await page.goto('/signup')
  await page.getByLabel('邮箱').fill(email)
  await page.getByLabel('密码').fill(password)
  await page.getByRole('button', { name: /^注册$/ }).click()
  await expect(page).toHaveURL('/')

  // 1. Mispricings page from sidebar
  await page.getByRole('link', { name: '错定价' }).click()
  await expect(page).toHaveURL('/insights/mispricing')
  await expect(page.getByRole('button', { name: '≥ 5%' })).toBeVisible()
  await page.screenshot({ path: 'test-results/desktop-insights-mispricing.png', fullPage: true })

  // 2. League stats — deep link to Serie A (499)
  await page.goto('/insights/leagues/499')
  await page.waitForLoadState('networkidle')
  await expect(page.getByText('联赛画像')).toBeVisible()
  await expect(page.getByText('已结束场次')).toBeVisible()
  await page.screenshot({ path: 'test-results/desktop-insights-league-stats.png', fullPage: true })

  // 3. Alerts settings — threshold slider + manual scan
  await page.getByRole('link', { name: '提醒设置' }).click()
  await expect(page).toHaveURL('/settings/alerts')
  await expect(page.getByText('分歧告警设置')).toBeVisible()
  await page.getByRole('button', { name: /立即扫描/ }).click()
  await page.screenshot({ path: 'test-results/desktop-insights-settings-alerts.png', fullPage: true })
})
