import { useUI } from './ui.ts'

/**
 * The reasoning behind a page, one click away from its instruction.
 *
 * A hint says what to do; this says why the page behaves as it does. Keeping the two
 * apart lets the hint stay one sentence while the logic is still there for anyone who
 * wants it — a reviewer, or a person deciding whether to trust a number.
 */
export function Explain({ text }: { text: string }) {
  const { t } = useUI()
  return <details className="bf-explain">
    <summary>{t('howItWorks')}</summary>
    <ul>{text.split('\n').map(line => <li key={line}>{line}</li>)}</ul>
  </details>
}
