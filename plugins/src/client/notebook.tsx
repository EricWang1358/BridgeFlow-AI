import { useState, type ReactNode } from 'react'
import { useUI } from './ui.ts'

/** Three native-plugin panels; the host still owns chat, trace and approvals. */
export function Notebook({ title, description, sources, studio, children }: {
  title: string; description: string; sources: ReactNode; studio: ReactNode; children: ReactNode
}) {
  const { t } = useUI()
  const [showSources, setShowSources] = useState(true), [showStudio, setShowStudio] = useState(true)
  return <main className="bf-state bf-notebook" aria-label={title}>
    <header className="bf-notebook-head"><div><p className="bf-eyebrow">BridgeFlow</p><h2>{title}</h2><p className="bf-hint">{description}</p></div>
      <div className="bf-actions"><button aria-expanded={showSources} onClick={() => setShowSources(v => !v)}>{t('sources')}</button><button aria-expanded={showStudio} onClick={() => setShowStudio(v => !v)}>{t('studio')}</button></div>
    </header>
    <div className="bf-notebook-grid" data-sources={showSources} data-studio={showStudio}>
      {showSources && <aside className="bf-notebook-pane bf-notebook-sources" aria-label={t('sources')}><header><h3>{t('sources')}</h3><span className="bf-hint">{t('sourceHelp')}</span></header>{sources}</aside>}
      <section className="bf-notebook-pane bf-notebook-work" aria-label={t('workArea')}>{children}</section>
      {showStudio && <aside className="bf-notebook-pane bf-notebook-studio" aria-label={t('studio')}><header><h3>{t('studio')}</h3><span className="bf-hint">{t('studioHelp')}</span></header>{studio}</aside>}
    </div>
  </main>
}
