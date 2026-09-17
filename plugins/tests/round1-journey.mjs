// Browser journey for round 1 of E13/E14 (issues 190, 195, 199): brief, evidence grades and self-check.
// Offline and isolated: own DSH_HOME, a scripted review through the host endpoints, no model calls.
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { randomBytes } from 'node:crypto'
import { mkdtemp, readFile, writeFile, mkdir } from 'node:fs/promises'
import { createServer } from 'node:net'
import { tmpdir } from 'node:os'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from '@playwright/test'
import { resolveDsh, assertClientModulesServed } from './dsh.mjs'
const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const scratch = await mkdtemp(`${tmpdir()}/bridgeflow-round1-`)
const evidence = resolve(root, 'docs/evidence/round1-e13-e14')
await mkdir(evidence, { recursive: true })
async function port() { const s = createServer(); await new Promise(r => s.listen(0, '127.0.0.1', r)); const p = s.address().port; await new Promise(r => s.close(r)); return p }
const backendPort = await port(), webPort = await port()
const env = { ...process.env, DSH_HOME: `${scratch}/dsh`, DSH_TOOLS_MODE: 'native',
  BRIDGEFLOW_SERVICE_TOKEN: randomBytes(32).toString('hex'), PYTHONPATH: `${root}/backend/src`, RESULT_STORE_PATH: `${scratch}/outputs`,
  MAPPING_MEMORY_PATH: `${scratch}/mappings.json`, COLUMN_MATCH_PATH: `${scratch}/column-matches.json`,
  FIELD_DICTIONARY_PATH: `${root}/data/mock_business/demo/dictionary.yaml`, INTEGRATION_SPEC_PATH: `${root}/data/company_templates/integration.yaml`,
  LLM_PROVIDER: 'mock', BRIDGEFLOW_ENABLE_LEGACY_CONSOLE: 'false', BRIDGEFLOW_ALLOW_SAMPLE_DATA: 'false', WORKFLOW_CATALOGUE_PATH: `${root}/data/workflow_demo/catalogue.yaml` }
