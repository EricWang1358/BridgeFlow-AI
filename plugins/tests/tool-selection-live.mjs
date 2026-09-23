// Live tool-selection evaluation (rubric 3). BILLED — every case is a real model turn.
//
// Does the captain pick the right tool first among all of its tools? Cases live in
// tests/fixtures/tool-selection.json (a person's words, the acceptable first tools, and
// tools that must never appear). Each case runs in a fresh session so earlier answers
// cannot steer it. Only the captain's own first tool calls are scored; approval cards are
// rejected, so the evaluation never writes anything.
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { randomBytes } from 'node:crypto'
import { mkdir, mkdtemp, readdir, readFile, stat, writeFile } from 'node:fs/promises'
import { createServer } from 'node:net'
import { tmpdir } from 'node:os'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from '@playwright/test'
import { assertClientModulesServed, resolveDsh } from './dsh.mjs'
import { switchLanguage } from './locale.mjs'

const live = true  // tool choice is a property of the real model; there is no offline mode
const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const scratch = await mkdtemp(`${tmpdir()}/bridgeflow-tools-`)
const evidence = process.env.BRIDGEFLOW_EVIDENCE ?? `${scratch}/evidence`
await mkdir(evidence, { recursive: true })
const python = process.env.BRIDGEFLOW_PYTHON ?? resolve(root, '../.venv/bin/python')
async function port() { const s = createServer(); await new Promise(r => s.listen(0, '127.0.0.1', r)); const p = s.address().port; await new Promise(r => s.close(r)); return p }
const backendPort = await port(), webPort = await port()
const env = { ...process.env, DSH_HOME: `${scratch}/dsh`, DSH_TOOLS_MODE: 'native',
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
    + (live ? '' : `\n- id: agent-default-model\n  name: '@deepseek-ai/dsh-agent-default-model'\n  config:\n    provider: bridgeflow-offline-test\n    model: offline\n- insert:\n    - id: scripted-test-model\n      name: ${JSON.stringify(`${root}/plugins/tests/fixtures/scripted-model/index.ts`)}\n`)
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

  const fixture = JSON.parse(await readFile(`${root}/plugins/tests/fixtures/tool-selection.json`, 'utf8'))
  const sessionsDir = `${scratch}/dsh/sessions`
  const listSessions = async () => (await readdir(sessionsDir, { recursive: true }).catch(() => [])).filter(p => p.endsWith('session.jsonl'))
  const events = async file => (await readFile(`${sessionsDir}/${file}`, 'utf8')).trim().split('\n').filter(Boolean).map(l => JSON.parse(l))
  // The sample batch and the sample workflow give every case something real to look at.
  const batch = await page.evaluate(async () => (await (await fetch('/bridgeflow/batches/demo', { method: 'POST' })).json()))
  await page.evaluate(async () => { await fetch('/bridgeflow/workflow/sample', { method: 'POST' }) })
  const top = page.locator('.bf-shell-top')
  const results = []
  for (const item of fixture.cases) {
    const prompt = item.prompt.replaceAll('{batch}', batch.batch_id).replaceAll('{period}', batch.period)
    const before = new Set(await listSessions())
    await top.getByRole('button', { name: 'Create notebook', exact: true }).click()
    const leave = page.getByRole('dialog', { name: /^(Save this notebook before leaving\?|离开前保存笔记本？)$/ })
    await leave.waitFor({ timeout: 2000 }).then(() => leave.getByRole('button', { name: /^(Discard and continue|不保存并继续)$/ }).click(), () => {})
    await wait(800)
    const composer = page.locator('[contenteditable=true]').first()
    await composer.fill(prompt); await composer.press('Enter')
    let captain = '', first = [], ended = false
    const began = Date.now()
    for (const until = Date.now() + 150_000; Date.now() < until && !ended;) {
      const fresh = (await listSessions()).filter(f => !before.has(f))
      if (!captain) for (const f of fresh) { const e = await events(f); if (e[0]?.data?.header?.origin !== 'subagent' && e.some(x => x.type === 'user/message')) captain = f }
      if (captain) {
        const log = await events(captain)
        if (!first.length) {
          const call = log.find(e => e.type === 'assistant/message' && e.data.message.content.some(b => b.type === 'tool-call'))
          if (call) first = call.data.message.content.filter(b => b.type === 'tool-call').map(b => b.name)
        }
        ended = log.at(-1)?.type === 'turn/end'
      }
      const reject = page.getByRole('button', { name: /^(拒绝|Reject)$/ })
      if (await reject.count()) {
        const box = page.getByRole('textbox', { name: /理由|reason/i })
        if (await box.count()) await box.first().fill('Tool-selection evaluation: nothing is written.')
        await reject.first().click().catch(() => {})
      }
      await wait(1000)
    }
    const all = (await listSessions()).filter(f => !before.has(f))
    const usage = {}
    for (const f of all) for (const e of await events(f)) if (e.type === 'assistant/message' && e.data.usage)
      for (const [k, v] of Object.entries(e.data.usage)) if (typeof v === 'number') usage[k] = (usage[k] ?? 0) + v
    const forbidden = (item.forbid ?? []).filter(name => first.includes(name))
    const correct = forbidden.length === 0 && (item.expect.length ? first.some(name => item.expect.includes(name)) : first.length === 0)
    results.push({ id: item.id, prompt, expect: item.expect, first, correct, ended, elapsed_ms: Date.now() - began, total_tokens: usage.totalTokens ?? 0 })
    console.log(`${correct ? 'PASS' : 'FAIL'} ${item.id}: first=${JSON.stringify(first)} expect=${JSON.stringify(item.expect)}`)
  }
  const passed = results.filter(r => r.correct).length
  const report = { generated_at: new Date().toISOString(), model: 'configured DSH_PROVIDER/DSH_MODEL', cases: results.length, passed,
    accuracy: Number((passed / results.length).toFixed(3)), total_tokens: results.reduce((n, r) => n + r.total_tokens, 0), results }
  await writeFile(`${evidence}/tool-selection.json`, JSON.stringify(report, null, 2))
  console.log(JSON.stringify({ status: 'done', cases: report.cases, passed, accuracy: report.accuracy, total_tokens: report.total_tokens, evidence }))
} catch (error) {
  if (page) await page.screenshot({ path: `${scratch}/failure.png` }).catch(() => {})
  console.error('Screenshot:', `${scratch}/failure.png`)
  console.error(logs.replace(/([?&]token=)[^\s)]+/g, '$1<redacted>').slice(-4000))
  throw error
} finally {
  await browser?.close()
  for (const child of processes) child.kill('SIGTERM')
}
