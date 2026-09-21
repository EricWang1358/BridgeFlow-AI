import { useState } from 'react'
import { navigate, reviewRequest, useUI, type Summary } from './ui.ts'

/**
 * What the status chip owes the person reading it: the sentence that says what to do
 * next, and the one control that does it (#244).
 *
 * The `next_<status>` copy existed for every status and was rendered by nothing —
 * a person importing four departments saw「需要人工复核」and a wall. The counts in the
 * sentence come from the same Summary the chip does, and each button goes where the
 * work is settled, the way the open-item inbox's `next_view` rows already work.
 */
export function NextStep({ batch }: { batch: Summary }) {
  const { t } = useUI()
  const [notice, setNotice] = useState(''), [error, setError] = useState('')
  const quarantined = batch.departments.reduce((n, d) => n + d.quarantined, 0)
  // Placeholders keep one key per status instead of a key per count permutation;
  // statuses without placeholders are untouched by the replace.
  const guidance = t(`next_${batch.status}`)
    .replaceAll('{quarantined}', String(quarantined))
    .replaceAll('{unresolved}', String(batch.unresolved))
  async function copyRequest() {
    setNotice(''); setError('')
    try { await navigator.clipboard.writeText(reviewRequest(batch.batch_id, batch.period)); setNotice(t('copiedRequest')) }
    catch (e) { setError(String(e)) }
  }
  const actions = batch.status === 'needs_review'
    // Each control is disabled by the count that justifies it, so a zero never sends
    // somebody into an empty tab — and the sentence above still shows both counts.
    ? <>
      <button disabled={!quarantined} onClick={() => navigate({ batch: batch.batch_id, view: 'quarantine' })}>{t('goQuarantine')}</button>
      <button disabled={!batch.unresolved} onClick={() => navigate({ batch: batch.batch_id, view: 'mappings' })}>{t('goMappings')}</button>
    </>
    : batch.status === 'ready'
      ? <button className="bf-primary" onClick={() => void copyRequest()}>{t('copyReviewRequest')}</button>
      // empty and needs_configuration share the exit: the import form. What differs —
      // why there is no data — is the refusal callout's job, not this row's.
      : <button onClick={() => window.dispatchEvent(new Event('bridgeflow:add-sources'))}>{t('newBatch')}</button>
  return <div className="bf-next">
    <p className="bf-hint" style={{ margin: 0 }}>{guidance}</p>
    <div className="bf-actions" style={{ margin: '6px 0 0' }}>{actions}</div>
    {notice && <p role="status" className="bf-hint">{notice}</p>}
    {error && <p role="alert" className="bf-error">{error}</p>}
  </div>
}
