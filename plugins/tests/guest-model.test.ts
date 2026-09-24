import assert from 'node:assert/strict'
import { test } from 'node:test'
import { Context } from '@deepseek-ai/cordis'
import * as guest from '../src/guest-model/index.ts'

// The guest instance's stand-in model: never a network call, the note for a chat turn and a
// short name for a title request.
test('guest notice model answers a chat turn with the note and a title request with a name', async () => {
  let adapter: any
  guest.apply({ llm: { registerAdapter: (_names: string[], value: unknown) => { adapter = value } } } as unknown as Context)
  const text = async (tools: unknown[]) => {
    let out = ''
    for await (const chunk of adapter.stream({ messages: [], tools } as any)) if (chunk.type === 'text-delta') out += chunk.text
    return out
  }
  assert.equal(await text([{ name: 'batch_summary' }]), guest.NOTICE)
  assert.equal(await text([]), guest.TITLE)
})
