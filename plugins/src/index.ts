import type { Context } from '@deepseek-ai/cordis'
import Schema from '@deepseek-ai/schemastery'

import { DEFAULT_BACKEND, type BackendConfig } from './backend.ts'
import * as approvalGate from './guards/approval-gate.ts'
import * as untrustedInput from './guards/untrusted-input.ts'
import { aggregateMetric } from './tools/aggregate-metric.ts'
import { confirmMapping } from './tools/confirm-mapping.ts'
import { listMetrics } from './tools/list-metrics.ts'
import { lookupFieldDictionary } from './tools/lookup-field-dictionary.ts'

export const name = 'bridgeflow'
export const inject = ['tools']

export interface Config {
  /** Base URL of the Python service that executes the tool bodies. */
  backendUrl: string
  /** Per-call timeout in milliseconds. */
  backendTimeoutMs: number
}

export const Config: Schema<Config> = Schema.object({
  backendUrl: Schema.string().default(DEFAULT_BACKEND.baseUrl),
  backendTimeoutMs: Schema.number().default(DEFAULT_BACKEND.timeoutMs),
})

export function apply(ctx: Context, config: Config): void {
  const backend: BackendConfig = {
    baseUrl: config.backendUrl,
    timeoutMs: config.backendTimeoutMs,
  }

  // Registration is effect-based: disposing this plugin unregisters every tool.
  ctx.tools.register(listMetrics(backend))
  ctx.tools.register(aggregateMetric(backend))
  ctx.tools.register(lookupFieldDictionary(backend))
  ctx.tools.register(confirmMapping(backend))

  ctx.plugin(untrustedInput)
  ctx.plugin(approvalGate)
}
