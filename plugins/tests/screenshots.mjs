/**
 * Photograph the real UI.
 *
 * Not an assertion suite — `web-smoke.mjs` owns the behaviour. This exists because
 * design questions cannot be answered by reading source: the closed data panel
 * leaking onto the shell, and the Master Table wrapping its headers one character
 * per line, were both invisible in review and obvious in a screenshot.
 *
 * It boots the same composition the enterprise patch describes, imports a batch that
 * matches the example field dictionary, and captures each surface in both themes.
 *
 *   source env.sh && node plugins/tests/screenshots.mjs /tmp/bridgeflow-ui
 *
 * The model is the offline scripted fixture, so nothing here is billed.
 */
import { spawn } from 'node:child_process'
import { randomBytes } from 'node:crypto'
import { readFile, writeFile, mkdir } from 'node:fs/promises'
import { createServer } from 'node:net'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from '@playwright/test'
import { assertClientModulesServed, browserOptions, resolveDsh } from './dsh.mjs'
import { switchLanguage } from './locale.mjs'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const out = process.argv[2] ?? '/tmp/bfshot/before'
await mkdir(out, { recursive: true })
const python = process.env.BRIDGEFLOW_PYTHON ?? resolve(root, '../.venv/bin/python')
async function port() {
  const s = createServer(); await new Promise(r => s.listen(0, '127.0.0.1', r))
  const p = s.address().port; await new Promise(r => s.close(r)); return p
}
const backendPort = await port(), webPort = await port()
const env = { ...process.env, DSH_HOME: process.env.DSH_HOME, DSH_TOOLS_MODE: 'native',
  BRIDGEFLOW_SERVICE_TOKEN: randomBytes(32).toString('hex'),
  PYTHONPATH: `${root}/backend/src`, RESULT_STORE_PATH: '/tmp/bfshot/outputs',
  MAPPING_MEMORY_PATH: '/tmp/bfshot/mappings.json',
  FIELD_DICTIONARY_PATH: `${root}/data/mappings/field-dictionary.example.yaml`,
  LLM_PROVIDER: 'mock', BRIDGEFLOW_ENABLE_LEGACY_CONSOLE: 'false', BRIDGEFLOW_ALLOW_SAMPLE_DATA: 'false' }
