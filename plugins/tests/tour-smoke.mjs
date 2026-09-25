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
const scratch = await mkdtemp(`${tmpdir()}/bridgeflow-tour-`)
const evidence = resolve(root, 'docs/evidence/onboarding')
await mkdir(evidence, { recursive: true })
async function port() { const s = createServer(); await new Promise(r => s.listen(0, '127.0.0.1', r)); const p = s.address().port; await new Promise(r => s.close(r)); return p }
const backendPort = await port(), webPort = await port()
const env = { ...process.env, PORTAL_BASE_URL: '', DSH_HOME: `${scratch}/dsh`, DSH_TOOLS_MODE: 'native',
  BRIDGEFLOW_SERVICE_TOKEN: randomBytes(32).toString('hex'), PYTHONPATH: `${root}/backend/src`, RESULT_STORE_PATH: `${scratch}/outputs`,
  MAPPING_MEMORY_PATH: `${scratch}/mappings.json`, COLUMN_MATCH_PATH: `${scratch}/column-matches.json`,
  FIELD_DICTIONARY_PATH: `${root}/data/mock_business/demo/dictionary.yaml`, INTEGRATION_SPEC_PATH: `${root}/data/company_templates/integration.yaml`,
  WORKFLOW_CATALOGUE_PATH: `${root}/data/workflow_demo/catalogue.yaml`,
  DISCOVERY_SCORING_POLICY_PATH: `${root}/data/discovery_demo/scoring-policy.yaml`, DISCOVERY_DECISION_POLICY_PATH: `${root}/data/discovery_demo/decision-policy.yaml`,
  LLM_PROVIDER: 'mock', BRIDGEFLOW_ENABLE_LEGACY_CONSOLE: 'false', BRIDGEFLOW_ALLOW_SAMPLE_DATA: 'false' }
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
  const errors = [], prompts = []; let imports = 0, saves = 0
  page.on('pageerror', e => errors.push(e.message))
  page.on('request', request => { if (request.method() === 'POST' && request.url().endsWith('/bridgeflow/batches/demo')) imports++; if (request.method() === 'POST' && request.url().includes('/bridgeflow/notebook?')) saves++; if (request.postData()?.includes('session.prompt')) prompts.push(request.url()) })
  const card = () => page.locator('[data-tour-card]:visible')
  const target = id => page.locator(`[data-tour-id="${id}"]:visible`)
  async function step(id) { await page.locator(`[data-tour-step="${id}"] [data-tour-card]`).waitFor(); await page.locator('.bf-tour-ring').waitFor() }
  async function help() { await target('help').click(); await page.locator('[data-tour-mode="help"] [data-tour-card]').waitFor() }
  await page.goto(match[1])
  await page.locator('[data-tour-mode="welcome"] [data-tour-card]').waitFor()
  await page.screenshot({ path: `${evidence}/welcome.png` })
  await card().getByRole('button', { name: 'Maybe later', exact: true }).click()
  await page.reload(); await page.locator('body[data-tour-ready]').waitFor()
  assert.equal(await card().count(), 0)
  await help(); await card().getByRole('button', { name: 'First task · combine & verify', exact: true }).click()
  await step('sample')
  assert.equal(await card().getByRole('button', { name: 'Next', exact: true }).isDisabled(), true)
  // A failed import must not advance the operation step.
  await page.route('**/bridgeflow/batches/demo', async route => { await route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'Synthetic import failure; retry' }) }); await page.unroute('**/bridgeflow/batches/demo') })
  await target('sample').click(); await page.getByRole('alert').filter({ hasText: 'Synthetic import failure' }).first().waitFor()
  assert.equal(await page.locator('[data-tour-step="sample"]').count(), 1)
  await target('sample').click(); await step('master')
  const batch = new URLSearchParams(new URL(page.url()).hash.split('?')[1]).get('batch')
  let releaseMaster
  const release = new Promise(r => { releaseMaster = r })
  const requested = page.waitForRequest('**/bridgeflow/integration/batches/*')
  await page.route('**/bridgeflow/integration/batches/*', async route => {
    await release
    await route.fulfill({status:403, contentType:'application/json',body:JSON.stringify({detail:'Injected access denial'})})
    await page.unroute('**/bridgeflow/integration/batches/*')
  })
  await target('master-open').click(); await requested
  assert.equal(await page.locator('[data-tour-step="master"]').count(),1)
  assert.equal(await card().getByRole('button',{name:'Next',exact:true}).isDisabled(),true)
  releaseMaster(); await page.getByRole('alert').filter({hasText:'Injected access denial'}).first().waitFor()
  assert.equal(await page.locator('[data-tour-step="master"]').count(),1)
  await page.locator('[data-tour-recovery]:visible').click(); await step('result')
  await page.screenshot({ path: `${evidence}/master.png` })
  await card().getByRole('button', { name: 'Back', exact: true }).click(); await step('master')
  const importsBefore = imports
  await card().getByRole('button', { name: 'Next', exact: true }).click(); await step('result')
  assert.equal(imports, importsBefore)
  await page.keyboard.press('Escape'); assert.equal(await card().count(), 0)
  await page.reload(); await page.locator('body[data-tour-ready]').waitFor(); assert.equal(await card().count(), 0)
  await help(); await card().getByRole('button', { name: 'Continue tour', exact: true }).click(); await step('result')
  await card().getByRole('button', { name: 'Next', exact: true }).click(); await step('issues')
  await target('master-issues').click(); await step('questionResult'); await card().getByRole('button', { name: 'Next', exact: true }).click(); await step('evidence')
  await target('master-evidence-open').click(); await step('source')
  await page.screenshot({ path: `${evidence}/evidence.png` })
  await target('evidence-source').click(); await step('sourceDetails')
  await target('source-details').click(); await step('sourceVerified'); await card().getByRole('button', { name: 'Next', exact: true }).click(); await step('download')
  // Download and rename are optional: Next is open before either happens (a download still advances by itself).
  assert.equal(await card().getByRole('button', { name: 'Next', exact: true }).isEnabled(), true)
  const download = page.waitForEvent('download'); await target('master-download').click(); await download; await step('named')
  assert.equal(await card().getByRole('button', { name: 'Next', exact: true }).isEnabled(), true)
  await target('notebook-name').fill('Guided monthly review'); await target('notebook-name').press('Tab'); await step('saved')
  await page.route('**/bridgeflow/notebook?*', async route => {
    if (route.request().method() !== 'POST') return route.continue()
    await route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({error:'Injected persistence failure'}) }); await page.unroute('**/bridgeflow/notebook?*')
  })
  await target('notebook-save').click(); await page.getByRole('alert').first().waitFor()
  assert.equal(await page.locator('[data-tour-step="saved"]').count(), 1)
  assert.equal(await page.locator('[data-tour-mode="complete"]').count(), 0)
  await target('notebook-save').click(); await page.locator('[data-tour-mode="complete"] [data-tour-card]').waitFor()
  await page.screenshot({ path: `${evidence}/complete.png` })
  await page.reload(); await page.locator('body[data-tour-ready]').waitFor()
  assert.equal(await card().count(), 0)
  await help(); await card().getByText('This tour is complete.', {exact:false}).waitFor()
  const count = imports, saved = saves
  await card().getByRole('button', { name: 'First task · combine & verify', exact: true }).click(); await step('sample')
  assert.equal(imports, count); assert.equal(saves, saved)
  await card().getByRole('button', { name:'Next',exact:true }).click(); await step('master')
  await target('master-open').click(); await step('result')
  const cdp = await context.newCDPSession(page)
  await cdp.send('Emulation.setPageScaleFactor',{pageScaleFactor:1.25})
  await page.waitForFunction(() => {
    const card=document.querySelector('[data-tour-card]'), vv=visualViewport
    if (!card || !vv) return false
    const r=card.getBoundingClientRect()
    return r.right <= vv.offsetLeft+vv.width+1 && r.bottom <= vv.offsetTop+vv.height+1
  })
  await cdp.send('Emulation.setPageScaleFactor',{pageScaleFactor:1}); await cdp.detach()
  // Deliberate DOM loss tests the same waiting path as a delayed/removed control.
  await target('master-status').evaluate(el => { el.dataset.tourId = 'test-missing-status' })
  await card().getByText('This step is not available yet', {exact:true}).waitFor()
  assert.equal(await card().getByRole('button',{name:'Next',exact:true}).isDisabled(),true)
  await card().getByRole('button',{name:'Retry locating',exact:true}).click()
  await page.locator('[data-tour-id="test-missing-status"]').evaluate(el => { el.dataset.tourId = 'master-status' })
  await step('result')
  await page.setViewportSize({width:390,height:844}); await step('result')
  async function withinViewport() {
    const box = await card().boundingBox(), size = page.viewportSize()
    assert(box.x >= 0 && box.y >= 0 && box.x + box.width <= size.width + 1 && box.y + box.height <= size.height + 1, JSON.stringify(box))
  }
  await withinViewport(); await page.screenshot({path:`${evidence}/mobile.png`})
  await card().getByRole('button',{name:'Next',exact:true}).click(); await step('issues'); await withinViewport()
  await target('master-issues').click(); await step('questionResult'); await withinViewport()
  await page.keyboard.press('Escape')
  await page.setViewportSize({width:1440,height:1000})
  // A real unsaved-edit dialog remains usable inside the tour's focus boundary.
  await target('notebook-name').fill('Unsaved demonstration draft'); await target('notebook-name').press('Tab')
  await help(); await card().getByRole('button',{name:'First task · combine & verify',exact:true}).click(); await step('sample')
  await target('sample').click()
  const confirm = page.locator('dialog[data-tour-surface="confirm"][open]')
  await confirm.waitFor(); await confirm.getByRole('button',{name:'Cancel, keep editing',exact:true}).click(); await step('sample')
  assert.equal(imports,count)
  await page.keyboard.press('Escape')
  await target('notebook-name').fill('Guided monthly review'); await target('notebook-name').press('Tab')
  await help(); await card().getByRole('button',{name:'Explore · quotation workspace',exact:true}).click(); await step('quoteOpen')
  await target('quotation-open').click(); await step('quoteScope')
  await card().getByRole('button',{name:'Finish tour',exact:true}).click(); await page.locator('[data-tour-mode="complete"] [data-tour-card]').waitFor()
  await page.keyboard.press('Escape')
  await help(); await card().getByRole('button',{name:'Explore · department review',exact:true}).click(); await step('reviewIntro')
  await card().getByRole('button',{name:'Next',exact:true}).click(); await step('reviewState')
  await card().getByRole('button',{name:'Next',exact:true}).click(); await step('reviewHistory')
  await card().getByRole('button',{name:'Finish tour',exact:true}).click()
  await page.keyboard.press('Escape')
  // From an idea to a handoff (#143 → workflow): each action step waits for the real result.
  const next = () => card().getByRole('button',{name:'Next',exact:true}).click()
  await help(); await card().getByRole('button',{name:'Explore · from an idea to a handoff between departments',exact:true}).click(); await step('wfSample')
  await target('discovery-sample').click(); await step('wfGraph')
  await page.locator('[data-tour-id="flow-diagram"] g path').first().waitFor()
  await page.screenshot({ path: `${evidence}/workflow-graph.png` })
  await next(); await step('wfScore')
  await target('discovery-kind-score').click(); await step('wfQuadrant')
  await page.locator('[data-tour-id="quadrant-chart"] .bf-quadrant-dot').first().waitFor()
  assert.match(await target('quadrant-chart').locator('.bf-quadrant-name').first().textContent(), /生产数据标准化后自动/)
  const chartBox = await target('quadrant-chart').boundingBox()
  assert(chartBox && chartBox.y >= 0 && chartBox.y + chartBox.height <= page.viewportSize().height,
    `Tour must bring the whole quadrant chart into view: ${JSON.stringify(chartBox)}`)
  await page.screenshot({ path: `${evidence}/workflow-quadrant.png` })
  await next(); await step('wfScope')
  assert.match(await target('workflow-scope').innerText(), /demo-handoff/)
  await next(); await step('wfRecords')
  await target('workflow-sample').click(); await page.locator('[data-tour-step="wfFlow"] [data-tour-card]').waitFor()
  await page.locator('.bf-pipeline > li[data-active=true]').nth(1).waitFor()  // the board refreshes after the load
  await page.screenshot({ path: `${evidence}/workflow-flow.png` })
  await next(); await step('wfTimeline')
  await target('workflow-timeline').click(); await step('wfOverview')
  await card().getByRole('button',{name:'Finish tour',exact:true}).click()
  await page.locator('[data-tour-mode="complete"] [data-tour-card]').getByText('You have followed an idea all the way to a handoff').waitFor()
  await page.keyboard.press('Escape')
  await help(); await card().getByText('Reset this notebook’s tour',{exact:true}).first().click()
  await card().getByRole('button',{name:'Reset this notebook’s tour',exact:true}).click()
  await page.locator('[data-tour-mode="welcome"] [data-tour-card]').waitFor()
  await page.keyboard.press('Escape')
  assert.equal(await page.locator('.bf-tour-shade').count(), 0)
  assert.equal(await page.locator('body[data-bf-tour-active]').count(), 0)
  assert.deepEqual(errors, []); assert.deepEqual(prompts, [])
  const denied = await browser.newContext({viewport:{width:1280,height:900}})
  const deniedPage = await denied.newPage()
  await deniedPage.route('**/bridgeflow/config', route => route.fulfill({status:403,contentType:'application/json',body:'{"detail":"Denied"}'}))
  const deniedResponse = deniedPage.waitForResponse(r => r.url().endsWith('/bridgeflow/config') && r.status()===403)
  await deniedPage.goto(match[1]); await deniedResponse
  await deniedPage.getByRole('complementary',{name:'Sources',exact:true}).waitFor()
  assert.equal(await deniedPage.locator('[data-tour-card]:visible').count(),0)
  await denied.close()
  await writeFile(`${evidence}/checks.json`, JSON.stringify({ status: 'passed', mode: 'offline', model_calls: 0, cases: ['welcome', 'later-refresh', 'import-failure-retry', 'real-source-and-master', 'back', 'escape-resume', 'download', 'save', 'replay-no-automatic-writes','save-failure-retry','completion-refresh','missing-target-timeout-retry','390px-layout','visual-viewport-zoom','delayed-load','403-retry','config-denied-no-welcome','unsaved-dialog','supplementary-tours','reset'], sample_batch: batch }, null, 2))
  console.log(JSON.stringify({ status: 'passed', artifacts: evidence, scratch }))
} catch (e) { if (page) { await page.screenshot({ path: `${scratch}/failure.png` }); console.error((await page.locator('body').innerText()).slice(-5000)) } console.error('Artifacts:', scratch); console.error(logs.replace(/([?&]token=)[^\s)]+/g, '$1<redacted>').slice(-3500)); throw e }
finally { await browser?.close(); for (const p of processes) p.kill('SIGTERM'); await Promise.all(processes.map(p => new Promise(r => { if (p.exitCode !== null) return r(); const timer = setTimeout(() => p.kill('SIGKILL'), 5000); p.once('exit', () => { clearTimeout(timer); r() }) }))) }
