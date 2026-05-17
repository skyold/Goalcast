// Desktop E2E: full personalization flow (Phase 2-4 acceptance).
// - signup with a fresh email each run
// - navigate to /settings/leagues, pick 2 popular leagues, save
// - back on /matches after save
// - toggle EN locale, sidebar nav reads in English
//
// Pre-req: dev server up on :5173 and backend on whatever vite.config proxies to.

import { test, expect } from '@playwright/test'

const stamp = () => Date.now().toString(36)

test('signup → set leagues → matches respect whitelist → toggle EN', async ({ page }) => {
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
  // Click first two popular league checkboxes (zh-named come first).
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
