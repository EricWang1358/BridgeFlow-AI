import { createHash } from 'node:crypto'
import { notebookDomain, parseNotebook, readNotebook, saveNotebook } from './notebooks.ts'
import type { SessionId } from '@deepseek-ai/dsh-session'
import type { Context } from '@deepseek-ai/cordis'
import type {} from '@deepseek-ai/dsh-client-connection'
import type {} from '@deepseek-ai/dsh-host-webserver'
import type {} from '@deepseek-ai/dsh-workspace'
import type { BackendConfig } from './backend.ts'
import type { ApprovalNotes } from './approval/notes.ts'
import type { PendingDetails } from './approval/detail.ts'

/** The browser reuses DSH's cookie and Host/Origin fence; no second login/token. */
export function mountWeb(ctx: Context, backend: BackendConfig, notes: ApprovalNotes, decisionTimeoutMs: number, details: PendingDetails): void {
  // The directory picker is disabled by enterprise policy. Provision the existing
  // launch directory through the native registry so a fresh Web can start a chat.
  ctx.inject(['connection', 'webServer', 'sessionController', 'sessions', 'storageDomain', 'workspaceRegistry'], async ctx => {
    const workspace = await ctx.workspaceRegistry.create(process.cwd(), 'BridgeFlow')
    const domain=await ctx.storageDomain.open(notebookDomain)
    ctx.effect(()=>()=>domain.close(), 'bridgeflow: close notebook store')
    const notebookTable=domain.table('notebooks'), noteTable=domain.table('approval_notes')
    ctx.effect(() => ctx.webServer.register({
      kind: 'prefix', path: '/bridgeflow',
      async handler(req, res) {
        const rejected = ctx.connection.requestRejection(req)
        if (rejected !== undefined) {
          res.writeHead(rejected).end('DSH authentication required')
          return
        }
        const url = new URL(req.url ?? '/', 'http://localhost')
        const path = url.pathname.slice('/bridgeflow'.length)
        if (path === '/approval-note-audit' && req.method === 'GET') {
          const id=url.searchParams.get('session_id')
          const rows=[...noteTable.entries()].map(([,value])=>value).filter(value=>value.sessionId===id).sort((a,b)=>b.time-a.time)
          res.writeHead(200,{'content-type':'application/json','cache-control':'no-store'}).end(JSON.stringify({total:rows.length,notes:rows.slice(0,50)}))
          return
        }
        if (path === '/notebook' && (req.method === 'GET' || req.method === 'POST')) {
          res.setHeader('content-type', 'application/json')
          res.setHeader('cache-control', 'no-store')
          const id = url.searchParams.get('session_id') ?? ''
          if (!/^[a-zA-Z0-9_-]{1,160}$/.test(id)) { res.writeHead(422).end('{}'); return }
          if (!ctx.get('sessionController')) { res.writeHead(503).end('{}'); return }
          try {
            if (req.method === 'GET') {
              const notebook = await readNotebook(ctx, id as SessionId, notebookTable)
              res.writeHead(200).end(JSON.stringify({ notebook }))
              return
            }
            let body = ''
            for await (const chunk of req) {
              body += chunk.toString()
              if (Buffer.byteLength(body) > 4096) { res.writeHead(413).end('{}'); return }
            }
            const notebook = parseNotebook(JSON.parse(body))
            if (notebook.batch) {
              const check = await fetch(`${backend.baseUrl}/batches/${notebook.batch}`, {
                headers: {authorization: `Bearer ${process.env.BRIDGEFLOW_SERVICE_TOKEN ?? ''}`},
                signal: AbortSignal.timeout(backend.timeoutMs),
              })
              if (!check.ok) { res.writeHead(422).end(JSON.stringify({detail:'Batch is unavailable; notebook was not saved'})); return }
            }
            await workspace.attachSession(id as SessionId)
            await saveNotebook(ctx, id as SessionId, notebook, notebookTable)
            res.writeHead(200).end(JSON.stringify({ notebook }))
          } catch (error) { ctx.logger.warn('Notebook operation failed: %s', String(error)); res.writeHead(409).end(JSON.stringify({detail:'Notebook could not be loaded or saved; keep this page open and retry'})) }
          return
        }
        if (path === '/config' && req.method === 'GET') {
          res.writeHead(200, { 'content-type': 'application/json', 'cache-control': 'no-store' }).end(JSON.stringify({
            workspaceId: workspace.id,
            maxUploadBytes: Math.min(Number(process.env.BRIDGEFLOW_MAX_UPLOAD_BYTES) || 25 * 1024 * 1024, 25 * 1024 * 1024),
            maxRequestBytes: 26 * 1024 * 1024, noteLimit: 240, decisionTimeoutMs,
          }))
          return
        }
        if (path === '/approval-detail' && req.method === 'GET') {
          // What the approval card renders instead of the raw reason string (#110).
          // Values are verbatim tool arguments, already capped by summarise(); the
          // summary only exists while the decision is pending, so an empty list is
          // the correct answer for a settled or unknown call — not an error.
          const callId = url.searchParams.get('call_id') ?? ''
          res.writeHead(200, { 'content-type': 'application/json', 'cache-control': 'no-store' })
            .end(JSON.stringify({ details: details.peek(callId) }))
          return
        }
        if (path === '/approval-notes' && (req.method === 'GET' || req.method === 'POST')) {
          res.setHeader('content-type', 'application/json')
          res.setHeader('cache-control', 'no-store')
          if (req.method === 'GET') {
            const ticket = notes.ticket(url.searchParams.get('session_id') ?? '', url.searchParams.get('call_id') ?? '')
            res.writeHead(ticket ? 200 : 409).end(JSON.stringify(ticket ? { ticket } : { detail: 'Approval is no longer pending' }))
            return
          }
          try {
            let body = ''
            for await (const chunk of req) {
              body += chunk.toString()
              if (Buffer.byteLength(body) > 4096) { res.writeHead(413).end('{}'); return }
            }
            const data = JSON.parse(body)
            if (['session_id', 'call_id', 'ticket', 'note'].some(key => typeof data[key] !== 'string')) {
              res.writeHead(422).end('{}'); return
            }
            const saved = await notes.record(data.session_id, data.call_id, data.ticket, data.note, entry=>noteTable.put(createHash('sha256').update(JSON.stringify([entry.sessionId,entry.callId])).digest('hex'),entry))
            res.writeHead(saved ? 200 : 409).end(JSON.stringify(saved ? { saved: true } : { detail: 'Note too long or approval expired; decision not submitted' }))
          } catch (error) { ctx.logger.warn('Approval note persistence failed: %s', String(error)); res.writeHead(422).end(JSON.stringify({ detail: 'Could not record approval note' })) }
          return
        }
        const read = req.method === 'GET' && (path === '/quotation/contract' || /^\/batches\/[a-f0-9]{32}(\/(view|review|artifacts|sources(?:\/(?:production|procurement|finance|marketing))?))?$/.test(path))
        const upload = req.method === 'POST' && (path === '/batches' || path === '/batches/demo')
        // No generic proxy. Browser requests cannot mint approval receipts or call writes.
        if (!read && !upload) { res.writeHead(403).end('Route not authorized'); return }
        const abort = new AbortController()
        req.on('aborted', () => abort.abort())
        res.on('close', () => { if (!res.writableEnded) abort.abort() })
        try {
          const chunks: Buffer[] = []
          let size = 0
          for await (const chunk of req) {
            const bytes = Buffer.from(chunk)
            size += bytes.length
            if (size > 26 * 1024 * 1024) {
              res.writeHead(413).end('Upload exceeds 26 MiB'); return
            }
            chunks.push(bytes)
          }
          const response = await fetch(`${backend.baseUrl}${path}${url.search}`, {
            method: req.method ?? 'GET',
            headers: {
              authorization: `Bearer ${process.env.BRIDGEFLOW_SERVICE_TOKEN ?? ''}`,
              'content-type': req.headers['content-type'] ?? 'application/json',
            },
            ...(upload ? { body: Buffer.concat(chunks) } : {}),
            signal: AbortSignal.any([abort.signal, AbortSignal.timeout(120_000)]),
          })
          res.writeHead(response.status, { 'content-type': 'application/json', 'cache-control': 'no-store' })
          res.end(await response.text())
        } catch {
          if (!res.headersSent) res.writeHead(502)
          res.end('BridgeFlow data service unavailable')
        }
      },
    }), 'bridgeflow: authenticated data views')
  })
}
