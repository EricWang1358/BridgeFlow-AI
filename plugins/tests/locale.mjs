import assert from 'node:assert/strict'

/**
 * Language switching for the smoke suites (#110).
 *
 * Everything goes through the host's own surfaces: the native Settings dialog's
 * Language row (dsh-client-locale) is the only write entry, and the durable
 * preference then lives in the Host user-settings document — surviving reload,
 * notebook reopen and host restart is the host's job, we only verify it.
 */

/** A fresh browser profile without a saved preference must land in English. */
export async function assertDefaultEnglish(page) {
  await page.getByRole('complementary', { name: 'Sources', exact: true }).waitFor()
  await page.locator('body[data-tour-ready]').waitFor()
  const welcome = page.locator('[data-tour-mode="welcome"] [data-tour-card]')
  if (await welcome.isVisible()) await welcome.getByRole('button', {name:'Maybe later', exact:true}).click()
  assert.equal(await page.getByRole('complementary', { name: '来源', exact: true }).count(), 0,
    'A new user on a zh-CN browser must still default to English')
}

/** Switch via the native Settings → Language row. target: '中文' | 'English'. */
export async function switchLanguage(page, target) {
  await page.locator('body[data-tour-ready]').waitFor()
  const welcome = page.locator('[data-tour-mode="welcome"] [data-tour-card]')
  if (await welcome.isVisible()) await welcome.getByRole('button', {name:/^(Maybe later|稍后再说)$/}).click()
  // Native modality correctly blocks Settings behind a data workspace. Dismiss
  // that read-only workspace through its own control, never force-click through it.
  const workspace = page.getByRole('dialog', { name: /^BridgeFlow (数据工作区|data workspace)$/ })
  if (await workspace.isVisible()) await workspace.getByRole('button', { name: /^(关闭|Close)$/, exact: true }).click()
  const toggle = page.getByRole('button', { name: /^(Sessions & settings|会话与设置)$/, exact: true })
  if (await toggle.getAttribute('aria-expanded') !== 'true') await toggle.click()
  const sidebar = page.locator('[data-slot="sidebar"]')
  await sidebar.getByRole('button', { name: /^(Settings|设置)$/, exact: true }).click()
  const dialog = page.getByRole('dialog', { name: /^(Settings|设置)$/ })
  // The selector pill's accessible name is the active language's own label.
  const pill = dialog.getByRole('button', { name: /^(English|中文)$/, exact: true })
  if (!(await pill.count())) {
    await dialog.getByRole('button', { name: /^(General settings|通用设置)$/ }).click()
  }
  await pill.click()
  await page.getByRole('menuitem', { name: target, exact: true }).click()
  await page.keyboard.press('Escape')
  const expected = target === '中文' ? '来源' : 'Sources'
  await page.getByRole('complementary', { name: expected, exact: true }).waitFor()
}
