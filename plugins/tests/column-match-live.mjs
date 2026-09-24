// Live acceptance for #102: a real captain turns a blocked import into an approved
// column match. BILLED — it calls the configured model. Run deliberately:
//   node tests/column-match-live.mjs <web url with token> <DSH_HOME> <batch id> <out dir>
// The person's part (reading the approval card and deciding) is played by this script
// only after it checks that the proposed target is a declared candidate.
import { chromium } from '@playwright/test'
import { readdir, readFile, stat, writeFile } from 'node:fs/promises'

const [url, dshHome, batch, out] = process.argv.slice(2)
const began = Date.now()
const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, locale: 'zh-CN' })
const errors = []; page.on('pageerror', e => errors.push(String(e)))
page.setDefaultTimeout(240_000)

async function sessions() {
  const folder = `${dshHome}/sessions`
  const files = (await readdir(folder, { recursive: true })).filter(p => p.endsWith('session.jsonl'))
  const fresh = []
  for (const file of files) if ((await stat(`${folder}/${file}`)).mtimeMs >= began) fresh.push(`${folder}/${file}`)
  return fresh
}
async function events(path) { return (await readFile(path, 'utf8')).trim().split('\n').map(line => JSON.parse(line)) }

await page.goto(url); await page.waitForTimeout(6000)
await page.evaluate(b => { location.hash = `bridgeflow?batch=${b}&view=columns`; window.dispatchEvent(new Event('bridgeflow:open-data')) }, batch)
await page.getByRole('button', { name: /让 captain 看这批数据|Ask the captain to look/ }).click()

const decisions = []
while (true) {
  const card = page.getByRole('region', { name: /列匹配审批|Column match approval/ })
  try { await card.waitFor({ timeout: decisions.length ? 90_000 : 240_000 }) } catch { break }
  await card.locator('.bf-approval-detail').first().waitFor()
  const detail = await card.innerText()
  await page.screenshot({ path: `${out}/live-approval-${decisions.length + 1}.png`, fullPage: false })
  const allow = /\bproject\b/.test(detail) && /project_code/.test(detail)
  decisions.push({ allow, detail: detail.slice(0, 600) })
  if (allow) await card.getByRole('button', { name: /^(允许一次|Allow once)$/ }).click()
  else { await card.getByRole('textbox').fill('提议的目标不是本部门已声明的候选列'); await card.getByRole('button', { name: /^(拒绝|Reject)$/ }).click() }
  await page.waitForTimeout(3000)
}

let turnEnded = false
for (let i = 0; i < 120 && !turnEnded; i++) {
  for (const path of await sessions()) {
    const log = await events(path)
    if (log.some(e => e.type === 'tool/call' || e.type === 'assistant/message') && log.filter(e => e.type === 'turn/end').length) turnEnded = true
  }
  if (!turnEnded) await page.waitForTimeout(2000)
}
const summary = { decisions, errors, sessions: [] }
for (const path of await sessions()) {
  const log = await events(path)
  const messages = log.filter(e => e.type === 'assistant/message')
  const calls = messages.flatMap(e => e.data.message.content.filter(b => b.type === 'tool-call').map(b => b.name))
  const usage = messages.reduce((u, e) => ({ input: u.input + (e.data.usage?.inputTokens ?? 0), output: u.output + (e.data.usage?.outputTokens ?? 0),
    total: u.total + (e.data.usage?.totalTokens ?? 0), cacheRead: u.cacheRead + (e.data.usage?.cacheReadTokens ?? 0) }), { input: 0, output: 0, total: 0, cacheRead: 0 })
  const narration = messages.at(-1)?.data.message.content.filter(b => b.type === 'text').map(b => b.text).join('\n') ?? ''
  summary.sessions.push({ path, steps: messages.length, calls, usage, turn_end: log.filter(e => e.type === 'turn/end').map(e => e.data.reason?.kind), narration: narration.slice(0, 800) })
}
await page.screenshot({ path: `${out}/live-after.png` })
await writeFile(`${out}/live-102.json`, JSON.stringify(summary, null, 2))
console.log(JSON.stringify(summary))
await browser.close()
