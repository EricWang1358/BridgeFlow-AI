import { randomUUID } from 'node:crypto'
import type { Agent } from '@deepseek-ai/dsh-agent'

/** Notes are scoped to one active request; they confer no write permission. */
export class ApprovalNotes {
  readonly #pending = new Map<string, { ticket: string; agent: Agent; note: string }>()
  key(sessionId: string, callId: string) { return JSON.stringify([sessionId, callId]) }
  open(agent: Agent, callId: string): () => void {
    const key = this.key(agent.id, callId)
    if (this.#pending.has(key) || this.#pending.size >= 64) throw new Error('Approval note capacity or call identity conflict')
    const entry = { ticket: randomUUID(), agent, note: '' }
    this.#pending.set(key, entry)
    return () => { if (this.#pending.get(key) === entry) this.#pending.delete(key) }
  }
  ticket(sessionId: string, callId: string) {
    return this.#pending.get(this.key(sessionId, callId))?.ticket
  }
  record(sessionId: string, callId: string, ticket: string, note: string): boolean {
    const pending = this.#pending.get(this.key(sessionId, callId))
    if (!pending || pending.ticket !== ticket || note.length > 240) return false
    const normalized = note.replace(/\s+/g, ' ').trim()
    pending.agent.session.append('bridgeflow/approval-note', { callId, note: normalized, author: 'dsh-authenticated-session' })
    pending.note = normalized
    return true
  }
  get(sessionId: string, callId: string) { return this.#pending.get(this.key(sessionId, callId))?.note }
}

declare module '@deepseek-ai/dsh-session/types' {
  interface SessionEventMap {
    'bridgeflow/approval-note': { callId: string; note: string; author: string }
  }
}
