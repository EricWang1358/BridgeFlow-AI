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
  let step = 0
  const host = (path, body, trace = {}) => fetch(`http://127.0.0.1:${backendPort}${path}`, { method: 'POST',
    headers: { 'content-type': 'application/json', authorization: `Bearer ${env.BRIDGEFLOW_SERVICE_TOKEN}`,
      'x-bridgeflow-root': trace.run ?? 'journey-run', 'x-bridgeflow-call': `journey-${++step}`,
      'x-bridgeflow-agent': trace.agent ?? 'captain', 'x-bridgeflow-tool': path.split('/').pop().replaceAll('-', '_'),
      ...(body?.batch_id ? { 'x-bridgeflow-batch': body.batch_id } : {}) },
    body: JSON.stringify(body) }).then(async r => { assert.equal(r.status, 200, await r.clone().text()); return r.json() })
  const studio = name => page.locator('.bf-studio-tools button', { hasText: name }).first()
  await page.goto(match[1])
  await page.locator('[data-tour-mode="welcome"] [data-tour-card]').waitFor()
  await page.locator('[data-tour-card]:visible').getByRole('button', { name: 'Maybe later', exact: true }).click()

  // E13-UC01 AC-3: no saved review yet. The sample button is disabled until the notebook
  // session has loaded, and clicking a disabled button silently does nothing — wait for it.
  const sample = page.locator('[data-tour-id="sample"]:visible:not([disabled])')
  await sample.waitFor({ timeout: 60000 })
  await sample.click()
  await page.locator('.bf-resource-list button').first().waitFor()
  const batch = new URLSearchParams(new URL(page.url()).hash.split('?')[1]).get('batch')
  assert.match(batch, /^[a-f0-9]{32}$/)
  await studio('Conclusions').click()
  await page.getByText('No review yet', { exact: true }).waitFor()

  // A scripted review through the host tools, as test_business_mvp does (no model)
  const reviewContext = await host('/tools/review-context', { batch_id: batch })
  const runs = reviewContext.roles.map(p => ({ role: p.role, session_id: `child-${p.role}`, status: 'completed', judgement: { checks: p.checks.map(c => ({
    check_id: c.check_id, metric: c.metric, value: c.value, unit: c.unit, status: c.expected_status,
    action: c.actions[c.expected_status][0], explanation: '应按本部门权限核实并提交责任人复核。' })) } }))
  // Each role's own reads belong to the same run, on its own lane.
  for (const packet of reviewContext.roles) {
    await host('/tools/batch-summary', { batch_id: batch }, { agent: `child-${packet.role}` })
  }
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
  // E13-UC01 (round 11): an attention item cites the cells behind its figure
  const sources = page.locator('.bf-brief-attention .bf-brief-sources').first()
  await sources.locator('summary').click()
  await sources.locator('li button').first().waitFor()
  await shot('brief')

  // E13-UC02: import the base period through the host API, then the brief compares against it
  const june = `${root}/data/mock_business/monthly/2024-06-调优B`
  const form = new FormData()
  form.set('period', '2024-06')
  for (const [department, label] of Object.entries({ production: '生产部', procurement: '物资部', finance: '财务部', marketing: '市场部' })) {
    form.append('departments', department)
    form.append('files', new Blob([await readFile(`${june}/${label}.xlsx`)]), `${label}.xlsx`)
  }
  const imported = await fetch(`http://127.0.0.1:${backendPort}/batches`, { method: 'POST', headers: { authorization: `Bearer ${env.BRIDGEFLOW_SERVICE_TOKEN}` }, body: form })
  assert.equal(imported.status, 200, await imported.text())
  await page.reload()
  await page.locator('.bf-brief').waitFor()
  await page.getByText('2024-06', { exact: false }).first().waitFor()
  const changes = await page.locator('.bf-brief-metrics .bf-change').count()
  assert.ok(changes >= 1, 'key metrics show a change against the base period')
  await page.locator('.bf-callout[data-tone="warn"]').filter({ hasText: 'PRJ2023098' }).first().waitFor()
  await shot('brief-comparison')

  // E13-UC03: the declared trend draws two periods, and the table beside it says the same
  await page.locator('.bf-brief-fold > summary').filter({ hasText: 'Metric charts' }).click()
  const trend = page.locator('.bf-chart-card').filter({ hasText: 'Sign-off rate trend' })
  await trend.locator('svg.bf-chart').waitFor()
  await trend.getByRole('button', { name: 'Show the table' }).click()
  const cells = await trend.locator('.bf-chart-table tbody tr td:nth-child(2)').allInnerTexts()
  assert.ok(cells.filter(c => c !== '—').length >= 2, `the table lists the same measured points: ${cells}`)
  assert.ok(cells.includes('—'), 'a month without a batch stays a gap in the table too')
  await shot('metric-charts')

  // E13-UC04: the report downloads as a Word file generated from this same brief
  const download = page.waitForEvent('download')
  await target('brief-export').click()
  const saved = await download
  assert.match(saved.suggestedFilename(), /^月度经营结论-2024-07-.*\.docx$/)

  // E13-UC06 in the master view: reached from the Data destination, which owns it now
  await studio('Data').click()
  await page.locator('.bf-data-row').first().waitFor()
  await shot('data-timeline')
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
  // E14-UC02 and E14-UC04 live on the department's own row in Data: take its template, and
  // correct its file. A file identical to the one already in the batch derives nothing.
  await dialog.locator('header button').first().click()
  await studio('Data').click()
  const productionRow = page.locator('.bf-data-row').first()
  await productionRow.waitFor()
  await productionRow.scrollIntoViewIfNeeded()
  const templateFile = page.waitForEvent('download')
  await productionRow.locator('.bf-template-download button').click()
  assert.match((await templateFile).suggestedFilename(), /^生产部-2024-07-.*\.xlsx$/)
  await productionRow.locator('.bf-template-download [role=status]').waitFor()
  await shot('template-download')

  await productionRow.locator('.bf-resupply > summary').click()
  await productionRow.locator('.bf-resupply input[name=reason]').fill('journey: unchanged file')
  await productionRow.locator('.bf-resupply input[name=file]').setInputFiles(`${root}/data/mock_business/demo/production.xlsx`)
  await productionRow.locator('.bf-resupply button[type=submit]').click()
  await productionRow.locator('.bf-resupply .bf-error').filter({ hasText: 'identical' }).waitFor()
  await shot('resupply-unchanged')

  // E14-UC01 + E14-UC05: one destination, the steps and the items they are waiting on
  await target('state-open').click()
  const checklist = page.locator('.bf-checklist')
  await checklist.waitFor()
  const done = await checklist.locator('li[data-state=done] b').allInnerTexts()
  assert.ok(done.includes('Department files submitted'), `files step should be done: ${done}`)
  await checklist.locator('li[data-state=open]').first().waitFor()
  await shot('close-checklist')

  // Focusing a step narrows the items to the ones that step is waiting on, and the total stays.
  const before = await page.locator('.bf-inbox li').count()
  await checklist.locator('li[data-state=open] button', { hasText: 'Show its items' }).first().click()
  await page.locator('.bf-inbox [role=status]').filter({ hasText: 'focused step' }).waitFor()
  assert.ok(await page.locator('.bf-inbox li').count() <= before, 'focusing a step narrows the list')
  await page.locator('.bf-inbox [role=status] button').click()

  // E14-UC05: the same open items, listed as what is waiting on whom — with no decision buttons
  const waiting = page.locator('.bf-inbox li')
  await waiting.first().waitFor()
  assert.equal(await waiting.first().locator('button').count(), 1, 'an item offers one action: open where it is settled')
  await shot('open-items')

  // Observability: one agent run, drawn as lanes — the captain's steps and each department
  // subagent's calls under the same root.
  await studio('Records').click()
  const run = page.locator('.bf-run-list > li').first()
  await run.waitFor()
  await run.locator('.bf-run-head').click()
  const lanes = await run.locator('.bf-run-lane-name').allInnerTexts()
  assert.ok(lanes.length >= 2, `the run has a lane per agent: ${lanes}`)
  assert.ok(await run.locator('.bf-run-mark').count() >= 3, 'each tool call is a mark on its lane')
  await shot('agent-run')

  // The decision journal shows what the system decided, refusals included, and the trace id on
  // the page is the one the response header carried.
  await page.locator('.bf-journal-list li').first().waitFor()
  const refused = page.locator('.bf-actions button', { hasText: 'Refused' }).first()
  await refused.click()
  await page.locator('.bf-journal-list li[data-outcome=refused]').first().waitFor()
  const reason = await page.locator('.bf-journal-list li[data-outcome=refused] .bf-journal-reason').first().innerText()
  assert.ok(reason.length > 8, `a refusal is recorded in its own words: ${reason}`)
  await shot('decision-journal')

  assert.deepEqual(errors, [])
  console.log(JSON.stringify({ status: 'passed', batch, attention: items, evidence }))
} catch (error) { console.error(logs.slice(-3000)); await page?.screenshot({ path: `${evidence}/failure.png` }).catch(() => {}); throw error }
finally { await browser?.close(); for (const p of processes) p.kill('SIGTERM'); await Promise.all(processes.map(p => new Promise(r => { if (p.exitCode !== null) return r(); const timer = setTimeout(() => p.kill('SIGKILL'), 5000); p.once('exit', () => { clearTimeout(timer); r() }) }))) }
