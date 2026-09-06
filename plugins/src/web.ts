import type { Context } from '@deepseek-ai/cordis'
import type {} from '@deepseek-ai/dsh-client-connection'
import type {} from '@deepseek-ai/dsh-host-webserver'
import type {} from '@deepseek-ai/dsh-workspace'
import type { BackendConfig } from './backend.ts'
import type { ApprovalNotes } from './approval/notes.ts'

/** The browser reuses DSH's cookie and Host/Origin fence; no second login/token. */
export function mountWeb(ctx: Context, backend: BackendConfig, notes: ApprovalNotes, decisionTimeoutMs: number): void {
  // The directory picker is disabled by enterprise policy. Provision the existing
  // launch directory through the native registry so a fresh Web can start a chat.
  ctx.inject(['workspaceRegistry'], async ctx => {
    await ctx.workspaceRegistry.create(process.cwd(), 'BridgeFlow')
  })
  ctx.inject(['connection', 'webServer'], ctx => {
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
        if (path === '/config' && req.method === 'GET') {
          res.writeHead(200, { 'content-type': 'application/json', 'cache-control': 'no-store' }).end(JSON.stringify({
            maxUploadBytes: Math.min(Number(process.env.BRIDGEFLOW_MAX_UPLOAD_BYTES) || 25 * 1024 * 1024, 25 * 1024 * 1024),
            maxRequestBytes: 26 * 1024 * 1024, noteLimit: 240, decisionTimeoutMs,
          }))
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
            const saved = notes.record(data.session_id, data.call_id, data.ticket, data.note)
            res.writeHead(saved ? 200 : 409).end(JSON.stringify(saved ? { saved: true } : { detail: 'Note too long or approval expired; decision not submitted' }))
          } catch { res.writeHead(422).end(JSON.stringify({ detail: 'Could not record approval note' })) }
          return
        }
        const read = req.method === 'GET' && /^\/batches\/[a-f0-9]{32}(\/(view|review))?$/.test(path)
        const upload = req.method === 'POST' && path === '/batches'
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
