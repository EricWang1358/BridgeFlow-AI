import { createHash } from 'node:crypto'
import { DEFAULT_BINDING_MS, actors } from './actor.ts'
import { notebookDomain, parseNotebook, readNotebook, saveNotebook } from './notebooks.ts'
import type { SessionId } from '@deepseek-ai/dsh-session'
import type { Context } from '@deepseek-ai/cordis'
import type {} from '@deepseek-ai/dsh-client-connection'
import type {} from '@deepseek-ai/dsh-host-webserver'
import type {} from '@deepseek-ai/dsh-workspace'
import type { BackendConfig } from './backend.ts'
import { settledNote, type ApprovalNotes } from './approval/notes.ts'
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
    const noteKey=(sessionId:string,callId:string)=>createHash('sha256').update(JSON.stringify([sessionId,callId])).digest('hex')
    notes.onSettled=async (sessionId,callId,outcome)=>{
      const key=noteKey(sessionId,callId), entry=noteTable.get(key)
      if (entry) await noteTable.put(key,settledNote(entry,outcome))
    }
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
        // The login portal's token (docs/27) rides beside the DSH session fence; the
        // backend verifies its signature against the portal's JWKS. Absent token =
        // absent identity — never invented here.
        const portalToken = req.headers['x-portal-token']
        const portalUser = typeof portalToken === 'string' && portalToken ? {'x-bridgeflow-user': portalToken} : {}
        if (path === '/approval-note-audit' && req.method === 'GET') {
          const id=url.searchParams.get('session_id')
          const rows=[...noteTable.entries()].map(([,value])=>value).filter(value=>value.sessionId===id).sort((a,b)=>b.time-a.time)
          res.writeHead(200,{'content-type':'application/json','cache-control':'no-store'}).end(JSON.stringify({total:rows.length,notes:rows.slice(0,50)}))
          return
        }
        if (path === '/actor' && req.method === 'POST') {
          // The browser says "this session is mine, here is my portal token" (#231).
          // The host never takes that on faith: the backend verifies the signature and
          // reports the subject, and only then is the token bound and later relayed on
          // the reads the model triggers. No token, or a token the backend refuses,
          // releases the binding — attribution goes absent rather than stale.
          res.setHeader('content-type', 'application/json')
          res.setHeader('cache-control', 'no-store')
          const id = url.searchParams.get('session_id') ?? ''
          if (!/^[a-zA-Z0-9_-]{1,160}$/.test(id)) { res.writeHead(422).end('{}'); return }
          if (typeof portalToken !== 'string' || !portalToken) {
            actors.release(id)
            res.writeHead(401).end(JSON.stringify({ detail: 'No portal token to bind' }))
            return
          }
          try {
            const checked = await fetch(`${backend.baseUrl}/identity/me`, {
              headers: { 'x-bridgeflow-user': portalToken },
              signal: AbortSignal.timeout(backend.timeoutMs),
            })
            if (!checked.ok) {
              actors.release(id)
              res.writeHead(checked.status === 401 ? 401 : 503)
                 .end(JSON.stringify({ detail: 'Portal token could not be verified' }))
              return
            }
            const subject = String(((await checked.json()) as {subject?: unknown}).subject ?? '')
            if (!subject) {
              actors.release(id)
              res.writeHead(503).end(JSON.stringify({ detail: 'Identity service named no subject' }))
              return
            }
            actors.bind(id, { token: portalToken, subject, expiresAt: Date.now() + DEFAULT_BINDING_MS })
            res.writeHead(200).end(JSON.stringify({ subject }))
          } catch (error) {
            actors.release(id)
            ctx.logger.warn('Actor binding failed for session %s: %s', id, String(error))
            res.writeHead(503).end(JSON.stringify({ detail: 'Identity service is unreachable' }))
          }
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
                headers: {authorization: `Bearer ${process.env.BRIDGEFLOW_SERVICE_TOKEN ?? ''}`, ...portalUser},
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
            portalUrl: process.env.PORTAL_BASE_URL ?? '',
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
        if (path === '/approval-authorize' && req.method === 'POST') {
          res.setHeader('content-type', 'application/json')
          res.setHeader('cache-control', 'no-store')
          try {
            let body = ''
            for await (const chunk of req) {
              body += chunk.toString()
              if (Buffer.byteLength(body) > 4096) { res.writeHead(413).end('{}'); return }
            }
            const data = JSON.parse(body)
            if (['session_id', 'call_id', 'ticket'].some(key => typeof data[key] !== 'string')) {
              res.writeHead(422).end('{}'); return
            }
            // Body and operation come only from the pending native call, never the browser.
            const write = notes.write(data.session_id, data.call_id, data.ticket)
            if (!write) { res.writeHead(409).end(JSON.stringify({ detail: 'Approval is no longer pending' })); return }
            const check = await fetch(`${backend.baseUrl}/identity/authorize-write`, {
              method: 'POST', headers: { authorization: `Bearer ${process.env.BRIDGEFLOW_SERVICE_TOKEN ?? ''}`,
                'content-type': 'application/json', ...portalUser },
              body: JSON.stringify(write), signal: AbortSignal.timeout(backend.timeoutMs),
            })
            const result = await check.json()
            if (!check.ok) { res.writeHead(check.status).end(JSON.stringify(result)); return }
            if (result.required && (typeof result.permit !== 'string' || typeof result.subject !== 'string'
              || !notes.authorize(data.session_id, data.call_id, data.ticket, result.permit, result.subject))) {
              res.writeHead(409).end(JSON.stringify({ detail: 'Approval expired or belongs to another employee' })); return
            }
            // Keep the permit in host memory; it never enters a browser response or model context.
            res.writeHead(200).end(JSON.stringify({ authorized: true }))
          } catch { res.writeHead(503).end(JSON.stringify({ detail: 'Employee authorization is unavailable; nothing was approved' })) }
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
            const saved = await notes.record(data.session_id, data.call_id, data.ticket, data.note, entry=>noteTable.put(noteKey(entry.sessionId,entry.callId),entry), actors.subjectForSession(data.session_id))
            res.writeHead(saved ? 200 : 409).end(JSON.stringify(saved ? { saved: true } : { detail: 'Note too long or approval expired; decision not submitted' }))
          } catch (error) { ctx.logger.warn('Approval note persistence failed: %s', String(error)); res.writeHead(422).end(JSON.stringify({ detail: 'Could not record approval note' })) }
          return
        }
        if (path === '/human-note' && req.method === 'POST') {
          // A note on a saved report is recorded by the host before the captain sees it,
          // so the record exists whatever the model does with the turn (#111).
          res.setHeader('content-type', 'application/json')
          res.setHeader('cache-control', 'no-store')
          try {
            let body = ''
            for await (const chunk of req) {
              body += chunk.toString()
              if (Buffer.byteLength(body) > 4096) { res.writeHead(413).end('{}'); return }
            }
            const data = JSON.parse(body)
            if (['batch_id', 'report_id', 'session_id', 'note_id', 'note'].some(key => typeof data[key] !== 'string')) {
              res.writeHead(422).end('{}'); return
            }
            const recorded = await fetch(`${backend.baseUrl}/tools/review-note`, {
              method: 'POST', headers: { authorization: `Bearer ${process.env.BRIDGEFLOW_SERVICE_TOKEN ?? ''}`,
                'content-type': 'application/json', ...portalUser },
              body: JSON.stringify({ batch_id: data.batch_id, report_id: data.report_id,
                parent_session_id: data.session_id, note_id: data.note_id, note: data.note }),
              signal: AbortSignal.timeout(15000),
            })
            res.writeHead(recorded.status).end(await recorded.text())
          } catch (error) { res.writeHead(422).end(JSON.stringify({ detail: String(error instanceof Error ? error.message : error) })) }
          return
        }
        const read = req.method === 'GET' && (path === '/quotation/contract' || /^\/batches\/[a-f0-9]{32}(\/(view|review|artifacts|review-notes\/[a-f0-9]{32}|sources(?:\/(?:production|procurement|finance|marketing))?))?$/.test(path)
          // Workflow views are read-only here; recording and approving go through the captain and approval.
          || /^\/workflow\/(board|catalogue|adoption|artifacts\/[a-f0-9]{32})$/.test(path)
          || /^\/discovery\/[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}\/(material|opportunity|graph|score|meeting|decision)(\/[a-zA-Z0-9][a-zA-Z0-9_-]{0,79})?$/.test(path)
          || /^\/discovery\/[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}\/(scoring-policy|decision-policy)$/.test(path)
          || /^\/discovery\/[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}\/material\/[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}\/original$/.test(path)
          || /^\/integration\/batches\/[a-f0-9]{32}(\/xlsx)?$/.test(path)
          || /^\/conclusions\/batches\/[a-f0-9]{32}(\/(comparison|charts|report))?$/.test(path)
          || /^\/conventions\/batches\/[a-f0-9]{32}(\/preview)?$/.test(path)
          || path === '/monthly/checklist' || path === '/monthly/inbox' || path === '/batches/demo/cases'
          || path === '/journal' || path === '/journal/runs' || path === '/eval/report'
          || /^\/reviews\/[a-f0-9]{32}\/dispositions$/.test(path)
          || /^\/batches\/templates\/(production|procurement|finance|marketing)$/.test(path))
        const upload = req.method === 'POST' && (path === '/batches' || path === '/batches/demo' || path === '/workflow/sample' || path === '/batches/self-check' || path === '/discovery/uploads'
          // Correcting one department derives a new batch; it is an upload like any other (E14-UC04).
          || /^\/batches\/[a-f0-9]{32}\/departments\/(production|procurement|finance|marketing)$/.test(path))
        // Feishu user-identity calls (docs/30, docs/31, docs/33): the browser relays the
        // user's own token; these endpoints are never model tools, so the click is the
        // approval. sheet-meta / bitable-meta answer names and dimensions only (docs/33).
        const feishuUser = req.method === 'POST' && /^\/tools\/feishu-(list|import-user|upload-user|wiki-spaces|wiki-list|wiki-upload|sheet-meta|bitable-meta)$/.test(path)
        // The route match alone is not enough: a feishu call without the user's own
        // token must stop here with the same 403 as any other unauthorized route.
        const feishuToken = req.headers['x-feishu-user-token']
        const feishuOk = feishuUser && typeof feishuToken === 'string' && feishuToken.length > 0
        const feishuAuth = feishuOk ? { 'x-feishu-user-token': String(feishuToken) } : {}
        // No generic proxy. Browser requests cannot mint approval receipts or call writes.
        if (!read && !upload && !feishuOk) { res.writeHead(403).end('Route not authorized'); return }
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
              ...portalUser,
              ...feishuAuth,
            },
            ...(upload || feishuUser ? { body: Buffer.concat(chunks) } : {}),
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
