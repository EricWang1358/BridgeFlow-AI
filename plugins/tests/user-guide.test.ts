import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, readdirSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { guideMarkdown, userGuide, guideLead } from '../src/client/user-guide.ts'

const here = dirname(fileURLToPath(import.meta.url))
const read = (dir: string): string => readdirSync(dir, { withFileTypes: true })
  .map(e => e.isDirectory() ? read(`${dir}/${e.name}`) : /\.tsx?$/.test(e.name) && e.name !== 'user-guide.ts' && e.name !== 'app-guide.ts' ? readFileSync(`${dir}/${e.name}`, 'utf8') : '').join('\n')
const client = read(resolve(here, '../src/client'))
// Drawn by DSH itself, not by this plugin.
const native = new Set(['对话', '轨迹'])

test('every button the guide names in Chinese is a label the screen shows', () => {
  const texts = [guideLead[0], ...userGuide.flatMap(s => [s.intro?.[0], s.note?.[0], ...(s.steps ?? []).map(x => x[0]), ...(s.points ?? []).map(x => x[0]),
    ...(s.faq ?? []).flatMap(([q, a]) => [q[0], a[0]]), ...(s.terms ?? []).flatMap(([t, m]) => [t[0], m[0]])])].filter(Boolean) as string[]
  const missing = texts.flatMap(text => [...text.matchAll(/「([^」]+)」/g)].map(m => m[1]!)).filter(label => !native.has(label) && !client.includes(`'${label}'`))
  assert.deepEqual([...new Set(missing)], [])
})

test('docs/user-guide.*.md are generated from the in-product guide', () => {
  for (const language of ['zh', 'en'] as const)
    assert.equal(readFileSync(resolve(here, `../../docs/user-guide.${language}.md`), 'utf8'), guideMarkdown(language), `run pnpm docs:guide (${language})`)
})
