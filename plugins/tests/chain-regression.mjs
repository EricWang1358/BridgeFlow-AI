import assert from 'node:assert/strict'
import { writeFile } from 'node:fs/promises'

/** Multiple user operations in one browser/session, never a fresh directory per click. */
export async function auditChain(page, root, scratch, report) {
  const results = []
  async function check(name, action) {
    try { await action(); results.push({ name, passed: true }) }
    catch (e) { results.push({ name, passed: false, error: String(e).slice(0, 700) }) }
  }
  const dialog = page.getByRole('dialog', {name:'BridgeFlow 数据工作区',exact:true})
  await page.evaluate(r => { location.hash = `bridgeflow?batch=${r.batch_id}&view=review&report=${r.report_id}` }, report)
  await dialog.getByRole('region', { name: '四部门研判报告' }).waitFor()
  await dialog.getByText('导入新批次', { exact: true }).click()
  await dialog.locator('input[name=period]').fill('2025-11')
  for (const role of ['production', 'procurement', 'finance', 'marketing']) await dialog.locator(`input[name=${role}]`).setInputFiles(`${root}/data/business_demo/balanced/${role}.csv`)
  await dialog.getByRole('button', { name: '导入并检查', exact: true }).click()
  await page.waitForFunction(old => document.querySelector('dialog code')?.textContent !== old, report.batch_id)
  const second = await dialog.locator('code').first().innerText()
  await check('import B after exact report A clears old report identity', async () => {
    await dialog.getByRole('button', { name: '四部门报告', exact: true }).click()
    await dialog.getByRole('alert').waitFor()
    assert.match(await dialog.getByRole('alert').innerText(), /尚无研判报告/)
    assert.equal(new URLSearchParams(new URL(page.url()).hash.slice(12)).get('batch'), second)
  })
  await dialog.getByRole('button', { name: '关闭', exact: true }).click()
  await page.getByRole('tab', { name: '业务状态', exact: true }).click()
  const state = page.getByRole('main', { name: '业务状态' })
  if (!await state.locator('.bf-document-evidence').evaluate(el => el.open)) await state.getByText('依据与归属', {exact:true}).click()
  await state.getByRole('textbox', { name: '批次编号' }).fill(second)
  await state.getByRole('button', { name: '打开', exact: true }).click()
  await state.locator('code').filter({ hasText: second }).waitFor()
  await check('refresh preserves the explicitly selected batch B', async () => {
    await state.getByRole('button', { name: '刷新', exact: true }).click()
    await page.waitForTimeout(400)
    assert.equal(await state.locator('code').first().innerText(), second)
  })
  await check('switching batch does not label captain A dispatches as batch B progress', async () => {
    await state.getByRole('textbox', { name: '批次编号' }).fill(second)
    await state.getByRole('button', { name: '打开', exact: true }).click()
    await state.locator('code').filter({ hasText: second }).waitFor()
    assert.match(await state.innerText(), /审批.*会话|会话.*审批/)
    assert(!/当前会话审计 · 4 Spawn/.test(await state.innerText()))
  })
  await check('bad batch link clears old batch content and does not spin forever', async () => {
    await page.evaluate(() => { location.hash = `bridgeflow?batch=${'f'.repeat(32)}&view=master` })
    await dialog.getByRole('alert').waitFor()
    assert.equal(await dialog.locator('code').count(), 0)
    assert(!/正在加载|批次已保存/.test(await dialog.innerText()))
  })
  await writeFile(`${scratch}/chain-audit.json`, JSON.stringify(results, null, 2))
  console.log(JSON.stringify({ chain: results, artifacts: scratch }))
  assert(results.every(r => r.passed), 'Cross-operation chain regressions failed')
}
