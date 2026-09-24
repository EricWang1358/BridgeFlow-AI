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
  for (const [id, expected, title] of [['core', 'needs_review', 'Many problems at once'], ['other', 'needs_review', 'A different set of problems'], ['clean', 'ready', 'All clear: ready to review']]) {
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
    const tasks = studio.locator('.bf-tasks')
    const guide = tasks.locator('.bf-demo-guide')
    await guide.getByRole('heading', { name: `This sample shows · ${title}` }).waitFor()
    const review = tasks.getByRole('button', { name: 'Start the review', exact: true })
    assert.equal(await review.isDisabled(), expected !== 'ready', `${id} review eligibility`)
    if (expected !== 'ready') await tasks.getByText('This batch needs data fixes before a review.', { exact: false }).waitFor()
    const summary = await page.evaluate(async id => (await fetch(`/bridgeflow/batches/${id}`)).json(), batch)
    const inbox = await page.evaluate(async id => (await fetch(`/bridgeflow/monthly/inbox?period=2024-07&batch_id=${id}`)).json(), batch)
    assert.equal(inbox.batch_id, batch)
    await page.waitForFunction(total => document.querySelector('.bf-inbox .bf-badge')?.textContent?.trim() === String(total), inbox.total)
    results[id] = { status: summary.status, blockers: summary.review_blockers, quarantined: summary.departments.reduce((n, d) => n + d.quarantined, 0),
      column_questions: summary.column_questions, batch_id: batch, open_items: inbox.total }
    await shot(`case-${id}`)
    await guide.getByRole('button', { name: 'Inspect data and open items' }).click()
    await studio.getByRole('region', { name: 'Data' }).waitFor()
  }
  assert.equal(results.core.status, 'needs_review'); assert(results.core.quarantined >= 1)
  assert.equal(results.other.status, 'needs_review'); assert.equal(results.other.blockers.length, 3); assert.equal(results.other.column_questions, 1)
  assert.equal(results.clean.status, 'ready'); assert.deepEqual(results.clean.blockers, [])
  const original = await page.evaluate(async id => (await (await fetch(`/bridgeflow/monthly/inbox?period=2024-07&batch_id=${id}`)).json()).total, results.core.batch_id)
  assert.equal(original, results.core.open_items, 'Later sample notebooks must not change the first notebook’s open items')
  await page.locator('.bf-shell-top').getByRole('button', { name: 'Notebooks', exact: true }).click()
  await page.getByRole('dialog', { name: 'Notebooks', exact: true }).getByRole('button', { name: /Many problems at once/ }).click()
  await page.waitForFunction(batch => new URLSearchParams(location.hash.slice(12)).get('batch') === batch
    && document.querySelector('.bf-notebook-title')?.value === 'Many problems at once', results.core.batch_id)
  await studio.locator('.bf-data').waitFor() // the notebook restores its last-read Data view
  await studio.getByRole('button', { name: /This month’s tasks/ }).first().click()
  await page.waitForFunction(({ batch, total }) => {
    const selected = new URLSearchParams(location.hash.slice(12)).get('batch')
    return selected === batch && document.querySelector('.bf-inbox .bf-badge')?.textContent?.trim() === String(total)
  }, { batch: results.core.batch_id, total: results.core.open_items })
  await switchLanguage(page, '中文')
  await page.locator('.bf-demo-guide').getByRole('heading', { name: /本示例展示.*多问题并发/ }).waitFor()
  assert.equal(await page.locator('.bf-tasks').getByRole('button', { name: '发起研判' }).isDisabled(), true)
  // The public guest console leaves AI off. A ready sample must not offer a model action
  // that can only produce the fixed guest notice; its data and guided paths remain usable.
  const guestPage = await browser.newPage({ viewport: { width: 1440, height: 1000 }, locale: 'en-US' })
  guestPage.on('pageerror', e => errors.push(e.message))
  await guestPage.route('**/bridgeflow/config', async route => {
    const response = await route.fetch()
    await route.fulfill({ response, json: { ...await response.json(), guestMode: true, guestLlm: false } })
  })
  await guestPage.goto(match[1])
  await switchLanguage(guestPage, 'English')
  const guestCases = guestPage.locator('.bf-sample-cases')
  await guestCases.locator('summary').click()
  await guestCases.locator('button[data-case="clean"]').click()
  const guestTasks = guestPage.locator('.bf-tasks')
  await guestTasks.getByText('AI review is off in this guest demo.', { exact: false }).waitFor()
  assert.equal(await guestTasks.getByRole('button', { name: 'Start the review' }).isDisabled(), true)
  await guestPage.screenshot({ path: `${evidence}/case-clean-guest.png` })
  await guestPage.close()
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
