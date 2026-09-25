import test from 'node:test'
import assert from 'node:assert/strict'
import { readdirSync, readFileSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { guide, guideFeatures } from '../src/app-guide.ts'
import { appGuide } from '../src/tools/app-guide.ts'

const src = resolve(dirname(fileURLToPath(import.meta.url)), '../src')
const read = (dir: string): string => readdirSync(dir, { withFileTypes: true })
  .map(e => e.isDirectory() ? read(`${dir}/${e.name}`) : /\.tsx?$/.test(e.name) && e.name !== 'app-guide.ts' ? readFileSync(`${dir}/${e.name}`, 'utf8') : '').join('\n')
const client = read(`${src}/client`), tools = read(`${src}/tools`)
// Labels drawn by DSH itself rather than by this plugin.
const native = new Set(['轨迹'])

test('every interface word the guide quotes is a label the screen actually shows', () => {
  for (const [feature, entry] of Object.entries(guide)) {
    const texts = [...entry.steps.map(s => s[0]), ...('note' in entry ? [entry.note[0]] : [])]
    for (const text of texts) for (const [, label] of text.matchAll(/「([^」]+)」/g)) {
      if (native.has(label!)) continue
      assert.ok(client.includes(`'${label}'`), `${feature}: 「${label}」 is not a label in client/`)
    }
  }
})

test('every check tool the guide names exists', () => {
  for (const entry of Object.values(guide)) for (const name of ('check' in entry ? entry.check : []))
    assert.ok(tools.includes(`'${name}'`), `${name} is not a registered tool`)
})

test('app_guide answers in both languages and only for listed features', async () => {
  const tool = appGuide() as unknown as { execute(args: Record<string, unknown>): Promise<Record<string, unknown>> }
  const answer = await tool.execute({ feature: 'quadrant_chart' })
  assert.equal(answer.opens_page, 'discovery')
  assert.ok((answer.steps_en as string[]).some(s => s.includes('Rating quadrants')))
  assert.ok((answer.steps_zh as string[]).some(s => s.includes('评分四象限')))
  // A feature outside the list is refused before it runs, so the model cannot invent one.
  await assert.rejects(() => tool.execute({ feature: 'four_quadrant_matrix_that_does_not_exist' }))
  assert.equal(guideFeatures.length, Object.keys(guide).length)
})
