import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { randomBytes } from 'node:crypto'
import { mkdtemp, readFile, readdir, writeFile, mkdir, copyFile, rm } from 'node:fs/promises'
import { createServer } from 'node:net'
import { tmpdir } from 'node:os'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from '@playwright/test'

const live = false
const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
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
  MAPPING_MEMORY_PATH: `${scratch}/mappings.json`, FIELD_DICTIONARY_PATH: `${root}/data/quotation_demo/dictionary.yaml`,
  BRIDGEFLOW_TEST_SCENARIO: 'business', LLM_PROVIDER: 'mock', BRIDGEFLOW_ENABLE_LEGACY_CONSOLE: 'false', BRIDGEFLOW_ALLOW_SAMPLE_DATA: 'false',
}
const processes = []
let browser
let page
let logs = ''
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
  start(process.env.BRIDGEFLOW_DSH ?? 'dsh', ['web', '--patch', `${scratch}/web.yml`, '--no-open', '--port', String(webPort)])
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
  page.setDefaultTimeout(live ? 240000 : 30000)
  await page.goto(match[1])
  const anonymous = await browser.newContext()
  const anonymousPage = await anonymous.newPage()
  assert.equal((await anonymousPage.request.get(`http://127.0.0.1:${webPort}/bridgeflow/quotation/contract`)).status(), 401)
  await anonymous.close()
  await page.getByRole('button', { name: '报价工作区', exact: true }).first().click()
  const quote = page.getByRole('main', { name: '报价', exact: true })
  await quote.getByRole('article', { name: '声明模板', exact: true }).waitFor()
  assert.equal(await page.getByRole('button', { name: '导入与数据', exact: true }).count(), 1)
  assert.match(await quote.innerText(), /模板预览，尚未生成交易报价/)
  assert.equal(await quote.getByRole('complementary').count(), 2)
  const panels = await quote.locator('.bf-notebook-pane').evaluateAll(items => items.map(x => { const r = x.getBoundingClientRect(); return {x:r.x, y:r.y, width:r.width} }))
  assert(panels[0].x < panels[1].x && panels[1].x < panels[2].x, 'Desktop must have sources, workspace and studio side by side')
  await page.screenshot({path:`${scratch}/quotation-light.png`, fullPage:true})
  await quote.getByRole('button', {name:'来源', exact:true}).click()
  assert.equal(await quote.getByRole('complementary', {name:'来源', exact:true}).count(), 0)
  await quote.getByRole('button', {name:'来源', exact:true}).click()
  await quote.getByText('查看声明公式', {exact:true}).click()
  await quote.getByText('查看字典出处', {exact:true}).click()
  await quote.getByText('dictionary.yaml · quotation', {exact:true}).waitFor()
  const rejected = await page.evaluate(async () => (await fetch('/bridgeflow/quotation/send', {method:'POST', body:'{}'})).status)
  assert.equal(rejected, 403)
  await page.emulateMedia({colorScheme:'dark'})
  await page.waitForTimeout(150)
  await page.screenshot({path:`${scratch}/quotation-dark.png`, fullPage:true})
  await page.setViewportSize({width:760,height:1000})
  assert(await quote.evaluate(el => el.scrollWidth <= el.clientWidth + 1), 'The workspace must not overflow at narrow widths')
  await page.screenshot({path:`${scratch}/quotation-narrow.png`, fullPage:true})
  await page.setViewportSize({width:1440,height:1000})
  await page.reload()
  await page.getByRole('main', {name:'报价'}).getByRole('article', {name:'声明模板'}).waitFor()
  const english = await browser.newContext({locale:'en-US', viewport:{width:1440,height:1000}, storageState:await page.context().storageState()})
  const en = await english.newPage()
  en.on('pageerror', e => errors.push(e.message))
  await en.goto(`http://127.0.0.1:${webPort}/#bridgeflow?view=quotation`)
  await en.getByRole('article', {name:'Declared template',exact:true}).waitFor()
  await en.screenshot({path:`${scratch}/quotation-en.png`,fullPage:true})
  await english.close()
  assert.deepEqual(errors, [])
  const sessionPaths = (await readdir(`${scratch}/dsh/sessions`, {recursive:true}).catch(() => [])).filter(p=>p.endsWith('session.jsonl'))
  for (const path of sessionPaths) {
    const events = (await readFile(`${scratch}/dsh/sessions/${path}`,'utf8')).trim().split('\n').map(JSON.parse)
    assert(!events.some(e=>e.type==='request/header' || e.type==='assistant/message'), 'Quotation UI must not invoke a model')
  }
  const evidence = `${root}/docs/evidence/quotation-ui/runs`
  const run = String(Date.now())
  await mkdir(`${evidence}/${run}`, {recursive:true})
  for (const name of ['quotation-light.png','quotation-dark.png','quotation-narrow.png','quotation-en.png']) await copyFile(`${scratch}/${name}`,`${evidence}/${run}/${name}`)
  const runs = (await readdir(evidence)).sort().reverse()
  for (const old of runs.slice(2)) await rm(`${evidence}/${old}`,{recursive:true})
  console.log(JSON.stringify({passed:true, artifacts:scratch, screenshot_run:run, model_requests:0}))
} catch (error) {
  if (page) await page.screenshot({path:`${scratch}/failure.png`,fullPage:true})
  console.error('Quotation UI failed; screenshot directory:',scratch)
  console.error(logs.replace(/([?&]token=)[^\s)]+/g,'$1<redacted>'))
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
