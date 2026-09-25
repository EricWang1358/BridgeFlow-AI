import { guideLead, guideTitle, userGuide } from './user-guide.ts'
import { useUI } from './ui.ts'

/** The user guide as a page under Sessions & settings: a contents list, then every section. */
export function GuidePage() {
  const { language } = useUI()
  const i = language === 'zh' ? 0 : 1
  return <article className="bf-state bf-user-guide" aria-label={guideTitle[i]}>
    <h2>{guideTitle[i]}</h2>
    <p className="bf-lead">{guideLead[i]}</p>
    <nav aria-label={language === 'zh' ? '目录' : 'Contents'}><ol className="bf-guide-toc">
      {userGuide.map(section => <li key={section.id}><a href={`#bf-guide-${section.id}`} onClick={e => {
        e.preventDefault(); document.getElementById(`bf-guide-${section.id}`)?.scrollIntoView({ block: 'start', behavior: 'smooth' })
      }}>{section.title[i]}</a></li>)}
    </ol></nav>
    {userGuide.map(section => <section key={section.id} id={`bf-guide-${section.id}`} aria-labelledby={`bf-guide-${section.id}-h`}>
      <h3 id={`bf-guide-${section.id}-h`}>{section.title[i]}</h3>
      {section.intro && <p>{section.intro[i]}</p>}
      {section.steps && <ol className="bf-guide-steps">{section.steps.map((step, n) => <li key={n}>{step[i]}</li>)}</ol>}
      {section.points && <ul className="bf-guide-points">{section.points.map((point, n) => <li key={n}>{point[i]}</li>)}</ul>}
      {section.faq && <dl className="bf-guide-faq">{section.faq.map(([q, a], n) => <div key={n}><dt>{q[i]}</dt><dd>{a[i]}</dd></div>)}</dl>}
      {section.terms && <dl className="bf-guide-terms">{section.terms.map(([term, meaning], n) => <div key={n}><dt>{term[i]}</dt><dd>{meaning[i]}</dd></div>)}</dl>}
      {section.note && <p className="bf-callout" data-tone="info">{section.note[i]}</p>}
    </section>)}
  </article>
}
