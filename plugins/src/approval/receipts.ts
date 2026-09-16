import { createHash, createHmac, randomBytes } from 'node:crypto'

/** Identical body at approval and dispatch; changing even one value invalidates it. */
export function mappingBody(args: Record<string, unknown>, agentId: string, callId: string | undefined) {
  return {
    source: args.source, target: args.target, relation: args.relation,
    accepted: args.accepted, evidence: args.evidence ?? '', period: args.period ?? '',
    confirmed_by: agentId, call_id: callId ?? null,
  }
}

export class ApprovalReceipts {
  readonly #receipts = new Map<string, { receipt: string; expires: number }>()

  authorize(callId: string, body: unknown, permit?: string): void {
    const secret = process.env.BRIDGEFLOW_SERVICE_TOKEN ?? ''
    if (secret.length < 32) throw new Error('BRIDGEFLOW_SERVICE_TOKEN must have 32+ characters')
    for (const [id, value] of this.#receipts) {
      if (value.expires < Date.now()) this.#receipts.delete(id)
    }
    if (this.#receipts.size >= 64) throw new Error('Approval receipt capacity exceeded')
    const stamp = Math.floor(Date.now() / 1000)
    const nonce = randomBytes(16).toString('hex')
    const digest = createHash('sha256').update(JSON.stringify(body)).digest('hex')
    const identity = permit ? `.${permit}` : ''
    const signature = createHmac('sha256', secret).update(`${stamp}.${nonce}.${digest}${identity}`).digest('hex')
    this.#receipts.set(callId, { receipt: `${stamp}.${nonce}.${signature}${identity}`, expires: Date.now() + 60_000 })
  }

  take(callId: string | undefined): string {
    const item = callId ? this.#receipts.get(callId) : undefined
    if (callId) this.#receipts.delete(callId)
    if (!item || item.expires < Date.now()) throw new Error('No current approval; nothing was written')
    return item.receipt
  }
}
