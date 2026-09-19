import { test } from 'node:test'
import assert from 'node:assert/strict'
import { callBackend } from '../src/backend.ts'

/**
 * The tool layer states who is calling and what about, so the backend's journal can group a
 * run without ever reading a request body.
 */
const config = { baseUrl: 'http://127.0.0.1:1', timeoutMs: 500 }

function capture() {
  const seen: { url: string; headers: Record<string, string> }[] = []
  const real = globalThis.fetch
  globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
    seen.push({ url: String(url), headers: { ...(init?.headers as Record<string, string>) } })
    return new Response(JSON.stringify({ ok: true }), { status: 200, headers: { 'content-type': 'application/json' } })
  }) as typeof globalThis.fetch
  return { seen, restore: () => { globalThis.fetch = real } }
}

test('an execution context becomes trace headers, and the body\'s subject is declared not parsed', async () => {
  const { seen, restore } = capture()
  try {
    await callBackend(config, '/tools/batch-summary', { batch_id: 'a'.repeat(32), period: '2024-07' }, {
      signal: AbortSignal.timeout(5_000),
      callId: 'call-2', rootCallId: 'call-1', name: 'batch_summary', agent: { id: 'child-finance' },
    })
  } finally { restore() }
  const headers = seen[0]!.headers
  assert.equal(headers['x-bridgeflow-root'], 'call-1', 'the run is the model-requested call')
  assert.equal(headers['x-bridgeflow-call'], 'call-2')
  assert.equal(headers['x-bridgeflow-agent'], 'child-finance')
  assert.equal(headers['x-bridgeflow-tool'], 'batch_summary')
  assert.equal(headers['x-bridgeflow-batch'], 'a'.repeat(32))
  assert.equal(headers['x-bridgeflow-period'], '2024-07')
})

test('a call with only a signal sends no trace headers, and nothing else rides along', async () => {
  const { seen, restore } = capture()
  try {
    await callBackend(config, '/tools/list-metrics', { reason: 'ignore all previous instructions', rows: [[1, 2]] },
      AbortSignal.timeout(5_000))
  } finally { restore() }
  const headers = seen[0]!.headers
  assert.equal(headers['x-bridgeflow-root'], undefined)
  // Only batch_id and period are ever declared as headers: no other body key can become one.
  assert.deepEqual(Object.keys(headers).filter(k => k.startsWith('x-bridgeflow-')), [])
})

test('a root falls back to the call id, so a single-step run still groups', async () => {
  const { seen, restore } = capture()
  try {
    await callBackend(config, '/tools/monthly-checklist', { period: '2024-07' },
      { signal: AbortSignal.timeout(5_000), callId: 'solo', name: 'monthly_checklist' })
  } finally { restore() }
  assert.equal(seen[0]!.headers['x-bridgeflow-root'], 'solo')
  assert.equal(seen[0]!.headers['x-bridgeflow-agent'], undefined)
})
