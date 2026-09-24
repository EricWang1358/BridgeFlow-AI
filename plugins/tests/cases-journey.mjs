// Browser journey for the demo cases (data/mock_business/cases/cases.yaml). Offline, no
// model calls: each case opens in its own notebook from Sources → More sample cases, and
// shows the states it exists for — the core case several kinds of open item, the other
// case different ones named as review blockers, the clean case ready with nothing open.
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { randomBytes } from 'node:crypto'
import { mkdir, mkdtemp, readdir, readFile, stat, writeFile } from 'node:fs/promises'
import { createServer } from 'node:net'
import { tmpdir } from 'node:os'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from '@playwright/test'
import { assertClientModulesServed, resolveDsh, liveModelPatch } from './dsh.mjs'
import { switchLanguage } from './locale.mjs'

const live = process.env.BRIDGEFLOW_LIVE === '1'
const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const scratch = await mkdtemp(`${tmpdir()}/bridgeflow-cases-`)
const evidence = process.env.BRIDGEFLOW_EVIDENCE ?? `${scratch}/evidence`
await mkdir(evidence, { recursive: true })
const python = process.env.BRIDGEFLOW_PYTHON ?? resolve(root, '../.venv/bin/python')
async function port() { const s = createServer(); await new Promise(r => s.listen(0, '127.0.0.1', r)); const p = s.address().port; await new Promise(r => s.close(r)); return p }
const backendPort = await port(), webPort = await port()
const env = { ...process.env, PORTAL_BASE_URL: '', DSH_HOME: `${scratch}/dsh`, DSH_TOOLS_MODE: 'native',
  BRIDGEFLOW_SERVICE_TOKEN: randomBytes(32).toString('hex'), PYTHONPATH: `${root}/backend/src`, RESULT_STORE_PATH: `${scratch}/outputs`,
  MAPPING_MEMORY_PATH: `${scratch}/mappings.json`, FIELD_DICTIONARY_PATH: `${root}/data/mock_business/demo/dictionary.yaml`,
  WORKFLOW_CATALOGUE_PATH: `${root}/data/workflow_demo/catalogue.yaml`,
  LLM_PROVIDER: 'mock', BRIDGEFLOW_ENABLE_LEGACY_CONSOLE: 'false', BRIDGEFLOW_ALLOW_SAMPLE_DATA: 'false' }
