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
const scratch = await mkdtemp(`${tmpdir()}/bridgeflow-guide-`)
const evidence = resolve(root, 'docs/evidence/guide')
await mkdir(evidence, { recursive: true })
async function port() { const s = createServer(); await new Promise(r => s.listen(0, '127.0.0.1', r)); const p = s.address().port; await new Promise(r => s.close(r)); return p }
const backendPort = await port(), webPort = await port()
const env = { ...process.env, PORTAL_BASE_URL: '', DSH_HOME: `${scratch}/dsh`, DSH_TOOLS_MODE: 'native',
  BRIDGEFLOW_SERVICE_TOKEN: randomBytes(32).toString('hex'), PYTHONPATH: `${root}/backend/src`, RESULT_STORE_PATH: `${scratch}/outputs`,
  MAPPING_MEMORY_PATH: `${scratch}/mappings.json`, COLUMN_MATCH_PATH: `${scratch}/column-matches.json`,
  FIELD_DICTIONARY_PATH: `${root}/data/mock_business/demo/dictionary.yaml`, INTEGRATION_SPEC_PATH: `${root}/data/company_templates/integration.yaml`,
  WORKFLOW_CATALOGUE_PATH: `${root}/data/workflow_demo/catalogue.yaml`,
  DISCOVERY_SCORING_POLICY_PATH: `${root}/data/discovery_demo/scoring-policy.yaml`, DISCOVERY_DECISION_POLICY_PATH: `${root}/data/discovery_demo/decision-policy.yaml`,
  LLM_PROVIDER: 'mock', BRIDGEFLOW_ENABLE_LEGACY_CONSOLE: 'false', BRIDGEFLOW_ALLOW_SAMPLE_DATA: 'false', BRIDGEFLOW_TEST_SCENARIO: 'guide' }
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
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, locale: 'en-US', reducedMotion: 'reduce' })
  page = await context.newPage(); page.setDefaultTimeout(20000)
  const errors = []; page.on('pageerror', e => errors.push(e.message))
  // The captain's "where is it" answer (app_guide): the clicks in the chat, the page opened once, never on replay.
  await page.goto(match[1])
  await page.locator('[data-tour-mode="welcome"] [data-tour-card]').waitFor()
  await page.locator('[data-tour-card]:visible').getByRole('button', { name: 'Maybe later', exact: true }).click()
  await page.locator('[data-tour-id="sample"]:visible').click()
  await page.locator('.bf-resource-list button').first().waitFor()
  const studio = page.getByRole('complementary', { name: 'Studio', exact: true })
  const discovery = studio.getByRole('button', { name: /Discovery materials and opportunities/ })
  const overview = studio.getByRole('button', { name: /^.?Overview/ }).first()
  await overview.click(); assert.equal(await discovery.getAttribute('aria-pressed'), 'false')
  const composer = page.locator('[contenteditable=true]').first()
  // The captain knows which notebook it is in: its context names the open notebook's batch.
  const sampleBatch = new URLSearchParams((await page.evaluate(() => location.hash)).slice(12)).get('batch')
  await composer.fill('Which batch is this notebook on?'); await composer.press('Enter')
  await page.getByText(`Notebook batch: ${sampleBatch}`).waitFor()
  await composer.fill('Where is it: quadrant_chart'); await composer.press('Enter')
  // A fresh answer opens the page by itself.
  await page.waitForFunction(() => location.hash.includes('view=discovery'))
  assert.equal(await discovery.getAttribute('aria-pressed'), 'true')
  await page.getByText('The steps are in the card above.').waitFor()
  // The card sits in DSH's folded tool-call group.
  const answer = page.getByRole('region', { name: 'Where to find it', exact: true }).last()
  const expand = async () => { await page.getByText(/^1 tool call$/).first().click(); await answer.waitFor() }
  await expand()
  assert.match(await answer.innerText(), /Rating quadrants/)
  await page.screenshot({ path: `${evidence}/guide-answer.png` })
  // Replayed from history it never moves the screen; the button still does.
  await overview.click(); await page.waitForFunction(() => location.hash.includes('view=overview'))
  await page.reload(); await page.getByText('The steps are in the card above.').waitFor(); await expand(); await page.waitForTimeout(1500)
  assert.ok((await page.evaluate(() => location.hash)).includes('view=overview'), 'a replayed answer must not navigate')
  await answer.getByRole('button', { name: 'Take me there', exact: true }).click()
  await page.waitForFunction(() => location.hash.includes('view=discovery'))
  // Open items say how they are settled, and a suggestion can be asked for one of them (the captain decides nothing).
  await studio.getByRole('button', { name: /This month.s tasks/ }).first().click()
  const inbox = page.getByRole('region', { name: 'Open items', exact: true })
  await inbox.getByText('How to settle:').first().waitFor()
  assert.match(await inbox.innerText(), /Replace one department’s file/)
  await inbox.getByRole('button', { name: 'Ask the captain for a suggestion', exact: true }).first().click()
  await inbox.getByText('Sent to the captain; the suggestion appears in the chat.').waitFor()
  await page.getByText(/Please suggest how to settle this open item: /).first().waitFor()
  await page.screenshot({ path: `${evidence}/settle-suggestion.png` })
  // The user guide is a page under Sessions & settings.
  await page.getByRole('button', { name: 'Sessions & settings', exact: true }).click()
  await page.getByRole('button', { name: /^Settings$/ }).first().click()
  await page.getByText('User guide', { exact: true }).first().click()
  await page.getByRole('heading', { name: 'BridgeFlow user guide' }).waitFor()
  await page.getByRole('heading', { name: 'Five minutes to your first result' }).waitFor()
  await page.screenshot({ path: `${evidence}/user-guide.png` })
  await page.keyboard.press('Escape')
  assert.deepEqual(errors, [])
  await writeFile(`${evidence}/checks.json`, JSON.stringify({ status: 'passed', mode: 'offline', model_calls: 0, cases: ['fresh-answer-opens-page', 'replay-does-not-navigate', 'button-opens-page', 'open-item-settle-guidance', 'ask-captain-for-suggestion', 'captain-knows-notebook-batch', 'user-guide-in-settings'] }, null, 2))
  console.log(JSON.stringify({ status: 'passed', artifacts: evidence, scratch }))
} catch (e) { if (page) { await page.screenshot({ path: `${scratch}/failure.png` }).catch(() => {}); console.error((await page.locator('body').innerText().catch(() => '')).slice(-3000)) } console.error('Artifacts:', scratch); console.error(logs.replace(/([?&]token=)[^\s)]+/g, '$1<redacted>').slice(-3000)); throw e }
finally { await browser?.close(); for (const p of processes) p.kill('SIGTERM'); await Promise.all(processes.map(p => new Promise(r => { if (p.exitCode !== null) return r(); const timer = setTimeout(() => p.kill('SIGKILL'), 5000); p.once('exit', () => { clearTimeout(timer); r() }) }))) }
