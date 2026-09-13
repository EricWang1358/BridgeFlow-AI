import { withAccess, type ProductTool } from '../tool-catalogue.ts'
import { defineTool } from '@deepseek-ai/dsh-tools'

import { callBackend, type BackendConfig } from '../backend.ts'
import type { ApprovalReceipts } from '../approval/receipts.ts'

/**
 * Feishu Drive shortcuts (#140): import department files, upload a saved report.
 * Both move files across a trust boundary, so both are approval-gated. The host holds
 * the Feishu credentials; without them it answers "not configured".
 */
type Json = string | number | boolean | null | Json[] | { [key: string]: Json }
const anyObject = { schema: { type: 'object' as const, additionalProperties: true as const } }

export function feishuImportBody(args: Record<string, unknown>, agentId: string, callId: string | undefined) {
  const files = (Array.isArray(args.files) ? args.files : []).map((f: Record<string, unknown>) => ({
    department: String(f?.label ?? f?.department ?? ''), file_token: String(f?.value ?? f?.file_token ?? '') }))
  return { period: args.period, files, confirmed_by: agentId, call_id: callId ?? null }
}

export function feishuUploadBody(args: Record<string, unknown>, agentId: string, callId: string | undefined) {
  return { batch_id: args.batch_id, folder_token: args.folder_token, report_id: args.report_id ?? null, confirmed_by: agentId, call_id: callId ?? null }
}

export function feishuImport(config: BackendConfig, receipts: ApprovalReceipts): ProductTool {
  return withAccess(defineTool({
    name: 'feishu_import',
    description: 'Download department files from Feishu Drive by file token and import them as one batch for a period. Use only tokens the person gave you. Requires approval.',
    parameters: {
      period: { type: 'string', required: true, description: 'YYYY-MM' },
      files: { type: 'array', required: true, items: { type: 'object', properties: {
        label: { type: 'string', required: true, description: 'Department: production, procurement, finance or marketing' },
        value: { type: 'string', required: true, description: 'Feishu file token' } }, additionalProperties: false } },
    },
    output: { ...anyObject, render: (_args, value) => {
      const batch = (value as { batch?: { batch_id?: string; status?: string } }).batch
      return [{ type: 'text', text: `Imported from Feishu as batch ${batch?.batch_id} (${batch?.status}).` }]
    } },
    async execute(args, exec) {
      return callBackend<Record<string, Json>>(config, '/tools/feishu-import', feishuImportBody(args, exec.agent?.id ?? 'unknown-agent', exec.callId),
        exec.signal, receipts.take(JSON.stringify([exec.agent?.id, exec.callId])))
    },
  }), { kind: 'approval', reason: 'Download these Feishu files into a new BridgeFlow batch.',
    denialEffect: 'Nothing was downloaded or imported. Do NOT mention a batch id', body: feishuImportBody })
}

export function feishuUploadReport(config: BackendConfig, receipts: ApprovalReceipts): ProductTool {
  return withAccess(defineTool({
    name: 'feishu_upload_report',
    description: 'Upload a saved review report (the latest for the batch, or report_id) to a Feishu Drive folder the person named. Requires approval.',
    parameters: {
      batch_id: { type: 'string', required: true },
      folder_token: { type: 'string', required: true, description: 'Feishu folder token the person gave you' },
      report_id: { type: 'string', description: 'Specific saved report; latest when omitted' },
    },
    output: { ...anyObject, render: (_args, value) => {
      const result = value as { filename?: string; file_token?: string }
      return [{ type: 'text', text: `Uploaded ${result.filename} to Feishu (file ${result.file_token}).` }]
    } },
    async execute(args, exec) {
      return callBackend<Record<string, Json>>(config, '/tools/feishu-upload-report', feishuUploadBody(args, exec.agent?.id ?? 'unknown-agent', exec.callId),
        exec.signal, receipts.take(JSON.stringify([exec.agent?.id, exec.callId])))
    },
  }), { kind: 'approval', reason: 'Send this saved report to the named Feishu folder.',
    denialEffect: 'Nothing was uploaded. Do NOT say the report is in Feishu', body: feishuUploadBody })
}
