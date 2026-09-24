// Browser journey for the template-filling and handoff workflow (#143–#147).
//
// Offline (default): the page draws the flow, the sample workflow loads, and the two
// sample records sit where they should. BRIDGEFLOW_LIVE=1 adds the captain — BILLED, it
// calls the configured model: submit for approval → approve → recorded → handed over →
// started → completed, then the missing quantity is asked for and answered. Every write
// goes through a native approval card; this script plays the person who clicks
// "Allow once" and who answers the captain's question.
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
const scratch = await mkdtemp(`${tmpdir()}/bridgeflow-workflow-`)
const evidence = process.env.BRIDGEFLOW_EVIDENCE ?? `${scratch}/evidence`
await mkdir(evidence, { recursive: true })
const python = process.env.BRIDGEFLOW_PYTHON ?? resolve(root, '../.venv/bin/python')
async function port() { const s = createServer(); await new Promise(r => s.listen(0, '127.0.0.1', r)); const p = s.address().port; await new Promise(r => s.close(r)); return p }
const backendPort = await port(), webPort = await port()
const env = { ...process.env, PORTAL_BASE_URL: '', DSH_HOME: `${scratch}/dsh`, DSH_TOOLS_MODE: 'native',
  BRIDGEFLOW_SERVICE_TOKEN: randomBytes(32).toString('hex'), PYTHONPATH: `${root}/backend/src`, RESULT_STORE_PATH: `${scratch}/outputs`,
  MAPPING_MEMORY_PATH: `${scratch}/mappings.json`, FIELD_DICTIONARY_PATH: `${root}/data/mock_business/demo/dictionary.yaml`,
  WORKFLOW_CATALOGUE_PATH: `${root}/data/workflow_demo/catalogue.yaml`,
  DISCOVERY_SCORING_POLICY_PATH: `${root}/data/discovery_demo/scoring-policy.yaml`,
  DISCOVERY_DECISION_POLICY_PATH: `${root}/data/discovery_demo/decision-policy.yaml`,
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

  // The flow is drawn before any record exists: the thing to understand first.
  await studio.getByRole('button', { name: /Filling & handoff/ }).click()
  await page.locator('.bf-pipeline').waitFor()
  assert.equal(await page.locator('.bf-pipeline > li').count(), 7)
  assert.equal(await page.locator('.bf-pipeline > li[data-active=true]').count(), 0)
  await shot('01-empty-flow')

  // Discovery → workflow: nothing is linked yet; the sample project ends in an approved
  // decision, which the card then offers for the captain to accept (behind approval).
  const scopeCard = page.getByRole('region', { name: 'Workflow scope' })
  await scopeCard.getByRole('button', { name: 'Load the sample discovery project', exact: true }).click()
  await scopeCard.getByRole('button', { name: 'Ask the captain to accept this scope', exact: true }).waitFor()
  assert.match(await scopeCard.innerText(), /demo-handoff \/ mvp/)
  await shot('00-scope-waiting')

  // The sample only receives: one record lacks its confirmed quantity, one awaits review.
  await page.getByRole('button', { name: 'Load the sample workflow', exact: true }).click()
  await page.getByRole('button', { name: 'Ask the captain to submit for approval', exact: true }).first().waitFor()
  const loaded = await board()
  assert.deepEqual(loaded.filter(r => r.kind === 'artifact').map(r => r.state).sort(), ['needs_input', 'ready_for_review', 'ready_for_review'])
  assert.equal(await page.locator('.bf-pipeline > li[data-active=true]').count(), 2)
  await shot('02-sample-loaded')

  // Every record keeps its own timeline: what happened, when, by whom.
  await page.locator('article.bf-source-item').first().getByRole('button', { name: 'Timeline', exact: true }).click()
  await page.locator('.bf-timeline > li').first().waitFor()
  assert.match(await page.locator('.bf-timeline').innerText(), /Submission received/)

  // The overview reads the same board: the two occupied stages show up as bars.
  await studio.getByRole('button', { name: /^Overview/ }).click()
  const stagesBlock = page.getByRole('region', { name: 'Workflow stages' })
  await stagesBlock.locator('.bf-ov-bar').first().waitFor()
  assert.equal(await page.locator('.bf-ov-tile').filter({ hasText: 'Records in flight' }).locator('b').innerText(), '3')
  await shot('07-overview-without-batch')
  await studio.getByRole('button', { name: 'Filling & handoff', exact: true }).click()
  await page.locator('.bf-pipeline').waitFor()

  const measured = { mode: live ? 'live' : 'offline', steps: [] }
  if (live) {
    async function sessionLogs() {
      const folder = `${scratch}/dsh/sessions`
      const files = (await readdir(folder, { recursive: true }).catch(() => [])).filter(p => p.endsWith('session.jsonl'))
      const logs = []
      for (const file of files) logs.push({ file, mtime: (await stat(`${folder}/${file}`)).mtimeMs,
        events: (await readFile(`${folder}/${file}`, 'utf8')).trim().split('\n').filter(Boolean).map(l => JSON.parse(l)) })
      return logs
    }
    async function captainIdle() {
      const [latest] = (await sessionLogs()).sort((a, b) => b.mtime - a.mtime)
      return !!latest && latest.events.at(-1)?.type === 'turn/end'
    }
    async function say(text) {
      const composer = page.locator('[contenteditable=true]').first()
      await composer.fill(text); await composer.press('Enter')
    }
    // Drive one step: click each approval card as it appears, answer once if asked, and
    // stop when the workflow itself (read from the backend) reaches the goal.
    // `within` names the record card whose button to press (title and project), because
    // several records can offer the same next step.
    async function drive(label, button, done, reply, within = []) {
      const stepBegan = Date.now()
      let card = page.locator('article.bf-source-item')
      for (const text of within) card = card.filter({ hasText: text })
      await (typeof button === 'string' ? card.getByRole('button', { name: button, exact: true }).first() : button).click()
      let lastActivity = Date.now(), replied = !reply, nudged = false
      for (const until = Date.now() + 300_000; Date.now() < until;) {
        const allow = page.getByRole('button', { name: /^(允许一次|Allow once)$/ })
        if (await allow.count()) {
          await shot(`approval-${approvals.length + 1}`)
          approvals.push({ step: label, at_ms: Date.now() - began })
          await allow.first().click(); lastActivity = Date.now(); await wait(1500); continue
        }
        // The captain may ask before acting (native ask-user card). The person's answer here:
        // the flagged 1.5 m³ is expected transit loss, so submit as it stands.
        const skip = page.getByRole('button', { name: /^(Skip this question|跳过此问题)$/ })
        if (await skip.count()) {
          await shot(`question-${questions.length + 1}`)
          const pick = page.getByText(/as it stands|submit (it )?now|proceed with (the )?submi|照原样|直接提交/i).first()
          questions.push({ step: label, picked: await pick.count() ? await pick.innerText() : 'skipped' })
          if (await pick.count()) { await pick.click(); await page.getByRole('button', { name: /^(Submit|提交)$/ }).last().click() }
          else { await skip.click(); await say('The 1.5 m³ difference is expected transit loss. Submit it as it stands; the approval card is my confirmation.') }
          lastActivity = Date.now(); await wait(1500); continue
        }
        if (await done(await board())) { measured.steps.push({ step: label, elapsed_ms: Date.now() - stepBegan }); await refresh(); return }
        if (await captainIdle() && Date.now() - lastActivity > 5000) {
          if (!replied) { await say(reply); replied = true }
          else if (!nudged) { await say('Please go ahead with the tool call; the approval card is my confirmation.'); nudged = true }
          else throw new Error(`${label}: the captain stopped before the workflow reached the goal`)
          lastActivity = Date.now()
        }
        await wait(1000)
      }
      throw new Error(`${label}: timed out`)
    }
    // Accept the approved MVP decision as this workflow's scope, before any record moves.
    await drive('scope accepted', scopeCard.getByRole('button', { name: 'Ask the captain to accept this scope', exact: true }),
      async () => (await page.evaluate(async () => (await (await fetch('/bridgeflow/workflow/scope')).json()))).current === true)
    await scopeCard.getByText('Running under an approved MVP decision').waitFor()
    await shot('00b-scope-accepted')
    const ready = loaded.find(r => r.kind === 'artifact' && r.template === 'production_record' && r.state === 'ready_for_review').id
    const missing = loaded.find(r => r.kind === 'artifact' && r.state === 'needs_input').id
    await drive('review and submit', 'Ask the captain to submit for approval',
      rows => rows.some(r => r.id === ready && r.state === 'data_ready') && rows.some(r => r.kind === 'handoff'),
      undefined, ['生产记录', '演示项目B'])
    await shot('03-recorded-and-handed-over')
    const market = r => r.kind === 'handoff' && r.stage === 'market_review'
    const finance = r => r.kind === 'handoff' && r.stage === 'finance_settlement'
    await drive('downstream starts', 'Ask the captain to start it', rows => rows.some(r => market(r) && r.state === 'in_progress'), undefined, ['市场部'])
    // Marketing's stage produces the settlement basis; it cannot be completed until that is
    // recorded, so the page offers no "complete" until then (the board says what is owed).
    assert.equal(await page.locator('article.bf-source-item').filter({ hasText: '入库后才能完成' })
      .getByRole('button', { name: 'Ask the captain to complete it', exact: true }).count(), 0)
    const settlement = loaded.find(r => r.kind === 'artifact' && r.template === 'settlement_basis').id
    await drive('settlement submitted', 'Ask the captain to submit for approval',
      rows => rows.some(r => r.id === settlement && r.state === 'data_ready') && rows.some(finance), undefined, ['结算依据'])
    await drive('downstream completes', 'Ask the captain to complete it', rows => rows.some(r => market(r) && r.state === 'completed'), undefined, ['市场部'])
    await shot('04-completed')
    // The second hop: marketing's settlement basis went to finance.
    await drive('finance starts', 'Ask the captain to start it', rows => rows.some(r => finance(r) && r.state === 'in_progress'), undefined, ['财务部'])
    await drive('finance completes', 'Ask the captain to complete it', rows => rows.some(r => finance(r) && r.state === 'completed'), undefined, ['财务部'])
    await shot('06-second-hop-completed')
    await drive('missing quantity answered', 'Ask the captain to fill the gaps',
      rows => rows.some(r => r.id === missing && r.state === 'ready_for_review'),
      'The actual quantity is 97 m³, confirmed by delivery note DEMO-0901.', ['生产记录', '演示项目A'])
    await shot('05-answered')
    const all = await sessionLogs()
    const messages = all.flatMap(l => l.events).filter(e => e.type === 'assistant/message')
    measured.approvals = approvals
    measured.questions = questions
    measured.model_requests = messages.length
    measured.tool_calls = messages.flatMap(e => e.data.message.content.filter(b => b.type === 'tool-call').map(b => b.name))
    measured.usage = messages.filter(e => e.data.usage).reduce((total, e) => {
      for (const [key, value] of Object.entries(e.data.usage)) if (typeof value === 'number') total[key] = (total[key] ?? 0) + value
      return total
    }, {})
    measured.final = (await board()).map(r => ({ kind: r.kind, state: r.state ?? r.stage }))
  }
  assert.deepEqual(errors, [])
  measured.elapsed_ms = Date.now() - began
  await writeFile(`${evidence}/measurement.json`, JSON.stringify(measured, null, 2))
  console.log(JSON.stringify({ status: 'passed', ...measured, evidence }))
} catch (error) {
  if (page) await page.screenshot({ path: `${scratch}/failure.png` }).catch(() => {})
  console.error('Screenshot:', `${scratch}/failure.png`)
  console.error(logs.replace(/([?&]token=)[^\s)]+/g, '$1<redacted>').slice(-4000))
  throw error
} finally {
  await browser?.close()
  for (const child of processes) child.kill('SIGTERM')
}
