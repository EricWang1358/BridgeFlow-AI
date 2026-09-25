// Writes docs/user-guide.{zh,en}.md from the in-product guide (src/client/user-guide.ts).
import { writeFileSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { guideMarkdown } from '../src/client/user-guide.ts'

const docs = resolve(dirname(fileURLToPath(import.meta.url)), '../../docs')
for (const language of ['zh', 'en'] as const) writeFileSync(`${docs}/user-guide.${language}.md`, guideMarkdown(language))
console.log('wrote docs/user-guide.zh.md and docs/user-guide.en.md')
