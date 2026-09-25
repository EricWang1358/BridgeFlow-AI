import { coldReload } from './cold-reload.mjs'
import { assertClientModulesServed, resolveDsh, liveModelPatch } from './dsh.mjs'
import { assertDefaultEnglish, switchLanguage } from './locale.mjs'
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { randomBytes, generateKeyPairSync, sign } from 'node:crypto'
import { createServer as createHttpServer } from 'node:http'
import { mkdtemp, readFile, readdir, writeFile } from 'node:fs/promises'
import { createServer } from 'node:net'
import { tmpdir } from 'node:os'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from '@playwright/test'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const live = process.env.BRIDGEFLOW_LIVE === '1'
const discoveryMode = process.env.BRIDGEFLOW_TEST_DISCOVERY === '1'
assert(!discoveryMode || !live, 'Discovery fixtures require offline mode')
const employeeMode = process.env.BRIDGEFLOW_TEST_EMPLOYEE === '1'
assert(!employeeMode || !live, 'Synthetic employee mode is an offline test only')
let portalServer
let employeeToken = '', secondEmployeeToken = ''
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
const env = { ...process.env, PORTAL_BASE_URL: '', DSH_HOME: `${scratch}/dsh`, DSH_TOOLS_MODE: 'native',
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
  if (discoveryMode) {
    env.DISCOVERY_SCORING_POLICY_PATH = `${scratch}/scoring-policy.json`
    env.DISCOVERY_DECISION_POLICY_PATH = `${scratch}/decision-policy.json`
    await writeFile(env.DISCOVERY_DECISION_POLICY_PATH, JSON.stringify({ id: 'browser-decision-policy', project_id: 'browser-project', version: 1, departments: ['production'], declared_by: 'offline-owner', declaration_ref: 'Synthetic voting rules for browser test only', proposers: ['offline-employee'], voters: ['offline-employee', 'offline-voter'], approvers: ['offline-employee'], condition_confirmers: ['offline-employee'], quorum: 2, minimum_yes: 2, no_votes_block: true, abstentions_count_for_quorum: false, agent2_owner_role: 'synthetic-standardization-owner' }))
    const axis = { title: 'Synthetic effort', unit: 'points', minimum: '0', maximum: '10', split: '5', split_is_high: true, low_meaning: 'Low', high_meaning: 'High' }
    await writeFile(env.DISCOVERY_SCORING_POLICY_PATH, JSON.stringify({ id: 'browser-policy', project_id: 'browser-project', version: 1, departments: ['production'], declared_by: 'offline-owner', declaration_ref: 'Synthetic browser test only', effort: axis, value: { ...axis, title: 'Synthetic value' } }))
  }
  if (employeeMode) {
    const { privateKey, publicKey } = generateKeyPairSync('ed25519')
    const jwk = { ...publicKey.export({ format: 'jwk' }), kid: 'offline-employee', use: 'sig', alg: 'EdDSA' }
    const departments = ['production', 'procurement', 'finance', 'marketing']
    const spaces = Object.fromEntries(departments.map(department => [department, {
      space_id: `offline-${department}`, member: 'voter', admin: 'voter',
    }]))
    portalServer = createHttpServer((req, res) => {
      const path = new URL(req.url ?? '/', 'http://localhost').pathname
      let body, status = 200
      if (path === '/.well-known/jwks.json') body = { keys: [jwk] }
      else if (path === '/open-apis/auth/v3/tenant_access_token/internal') {
        body = { code: 0, tenant_access_token: 'offline-test-token', expire: 7200 }
      } else if (path.startsWith('/open-apis/wiki/v2/spaces/') && path.endsWith('/members')) {
        const space = path.split('/')[5]
        const members = space === 'offline-master'
          ? [{ member_id: 'offline-employee', member_role: 'admin', member_type: 'openid' }]
          : space === 'offline-production'
            ? [{ member_id: 'offline-voter', member_role: 'member', member_type: 'openid' }]
            : []
        body = { code: 0, data: { members, has_more: false } }
      } else { status = 404; body = { code: 404, msg: 'Not in the offline fixture' } }
      res.writeHead(status, { 'content-type': 'application/json', 'access-control-allow-origin': '*' })
      res.end(JSON.stringify(body))
    })
    await new Promise(resolve => portalServer.listen(0, '127.0.0.1', resolve))
    env.PORTAL_BASE_URL = `http://127.0.0.1:${portalServer.address().port}`
    env.PORTAL_AUDIENCE = 'bridgeflow'
    env.FEISHU_BASE_URL = env.PORTAL_BASE_URL
    env.FEISHU_APP_ID = 'offline-test'
    env.FEISHU_APP_SECRET = 'offline-test'
    env.ACCESS_CONTROL_PATH = `${scratch}/access.yaml`
    await writeFile(env.ACCESS_CONTROL_PATH, JSON.stringify({ spaces: {
      departments: spaces,
      master_office: { space_id: 'offline-master', member: 'employee', admin: 'employee' },
    }, roles: {
      employee: { departments, operations: ['batch_import', 'confirm_mapping', 'review_note', 'discovery_upload', 'discovery_register', 'discovery_propose', 'discovery_graph_save', 'discovery_score_save', 'discovery_meeting_save', 'discovery_decision_propose', 'discovery_decision_vote', 'discovery_decision_resolve', 'discovery_decision_finalize'] },
      voter: { departments: ['production'], operations: ['discovery_decision_vote'] },
    } }))
    const encode = value => Buffer.from(JSON.stringify(value)).toString('base64url')
    const makeEmployeeToken = subject => {
      const unsigned = `${encode({ alg: 'EdDSA', kid: jwk.kid })}.${encode({ sub: subject, iss: env.PORTAL_BASE_URL, aud: 'bridgeflow', iat: Math.floor(Date.now() / 1000), exp: Math.floor(Date.now() / 1000) + 900 })}`
      return `${unsigned}.${sign(null, Buffer.from(unsigned), privateKey).toString('base64url')}`
    }
    employeeToken = makeEmployeeToken('offline-employee')
    secondEmployeeToken = makeEmployeeToken('offline-voter')
  }
  const patch = (await readFile(`${root}/dsh/enterprise.patch.yml`, 'utf8'))
    .replace("'../plugins/src/index.ts'", JSON.stringify(`${root}/plugins/src/index.ts`))
    .replace('./dsh/presets', `${root}/dsh/presets`)
    .replace('http://127.0.0.1:8000', `http://127.0.0.1:${backendPort}`)
    .replace('approvalMode: native', 'approvalMode: native\n        decisionTimeoutMs: 5000')
    + (live ? liveModelPatch() : `\n- id: agent-default-model\n  name: '@deepseek-ai/dsh-agent-default-model'\n  config:\n    provider: bridgeflow-offline-test\n    model: offline\n- insert:\n    - id: scripted-test-model\n      name: ${JSON.stringify(`${root}/plugins/tests/fixtures/scripted-model/index.ts`)}\n`)
  await writeFile(`${scratch}/web.yml`, patch)
  start(python, ['-m', 'uvicorn', 'bridgeflow.api.main:app', '--host', '127.0.0.1', '--port', String(backendPort)])
  const web = start(resolveDsh(), ['web', '--patch', `${scratch}/web.yml`, '--no-open', '--port', String(webPort)])
  const deadline = Date.now() + 30_000
  let match
  while (Date.now() < deadline) {
    match = logs.match(/dsh web: (http:\/\/127\.0\.0\.1:\d+\/\?token=[^\s)]+)/)
    if (match) break
    if (processes.some(child => child.exitCode !== null)) throw new Error('Service exited before readiness')
    await new Promise(resolve => setTimeout(resolve, 100))
  }
  assert(match, 'DSH did not become ready')
  // #97: a partial client graph only surfaces as a locator timeout inside the
  // browser; catch it here, where the cause is still nameable.
  await assertClientModulesServed(match[1])
  browser = await chromium.launch({ headless: true })
  page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, locale: 'zh-CN' })
  if (employeeMode) await page.addInitScript(token => {
    // Cold-reload verification navigates through a document without a storage origin.
    if (location.protocol === 'http:' || location.protocol === 'https:') {
      sessionStorage.setItem('bridgeflow.portal-token', token)
    }
  }, employeeToken)
  const errors = []
  page.on('pageerror', error => { errors.push(error.message); logs += '\nBROWSER: ' + error.message })
  page.on('console', message => { if (message.type() === 'error') logs += '\nCONSOLE: ' + message.text() })
  page.setDefaultTimeout(15000)
  await page.goto(match[1])
  // #110: a new user on a zh-CN browser defaults to English; the explicit switch
  // to Chinese goes through the native Settings language row and persists.
  await assertDefaultEnglish(page)
  await switchLanguage(page, '中文')
  // #225: importing has one entry, the Sources pane's Add sources dialog.
  const sources = page.getByRole('complementary', { name: '来源', exact: true })
  await sources.getByRole('button', { name: '＋ 添加来源', exact: true }).click({ timeout: 30_000 })
  const importer = page.getByRole('dialog', { name: '添加来源', exact: true })
  await importer.locator('input[name=period]').fill('2025-11')
  const limits = await page.evaluate(async () => (await fetch('/bridgeflow/config')).json())
  assert.equal(limits.maxUploadBytes, 25 * 1024 * 1024)
  assert.equal(limits.maxRequestBytes, 26 * 1024 * 1024)
  assert.equal(limits.decisionTimeoutMs, 5000)
  assert.equal((await fetch(`http://127.0.0.1:${webPort}/bridgeflow/config`)).status, 401)
  // Use the file chooser's disk path, avoiding a large base64 CDP transfer.
  await writeFile(`${scratch}/oversized.csv`, Buffer.alloc(limits.maxUploadBytes + 1))
  await importer.locator('input[name=production]').setInputFiles(`${scratch}/oversized.csv`)
  let uploads = 0
  const countUpload = request => { if (request.method() === 'POST' && request.url().endsWith('/bridgeflow/batches')) uploads++ }
  page.on('request', countUpload)
  await importer.getByRole('button', { name: '导入并检查', exact: true }).click()
  await importer.getByText('请选择至少一个 CSV/XLSX，文件总大小不得超过上限。', { exact: true }).waitFor()
  assert.equal(uploads, 0, 'Oversized data must be rejected before the upload request')
  page.off('request', countUpload)
  await importer.locator('input[name=production]').setInputFiles({ name: 'production.csv', mimeType: 'text/csv', buffer: Buffer.from('sku,output_qty\nSKU-A1,17\n') })
  await importer.getByRole('button', { name: '导入并检查', exact: true }).click()
  // A saved batch closes the dialog and opens its Data view; the master rows live in
  // the batch tables dialog.
  await page.waitForURL(/[?&]batch=[a-f0-9]{32}/)
  await page.evaluate(() => { const q = new URLSearchParams(location.hash.slice(12)); location.hash = `bridgeflow?batch=${q.get('batch')}&view=master` })
  await page.getByText('主表 1 行 · 待确认映射 0 条').waitFor()
  await page.getByRole('cell', { name: '17', exact: true }).waitFor()
  await page.screenshot({ path: `${scratch}/data-workspace.png`, fullPage: true })
  const data = await page.evaluate(async () => {
    const rejected = await fetch('/bridgeflow/tools/confirm-mapping', { method: 'POST', body: '{}' })
    return { status: rejected.status, boot: JSON.stringify(window.__DSH_BOOT__) }
  })
  assert.equal(data.status, 403)
  for (const name of ['bridgeflow-plugins', 'dsh-client-ui-approval', 'dsh-client-ui-trajectory', 'dsh-client-ui-chat']) assert(data.boot.includes(name), name)
  for (const name of ['dsh-client-ui-cordis', 'dsh-client-ui-settings-plugins', 'dsh-client-ui-attachment', 'dsh-client-ui-permission-presets', 'dsh-client-ui-settings-models']) assert(!data.boot.includes(name), name)
  // dsh's own model picker chooses among configured models; adding providers stays off.
  assert(data.boot.includes('dsh-client-ui-model-selection'), 'dsh-client-ui-model-selection')
  assert.equal((await fetch(`http://127.0.0.1:${webPort}/bridgeflow/batches/00000000000000000000000000000000`)).status, 401)
  await page.getByRole('button', { name: '关闭', exact: true }).click()
  await page.getByRole('button', { name: '会话与设置', exact: true }).click()
  await page.getByRole('button', { name: /^(Choose workspace|选择工作区)$/ }).click()
  await page.getByRole('menuitem', { name: 'BridgeFlow', exact: true }).click()
  const composer = page.locator('[contenteditable=true]').first()
  const request = step => `这是隔离测试目录中的合成映射验收。请只调用一次 confirm_mapping，参数 source="sku:test-${step}", target="customer:test", relation="ordered_by", accepted=true, evidence="合成业务用例的人工作业关系", period="2025-11"。等待操作者审批，随后简短说明实际结果，若拒绝必须原样转述理由。不要重试，不调用其他工具或提问。`
  // #96: the first summary request fails; the card must say so and offer a working retry.
  let failDetailOnce = true
  await page.route('**/bridgeflow/approval-detail**', route => { if (failDetailOnce) { failDetailOnce = false; return route.fulfill({ status: 503, body: 'unavailable' }) } return route.continue() })
  await composer.fill(live ? request(0) : 'Exercise the approved mapping fixture.')
  await composer.press('Enter')
  await page.getByText(/决定摘要加载失败|decision summary failed to load/).waitFor({ timeout: 30_000 })
  await page.getByRole('region', { name: '映射审批' }).getByRole('button', { name: /^(重试|Retry)$/ }).click()
  // #110: the approval card renders the structured decision summary localized —
  // labels translated, values verbatim — not just translated buttons.
  const decision = page.getByRole('region', { name: '映射审批' })
  await decision.locator('.bf-approval-detail').first().waitFor({ timeout: 30_000 })
  await decision.getByText('sku:test-0', { exact: true }).waitFor()
  await decision.getByText('接受映射', { exact: true }).waitFor()
  await decision.getByText('决定时展示的依据', { exact: true }).waitFor()
  const revisionBefore = await page.evaluate(() => Number(document.body.dataset.bfDataRevision ?? 0))
  await page.getByRole('button', { name: /^(允许一次|Allow once)$/ }).click({ timeout: 30_000 })
  await waitTurn(1)
  // The approved write reaches the Studio by itself: every page is told to reload, no Refresh click.
  await page.waitForFunction(before => Number(document.body.dataset.bfDataRevision ?? 0) > before, revisionBefore, { timeout: 10_000 })
  const revisionAfterWrite = await page.evaluate(() => Number(document.body.dataset.bfDataRevision ?? 0))
  const acceptedMemory = await readFile(`${scratch}/mappings.json`, 'utf8')
  assert(acceptedMemory.includes('sku:test-0'))
  if (employeeMode) {
    assert(acceptedMemory.includes('offline-employee'), 'The persisted decision must name the verified employee')
    assert(!acceptedMemory.includes('dsh-authenticated-session'), 'Employee approval must not fall back to shared identity')
  } else {
    assert(acceptedMemory.includes('dsh-authenticated-session'))
  }
  await composer.fill(live ? request(2) : 'Exercise the rejected mapping fixture.')
  await composer.press('Enter')
  // #96: decide with the keyboard only. Focus lands on the card; Tab reaches the reason, then Reject.
  const reason = page.getByRole('textbox', { name: '拒绝理由', exact: true })
  await reason.waitFor({ timeout: 30_000 })
  await page.waitForFunction(() => document.activeElement?.classList.contains('bf-decision'))
  await page.keyboard.press('Tab')
  assert.equal(await reason.evaluate(el => el === document.activeElement), true, 'Tab from the card reaches the reason')
  await page.keyboard.type('客户编码未核实，请销售负责人确认后再提交。')
  await page.screenshot({ path: `${scratch}/rejection-note.png`, fullPage: true })
  await page.keyboard.press('Tab')
  assert.match(await page.evaluate(() => document.activeElement?.textContent ?? ''), /^(拒绝|Reject)$/)
  await page.keyboard.press('Enter')
  await waitTurn(2)
  assert.equal(await page.evaluate(() => Number(document.body.dataset.bfDataRevision ?? 0)), revisionAfterWrite, 'a rejected call wrote nothing, so nothing reloads')
  const afterRejection = await sessionEvents()
  const refusalNarration = afterRejection.filter(e => e.type === 'assistant/message').at(-1).data.message.content
    .filter(block => block.type === 'text').map(block => block.text).join('\n')
  if (live) {
    assert(refusalNarration.includes('客户编码未核实'), refusalNarration)
    assert(/拒绝|未.*(写入|保存|确认|执行)/.test(refusalNarration), refusalNarration)
    // An overclaim is a sentence promising the question is gone. A sentence that says the
    // opposite ("不能说以后不再询问", "未来仍可能再次询问") is the correct narration, so it is
    // judged per sentence and qualified sentences are not violations.
    const overclaims = refusalNarration.split(/[。\n；;]/).filter(sentence =>
      /不会.{0,12}(询问|再问)|不再.{0,6}(询问|问)/.test(sentence) && !/不能|无法|没法|不保证|不代表|未必|不一定|可能|仍|并不/.test(sentence))
    assert.deepEqual(overclaims, [], refusalNarration)
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
  // #87: the note is attributed to the final decision only because that decision was a rejection.
  assert.equal(noteEvents[0].data.status, 'final')
  assert.equal(noteEvents[0].data.outcome, 'rejected')
  assert(events.some(event => event.type === 'tool/result' && JSON.stringify(event).includes(noteEvents[0].data.note))
    || events.some(event => event.type.includes('tool') && JSON.stringify(event).includes('The reviewer said')))
  assert.equal(asks.length, 3)
  assert.deepEqual(decisions.map(event => event.data.outcome), ['allowed-once', 'rejected', 'cancelled'])
  assert.deepEqual(decisions.map(event => event.data.id), asks.map(event => event.data.id))
  for (const group of await page.getByText(/^(1 tool call|1 次工具调用)$/).all()) await group.click()
  assert.equal(await page.getByRole('region', { name: '映射决定' }).count(), 3)
  await page.screenshot({ path: `${scratch}/native-approval.png`, fullPage: true })
  if (discoveryMode) {
    await page.getByRole('button', { name: '立项材料与候选', exact: true }).click()
    const discovery = page.getByRole('region', { name: '立项材料与候选', exact: true })
    await discovery.getByLabel('项目标识', { exact: true }).fill('browser-project')
    await discovery.getByRole('button', { name: '打开项目', exact: true }).click()
    for (const [name, value] of Object.entries({ id: 'browser-material', department: 'production', period: '2026-09', source_description: 'Offline browser fixture' })) {
      await discovery.locator(`input[name=${name}]`).fill(value)
    }
    await discovery.locator('input[name=file]').setInputFiles({ name: 'material.csv', mimeType: 'text/csv', buffer: Buffer.from('a,b\n') })
    await discovery.getByRole('button', { name: '暂存材料', exact: true }).click()
    const instruction = discovery.getByRole('textbox', { name: '登记审批请求', exact: true })
    await instruction.waitFor()
    const message = await instruction.inputValue()
    assert(message.includes('browser-material'))
    await page.screenshot({ path: `${scratch}/discovery-staged.png`, fullPage: true })
    await page.evaluate(() => { location.hash = '#bridgeflow?view=state' })
    await composer.fill(message)
    await composer.press('Enter')
    const registration = page.getByRole('region', { name: '材料登记确认', exact: true })
    await registration.getByText(/browser-material/).waitFor()
    await registration.getByRole('button', { name: '允许一次', exact: true }).click()
    await waitTurn(4)
    await page.getByRole('button', { name: '立项材料与候选', exact: true }).click()
    await discovery.getByLabel('项目标识', { exact: true }).fill('browser-project')
    await discovery.getByRole('button', { name: '打开项目', exact: true }).click()
    await discovery.getByText('material.csv · browser-material · v1', { exact: true }).waitFor()
    const downloadEvent = page.waitForEvent('download')
    await discovery.getByRole('button', { name: '下载此版本原件', exact: true }).click()
    const original = await downloadEvent
    assert.equal(original.suggestedFilename(), 'material.csv')
    assert.equal(await readFile(await original.path(), 'utf8'), 'a,b\n')
    await discovery.getByRole('button', { name: '查看详情与依据', exact: true }).click()
    await discovery.locator('details.bf-raw-record > summary').click()
    await discovery.locator('pre').getByText(/"detected_kind": "template"/).waitFor()
    await page.screenshot({ path: `${scratch}/discovery-registered.png`, fullPage: true })
    await discovery.getByRole('button', { name: '候选', exact: true }).click()
    const editor = discovery.getByRole('region', { name: '候选共创', exact: true })
    await editor.getByLabel('候选标识', { exact: true }).fill('browser-opportunity')
    await editor.getByLabel('候选标题', { exact: true }).fill('核对交接问题')
    await editor.getByLabel('涉及部门（每行一个准确名称）', { exact: true }).fill('production')
    await editor.getByLabel('陈述内容', { exact: true }).fill('需要确认实际交接缺口，空模板不能证明问题已发生。')
    await editor.getByLabel('来源材料标识', { exact: true }).fill('browser-material')
    await editor.getByLabel('工作表名称', { exact: true }).fill('csv')
    await editor.getByLabel('待确认问题（每行一条）', { exact: true }).fill('请提供一次实际交接案例。')
    async function approveProposal(turn) {
      await editor.getByRole('button', { name: '准备候选审批请求', exact: true }).click()
      const instruction = await editor.getByRole('textbox', { name: '候选审批请求', exact: true }).inputValue()
      await page.evaluate(() => { location.hash = '#bridgeflow?view=state' })
      await composer.fill(instruction); await composer.press('Enter')
      const card = page.getByRole('region', { name: '候选提案确认', exact: true })
      await card.getByText(/browser-opportunity/).waitFor()
      await card.getByRole('button', { name: '允许一次', exact: true }).click()
      await waitTurn(turn)
      await page.getByRole('button', { name: '立项材料与候选', exact: true }).click()
      await discovery.getByLabel('项目标识', { exact: true }).fill('browser-project')
      await discovery.getByRole('button', { name: '打开项目', exact: true }).click()
      await discovery.getByRole('button', { name: '候选', exact: true }).click()
    }
    await approveProposal(5)
    await discovery.getByText('核对交接问题 · browser-opportunity · v1', { exact: true }).waitFor()
    await discovery.getByRole('button', { name: '修订此候选', exact: true }).click()
    await editor.getByText('基于版本: 1', { exact: true }).waitFor()
    await editor.getByLabel('候选标题', { exact: true }).fill('核对交接问题（待试点）')
    await approveProposal(6)
    await discovery.getByText('核对交接问题（待试点） · browser-opportunity · v2', { exact: true }).waitFor()
    await discovery.getByRole('button', { name: '查看详情与依据', exact: true }).click()
    await discovery.locator('details.bf-raw-record > summary').click()
    await discovery.locator('pre').getByText(/"approval": "not_decided"/).waitFor()
    await page.screenshot({ path: `${scratch}/discovery-opportunity.png`, fullPage: true })
    await discovery.getByRole('button', { name: '设计流程草图', exact: true }).click()
    const flow = discovery.getByRole('region', { name: '流程图编辑', exact: true })
    await flow.getByLabel('图标识', { exact: true }).fill('browser-flow')
    await flow.getByLabel('图标题', { exact: true }).fill('待确认交接流程')
    for (let i = 0; i < 2; i++) {
      await flow.getByRole('button', { name: '添加节点', exact: true }).click()
      await flow.getByLabel('节点标识', { exact: true }).nth(i).fill(`stage${i}`)
      await flow.getByLabel('节点标题', { exact: true }).nth(i).fill(`阶段 ${i}`)
      await flow.getByLabel('负责角色', { exact: true }).nth(i).fill('业务负责人')
      await flow.getByLabel('触发条件', { exact: true }).nth(i).fill('由负责人确认触发')
      await flow.getByLabel('材料标识', { exact: true }).nth(i).fill('browser-material')
      await flow.getByLabel('工作表', { exact: true }).nth(i).fill('csv')
    }
    await flow.getByRole('button', { name: '添加关系', exact: true }).click()
    await flow.getByLabel('关系标识', { exact: true }).fill('return-edge')
    await flow.getByLabel('起点', { exact: true }).selectOption('stage1')
    await flow.getByLabel('终点', { exact: true }).selectOption('stage0')
    await flow.getByLabel('关系说明', { exact: true }).fill('返工过程缺少实际材料，待负责人确认。')
    await flow.getByLabel('返工关系', { exact: true }).check()
    await flow.getByRole('button', { name: '准备流程图审批请求', exact: true }).click()
    const flowRequest = await flow.getByRole('textbox', { name: '流程图审批请求', exact: true }).inputValue()
    assert(flowRequest.includes('"opportunity_version": 2'))
    await page.screenshot({ path: `${scratch}/discovery-flow-edit.png`, fullPage: true })
    await page.evaluate(() => { location.hash = '#bridgeflow?view=state' })
    await composer.fill(flowRequest); await composer.press('Enter')
    const graphApproval = page.getByRole('region', { name: '流程草图确认', exact: true })
    await graphApproval.getByText(/return-edge/).waitFor()
    await graphApproval.getByRole('button', { name: '允许一次', exact: true }).click()
    await waitTurn(7)
    await page.getByRole('button', { name: '立项材料与候选', exact: true }).click()
    await discovery.getByLabel('项目标识', { exact: true }).fill('browser-project')
    await discovery.getByRole('button', { name: '打开项目', exact: true }).click()
    await discovery.getByRole('button', { name: '流程图', exact: true }).click()
    await discovery.getByText('待确认交接流程 · browser-flow · v1', { exact: true }).waitFor()
    await discovery.getByRole('button', { name: '查看详情与依据', exact: true }).click()
    const diagram = discovery.getByRole('region', { name: '流程草图', exact: true })
    await diagram.getByRole('img', { name: '信息流与文件流' }).waitFor()
    await diagram.getByRole('button', { name: /阶段 1 → 阶段 0.*缺失.*返工/ }).click()
    await diagram.getByText('返工过程缺少实际材料，待负责人确认。', { exact: true }).waitFor()
    await diagram.getByRole('button', { name: '阶段 0', exact: true }).click()
    await diagram.getByText(/browser-material.*v1/).waitFor()
    await page.screenshot({ path: `${scratch}/discovery-flow.png`, fullPage: true })
    async function fillRating(id, complete) {
      await discovery.getByRole('button', { name: '候选', exact: true }).click()
      await discovery.getByRole('button', { name: '为候选评分', exact: true }).click()
      const editor = discovery.getByRole('region', { name: '候选评分编辑', exact: true })
      await editor.getByLabel('评分标识', { exact: true }).fill(id)
      const effort = editor.getByRole('group', { name: '投入评分', exact: true })
      await effort.getByLabel('分值（可留空）', { exact: true }).fill('3')
      await effort.getByLabel('评分理由', { exact: true }).fill('Synthetic effort estimate for browser verification')
      await effort.getByRole('button', { name: '添加依据', exact: true }).click()
      await effort.getByLabel('材料标识', { exact: true }).fill('browser-material')
      await effort.getByLabel('工作表', { exact: true }).fill('csv')
      if (complete) {
        const value = editor.getByRole('group', { name: '价值评分', exact: true })
        await value.getByLabel('分值（可留空）', { exact: true }).fill('8')
        await value.getByLabel('评分理由', { exact: true }).fill('Synthetic value hypothesis, not measured savings')
        await value.getByRole('button', { name: '添加依据', exact: true }).click()
        await value.getByLabel('材料标识', { exact: true }).fill('browser-material')
        await value.getByLabel('工作表', { exact: true }).fill('csv')
      }
      await editor.getByRole('button', { name: '准备评分审批请求', exact: true }).click()
      const instruction = await editor.getByRole('textbox', { name: '评分审批请求', exact: true }).inputValue()
      await page.evaluate(() => { location.hash = '#bridgeflow?view=state' })
      await composer.fill(instruction); await composer.press('Enter')
      const approval = page.getByRole('region', { name: '候选评分确认', exact: true })
      await approval.getByText(new RegExp(id)).waitFor()
      await approval.getByRole('button', { name: '允许一次', exact: true }).click()
      await waitTurn(complete ? 8 : 9)
      await page.getByRole('button', { name: '立项材料与候选', exact: true }).click()
      await discovery.getByLabel('项目标识', { exact: true }).fill('browser-project')
      await discovery.getByRole('button', { name: '打开项目', exact: true }).click()
      await discovery.getByRole('button', { name: '评分四象限', exact: true }).click()
    }
    await fillRating('browser-rating', true)
    const board = discovery.getByRole('region', { name: '评分四象限', exact: true })
    await board.getByRole('button', { name: 'browser-opportunity · browser-rating', exact: true }).click()
    await board.getByRole('region', { name: '评分依据', exact: true }).getByText('Synthetic value hypothesis, not measured savings', { exact: true }).waitFor()
    await fillRating('incomplete-rating', false)
    await board.getByText(/价值评分缺少分值、理由或依据/).waitFor()
    assert.equal(await board.locator('svg circle').count(), 1)
    await board.locator('svg').scrollIntoViewIfNeeded()
    await page.screenshot({ path: `${scratch}/discovery-quadrants.png`, fullPage: true })
    const policy = JSON.parse(await readFile(env.DISCOVERY_SCORING_POLICY_PATH, 'utf8'))
    await writeFile(env.DISCOVERY_SCORING_POLICY_PATH, JSON.stringify({ ...policy, version: 2 }))
    await board.getByRole('button', { name: '刷新', exact: true }).click()
    await board.getByText(/量表已改变/).first().waitFor()
    assert.equal(await board.locator('svg circle').count(), 0, 'Changed policy must withdraw stale points')
    await discovery.getByRole('button', { name: '候选', exact: true }).click()
    await discovery.getByRole('button', { name: '准备会议', exact: true }).click()
    const meetingEditor = discovery.getByRole('region', { name: '会议记录编辑', exact: true })
    await meetingEditor.getByLabel('会议标识', { exact: true }).fill('browser-meeting')
    await meetingEditor.getByLabel('会议标题', { exact: true }).fill('Offline pilot preparation')
    await meetingEditor.getByRole('group', { name: '范围', exact: true }).getByLabel('陈述 1', { exact: true }).fill('Proposed pilot scope, pending owner review')
    const stages = meetingEditor.getByRole('group', { name: '实施阶段', exact: true })
    await stages.getByLabel('阶段标识', { exact: true }).fill('pilot')
    await stages.getByLabel('阶段标题', { exact: true }).fill('Validate proposal')
    await stages.getByLabel('责任角色', { exact: true }).fill('pilot owner')
    await stages.getByLabel('退出条件（每行一项）', { exact: true }).fill('Owner reviews all cited material')
    await stages.getByLabel('阶段理由（假设／建议）', { exact: true }).fill('Synthetic implementation proposal')
    await meetingEditor.getByLabel('本次记录／修订原因', { exact: true }).fill('Prepare discussion')
    async function saveMeeting(turn) {
      await meetingEditor.getByRole('button', { name: '准备会议审批请求', exact: true }).click()
      const instruction = await meetingEditor.getByRole('textbox', { name: '会议审批请求', exact: true }).inputValue()
      await page.evaluate(() => { location.hash = '#bridgeflow?view=state' })
      await composer.fill(instruction); await composer.press('Enter')
      const approval = page.getByRole('region', { name: '会议记录确认', exact: true })
      await approval.getByText(/browser-meeting/).waitFor()
      await approval.getByRole('button', { name: '允许一次', exact: true }).click()
      await waitTurn(turn)
      await page.getByRole('button', { name: '立项材料与候选', exact: true }).click()
      await discovery.getByLabel('项目标识', { exact: true }).fill('browser-project')
      await discovery.getByRole('button', { name: '打开项目', exact: true }).click()
      await discovery.getByRole('button', { name: '会议', exact: true }).click()
    }
    await saveMeeting(10)
    await discovery.getByText('Offline pilot preparation · browser-meeting · v1', { exact: true }).waitFor()
    await discovery.getByRole('button', { name: '修订会议记录', exact: true }).click()
    await meetingEditor.getByLabel('记录阶段', { exact: true }).selectOption('minutes')
    await meetingEditor.getByLabel('参会者记录（每行一人）', { exact: true }).fill('Reported offline participant')
    const minutes = meetingEditor.getByRole('group', { name: '纪要', exact: true })
    await minutes.getByRole('button', { name: '添加陈述', exact: true }).click()
    await minutes.getByLabel('陈述 1', { exact: true }).fill('Further scope confirmation is proposed; no approval')
    await meetingEditor.getByLabel('本次记录／修订原因', { exact: true }).fill('Record discussion; no decision')
    await saveMeeting(11)
    await discovery.getByText('Offline pilot preparation · browser-meeting · v2', { exact: true }).waitFor()
    await discovery.getByRole('button', { name: '查看详情与依据', exact: true }).click()
    await discovery.getByRole('region', { name: '会议记录详情', exact: true }).getByText(/Further scope confirmation is proposed; no approval/).waitFor()
    assert.equal(await discovery.getByLabel('材料文件', { exact: true }).isVisible(), false, 'Upload form is hidden outside materials')
    await discovery.getByRole('region', { name: '会议记录详情', exact: true }).getByRole('heading', { name: '冻结候选版本', exact: true }).scrollIntoViewIfNeeded()
    await page.screenshot({ path: `${scratch}/discovery-meeting.png`, fullPage: true })
    if (employeeMode) {
      await discovery.getByRole('button', { name: '准备 MVP 决策', exact: true }).click()
      const decisionEditor = discovery.getByRole('region', { name: '决策提案编辑', exact: true })
      await decisionEditor.getByLabel('决策标识', { exact: true }).fill('browser-mvp')
      await decisionEditor.getByRole('checkbox', { name: 'browser-opportunity · v2', exact: true }).check()
      await decisionEditor.getByLabel('批准范围（每行一项）', { exact: true }).fill('Synthetic pilot only')
      await decisionEditor.getByLabel('排除范围（每行一项）', { exact: true }).fill('No rollout approval')
      await decisionEditor.getByLabel('提案或修订理由', { exact: true }).fill('Discussed in offline minutes')
      await decisionEditor.getByRole('button', { name: '添加条件', exact: true }).click()
      await decisionEditor.getByLabel('条件标识', { exact: true }).fill('verify-source')
      await decisionEditor.getByLabel('条件说明', { exact: true }).fill('Verify cited source before release')
      await decisionEditor.getByLabel('指定确认人', { exact: true }).selectOption('offline-employee')
      await decisionEditor.getByRole('button', { name: '准备决策提案请求', exact: true }).click()
      const panel = discovery.getByRole('region', { name: '决策详情与操作', exact: true })
      async function submitDecision(turn, approvalName) {
        const instruction = await discovery.getByRole('textbox', { name: '决策审批请求', exact: true }).inputValue()
        await page.evaluate(() => { location.hash = '#bridgeflow?view=state' })
        await composer.fill(instruction); await composer.press('Enter')
        const approval = page.getByRole('region', { name: approvalName, exact: true })
        await approval.getByText(/browser-mvp/).waitFor()
        await approval.getByRole('button', { name: '允许一次', exact: true }).click()
        await waitTurn(turn)
        await page.getByRole('button', { name: '立项材料与候选', exact: true }).click()
        await discovery.getByLabel('项目标识', { exact: true }).fill('browser-project')
        await discovery.getByRole('button', { name: '打开项目', exact: true }).click()
        await discovery.getByRole('button', { name: '决策', exact: true }).click()
        await discovery.getByRole('button', { name: '查看详情与依据', exact: true }).click()
        await panel.getByRole('button', { name: '刷新决策与身份', exact: true }).waitFor()
      }
      await submitDecision(12, '决策提案确认')
      await panel.getByLabel('本次操作理由', { exact: true }).fill('First voter supports scoped pilot')
      await panel.getByLabel('本人投票', { exact: true }).selectOption('yes')
      await panel.getByRole('button', { name: '准备本人投票请求', exact: true }).click()
      await submitDecision(13, '本人投票确认')
      await panel.getByText(/offline-employee · yes/).waitFor()
      assert(await panel.getByRole('button', { name: '准备批准决定请求', exact: true }).isDisabled())
      // Sequential signed identity switch tests personal attribution, not native session isolation.
      await page.evaluate(token => sessionStorage.setItem('bridgeflow.portal-token', token), secondEmployeeToken)
      await panel.getByRole('button', { name: '刷新决策与身份', exact: true }).click()
      await panel.getByText('当前身份: offline-voter', { exact: true }).waitFor()
      assert.equal(await panel.getByRole('button', { name: '准备批准决定请求', exact: true }).count(), 0)
      await panel.getByLabel('本次操作理由', { exact: true }).fill('Second voter independently supports pilot')
      await panel.getByLabel('本人投票', { exact: true }).selectOption('yes')
      await panel.getByRole('button', { name: '准备本人投票请求', exact: true }).click()
      await submitDecision(14, '本人投票确认')
      await panel.getByText(/offline-voter · yes/).waitFor()
      await panel.getByText('待决定', { exact: true }).waitFor()
      assert.equal(await panel.getByRole('region', { name: 'Agent 2 批准范围', exact: true }).count(), 0)
      await page.evaluate(token => sessionStorage.setItem('bridgeflow.portal-token', token), employeeToken)
      await panel.getByRole('button', { name: '刷新决策与身份', exact: true }).click()
      await panel.getByText('当前身份: offline-employee', { exact: true }).waitFor()
      await panel.getByLabel('本次操作理由', { exact: true }).fill('Approve only after source verification')
      await panel.getByRole('button', { name: '准备批准决定请求', exact: true }).click()
      await submitDecision(15, '立项决定确认')
      await panel.getByText('条件式决定，尚未批准交付', { exact: true }).waitFor()
      assert.equal(await panel.getByRole('region', { name: 'Agent 2 批准范围', exact: true }).count(), 0)
      await panel.getByLabel('本次操作理由', { exact: true }).fill('Assigned confirmer checked the source')
      await panel.getByLabel('待确认条件', { exact: true }).selectOption('verify-source')
      await panel.getByRole('button', { name: '添加依据', exact: true }).click()
      await panel.getByLabel('材料标识', { exact: true }).fill('browser-material')
      await panel.getByLabel('工作表', { exact: true }).fill('csv')
      await panel.getByRole('button', { name: '准备条件确认请求', exact: true }).click()
      await submitDecision(16, '决策条件确认')
      await panel.getByText('条件式决定，尚未批准交付', { exact: true }).waitFor()
      assert.equal(await panel.getByRole('region', { name: 'Agent 2 批准范围', exact: true }).count(), 0)
      await panel.getByLabel('本次操作理由', { exact: true }).fill('Conditions verified; release pilot scope')
      await panel.getByRole('button', { name: '准备批准决定请求', exact: true }).click()
      await submitDecision(17, '立项决定确认')
      await panel.getByRole('region', { name: 'Agent 2 批准范围', exact: true }).getByText('当前有效批准范围', { exact: true }).waitFor()
      await panel.getByRole('region', { name: 'Agent 2 批准范围', exact: true }).scrollIntoViewIfNeeded()
      await page.screenshot({ path: `${scratch}/discovery-decision.png`, fullPage: true })
      const votingPolicy = JSON.parse(await readFile(env.DISCOVERY_DECISION_POLICY_PATH, 'utf8'))
      await writeFile(env.DISCOVERY_DECISION_POLICY_PATH, JSON.stringify({ ...votingPolicy, version: 2 }))
      await panel.getByRole('button', { name: '刷新决策与身份', exact: true }).click()
      await panel.getByText('输入已变化，需重审', { exact: true }).waitFor()
      assert.equal(await panel.getByRole('region', { name: 'Agent 2 批准范围', exact: true }).count(), 0)
    }


    await page.evaluate(() => { location.hash = '#bridgeflow?view=state' })
  }
  // #99: an image in the composer shows our way forward (sources), not only the native
  // message pointing at a model selector this deployment removes.
  await composer.click()
  await page.evaluate(() => {
    const bytes = Uint8Array.from(atob('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=='), c => c.charCodeAt(0))
    const data = new DataTransfer()
    data.items.add(new File([bytes], 'table.png', { type: 'image/png' }))
    document.querySelector('[contenteditable=true]').dispatchEvent(new ClipboardEvent('paste', { clipboardData: data, bubbles: true, cancelable: true }))
  })
  const imageNotice = page.getByRole('status', { name: /这里读不了图片里的数字|Numbers in images cannot be read here/ })
  await imageNotice.waitFor({ timeout: 10_000 })
  assert.equal(await imageNotice.getByRole('button', { name: /^(添加来源|Add sources)$/ }).count(), 1)
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
  assert(!logs.includes('Pattern attribute value'), 'HTML identifier patterns must compile')
  assert(!logs.includes('slot entry crashed'), 'Native client slots must not crash during navigation')
  const finalEvents = await sessionEvents()
  const measurement = { discovery_journey: discoveryMode, mode: live ? 'live' : 'offline', employee_identity: employeeMode, approval_outcomes: finalEvents.filter(e => e.type === 'approval/decided').map(e => e.data.outcome), refusalNarration,
    model_requests: finalEvents.filter(e => e.type === 'assistant/message').length,
    usage: finalEvents.filter(e => e.type === 'assistant/message' && e.data.usage).reduce((total, e) => {
      for (const [key, value] of Object.entries(e.data.usage)) if (typeof value === 'number') total[key] = (total[key] ?? 0) + value
      return total
    }, {}) }
  await writeFile(`${scratch}/measurement.json`, JSON.stringify(measurement, null, 2))
  await writeFile(`${scratch}/approval-note-audit.json`, JSON.stringify(noteAudit, null, 2))
  await writeFile(`${scratch}/approval-events.json`, JSON.stringify(finalEvents.filter(e => ['approval/asked', 'approval/decided', 'bridgeflow/approval-note', 'tool/result'].includes(e.type)), null, 2))
  console.log(JSON.stringify({ ...measurement, artifacts: scratch }))
  console.log(JSON.stringify({ status: 'passed', screenshot: `${scratch}/data-workspace.png`, approvalScreenshot: `${scratch}/native-approval.png`, checks: ['native shell', 'plugin loading', 'upload', 'master table', 'authenticated proxy', 'write proxy denied', `native approval allow/reject/timeout with ${live ? 'live model' : 'offline adapter'}`, 'approval summary retry after failure', 'keyboard-only rejection', 'image paste guidance', 'paired native audit events', 'zero browser errors'] }))
} catch (error) {
  if (page) { await page.screenshot({path: `${scratch}/failure.png`}); console.error('Screenshot:', `${scratch}/failure.png`); console.error((await page.locator('body').innerText()).slice(0,3000)); await writeFile(`${scratch}/failure.html`, await page.content()); console.error(await page.evaluate(() => ({scripts: [...document.scripts].map(x => x.src), boot: window.__DSH_BOOT__}))) }
  console.error(logs.replace(/([?&]token=)[^\s)]+/g, '$1<redacted>'))
  throw error
} finally {
  await browser?.close()
  if (portalServer) await new Promise(resolve => portalServer.close(resolve))
  for (const child of processes) child.kill('SIGTERM')
  await Promise.all(processes.map(child => new Promise(resolve => {
    if (child.exitCode !== null) return resolve()
    const timer = setTimeout(() => child.kill('SIGKILL'), 5000)
    child.once('exit', () => { clearTimeout(timer); resolve() })
  })))
}