const processes = []
let logs = '', browser, page
function start(command, args) {
  const child = spawn(command, args, { cwd: root, env, stdio: ['ignore', 'pipe', 'pipe'] })
  child.stdout.on('data', d => { logs += d }); child.stderr.on('data', d => { logs += d })
  processes.push(child); return child
}
const wait = ms => new Promise(r => setTimeout(r, ms))
const began = Date.now()
const approvals = [], questions = []
try {
  const patch = (await readFile(`${root}/dsh/enterprise.patch.yml`, 'utf8'))
    .replace("'../plugins/src/index.ts'", JSON.stringify(`${root}/plugins/src/index.ts`))
    .replace('./dsh/presets', `${root}/dsh/presets`)
    .replace('http://127.0.0.1:8000', `http://127.0.0.1:${backendPort}`)
    + (live ? liveModelPatch() : `\n- id: agent-default-model\n  name: '@deepseek-ai/dsh-agent-default-model'\n  config:\n    provider: bridgeflow-offline-test\n    model: offline\n- insert:\n    - id: scripted-test-model\n      name: ${JSON.stringify(`${root}/plugins/tests/fixtures/scripted-model/index.ts`)}\n`)
  await writeFile(`${scratch}/web.yml`, patch)
  start(python, ['-m', 'uvicorn', 'bridgeflow.api.main:app', '--host', '127.0.0.1', '--port', String(backendPort)])
  start(resolveDsh(), ['web', '--patch', `${scratch}/web.yml`, '--no-open', '--port', String(webPort)])
  let match
  for (const until = Date.now() + 30_000; Date.now() < until;) {
    match = logs.match(/dsh web: (http:\/\/127\.0\.0\.1:\d+\/\?token=[^\s)]+)/)
    if (match || processes.some(c => c.exitCode !== null)) break
    await wait(100)
  }
  assert(match, 'DSH did not become ready')
  await assertClientModulesServed(match[1])
  browser = await chromium.launch({ headless: true })
  page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, locale: 'en-US' })
  const errors = []
  page.on('pageerror', e => { errors.push(e.message); logs += '\nBROWSER: ' + e.message })
  page.setDefaultTimeout(live ? 240_000 : 30_000)
  await page.goto(match[1])
  await switchLanguage(page, 'English')
  const studio = page.getByRole('complementary', { name: 'Studio', exact: true })
  const board = () => page.evaluate(async () => (await (await fetch('/bridgeflow/workflow/board')).json()).rows)
  const refresh = () => page.locator('.bf-card-head').getByRole('button', { name: 'Refresh', exact: true }).click()
  // Arrivals ease in over ~200 ms; photograph the settled page, not the middle of a fade.
  const shot = async name => { await wait(450); await page.screenshot({ path: `${evidence}/${name}.png` }) }

  // Each case opens in its own notebook from Sources → More sample cases.
  const sources = page.getByRole('complementary', { name: 'Sources', exact: true })
  const results = {}
  for (const [id, expected] of [['core', 'needs_review'], ['other', 'needs_review'], ['clean', 'ready']]) {
    const more = sources.locator('.bf-sample-cases')
    if (!await more.evaluate(el => el.open)) await more.locator('summary').click()
    const previous = new URLSearchParams(new URL(page.url()).hash.slice(12)).get('batch')
    await more.locator(`button[data-case="${id}"]`).click()
    // Opening a case leaves the current notebook: the leave dialog asks first.
    const leave = page.getByRole('dialog', { name: /^(Save this notebook before leaving\?|离开前保存笔记本？)$/ })
    await leave.waitFor({ timeout: 3000 }).then(() => leave.getByRole('button', { name: /^(Discard and continue|不保存并继续)$/ }).click(), () => {})
    await page.waitForFunction(old => { const b = new URLSearchParams(location.hash.slice(12)).get('batch'); return !!b && b !== old && /[?&]view=tasks/.test(location.hash) }, previous)
    const chip = sources.locator('.bf-source-batch .bf-chip')
    await sources.locator(`.bf-source-batch .bf-chip[data-status="${expected}"]`).waitFor()
    const batch = new URLSearchParams(new URL(page.url()).hash.slice(12)).get('batch')
    const summary = await page.evaluate(async id => (await fetch(`/bridgeflow/batches/${id}`)).json(), batch)
    results[id] = { status: summary.status, blockers: summary.review_blockers, quarantined: summary.departments.reduce((n, d) => n + d.quarantined, 0),
      column_questions: summary.column_questions }
    await shot(`case-${id}`)
  }
  assert.equal(results.core.status, 'needs_review'); assert(results.core.quarantined >= 1)
  assert.equal(results.other.status, 'needs_review'); assert.equal(results.other.blockers.length, 3); assert.equal(results.other.column_questions, 1)
  assert.equal(results.clean.status, 'ready'); assert.deepEqual(results.clean.blockers, [])
  assert.deepEqual(errors, [])
  await writeFile(`${evidence}/cases.json`, JSON.stringify(results, null, 2))
  console.log(JSON.stringify({ status: 'passed', results, evidence }))
} catch (error) {
  if (page) await page.screenshot({ path: `${scratch}/failure.png` }).catch(() => {})
  console.error('Screenshot:', `${scratch}/failure.png`)
  console.error(logs.replace(/([?&]token=)[^\s)]+/g, '$1<redacted>').slice(-4000))
  throw error
} finally {
  await browser?.close()
  for (const child of processes) child.kill('SIGTERM')
}