const processes = []; let logs = '', browser, page
function start(cmd, args) { const p = spawn(cmd, args, { cwd: root, env, stdio: ['ignore', 'pipe', 'pipe'] }); p.stdout.on('data', d => { logs += d }); p.stderr.on('data', d => { logs += d }); processes.push(p); return p }
try {
  const patch = (await readFile(`${root}/dsh/enterprise.patch.yml`, 'utf8')).replace("'../plugins/src/index.ts'", JSON.stringify(`${root}/plugins/src/index.ts`)).replace('./dsh/presets', `${root}/dsh/presets`).replace('http://127.0.0.1:8000', `http://127.0.0.1:${backendPort}`)
    + `\n- id: agent-default-model\n  name: '@deepseek-ai/dsh-agent-default-model'\n  config:\n    provider: bridgeflow-offline-test\n    model: offline\n- insert:\n    - id: scripted-test-model\n      name: ${JSON.stringify(`${root}/plugins/tests/fixtures/scripted-model/index.ts`)}\n`
  await writeFile(`${scratch}/web.yml`, patch)
  start(process.env.BRIDGEFLOW_PYTHON ?? resolve(root, '../.venv/bin/python'), ['-m', 'uvicorn', 'bridgeflow.api.main:app', '--host', '127.0.0.1', '--port', String(backendPort)])
  start(resolveDsh(), ['web', '--patch', `${scratch}/web.yml`, '--no-open', '--port', String(webPort)])
  let match; const deadline = Date.now() + 30000
  while (!(match = logs.match(/dsh web: (http:\/\/127\.0\.0\.1:\d+\/\?token=[^\s)]+)/))) {
    if (Date.now() > deadline || processes.some(p => p.exitCode !== null)) throw new Error('Service not ready')
    await new Promise(r => setTimeout(r, 100))
  }
  await assertClientModulesServed(match[1])
  browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, locale: 'en-US', reducedMotion: 'reduce', locale: process.env.SHOT_LOCALE ?? 'en-US' })
  page = await context.newPage(); page.setDefaultTimeout(20000)
  const errors = [], prompts = []; let imports = 0, saves = 0
  page.on('pageerror', e => errors.push(e.message))
  page.on('request', request => { if (request.method() === 'POST' && request.url().endsWith('/bridgeflow/batches/demo')) imports++; if (request.method() === 'POST' && request.url().includes('/bridgeflow/notebook?')) saves++; if (request.postData()?.includes('session.prompt')) prompts.push(request.url()) })
  const target = id => page.locator(`[data-tour-id="${id}"]:visible`)
  const shot = name => page.screenshot({ path: `${evidence}/${name}.png` })
  const host = (path, body) => fetch(`http://127.0.0.1:${backendPort}${path}`, { method: 'POST',
    headers: { 'content-type': 'application/json', authorization: `Bearer ${env.BRIDGEFLOW_SERVICE_TOKEN}` }, body: JSON.stringify(body) }).then(async r => { assert.equal(r.status, 200, await r.clone().text()); return r.json() })
  const studio = name => page.locator('.bf-studio-tools button', { hasText: name }).first()
  await page.goto(match[1])
  await page.locator('[data-tour-mode="welcome"] [data-tour-card]').waitFor()
  await page.locator('[data-tour-card]:visible').getByRole('button', { name: 'Maybe later', exact: true }).click()

  // E13-UC01 AC-3: no saved review yet
  await target('sample').click()
  await page.locator('.bf-resource-list button').first().waitFor()
  const batch = new URLSearchParams(new URL(page.url()).hash.split('?')[1]).get('batch')
  assert.match(batch, /^[a-f0-9]{32}$/)
  await studio('This month').click()
  await page.getByText('No review yet', { exact: true }).waitFor()

  // A scripted review through the host tools, as test_business_mvp does (no model)
  const reviewContext = await host('/tools/review-context', { batch_id: batch })
  const runs = reviewContext.roles.map(p => ({ role: p.role, session_id: `child-${p.role}`, status: 'completed', judgement: { checks: p.checks.map(c => ({
    check_id: c.check_id, metric: c.metric, value: c.value, unit: c.unit, status: c.expected_status,
    action: c.actions[c.expected_status][0], explanation: '应按本部门权限核实并提交责任人复核。' })) } }))
  const report = await host('/tools/review-finalize', { batch_id: batch, parent_session_id: 'journey', runs })
  assert.equal(report.status, 'validated')

  // E13-UC01 AC-1 and E13-UC06: ordered attention items with grades
  await page.reload()
  await page.locator('.bf-brief').waitFor()
  const items = await page.locator('.bf-brief-attention > li .bf-check-title').allInnerTexts()
  assert.equal(items.length, 3)
  const grades = await page.locator('.bf-brief-attention .bf-check .bf-grade').allInnerTexts()
  assert.deepEqual(grades.slice().sort(), ['G2', 'G2', 'G3'])
  assert.equal(await page.locator('.bf-brief-attention .bf-grade[data-grade="G4"]').count(), 3)
  await shot('brief')

  // E13-UC06 in the master view: a selected cell shows its grade
  await target('master-open').click(); await target('master-status').waitFor()
  await target('master-evidence-open').click()
  await page.locator('.bf-cell-evidence .bf-grade').waitFor()
  await shot('master-grade')

  // E14-UC03: self-check in the import dialog, no batch created
  await page.locator('.bf-add-source').first().click()
  const dialog = page.locator('dialog[open]').last()
  await dialog.locator('input[name=period]').fill('2024-07')
  await dialog.locator('input[name=marketing]').setInputFiles(`${root}/data/mock_business/monthly/2024-07-模拟留出/市场部.xlsx`)
  await dialog.locator('input[name=finance]').setInputFiles(`${root}/data/mock_business/monthly/2024-07-模拟留出/财务部.xlsx`)
  await dialog.getByRole('button', { name: 'Check first', exact: true }).click()
  await dialog.locator('.bf-callout[data-tone="warn"]').filter({ hasText: '市场_可争取' }).waitFor()
  await dialog.locator('.bf-callout[data-tone="ok"]').filter({ hasText: 'Ready to submit' }).waitFor()
  await dialog.locator('.bf-callout[data-tone="warn"]').scrollIntoViewIfNeeded()
  await shot('self-check')
  assert.deepEqual(errors, [])
  console.log(JSON.stringify({ status: 'passed', batch, attention: items, evidence }))
} catch (error) { console.error(logs.slice(-3000)); await page?.screenshot({ path: `${evidence}/failure.png` }).catch(() => {}); throw error }
finally { await browser?.close(); for (const p of processes) p.kill('SIGTERM'); await Promise.all(processes.map(p => new Promise(r => { if (p.exitCode !== null) return r(); const timer = setTimeout(() => p.kill('SIGKILL'), 5000); p.once('exit', () => { clearTimeout(timer); r() }) }))) }
