import assert from 'node:assert/strict'
import test from 'node:test'
import { readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { labelKeys } from '../src/client/ui.ts'

/**
 * Copy that nothing renders is the quietest failure this client has (#244): the four
 * `next_<status>` guidance strings existed and were wired to nothing, so an operator
 * importing four departments saw a status chip and a wall.
 *
 * Two directions, both mechanical:
 *
 * 1. Every statically-written `t('…')` / `labelText('…')` call in src must name a
 *    defined key — a typo'd key renders as its own name, in the UI, silently.
 * 2. The `next_*` family is consumed as one `t(\`next_${batch.status}\`)`; some source
 *    outside the dictionary must compose that key, or the whole family is dead again.
 *
 * Dynamic keys (`t(name)`, `t(\`heroStep${n}\`)`) cannot be checked this way and are
 * deliberately out of scope: their sources enumerate values the type system can't see.
 */

const ROOT = join(import.meta.dirname, '..', 'src')
const files: string[] = []
const walk = (dir: string) => {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (entry.isDirectory()) walk(join(dir, entry.name))
    else if (/\.(ts|tsx)$/.test(entry.name)) files.push(join(dir, entry.name))
  }
}
walk(ROOT)
const sources = files
  .map(path => ({ path, text: readFileSync(path, 'utf8') }))
  .filter(({ path }) => !path.endsWith(join('client', 'ui.ts')))

test('every statically-written t()/labelText() key is defined', () => {
  const defined = new Set(labelKeys())
  const undefinedCalls: string[] = []
  for (const { path, text } of sources)
    for (const match of text.matchAll(/\b(?:t|labelText)\(\s*(['`])([a-z0-9_]+)\1\s*\)/g))
      if (!defined.has(match[2]!)) undefinedCalls.push(`${path.replaceAll('\\', '/')}: ${match[2]}`)
  assert.deepEqual(undefinedCalls, [], 'undefined label keys (file: key)')
})

test('the next_<status> guidance family is composed somewhere outside the dictionary', () => {
  const next = labelKeys().filter(key => key.startsWith('next_'))
  assert.ok(next.length >= 4, 'the guidance family shrank; update this test deliberately')
  const composers = sources.filter(({ text }) => /`next_\$\{/.test(text))
  assert.ok(composers.length > 0, 'no source composes a next_<status> key; the guidance copy is dead again (#244)')
})

test('placeholders used by next_* copy are all substituted where it is rendered', () => {
  const dictionary = readFileSync(join(ROOT, 'client', 'ui.ts'), 'utf8')
  const substituted = [...readFileSync(join(ROOT, 'client', 'next-step.tsx'), 'utf8')
    .matchAll(/replaceAll\('\{(\w+)\}',/g)].map(m => m[1]!)
  // Only the next_* label lines, not every brace in the dictionary file.
  const unsubstituted = new Set<string>()
  for (const line of dictionary.split('\n')) {
    if (!/^\s*next_[a-z0-9_]*:/.test(line)) continue
    for (const match of line.matchAll(/\{(\w+)\}/g))
      if (!substituted.includes(match[1]!)) unsubstituted.add(match[1]!)
  }
  assert.deepEqual([...unsubstituted], [], 'placeholders in next_* copy that NextStep does not substitute')
})
