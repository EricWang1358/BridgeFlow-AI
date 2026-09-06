import type { ReactNode } from 'react'
import { useUI } from './ui.ts'
/** Documents sit inside the shell; uploaded Sources and Studio belong to it. */
export function Notebook({ title, description, sources, studio, children }: {
  title: string; description: string; sources: ReactNode; studio: ReactNode; children: ReactNode
}) {
  const { t } = useUI()
  return <main className="bf-state bf-document" aria-label={title}>
    <header><h2>{title}</h2><p className="bf-hint">{description}</p></header>
    {children}
    <details className="bf-document-evidence"><summary>{t('sourceHelp')}</summary>{sources}</details>
    <section className="bf-document-checks" aria-label={t('studioHelp')}>{studio}</section>
  </main>
}
