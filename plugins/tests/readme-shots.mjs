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
const scratch = await mkdtemp(`${tmpdir()}/bridgeflow-readme-`)
const evidence = resolve(root, 'docs/images')
await mkdir(evidence, { recursive: true })
async function port() { const s = createServer(); await new Promise(r => s.listen(0, '127.0.0.1', r)); const p = s.address().port; await new Promise(r => s.close(r)); return p }
const backendPort = await port(), webPort = await port()
const env = { ...process.env, DSH_HOME: `${scratch}/dsh`, DSH_TOOLS_MODE: 'native',
  BRIDGEFLOW_SERVICE_TOKEN: randomBytes(32).toString('hex'), PYTHONPATH: `${root}/backend/src`, RESULT_STORE_PATH: `${scratch}/outputs`,
  MAPPING_MEMORY_PATH: `${scratch}/mappings.json`, COLUMN_MATCH_PATH: `${scratch}/column-matches.json`,
  FIELD_DICTIONARY_PATH: `${root}/data/mock_business/demo/dictionary.yaml`, INTEGRATION_SPEC_PATH: `${root}/data/company_templates/integration.yaml`,
  LLM_PROVIDER: 'mock', BRIDGEFLOW_ENABLE_LEGACY_CONSOLE: 'false', BRIDGEFLOW_ALLOW_SAMPLE_DATA: 'false', WORKFLOW_CATALOGUE_PATH: `${root}/data/workflow_demo/catalogue.yaml`,
  DISCOVERY_SCORING_POLICY_PATH: `${root}/data/discovery_demo/scoring-policy.yaml`, DISCOVERY_DECISION_POLICY_PATH: `${root}/data/discovery_demo/decision-policy.yaml` }
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
  // README screenshots of the current product, taken in an isolated DSH_HOME (no model calls).
  const target = id => page.locator(`[data-tour-id="${id}"]:visible`)
  const shot = name => page.screenshot({ path: `${evidence}/${name}.png` })
  await page.goto(match[1])
  await page.locator('[data-tour-mode="welcome"] [data-tour-card]').waitFor()
  await shot('14-guided-tour')
  await page.locator('[data-tour-card]:visible').getByRole('button', { name: 'Maybe later', exact: true }).click()
  await page.waitForTimeout(400); await shot('01-notebook-empty')
  await target('sample').click()
  await page.locator('.bf-resource-list button').first().waitFor(); await page.waitForTimeout(800)
  await page.locator('.bf-resource-list button').first().click(); await page.waitForTimeout(1200)
  await shot('02-sample-sources')
  await target('source-provenance').click().catch(() => {}); await page.waitForTimeout(500)
  await shot('03-source-provenance')
  // #219: the combined table opens from the studio's Data destination.
  const studio = page.getByRole('complementary', { name: 'Studio', exact: true })
  await studio.getByRole('button', { name: /^.?Data/ }).first().click()
  await target('master-open').click(); await target('master-status').waitFor(); await page.waitForTimeout(600)
  await target('master-issues').click(); await page.waitForTimeout(400)
  await target('master-evidence-open').click(); await page.waitForTimeout(600)
  await shot('12-cross-department-master')
  await studio.locator('.bf-artifact[data-kind=master]').click()
  await page.locator('dialog[open]').waitFor(); await page.waitForTimeout(1200)
  await shot('04-batch-master-table')
  await page.keyboard.press('Escape'); await page.waitForTimeout(400)
  // The workflow with its sample loaded, so the flow strip shows where records sit.
  await studio.getByRole('button', { name: /Filling & handoff/ }).first().click()
  await page.getByRole('button', { name: 'Load the sample workflow', exact: true }).click()
  await page.getByRole('button', { name: 'Ask the captain to submit for approval', exact: true }).first().waitFor()
  await page.getByRole('button', { name: 'Load the sample discovery project', exact: true }).click()
  await page.getByRole('button', { name: 'Ask the captain to accept this scope', exact: true }).waitFor(); await page.waitForTimeout(800)
  await shot('13-workflow-handoff')
  // The overview reads the same sources as each page and links back to them.
  await studio.getByRole('button', { name: /^.?Overview/ }).first().click()
  await page.locator('.bf-ov-kpis .bf-ov-tile').first().waitFor()
  await studio.getByRole('button', { name: 'Expand preview', exact: true }).click()
  await page.locator('dialog[open] .bf-ov-spark, dialog[open] .bf-ov-bars').first().waitFor(); await page.waitForTimeout(1000)
  await shot('15-overview')
  assert.deepEqual(errors, [])
  console.log(JSON.stringify({ status: 'captured', out: evidence }))
} catch (error) { console.error(logs.slice(-3000)); throw error }
finally { await browser?.close(); for (const p of processes) p.kill('SIGTERM'); await Promise.all(processes.map(p => new Promise(r => { if (p.exitCode !== null) return r(); const timer = setTimeout(() => p.kill('SIGKILL'), 5000); p.once('exit', () => { clearTimeout(timer); r() }) }))) }
