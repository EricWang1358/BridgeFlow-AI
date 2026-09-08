import { coldReload } from './cold-reload.mjs'
import { assertDefaultEnglish, switchLanguage } from './locale.mjs'
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { randomBytes } from 'node:crypto'
import { mkdtemp, readFile, readdir, writeFile } from 'node:fs/promises'
import { createServer } from 'node:net'
import { tmpdir } from 'node:os'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from '@playwright/test'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const live = process.env.BRIDGEFLOW_LIVE === '1'
const scratch = await mkdtemp(`${tmpdir()}/bridgeflow-web-e2e-`)
const python = process.env.BRIDGEFLOW_PYTHON ?? resolve(root, '../.venv/bin/python')
async function port() {
  const server = createServer()
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve))
  const value = server.address().port
  await new Promise(resolve => server.close(resolve))
  return value
}
const backendPort = await port(), webPort = await port()
const env = { ...process.env, DSH_HOME: `${scratch}/dsh`, DSH_TOOLS_MODE: 'native',
  BRIDGEFLOW_SERVICE_TOKEN: randomBytes(32).toString('hex'),
  PYTHONPATH: `${root}/backend/src`, RESULT_STORE_PATH: `${scratch}/outputs`,
  MAPPING_MEMORY_PATH: `${scratch}/mappings.json`, FIELD_DICTIONARY_PATH: `${root}/data/mappings/field-dictionary.example.yaml`,
  LLM_PROVIDER: 'mock', BRIDGEFLOW_ENABLE_LEGACY_CONSOLE: 'false', BRIDGEFLOW_ALLOW_SAMPLE_DATA: 'false',
}
const processes = []
let browser
let page
let logs = ''
async function sessionEvents() {
  const folder = `${scratch}/dsh/sessions`
  const paths = (await readdir(folder, { recursive: true })).filter(path => path.endsWith('session.jsonl'))
  return (await Promise.all(paths.map(path => readFile(`${folder}/${path}`, 'utf8'))))
    .flatMap(text => text.trim().split('\n').map(line => JSON.parse(line)))
}
async function waitTurn(number) {
  const deadline = Date.now() + 90000
  while (Date.now() < deadline) {
    const events = await sessionEvents()
    if (events.filter(e => e.type === 'turn/end').length >= number) {
      const last = events.filter(e => e.type === 'turn/end').at(-1)
      assert.equal(last.data.reason.kind, 'completed')
      return
    }
    await new Promise(resolve => setTimeout(resolve, 200))
  }
  throw new Error(`Turn ${number} did not finish`)
}
function start(command, args) {
  const child = spawn(command, args, { cwd: root, env, stdio: ['ignore', 'pipe', 'pipe'] })
  child.stdout.on('data', data => { logs += data })
  child.stderr.on('data', data => { logs += data })
  processes.push(child)
  return child
}
try {
  const patch = (await readFile(`${root}/dsh/enterprise.patch.yml`, 'utf8'))
    .replace("'../plugins/src/index.ts'", JSON.stringify(`${root}/plugins/src/index.ts`))
    .replace('./dsh/presets', `${root}/dsh/presets`)
    .replace('http://127.0.0.1:8000', `http://127.0.0.1:${backendPort}`)
    .replace('approvalMode: native', 'approvalMode: native\n        decisionTimeoutMs: 5000')
    + (live ? '' : `\n- id: agent-default-model\n  name: '@deepseek-ai/dsh-agent-default-model'\n  config:\n    provider: bridgeflow-offline-test\n    model: offline\n- insert:\n    - id: scripted-test-model\n      name: ${JSON.stringify(`${root}/plugins/tests/fixtures/scripted-model/index.ts`)}\n`)
  await writeFile(`${scratch}/web.yml`, patch)
  start(python, ['-m', 'uvicorn', 'bridgeflow.api.main:app', '--host', '127.0.0.1', '--port', String(backendPort)])
  const web = start(process.env.BRIDGEFLOW_DSH ?? 'dsh', ['web', '--patch', `${scratch}/web.yml`, '--no-open', '--port', String(webPort)])
  const deadline = Date.now() + 30_000
  let match
  while (Date.now() < deadline) {
    match = logs.match(/dsh web: (http:\/\/127\.0\.0\.1:\d+\/\?token=[^\s)]+)/)
    if (match) break
    if (processes.some(child => child.exitCode !== null)) throw new Error('Service exited before readiness')
    await new Promise(resolve => setTimeout(resolve, 100))
  }
  assert(match, 'DSH did not become ready')
  browser = await chromium.launch({ headless: true })
  page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, locale: 'zh-CN' })
  const errors = []
  page.on('pageerror', error => { errors.push(error.message); logs += '\nBROWSER: ' + error.message })
  page.on('console', message => { if (message.type() === 'error') logs += '\nCONSOLE: ' + message.text() })
  page.setDefaultTimeout(15000)
  await page.goto(match[1])
  // #110: a new user on a zh-CN browser defaults to English; the explicit switch
  // to Chinese goes through the native Settings language row and persists.
  await assertDefaultEnglish(page)
  await switchLanguage(page, '中文')
  await page.getByRole('button', { name: '会话与设置', exact: true }).click()
  await page.getByRole('button', { name: '导入与数据', exact: true }).click({ timeout: 30_000 })
  await page.locator('dialog[open] input[name=period]').fill('2025-11')
  const limits = await page.evaluate(async () => (await fetch('/bridgeflow/config')).json())
  assert.equal(limits.maxUploadBytes, 25 * 1024 * 1024)
  assert.equal(limits.maxRequestBytes, 26 * 1024 * 1024)
  assert.equal(limits.decisionTimeoutMs, 5000)
  assert.equal((await fetch(`http://127.0.0.1:${webPort}/bridgeflow/config`)).status, 401)
  // Use the file chooser's disk path, avoiding a large base64 CDP transfer.
  await writeFile(`${scratch}/oversized.csv`, Buffer.alloc(limits.maxUploadBytes + 1))
  await page.locator('dialog[open] input[name=production]').setInputFiles(`${scratch}/oversized.csv`)
  let uploads = 0
  const countUpload = request => { if (request.method() === 'POST' && request.url().endsWith('/bridgeflow/batches')) uploads++ }
  page.on('request', countUpload)
  await page.getByRole('button', { name: '导入并检查', exact: true }).click()
  await page.getByText('请选择至少一个 CSV/XLSX，文件总大小不得超过上限。', { exact: true }).waitFor()
  assert.equal(uploads, 0, 'Oversized data must be rejected before the upload request')
  page.off('request', countUpload)
  await page.locator('dialog[open] input[name=production]').setInputFiles({ name: 'production.csv', mimeType: 'text/csv', buffer: Buffer.from('sku,output_qty\nSKU-A1,17\n') })
  await page.getByRole('button', { name: '导入并检查', exact: true }).click()
  await page.getByText('主表 1 行 · 待确认映射 0 条').waitFor()
  await page.getByRole('cell', { name: '17', exact: true }).waitFor()
  await page.screenshot({ path: `${scratch}/data-workspace.png`, fullPage: true })
  const data = await page.evaluate(async () => {
    const rejected = await fetch('/bridgeflow/tools/confirm-mapping', { method: 'POST', body: '{}' })
    return { status: rejected.status, boot: JSON.stringify(window.__DSH_BOOT__) }
  })
  assert.equal(data.status, 403)
  for (const name of ['bridgeflow-plugins', 'dsh-client-ui-approval', 'dsh-client-ui-trajectory', 'dsh-client-ui-chat']) assert(data.boot.includes(name), name)
  for (const name of ['dsh-client-ui-cordis', 'dsh-client-ui-settings-plugins', 'dsh-client-ui-attachment', 'dsh-client-ui-permission-presets']) assert(!data.boot.includes(name), name)
  assert.equal((await fetch(`http://127.0.0.1:${webPort}/bridgeflow/batches/00000000000000000000000000000000`)).status, 401)
  await page.getByRole('button', { name: '关闭', exact: true }).click()
  await page.getByRole('button', { name: '会话与设置', exact: true }).click()
  await page.getByRole('button', { name: /^(Choose workspace|选择工作区)$/ }).click()
  await page.getByRole('menuitem', { name: 'BridgeFlow', exact: true }).click()
  const composer = page.locator('[contenteditable=true]').first()
  const request = step => `这是隔离测试目录中的合成映射验收。请只调用一次 confirm_mapping，参数 source="sku:test-${step}", target="customer:test", relation="ordered_by", accepted=true, evidence="合成业务用例的人工作业关系", period="2025-11"。等待操作者审批，随后简短说明实际结果，若拒绝必须原样转述理由。不要重试，不调用其他工具或提问。`
  await composer.fill(live ? request(0) : 'Exercise the approved mapping fixture.')
  await composer.press('Enter')
  // #110: the approval card renders the structured decision summary localized —
  // labels translated, values verbatim — not just translated buttons.
  const decision = page.getByRole('region', { name: '映射审批' })
  await decision.getByText('决定内容', { exact: true }).waitFor({ timeout: 30_000 })
  await decision.getByText('sku:test-0', { exact: true }).waitFor()
  await decision.getByText('接受映射', { exact: true }).waitFor()
  await decision.getByText('决定时展示的依据', { exact: true }).waitFor()
  await page.getByRole('button', { name: /^(允许一次|Allow once)$/ }).click({ timeout: 30_000 })
  await waitTurn(1)
  const acceptedMemory = await readFile(`${scratch}/mappings.json`, 'utf8')
  assert(acceptedMemory.includes('sku:test-0'))
  assert(acceptedMemory.includes('dsh-authenticated-session'))
  await composer.fill(live ? request(2) : 'Exercise the rejected mapping fixture.')
  await composer.press('Enter')
  await page.getByRole('textbox', { name: '拒绝理由', exact: true }).fill('客户编码未核实，请销售负责人确认后再提交。')
  await page.screenshot({ path: `${scratch}/rejection-note.png`, fullPage: true })
  await page.getByRole('button', { name: /^(拒绝|Reject)$/ }).click({ timeout: 30_000 })
  await waitTurn(2)
  const afterRejection = await sessionEvents()
  const refusalNarration = afterRejection.filter(e => e.type === 'assistant/message').at(-1).data.message.content
    .filter(block => block.type === 'text').map(block => block.text).join('\n')
  if (live) {
    assert(refusalNarration.includes('客户编码未核实'), refusalNarration)
    assert(/拒绝|未.*(写入|保存|确认|执行)/.test(refusalNarration), refusalNarration)
    assert(!/不会.{0,12}(询问|再问)|不再.{0,6}(询问|问)/.test(refusalNarration), refusalNarration)
  }
  assert.equal(await page.getByRole('button', { name: /Workspace Write|Full Access|工作区写入|完全访问/ }).count(), 0)
  assert.equal(await readFile(`${scratch}/mappings.json`, 'utf8'), acceptedMemory)
  await composer.fill(live ? request(4) : 'Exercise an unattended approval timeout.')
  await composer.press('Enter')
  await page.getByRole('button', { name: /^(允许一次|Allow once)$/ }).waitFor()
  await waitTurn(3)
  assert.equal(await readFile(`${scratch}/mappings.json`, 'utf8'), acceptedMemory)
  const sessionRoot = `${scratch}/dsh/sessions`
  const logsOnDisk = (await readdir(sessionRoot, { recursive: true })).filter(path => path.endsWith('session.jsonl'))
  const events = (await Promise.all(logsOnDisk.map(path => readFile(`${sessionRoot}/${path}`, 'utf8'))))
    .flatMap(text => text.trim().split('\n').map(line => JSON.parse(line)))
  const asks = events.filter(event => event.type === 'approval/asked')
  const decisions = events.filter(event => event.type === 'approval/decided')
  const noteSession=logsOnDisk.find(path=>path.endsWith('session.jsonl')).split('/').at(-2)
  const noteAudit=await page.evaluate(async id=>(await fetch(`/bridgeflow/approval-note-audit?session_id=${encodeURIComponent(id)}`)).json(),noteSession)
  const noteEvents=noteAudit.notes.map(data=>({type:'bridgeflow/approval-note',data}))
  assert.equal(noteEvents.length, 1)
  assert.equal(noteEvents[0].data.note, '客户编码未核实，请销售负责人确认后再提交。')
  assert(events.some(event => event.type === 'tool/result' && JSON.stringify(event).includes(noteEvents[0].data.note))
    || events.some(event => event.type.includes('tool') && JSON.stringify(event).includes('The reviewer said')))
  assert.equal(asks.length, 3)
  assert.deepEqual(decisions.map(event => event.data.outcome), ['allowed-once', 'rejected', 'cancelled'])
  assert.deepEqual(decisions.map(event => event.data.id), asks.map(event => event.data.id))
  for (const group of await page.getByText(/^(1 tool call|1 次工具调用)$/).all()) await group.click()
  assert.equal(await page.getByRole('region', { name: '映射决定' }).count(), 3)
  await page.screenshot({ path: `${scratch}/native-approval.png`, fullPage: true })
  await page.getByRole('tab', { name: '业务状态', exact: true }).click()
  await page.getByRole('main', { name: '业务状态' }).getByRole('button', { name: '已拒绝 1', exact: true }).click()
  await page.getByRole('main', { name: '业务状态' }).getByText('客户编码未核实，请销售负责人确认后再提交。', { exact: true }).waitFor()
  await page.screenshot({ path: `${scratch}/business-state.png`, fullPage: true })
  await coldReload({page,web,start,args:['web','--patch',`${scratch}/web.yml`,'--no-open','--port',String(webPort)],readLogs:()=>logs,sessionIds:[noteSession]})
  const restoredNotes=await page.evaluate(async id=>(await fetch(`/bridgeflow/approval-note-audit?session_id=${encodeURIComponent(id)}`)).json(),noteSession)
  assert.deepEqual(restoredNotes,noteAudit,'Refusal note audit must survive a full host restart')
  // #110: the language choice is a durable Host setting, so a full host restart
  // must not reset it to the browser-derived or default locale.
  await page.getByRole('complementary', { name: '来源', exact: true }).waitFor()
  assert.equal(await page.getByRole('complementary', { name: 'Sources', exact: true }).count(), 0,
    'Language preference must survive a full host restart')
  assert.deepEqual(errors, [])
  const measurement = { mode: live ? 'live' : 'offline', approval_outcomes: decisions.map(e => e.data.outcome), refusalNarration,
    model_requests: events.filter(e => e.type === 'assistant/message').length,
    usage: events.filter(e => e.type === 'assistant/message' && e.data.usage).reduce((total, e) => {
      for (const [key, value] of Object.entries(e.data.usage)) if (typeof value === 'number') total[key] = (total[key] ?? 0) + value
      return total
    }, {}) }
  await writeFile(`${scratch}/measurement.json`, JSON.stringify(measurement, null, 2))
  await writeFile(`${scratch}/approval-note-audit.json`, JSON.stringify(noteAudit, null, 2))
  await writeFile(`${scratch}/approval-events.json`, JSON.stringify(events.filter(e => ['approval/asked', 'approval/decided', 'bridgeflow/approval-note', 'tool/result'].includes(e.type)), null, 2))
  console.log(JSON.stringify({ ...measurement, artifacts: scratch }))
  console.log(JSON.stringify({ status: 'passed', screenshot: `${scratch}/data-workspace.png`, approvalScreenshot: `${scratch}/native-approval.png`, checks: ['native shell', 'plugin loading', 'upload', 'master table', 'authenticated proxy', 'write proxy denied', `native approval allow/reject/timeout with ${live ? 'live model' : 'offline adapter'}`, 'paired native audit events', 'zero browser errors'] }))
} catch (error) {
  if (page) { await page.screenshot({path: `${scratch}/failure.png`}); console.error('Screenshot:', `${scratch}/failure.png`); console.error((await page.locator('body').innerText()).slice(0,3000)); await writeFile(`${scratch}/failure.html`, await page.content()); console.error(await page.evaluate(() => ({scripts: [...document.scripts].map(x => x.src), boot: window.__DSH_BOOT__}))) }
  console.error(logs.replace(/([?&]token=)[^\s)]+/g, '$1<redacted>'))
  throw error
} finally {
  await browser?.close()
  for (const child of processes) child.kill('SIGTERM')
  await Promise.all(processes.map(child => new Promise(resolve => {
    if (child.exitCode !== null) return resolve()
    const timer = setTimeout(() => child.kill('SIGKILL'), 5000)
    child.once('exit', () => { clearTimeout(timer); resolve() })
  })))
}
