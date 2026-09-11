import type { Context } from '@deepseek-ai/cordis'
import type { ToolDefinition } from '@deepseek-ai/dsh-tools'

export type ToolAccess =
  | { readonly kind: 'read' }
  | { readonly kind: 'review' }
  | {
    readonly kind: 'approval'
    readonly reason: string
    readonly denialEffect: string
    readonly body: (args: Record<string, unknown>, agentId: string, callId: string | undefined) => unknown
  }

export type ProductTool = ToolDefinition & { readonly access: ToolAccess }

/** Keep execution and its authorization contract together at the extension point. */
export function withAccess(tool: ToolDefinition, access: ToolAccess): ProductTool {
  return { ...tool, access: Object.freeze({ ...access }) }
}

/** Registration is the source of the deployment allowlist, not a parallel list. */
export class ToolCatalogue {
  readonly #policies = new Map<string, ToolAccess>()

  access(name: string): ToolAccess | undefined { return this.#policies.get(name) }

  register(ctx: Context, tool: ProductTool): void {
    const access = tool.access
    if (!access || !['read', 'review', 'approval'].includes(access.kind)) {
      throw new Error(`Tool ${tool.name} has no valid access contract`)
    }
    if (access.kind === 'approval' && (!access.reason || !access.denialEffect || typeof access.body !== 'function')) {
      throw new Error(`Tool ${tool.name} has no complete approval contract`)
    }
    if (this.#policies.has(tool.name)) throw new Error(`Duplicate product tool: ${tool.name}`)
    // A failed registration must never leave an authorized name behind.
    const unregister = ctx.tools.register(tool)
    const frozen = Object.freeze({ ...access })
    this.#policies.set(tool.name, frozen)
    ctx.effect(() => () => {
      unregister()
      if (this.#policies.get(tool.name) === frozen) this.#policies.delete(tool.name)
    })
  }
}
