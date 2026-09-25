import { withAccess, type ProductTool } from '../tool-catalogue.ts'
import { defineTool } from '@deepseek-ai/dsh-tools'

import { guide, guideFeatures, type GuideFeature } from '../app-guide.ts'

/**
 * Answers "is there a …?" and "where do I …?" from the declared map of the interface
 * (`app-guide.ts`), with the exact clicks in both languages. No backend call and no data:
 * whether the current notebook already holds something is a question for the `check` tools.
 * The chat card turns the answer into a button that opens the page.
 */
export function appGuide(): ProductTool {
  return withAccess(defineTool({
    name: 'app_guide',
    description: 'Where a BridgeFlow feature is in the interface and exactly what to click, in Chinese and English. '
      + 'Use it whenever someone asks whether the product has something, where to find it, or how to open it; '
      + 'answer with its steps in their language. The chat card offers a button that opens the page. '
      + 'If no feature fits, say the product does not have it rather than describing one. '
      + `Features: ${guideFeatures.join(', ')}.`,
    parameters: { feature: { type: 'string', required: true, enum: guideFeatures, description: 'The feature asked about' } },
    // The whole answer as JSON: the model reads both languages, the chat card reads `feature`.
    output: { schema: { type: 'object' as const, additionalProperties: true as const },
      render: (_args, value) => [{ type: 'text' as const, text: JSON.stringify(value) }] },
    async execute(args) {
      const feature = String(args.feature) as GuideFeature
      const entry = guide[feature]
      if (!entry) return { error: `Unknown feature. Known: ${guideFeatures.join(', ')}` }
      const extra = entry as { view?: string; needsBatch?: boolean; note?: readonly [string, string]; check?: readonly string[] }
      return {
        feature,
        what_zh: entry.what[0], what_en: entry.what[1],
        steps_zh: entry.steps.map(s => s[0]), steps_en: entry.steps.map(s => s[1]),
        opens_page: extra.view ?? null,
        needs_open_batch: extra.needsBatch ?? false,
        ...(extra.note ? { note_zh: extra.note[0], note_en: extra.note[1] } : {}),
        ...(extra.check ? { check_with: [...extra.check] } : {}),
      }
    },
  }), { kind: 'read' })
}
