import assert from 'node:assert/strict'
import { writeFile } from 'node:fs/promises'

/** Multiple user operations in one browser/session, never a fresh directory per click. */
export async function auditChain(page, root, scratch, report) {
  const results = []
  async function check(name, action) {
    try { await action(); results.push({ name, passed: true }) }
    catch (e) { results.push({ name, passed: false, error: String(e).slice(0, 700) }) }
  }
  const dialog = page.getByRole('dialog', {name:'批次数据表',exact:true})
  await page.evaluate(r => { location.hash = `bridgeflow?batch=${r.batch_id}&view=review&report=${r.report_id}` }, report)
  await dialog.getByRole('region', { name: '四部门研判报告' }).waitFor()
  // #225: importing has one entry, the Sources pane. Leave report A's dialog first.
  await dialog.getByRole('button', { name: '关闭', exact: true }).click()
  const sources = page.getByRole('complementary', { name: '来源', exact: true })
  await sources.getByRole('button', { name: '＋ 添加来源', exact: true }).click()
  const importer = page.getByRole('dialog', { name: '添加来源', exact: true })
  await importer.locator('input[name=period]').fill('2025-11')
  for (const role of ['production', 'procurement', 'finance', 'marketing']) await importer.locator(`input[name=${role}]`).setInputFiles(`${root}/data/business_demo/balanced/${role}.csv`)
  await importer.getByRole('button', { name: '导入并检查', exact: true }).click()
  await page.waitForFunction(old => { const id = new URLSearchParams(location.hash.slice(12)).get('batch'); return !!id && id !== old }, report.batch_id)
  const second = new URLSearchParams(new URL(page.url()).hash.slice(12)).get('batch')
  await check('import B after exact report A clears old report identity', async () => {
    assert.equal(new URLSearchParams(new URL(page.url()).hash.slice(12)).get('report'), null)
    await page.evaluate(id => { location.hash = `bridgeflow?batch=${id}&view=review` }, second)
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
  await check('notebook purpose selects real workflows without hidden monthly requests', async () => {
    const purpose = page.getByRole('combobox', { name: '笔记本用途' })
    const business = page.locator('.bf-business-state')
    await purpose.selectOption('quotation')
    await business.getByRole('region', { name: '报价进度', exact: true }).waitFor()
    assert.equal(await state.count(), 0, 'Monthly workflow must unmount, not merely hide')
    const requests = []
    const record = request => {
      if (/\/bridgeflow\/batches\/[^/]+\/review(?:\?|$)/.test(request.url())) requests.push(request.url())
    }
    page.on('request', record)
    try {
      const loaded = page.waitForResponse(response => response.url().endsWith(`/bridgeflow/batches/${report.batch_id}`) && response.ok())
      await page.evaluate(id => { location.hash = `bridgeflow?batch=${id}&view=state&kind=quotation` }, report.batch_id)
      await loaded
      await page.waitForFunction(id => document.querySelector('.bf-source-batch code')?.textContent === id, report.batch_id)
      assert.deepEqual(requests, [], 'Quotation status must not fetch a hidden monthly report')
    } finally { page.off('request', record) }
    await purpose.selectOption('monthly')
    await state.getByRole('region', { name: '四部门研判报告' }).waitFor()
    assert.equal(await business.getByRole('region', { name: '报价进度', exact: true }).count(), 0)
    await purpose.selectOption('mixed')
    await business.getByRole('region', { name: '报价进度', exact: true }).waitFor()
    await state.getByRole('region', { name: '四部门研判报告' }).waitFor()
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