let logs = ''
const kids = []
function start(cmd, args) {
  const c = spawn(cmd, args, { cwd: root, env, stdio: ['ignore','pipe','pipe'] })
  c.stdout.on('data', d => logs += d); c.stderr.on('data', d => logs += d); kids.push(c); return c
}
let browser
try {
  const patch = (await readFile(`${root}/dsh/enterprise.patch.yml`, 'utf8'))
    .replace("'../plugins/src/index.ts'", JSON.stringify(`${root}/plugins/src/index.ts`))
    .replace('./dsh/presets', `${root}/dsh/presets`)
    .replace('http://127.0.0.1:8000', `http://127.0.0.1:${backendPort}`)
    + `\n- id: agent-default-model\n  name: '@deepseek-ai/dsh-agent-default-model'\n  config:\n    provider: bridgeflow-offline-test\n    model: offline\n- insert:\n    - id: scripted-test-model\n      name: ${JSON.stringify(`${root}/plugins/tests/fixtures/scripted-model/index.ts`)}\n`
  await writeFile('/tmp/bfshot/web.yml', patch)
  start(python, ['-m','uvicorn','bridgeflow.api.main:app','--host','127.0.0.1','--port',String(backendPort)])
  start(resolveDsh(), ['web','--patch','/tmp/bfshot/web.yml','--no-open','--port',String(webPort)])
  const deadline = Date.now() + 60000
  let m
  while (Date.now() < deadline) {
    m = logs.match(/dsh web: (http:\/\/127\.0\.0\.1:\d+\/\?token=[^\s)]+)/)
    if (m) break
    if (kids.some(k => k.exitCode !== null)) throw new Error('exited early:\n' + logs.slice(-3000))
    await new Promise(r => setTimeout(r, 150))
  }
  if (!m) throw new Error('not ready:\n' + logs.slice(-3000))
  await assertClientModulesServed(m[1])
  browser = await chromium.launch(browserOptions())
  const page = await browser.newPage({ viewport: { width: 1440, height: 950 }, locale: 'zh-CN' })
  page.on('console', x => { if (x.type() === 'error') logs += '\nCONSOLE: ' + x.text() })
  page.on('pageerror', e => logs += '\nPAGEERROR: ' + e.message)
  page.setDefaultTimeout(30000)
  await page.goto(m[1])
  // #110: new profiles default to English even on a zh-CN browser; the captures
  // below assert Chinese copy, so switch explicitly through the native settings.
  await switchLanguage(page, '中文')
  await page.waitForTimeout(3000)
  await page.screenshot({ path: `${out}/01-shell.png`, fullPage: false })
  console.log('shell captured')
  await page.getByRole('button', { name: '导入与数据', exact: true }).click({ timeout: 30000 })
  await page.waitForTimeout(800)
  await page.screenshot({ path: `${out}/02-workspace-empty.png`, fullPage: false })
  await page.locator('input[name=period]').fill('2025-11')
  await page.locator('input[name=production]').setInputFiles({ name: 'production.csv', mimeType: 'text/csv',
    buffer: Buffer.from('sku,line,output_qty,capacity_hrs\nSKU-A1,Line 2,1200,180\nSKU-B7,Line 1,980,150\nSKU-A1,Line 2,450,90\nSKU-C3,Line 3,,120\n') })
  await page.locator('input[name=procurement]').setInputFiles({ name: 'procurement.csv', mimeType: 'text/csv',
    buffer: Buffer.from('material,unit_price,qty\nRM-ALU-6061,"S$ 12.50",4000\nRM-STEEL-304,8.10,2200\nRM-ALU-6061,13.20,1100\n') })
  await page.locator('input[name=finance]').setInputFiles({ name: 'finance.csv', mimeType: 'text/csv',
    buffer: Buffer.from('gl_account,customer,amount,ar_days\n4000-SALES-A1,Acme Pte Ltd,88400,130\n5000-COGS,Acme Pte Ltd,-76700,\n4000-SALES-A1,Cedar Works,11700,95\n') })
  await page.locator('input[name=marketing]').setInputFiles({ name: 'marketing.csv', mimeType: 'text/csv',
    buffer: Buffer.from('customer,product,order_qty,quoted_price\nAcme Pte Ltd,SKU-A1,3200,26.50\nCedar Works,SKU-B7,120,31.00\nacme pte. ltd.,sku a1,400,25.90\n') })
  await page.getByRole('button', { name: '导入并检查', exact: true }).click()
  await page.waitForTimeout(2500)
  await page.screenshot({ path: `${out}/03-workspace-imported.png`, fullPage: true })
  // The same screen in the other theme: every colour resolves through one token set,
  // so this is the check that the swap is complete rather than approximately right.
  await page.emulateMedia({ colorScheme: 'light' })
  await page.evaluate(() => document.body.removeAttribute('data-ds-dark-theme'))
  await page.waitForTimeout(400)
  await page.screenshot({ path: `${out}/03b-light.png`, fullPage: false })
  await page.evaluate(() => document.body.setAttribute('data-ds-dark-theme', ''))
  await page.emulateMedia({ colorScheme: 'dark' })
  for (const tab of ['清洗记录','待确认映射','隔离行','四部门报告']) {
    try { await page.getByRole('button', { name: tab, exact: true }).click({ timeout: 4000 }); await page.waitForTimeout(700)
      await page.screenshot({ path: `${out}/04-${tab}.png`, fullPage: true }) } catch { logs += `\n(no tab ${tab})` }
  }
  // The approval composer takeover — the human-in-the-loop centrepiece.
  //
  // Best effort: whether the offline fixture reaches `confirm_mapping` depends on
  // session state this script does not control, so a miss prints and continues
  // rather than failing the run. `web-smoke.mjs` is the authority on this flow and
  // captures the same frames — see #97 for why it currently does not run.
  try {
    await page.getByRole('button', { name: '关闭', exact: true }).click()
    // A session has to be chosen before the composer is live; without this the fill
    // lands on the inert no-session composer and nothing is ever asked.
    await page.getByRole('button', { name: /^(Choose workspace|选择工作区)$/ }).click({ timeout: 15000 })
    await page.getByRole('menuitem').first().click()

    const composer = page.locator('[contenteditable=true]').first()
    await composer.fill('Exercise the approved mapping fixture.')
    await composer.press('Enter')
    await page.getByRole('button', { name: /^(允许一次|Allow once)$/ }).waitFor({ timeout: 40000 })
    await page.getByRole('textbox', { name: '拒绝理由', exact: true }).fill('客户编码未核实，请销售负责人确认后再提交。')
    await page.waitForTimeout(400)
    await page.screenshot({ path: `${out}/05-approval.png`, fullPage: false })
    await page.getByRole('button', { name: /^(允许一次|Allow once)$/ }).click()
    await page.waitForTimeout(4000)
    await page.screenshot({ path: `${out}/06-toolcards.png`, fullPage: false })
  } catch (e) { console.error('approval capture failed:', e.message.slice(0, 400)) }
  await page.getByRole('button', { name: '导入与数据', exact: true }).click().catch(() => {})
  await page.waitForTimeout(1200)
  // The panel must be able to start the review itself. Copy/close/paste was three
  // steps of clerical work, and the request names a batch id — a stale paste
  // reviews last month.
  try {
    await page.getByRole('button', { name: '发起研判', exact: true }).click({ timeout: 8000 })
    await page.waitForTimeout(2500)
    const sent = await page.getByText(/review_context/).count()
    console.log('start-review delivered into the conversation:', sent > 0)
    await page.screenshot({ path: `${out}/07-started.png`, fullPage: false })
  } catch (e) { console.error('start-review failed:', e.message.slice(0, 200)) }

  console.log('done: ' + out)
} catch (e) {
  console.error('FAILED', e.message)
  console.error(logs.replace(/([?&]token=)[^\s)]+/g,'$1<redacted>').slice(-4000))
} finally {
  await browser?.close()
  for (const k of kids) k.kill('SIGTERM')
  await new Promise(r => setTimeout(r, 1200))
  for (const k of kids) if (k.exitCode === null) k.kill('SIGKILL')
}
