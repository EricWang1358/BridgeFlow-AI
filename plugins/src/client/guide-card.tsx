import { useEffect, useRef, useState } from 'react'
import { guide, type GuideEntry, type GuideFeature } from '../app-guide.ts'
import { navigate, route, useUI } from './ui.ts'

/**
 * The captain's answer to "where is …?": the clicks, in the reader's language, and a button
 * that opens the page. A fresh answer opens it once by itself; one replayed from history
 * never moves the screen.
 */
export function GuideCard({ feature, fresh }: { feature: string; fresh: boolean }) {
  const { t, language } = useUI()
  const entry = (guide as Record<string, GuideEntry>)[feature as GuideFeature]
  const batch = route().batch
  const blocked = !!entry?.needsBatch && !batch
  const [opened, setOpened] = useState(false), done = useRef(false)
  const open = () => { if (!entry?.view || blocked) return; navigate({ ...(batch ? { batch } : {}), view: entry.view }); setOpened(true) }
  useEffect(() => { if (fresh && !done.current) { done.current = true; open() } }, [])
  if (!entry) return null
  const pick = (text: readonly [string, string]) => language === 'zh' ? text[0] : text[1]
  return <section className="bf-card bf-guide" aria-label={t('app_guide')}>
    <header className="bf-card-head"><strong>{t('app_guide')}</strong></header>
    <p>{pick(entry.what)}</p>
    <ol className="bf-guide-steps">{entry.steps.map((step, i) => <li key={i}>{pick(step)}</li>)}</ol>
    {entry.note && <p className="bf-hint">{pick(entry.note)}</p>}
    {entry.view && <div className="bf-actions" style={{ margin: '10px 0 0' }}>
      <button className="bf-primary" disabled={blocked} onClick={open}>{t('guideOpen')}</button>
      {opened && <span className="bf-hint" role="status">{t('guideOpened')}</span>}
    </div>}
    {blocked && <p className="bf-hint">{t('guideNeedsBatch')}</p>}
  </section>
}
