import assert from 'node:assert/strict'
import { resolveDsh } from './dsh.mjs'

/** Restart the actual host, then make its native cold reader inspect every session. */
export async function coldReload({page, web, start, args, readLogs, sessionIds}) {
  const restoreUrl = page.url()
  await page.goto('about:blank')
  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => { web.kill('SIGKILL'); reject(new Error('Host did not stop')) }, 10000)
    web.once('exit', () => { clearTimeout(timer); resolve() })
    web.kill('SIGTERM')
  })
  const offset = readLogs().length
  start(resolveDsh(), args)
  const deadline = Date.now() + 30000
  while (!readLogs().slice(offset).includes('dsh web: ') && Date.now() < deadline) {
    await new Promise(resolve => setTimeout(resolve, 100))
  }
  assert(readLogs().slice(offset).includes('dsh web: '), 'Host restart must become ready')
  await page.goto(restoreUrl)
  const statuses = await page.evaluate(async ids => Promise.all(ids.map(async id => {
    const result = await fetch(`/bridgeflow/notebook?session_id=${encodeURIComponent(id)}`)
    return result.status
  })), sessionIds)
  assert(statuses.every(status => status === 200), `Native cold session inspection failed: ${statuses}`)
}
