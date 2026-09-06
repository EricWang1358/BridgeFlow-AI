import type { ApprovalNote } from '../notebooks.ts'
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
  async record(sessionId: string, callId: string, ticket: string, note: string, persist: (entry:ApprovalNote)=>Promise<void>): Promise<boolean> {
    const pending = this.#pending.get(this.key(sessionId, callId))
    if (!pending || pending.ticket !== ticket || note.length > 240) return false
    const normalized = note.replace(/\s+/g, ' ').trim()
    await persist({sessionId,callId,note:normalized,author:'dsh-authenticated-session',time:Date.now()})
    if (this.#pending.get(this.key(sessionId,callId)) !== pending) return false
    pending.note = normalized
    return true
  }
  get(sessionId: string, callId: string) { return this.#pending.get(this.key(sessionId, callId))?.note }
}
