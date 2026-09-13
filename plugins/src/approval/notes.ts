import type { ApprovalNote } from '../notebooks.ts'
import { randomUUID } from 'node:crypto'
import type { Agent } from '@deepseek-ai/dsh-agent'

/** A saved note after its request ended: the rejection reason, or a draft no decision used. */
export function settledNote(entry: ApprovalNote, outcome: string): ApprovalNote {
  return { ...entry, outcome, status: outcome === 'rejected' ? 'final' : 'unused' }
}

/** Notes are scoped to one active request; they confer no write permission. */
export class ApprovalNotes {
  readonly #pending = new Map<string, { ticket: string; agent: Agent; note: string }>()
  /**
   * Where a saved note learns how its request ended (#87). A note is saved before the
   * decision, so until then it is only a draft; it becomes the final rejection reason
   * only if the official decision is a rejection, and is marked unused otherwise.
   */
  onSettled: ((sessionId: string, callId: string, outcome: string) => Promise<void>) | undefined
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
    await persist({sessionId,callId,note:normalized,author:'dsh-authenticated-session',time:Date.now(),status:'draft'})
    if (this.#pending.get(this.key(sessionId,callId)) !== pending) return false
    pending.note = normalized
    return true
  }
  get(sessionId: string, callId: string) { return this.#pending.get(this.key(sessionId, callId))?.note }
  async settle(sessionId: string, callId: string, outcome: string): Promise<void> {
    if (this.onSettled && this.get(sessionId, callId)) await this.onSettled(sessionId, callId, outcome)
  }
}
