/**
 * The guest instance's "model" when the operator has not allowed guests to use the real one
 * (docs/22 §9e, BRIDGEFLOW_GUEST_LLM unset). It calls nothing and costs nothing: every chat
 * turn is answered with one fixed note saying what still works, and a session title request
 * (no tools offered) gets a short name. Composed only by `scripts/start_web.py --guest`;
 * the production patch never loads it.
 */
import type { Context } from '@deepseek-ai/cordis'
import { LlmAdapter, type StreamChunk, type GenerateOptions, type LlmResolvedModelInfo } from '@deepseek-ai/dsh-llm'

export const name = 'bridgeflow-guest-notice-model'
export const inject = ['llm']

export const NOTICE =
  'Guest mode: the AI model is switched off on this server, so I cannot answer or call tools here. ' +
  'Everything in the Studio works without me — open the sample notebook, the Overview, Filling & handoff ' +
  'and Discovery from the Studio on the right. ' +
  '访客模式：本服务器没有为访客开启 AI 模型，我不能回答或调用工具。右侧工作室里的页面都能直接使用：' +
  '示例笔记本、总览、填报与流转、立项。'
export const TITLE = 'Guest session'

class GuestNotice extends LlmAdapter {
  override async resolveModel(provider: string, model: string): Promise<LlmResolvedModelInfo> {
    return { provider, id: model, name: 'AI off (guest mode)' }
  }
  async *stream(options: GenerateOptions): AsyncIterable<StreamChunk> {
    const text = options.tools?.length ? NOTICE : TITLE
    yield { type: 'block-start', index: 0, blockType: 'text' }
    yield { type: 'text-delta', index: 0, text }
    yield { type: 'block-end', index: 0, block: { type: 'text', text } }
    yield { type: 'usage', usage: { inputTokens: 0, outputTokens: 0 } }
    yield { type: 'finish', reason: { kind: 'stop' } }
  }
}

export function apply(ctx: Context) {
  ctx.llm.registerAdapter(['bridgeflow-guest-notice'], new GuestNotice())
}
