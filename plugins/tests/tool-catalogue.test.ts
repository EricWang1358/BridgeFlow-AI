import assert from 'node:assert/strict'
import test from 'node:test'
import { Context } from '@deepseek-ai/cordis'
import SystemPrompt from '@deepseek-ai/dsh-system-prompt'
import ToolRuntime, { defineTool } from '@deepseek-ai/dsh-tools'
import { ToolCatalogue, withAccess, type ProductTool } from '../src/tool-catalogue.ts'
import { gate } from '../src/approval/gate.ts'
import { PendingDetails } from '../src/approval/detail.ts'
import { ApprovalNotes } from '../src/approval/notes.ts'
import { ApprovalReceipts } from '../src/approval/receipts.ts'

const tool = () => defineTool({ name: 'new_document_action', description: 'Extension fixture', parameters: {},
  output: { schema: { type: 'string' }, render: (_args, value) => [{ type: 'text', text: value }] },
  async execute() { return 'ok' },
})

test('an extension needs a complete access contract and disposal removes its permission', async () => {
  const ctx = new Context(), catalogue = new ToolCatalogue()
  await ctx.plugin(SystemPrompt); await ctx.plugin(ToolRuntime)
  assert.throws(() => catalogue.register(ctx, tool() as ProductTool), /access contract/)
  assert.equal(catalogue.access('new_document_action'), undefined)
  assert.throws(() => catalogue.register(ctx, { ...tool(), access: { kind: 'approval' } } as ProductTool), /approval contract/)
  assert(!ctx.tools.schemas().some(t => t.name === 'new_document_action'))
  catalogue.register(ctx, withAccess(tool(), { kind: 'read' }))
  assert.throws(() => catalogue.register(ctx, withAccess(tool(), { kind: 'read' })), /Duplicate/)
  assert.equal(catalogue.access('new_document_action')?.kind, 'read')
  await ctx.fiber.dispose()
  assert.equal(catalogue.access('new_document_action'), undefined)
})

test('approval gate uses the new action contract without mapping-specific branching', async () => {
  let handler: Function | undefined
  const requests: { reason: string }[] = []
  const ctx = { on: (_event: string, fn: Function) => { handler = fn }, approval: {
    request: async (request: { reason: string }) => { requests.push(request); return 'rejected' },
  } } as unknown as Context
  const catalogue = new ToolCatalogue()
  const registration = { tools: { register: () => () => {} }, effect: () => {} } as unknown as Context
  catalogue.register(registration, withAccess(tool(), { kind: 'approval',
    reason: 'Release the selected document.', denialEffect: 'The document remains a draft.',
    body: args => ({ document: args.document }),
  }))
  gate(ctx, new PendingDetails(), new ApprovalReceipts(), 1000, new ApprovalNotes(), catalogue)
  const result = await handler!({ name: 'new_document_action', arguments: { document: 'draft-a' },
    agent: { id: 'owner' }, signal: new AbortController().signal }, () => { throw Error('Write must not run') })
  assert.equal(result.kind, 'deny')
  assert.match(requests[0]!.reason, /Release the selected document/)
  assert.match(result.reason, /The document remains a draft/)
  assert.doesNotMatch(result.reason, /remembered for next month/)
})
