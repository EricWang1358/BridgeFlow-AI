import assert from 'node:assert/strict'
import { notebookWalkthrough } from './notebook-walkthrough.mjs'
import { assertClientModulesServed, resolveDsh } from './dsh.mjs'
import { assertDefaultEnglish, switchLanguage } from './locale.mjs'
import { spawn } from 'node:child_process'
import { randomBytes } from 'node:crypto'
import { mkdtemp, readFile, readdir, writeFile, mkdir, copyFile, rm, lstat } from 'node:fs/promises'
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
  // Reproduce a shared home left by the Python packed runtime. Official Node
  // boot must heal generated proxies, while leaving real profile state intact.
  for (const name of ['dsh-persona', 'dsh-tool-ask-user']) {
    const dir = `${env.DSH_HOME}/profiles/node_modules/@deepseek-ai/${name}`
    const target = `file:///snapshot/deepseek-harness/node_modules/@deepseek-ai/${name}/lib/index.js`
    await mkdir(dir, {recursive:true})
    await writeFile(`${dir}/package.json`, JSON.stringify({name:`@deepseek-ai/${name}`, version:'0.1.2-rc.1', private:true, type:'module', exports:{'.':'./entry-0.js'}, dsh:{moduleFallback:{targets:{'.':target}}}}))
    await writeFile(`${dir}/entry-0.js`, `export * from ${JSON.stringify(target)}`)
  }
  const patch = (await readFile(`${root}/dsh/enterprise.patch.yml`, 'utf8'))
    .replace("'../plugins/src/index.ts'", JSON.stringify(`${root}/plugins/src/index.ts`))
    .replace('./dsh/presets', `${root}/dsh/presets`)
    .replace('http://127.0.0.1:8000', `http://127.0.0.1:${backendPort}`)
    .replace('approvalMode: native', 'approvalMode: native\n        decisionTimeoutMs: 5000')
    + (live ? '' : `\n- id: agent-default-model\n  name: '@deepseek-ai/dsh-agent-default-model'\n  config:\n    provider: bridgeflow-offline-test\n    model: offline\n- insert:\n    - id: scripted-test-model\n      name: ${JSON.stringify(`${root}/plugins/tests/fixtures/scripted-model/index.ts`)}\n`)
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
  const errors = []
  const createResponses = []
  const promptRequests = []
  page.on('request', request => { if (request.url().endsWith('/session/prompt')) promptRequests.push(request) })
  page.on('response', response => {
    if (response.url().endsWith('/session/create')) createResponses.push(response.json())
  })
  const failedConsole = []
  page.on('pageerror', error => { errors.push(error.message); logs += '\nBROWSER: ' + error.message })
  page.on('console', message => { if (message.type() === 'error') { logs += '\nCONSOLE: ' + message.text(); if (!message.text().startsWith('Failed to load resource:')) failedConsole.push(message.text()) } })
  page.setDefaultTimeout(live ? 240000 : 30000)
  await page.goto(match[1])
  // #110: a new user on a zh-CN browser defaults to English; switch explicitly.
  await assertDefaultEnglish(page)
  await switchLanguage(page, '中文')
  const anonymous = await browser.newContext()
  const anonymousPage = await anonymous.newPage()
  assert.equal((await anonymousPage.request.get(`http://127.0.0.1:${webPort}/bridgeflow/quotation/contract`)).status(), 401)
  await anonymous.close()
  const sources = page.getByRole('complementary', {name:'来源', exact:true})
  const studio = page.getByRole('complementary', {name:'工作室', exact:true})
  await sources.getByRole('button', {name:'＋ 添加来源',exact:true}).waitFor()
  const chat = page.locator('[data-slot="conversation"] > div')
  const bounds = await Promise.all([sources, chat, studio].map(async el => el.boundingBox()))
  assert(bounds[0].x + bounds[0].width <= bounds[1].x && bounds[1].x + bounds[1].width <= bounds[2].x, 'Native Chat must occupy the center between Sources and Studio')
  assert(bounds[1].width > 400 && bounds.every(r => r.y >= 52 && r.height > 850), 'Notebook panels fill the viewport')
  await page.waitForTimeout(800)
  await writeFile(`${scratch}/shell.html`, await page.content())

  await page.screenshot({path:`${scratch}/notebook-empty.png`,fullPage:true})
  const sourcesToggle = page.locator('.bf-shell-top').getByRole('button',{name:'来源',exact:true})
  await sourcesToggle.click()
  assert.equal(await sources.isVisible(),false)
  await sourcesToggle.click()
  assert.equal(await sourcesToggle.getAttribute('aria-expanded'),'true')
  let composerIdentity = await page.locator('[contenteditable=true]').first().elementHandle()
  await studio.getByRole('button', { name: /报价工作区/ }).click()
  assert(await composerIdentity.evaluate(el => el === document.querySelector('[contenteditable=true]')), 'Opening a preview must not remount native Chat or its composer')
  const quote = studio.getByRole('main', { name: '报价', exact: true })
  await quote.getByRole('article', { name: '声明模板', exact: true }).waitFor()
  assert.match(await quote.innerText(), /模板预览，尚未生成交易报价/)
  assert.equal(await sources.locator('.bf-resource-list li').count(), 0, 'Declaration inputs are not uploaded sources')
  assert.equal(await page.locator('dialog[open]').count(), 0, 'Blank-session quotation opens in Studio, without replacing Chat with a modal')
  await page.screenshot({path:`${scratch}/quotation-light.png`, fullPage:true})
  await quote.getByText('查看声明公式', {exact:true}).click()
  await quote.getByText('查看字典出处', {exact:true}).click()
  await quote.getByText('dictionary.yaml · quotation', {exact:true}).waitFor()
  const rejected = await page.evaluate(async () => (await fetch('/bridgeflow/quotation/send', {method:'POST', body:'{}'})).status)
  assert.equal(rejected, 403)
  await page.emulateMedia({colorScheme:'dark'})
  await page.waitForTimeout(150)
  await studio.locator('.bf-shell-scroll').evaluate(el => {el.scrollTop=0})
  await page.screenshot({path:`${scratch}/quotation-dark.png`, fullPage:true})
  await page.setViewportSize({width:760,height:1000})
  assert(await quote.evaluate(el => el.scrollWidth <= el.clientWidth + 1), 'The workspace must not overflow at narrow widths')
  await page.screenshot({path:`${scratch}/quotation-narrow.png`, fullPage:true})
  await page.setViewportSize({width:1440,height:1000})
  await page.reload()
  await studio.getByRole('main', {name:'报价'}).getByRole('article', {name:'声明模板'}).waitFor()
  const english = await browser.newContext({locale:'en-US', viewport:{width:1440,height:1000}, storageState:await page.context().storageState()})
  const en = await english.newPage()
  en.on('pageerror', e => errors.push(e.message))
  await en.goto(`http://127.0.0.1:${webPort}/#bridgeflow?view=quotation`)
  // #110: the saved preference (zh, chosen above) outranks this context's en-US
  // browser language — preference wins over browser derivation by design.
  await switchLanguage(en, 'English')
  await en.getByRole('article', {name:'Declared template',exact:true}).waitFor()
  await en.screenshot({path:`${scratch}/quotation-en.png`,fullPage:true})
  await english.close()
  // The preference is shared and durable; hand Chinese back to the main flow.
  await switchLanguage(page, '中文')
  composerIdentity = await page.locator('[contenteditable=true]').first().elementHandle()
  // Real source lifecycle: import through Sources, preview before sanitation,
  // paginate, reload the route, and switch batches without stale originals.
  await sources.getByRole('button', {name:'＋ 添加来源',exact:true}).click()
  const importer = page.getByRole('dialog', {name:'添加来源',exact:true})
  await importer.locator('input[type=month]').fill('2025-11')
  const csv = 'item,value\n' + Array.from({length:65}, (_,i) => `SOURCE-A-${i},${i}`).join('\n')
  await importer.locator('input[name=production]').setInputFiles({name:'original-production.csv',mimeType:'text/csv',buffer:Buffer.from(csv)})
  await importer.getByRole('button', {name:'导入并检查',exact:true}).click()
  const original = sources.getByRole('button', {name:/original-production.csv/})
  await original.waitFor()
  await original.click()
  const preview = studio.getByRole('region', {name:'来源预览',exact:true})
  await preview.getByRole('cell', {name:'SOURCE-A-0',exact:true}).waitFor()
  assert(await composerIdentity.evaluate(el => el === document.querySelector('[contenteditable=true]')), 'Import and preview retain the native composer')
  assert.equal(await preview.locator('tbody tr').count(),50)
  await preview.getByRole('button', {name:'下一页',exact:true}).click()
  await preview.getByRole('cell', {name:'SOURCE-A-50',exact:true}).waitFor()
  assert.equal(await preview.locator('tbody tr').count(),15)
  assert.equal(await preview.getByRole('button',{name:'下一页',exact:true}).isDisabled(),true)
  await preview.getByRole('button',{name:'上一页',exact:true}).click()
  await preview.getByRole('cell',{name:'SOURCE-A-0',exact:true}).waitFor()
  assert.equal(await preview.getByRole('cell',{name:'SOURCE-A-50',exact:true}).count(),0)
  assert.equal(await preview.getByRole('button',{name:'上一页',exact:true}).isDisabled(),true)
  await preview.getByText('文件来源信息',{exact:true}).click()
  await preview.getByText('文件指纹（SHA-256）',{exact:true}).waitFor()
  assert.equal(await preview.getByText('批次编号',{exact:true}).count(),1)
  const aHash = new URL(page.url()).hash
  await page.reload()
  await preview.getByRole('cell', {name:'SOURCE-A-0',exact:true}).waitFor()
  await studio.getByRole('button', {name:'展开预览',exact:true}).click()
  await page.getByRole('dialog', {name:'预览',exact:true}).getByRole('cell', {name:'SOURCE-A-0',exact:true}).waitFor()
  const expandedSource=page.getByRole('dialog',{name:'预览',exact:true})
  await expandedSource.getByRole('button',{name:'下一页',exact:true}).click()
  await expandedSource.getByRole('cell',{name:'SOURCE-A-50',exact:true}).waitFor()
  await expandedSource.getByRole('button',{name:'上一页',exact:true}).click()
  await expandedSource.getByRole('cell',{name:'SOURCE-A-0',exact:true}).waitFor()
  await page.getByRole('dialog', {name:'预览',exact:true}).getByRole('button', {name:'关闭',exact:true}).click()
  await page.screenshot({path:`${scratch}/source-preview.png`,fullPage:true})
  await sources.getByRole('button', {name:'＋ 添加来源',exact:true}).click()
  await importer.locator('input[type=month]').fill('2025-11')
  await importer.locator('input[name=production]').setInputFiles({name:'batch-b.csv',mimeType:'text/csv',buffer:Buffer.from('item,value\nSOURCE-B,99')})
  await importer.getByRole('button', {name:'导入并检查',exact:true}).click()
  await sources.getByRole('button', {name:/batch-b.csv/}).waitFor()
  assert.equal(await sources.getByText('original-production.csv',{exact:true}).count(),0)
  assert.equal(await studio.getByRole('cell', {name:'SOURCE-A-0',exact:true}).count(),0)
  await page.goto(`http://127.0.0.1:${webPort}/${aHash}`)
  await preview.getByRole('cell', {name:'SOURCE-A-0',exact:true}).waitFor()
  // An unavailable original is a settled refusal, never a stale table or spinner.
  await page.goto(`http://127.0.0.1:${webPort}/${aHash.replace('source=production','source=finance')}`)
  await studio.getByRole('alert').waitFor()
  await studio.getByText('无法加载此预览，请检查批次或重新选择来源。',{exact:true}).waitFor()
  assert.equal(await studio.getByRole('cell',{name:'SOURCE-A-0',exact:true}).count(),0)
  // Starting the real SDK while Web is alive must not rewrite fallback links
  // into /snapshot. Initialize only: never harness.run or any model request.
  const sdk = start(python, ['-c', `
from deepseek_harness import DeepSeekHarness
from bridgeflow.dsh_runtime import native_command
with DeepSeekHarness(dsh_bin=native_command(), profile="sdk-minimal", initialize_timeout_seconds=30):
    pass
`])
  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => { sdk.kill('SIGKILL'); reject(new Error('SDK initialize timed out')) }, 45000)
    sdk.once('error', error => {clearTimeout(timer); reject(error)})
    sdk.once('exit', code => { clearTimeout(timer); code === 0 ? resolve() : reject(new Error(`SDK initialize failed: ${code}`)) })
  })
  for (const name of ['dsh-persona','dsh-tool-ask-user']) {
    assert((await lstat(`${env.DSH_HOME}/profiles/node_modules/@deepseek-ai/${name}`)).isSymbolicLink(), 'SDK must preserve native module fallback links')
  }
  await page.locator('.bf-shell-top').getByRole('button',{name:'新建笔记本',exact:true}).click()
  await page.getByRole('dialog',{name:'离开前保存笔记本？'}).getByRole('button',{name:'不保存并继续'}).click()
  await page.waitForFunction(() => document.querySelectorAll('.bf-resource-list li').length === 0)
  assert.equal(new URLSearchParams(new URL(page.url()).hash.slice(12)).get('batch'),null)
  await notebookWalkthrough(page,scratch)
  // A full host restart must recover notebook title, purpose, batch and preview
  // from DSH persistence, without relying on the browser's transient drafts.
  const restoreUrl=page.url()
  await page.goto('about:blank')
  const stopped = new Promise(resolve => web.once('exit', resolve))
  web.kill('SIGTERM'); await stopped
  const restartOffset = logs.length
  start(resolveDsh(), ['web','--patch',`${scratch}/web.yml`,'--no-open','--port',String(webPort)])
  const restartDeadline = Date.now()+30000
  while (!logs.slice(restartOffset).includes('dsh web: ') && Date.now()<restartDeadline) await new Promise(resolve=>setTimeout(resolve,100))
  assert(logs.slice(restartOffset).includes('dsh web: '),'Restart did not become ready')
  await page.goto(restoreUrl)
  await page.getByRole('complementary',{name:'来源',exact:true}).getByRole('button',{name:/sample-production.csv/}).waitFor()
  await page.getByRole('complementary',{name:'工作室',exact:true}).getByRole('region',{name:'来源预览'}).waitFor()
  await page.waitForFunction(()=>document.querySelector('.bf-notebook-title')?.value==='业务示例复核')
  const created = await Promise.all(createResponses)
  assert(created.length > 0, 'A real session.create reply is required; blank sessions need not be persisted')
  assert(created.every(reply => reply.result?.ok && reply.result.value?.agentPreset === 'bridgeflow'), 'Every created session must mount the BridgeFlow preset successfully')
  assert.equal(promptRequests.length, 0, 'No session prompt may be submitted')
  assert.deepEqual(errors, [])
  assert.deepEqual(failedConsole, [])
  const sessionPaths = (await readdir(`${scratch}/dsh/sessions`, {recursive:true}).catch(() => [])).filter(p=>p.endsWith('session.jsonl'))
  for (const path of sessionPaths) {
    const events = (await readFile(`${scratch}/dsh/sessions/${path}`,'utf8')).trim().split('\n').map(JSON.parse)
    assert(!events.some(e=>e.type==='request/header' || e.type==='assistant/message'), 'Quotation UI must not invoke a model')
  }
  const evidence = `${root}/docs/evidence/quotation-ui/runs`
  const run = String(Date.now())
  await mkdir(`${evidence}/${run}`, {recursive:true})
  for (const name of ['notebook-empty.png','source-preview.png','quotation-light.png','quotation-dark.png','quotation-narrow.png','quotation-en.png','notebook-history.png','notebook-save.png','notebook-sample.png']) await copyFile(`${scratch}/${name}`,`${evidence}/${run}/${name}`)
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
