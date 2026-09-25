/** Offline browser-test fixture. Never composed by the production Web patch. */
import type { Context } from '@deepseek-ai/cordis'
import { LlmAdapter, ToolCallId, type StreamChunk, type GenerateOptions } from '@deepseek-ai/dsh-llm'

export const name = 'bridgeflow-scripted-model-test'
export const inject = ['llm']
class ScriptedModel extends LlmAdapter {
  private step = 0
  override async resolveModel(provider: string, model: string) {
    return { provider, id: model, name: 'Offline approval fixture', reasoning: { efforts: [{ id: 'low', name: 'Low' }] } }
  }
  async *stream(options: GenerateOptions): AsyncIterable<StreamChunk> {
    if (process.env.BRIDGEFLOW_TEST_SCENARIO === 'guide') {
      // "Where is it: <feature>" asks app_guide once; the turn after its result answers in text.
      const words = (value: any): string[] => value && typeof value === 'object'
        ? [typeof value.text === 'string' ? value.text : '', ...Object.values(value).flatMap(words)] : []
      const messages = options.messages as any[]
      // The person's own turn: DSH appends a runtime-context user message after it.
      const lastUser = messages.findLastIndex(m => m?.role === 'user' && m?.source?.kind === 'user')
      const asked = words(messages[lastUser]).find(text => text.includes('Where is it: '))
      const answered = messages.slice(lastUser + 1).some(m => JSON.stringify(m).includes('app_guide'))
      // "Which batch is this notebook on?" is answered only from the notebook context the host sends.
      if (words(messages[lastUser]).some(text => text.includes('Which batch is this notebook on?'))) {
        const all = words(messages).join('\n')
        const bound = /bound to batch ([a-f0-9]{32})/.exec(all)?.[1]
        const text = bound ? `Notebook batch: ${bound}` : /has no data yet/.test(all) ? 'Notebook: no data yet' : 'Notebook: unknown'
        yield { type: 'block-start', index: 0, blockType: 'text' }
        yield { type: 'text-delta', index: 0, text }
        yield { type: 'block-end', index: 0, block: { type: 'text', text } }
        yield { type: 'usage', usage: { inputTokens: 10, outputTokens: 10 } }
        yield { type: 'finish', reason: { kind: 'stop' } }
        return
      }
      if (asked && !answered) {
        const id = ToolCallId(`guide-${Date.now()}`), args = JSON.stringify({ feature: asked.slice(asked.indexOf('Where is it: ') + 13).trim().split(/\s/)[0] })
        yield { type: 'block-start', index: 0, blockType: 'tool-call' }
        yield { type: 'tool-call-delta', index: 0, id, name: 'app_guide', argumentsDelta: args }
        yield { type: 'block-end', index: 0, block: { type: 'tool-call', id, name: 'app_guide', arguments: args } }
        yield { type: 'usage', usage: { inputTokens: 10, outputTokens: 10 } }
        yield { type: 'finish', reason: { kind: 'tool-calls' } }
        return
      }
      const text = 'The steps are in the card above.'
      yield { type: 'block-start', index: 0, blockType: 'text' }
      yield { type: 'text-delta', index: 0, text }
      yield { type: 'block-end', index: 0, block: { type: 'text', text } }
      yield { type: 'usage', usage: { inputTokens: 10, outputTokens: 10 } }
      yield { type: 'finish', reason: { kind: 'stop' } }
      return
    }
    if (process.env.BRIDGEFLOW_TEST_SCENARIO === 'business') {
      const allText = (value: any): string[] => value && typeof value === 'object'
        ? [typeof value.text === 'string' ? value.text : '', ...Object.values(value).flatMap(allText)] : []
      const texts = allText(options.messages)
      const history = JSON.stringify(options.messages)
      let calls: Array<{ name: string; args: unknown }> = []
      const humanNote = /(人工复核意见（报告|Human review note \(report)/.test(texts.at(-1) ?? '')
      if (humanNote) { /* Acknowledge without another review. */ } else if (options.tools?.some(tool => tool.name === 'structured_output')) {
        const packet = JSON.parse(texts.find(text => text.includes('"packet"'))!).packet
        const args = process.env.BRIDGEFLOW_TEST_FAULT === 'step-limit' && packet.role === 'finance' ? { checks: null } : {
          checks: packet.checks.map((check: any) => ({ check_id: check.check_id, metric: check.metric,
            value: check.value, unit: check.unit, status: check.expected_status,
            action: check.actions[check.expected_status][0], explanation: '按关注阈值核对，由本部门负责人复核并采取职责内下一步。' })) }
        calls = [{ name: 'structured_output', args }]
        await new Promise(resolve => setTimeout(resolve, Number(process.env.BRIDGEFLOW_TEST_REVIEW_DELAY_MS ?? 150)))
      } else if (!texts.some(text => text.startsWith('{') && text.includes('"report_id"'))) {
        const dossier = texts.find(text => text.startsWith('{') && text.includes('"delegations"'))
        if (!dossier) {
          const batch = history.match(/[a-f0-9]{32}/)?.[0]
          if (!batch) throw new Error('Missing batch')
          calls = [{ name: 'review_context', args: { batch_id: batch } }]
        } else {
          const context = JSON.parse(dossier)
          calls = history.includes('"name":"subagent"')
            ? [{ name: 'review_finalize', args: { review_id: context.review_id } }]
            : context.delegations.map((args: unknown) => ({ name: 'subagent', args }))
        }
      }
      if (calls.length) {
        for (const [index, call] of calls.entries()) {
          const id = ToolCallId(`business-${this.step++}`), raw = JSON.stringify(call.args)
          yield { type: 'block-start', index, blockType: 'tool-call' }
          yield { type: 'tool-call-delta', index, id, name: call.name, argumentsDelta: raw }
          yield { type: 'block-end', index, block: { type: 'tool-call', id, name: call.name, arguments: raw } }
        }
      } else {
        const text = '离线业务协议测试结束，请查看已保存的四部门报告。'
        yield { type: 'block-start', index: 0, blockType: 'text' }
        yield { type: 'text-delta', index: 0, text }
        yield { type: 'block-end', index: 0, block: { type: 'text', text } }
      }
      yield { type: 'usage', usage: { inputTokens: 10, outputTokens: 10 } }
      yield { type: 'finish', reason: { kind: calls.length ? 'tool-calls' : 'stop' } }
      return
    }
    const step = this.step++
    if (step > (process.env.BRIDGEFLOW_TEST_DISCOVERY === '1' ? 33 : 5)) throw new Error('Offline test script exhausted')
    if (step % 2 === 0) {
      const id = ToolCallId(`approval-fixture-${step}`)
      let args = JSON.stringify({ source: `sku:test-${step}`, target: 'customer:test',
        relation: 'ordered_by', accepted: true, evidence: 'Offline browser test', period: '2025-11' })
      let toolName = 'confirm_mapping'
      if (step >= 6 && process.env.BRIDGEFLOW_TEST_DISCOVERY === '1') {
        const texts = (value: any): string[] => value && typeof value === 'object'
          ? [typeof value.text === 'string' ? value.text : '', ...Object.values(value).flatMap(texts)] : []
        const requestedTool = step >= 22 ? ['discovery_decision_propose', 'discovery_decision_vote', 'discovery_decision_vote', 'discovery_decision_finalize', 'discovery_decision_resolve', 'discovery_decision_finalize'][(step - 22) / 2]! : step === 6 ? 'discovery_register' : step >= 18 ? 'discovery_meeting_save' : step >= 14 ? 'discovery_score_save' : step >= 12 ? 'discovery_graph_save' : 'discovery_propose'
        const request = texts(options.messages).reverse().find(text => text.startsWith(`Please call ${requestedTool}`))
        if (!request) throw new Error('Missing browser registration request')
        args = JSON.stringify(JSON.parse(request.slice(request.indexOf('\n') + 1)))
        toolName = requestedTool
      }
      yield { type: 'block-start', index: 0, blockType: 'tool-call' }
      yield { type: 'tool-call-delta', index: 0, id, name: toolName, argumentsDelta: args }
      yield { type: 'block-end', index: 0, block: { type: 'tool-call', id, name: toolName, arguments: args } }
      yield { type: 'usage', usage: { inputTokens: 10, outputTokens: 10 } }
      yield { type: 'finish', reason: { kind: 'tool-calls' } }
    } else {
      const text = `Offline fixture turn ${step} finished.`
      yield { type: 'block-start', index: 0, blockType: 'text' }
      yield { type: 'text-delta', index: 0, text }
      yield { type: 'block-end', index: 0, block: { type: 'text', text } }
      yield { type: 'usage', usage: { inputTokens: 10, outputTokens: 10 } }
      yield { type: 'finish', reason: { kind: 'stop' } }
    }
  }
}
export function apply(ctx: Context) {
  ctx.llm.registerAdapter(['bridgeflow-offline-test'], new ScriptedModel())
}
