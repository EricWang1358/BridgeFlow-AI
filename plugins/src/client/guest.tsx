import { useEffect, useState } from 'react'
import { api, useUI } from './ui.ts'

/**
 * Guest mode: an isolated instance with sample data only, for people without a Feishu
 * account (evaluators). Feishu is never available here, and the AI model only when the
 * operator switched it on. Read once from the host's /config and shared.
 */
export type GuestMode = { guest: boolean; llm: boolean }
let cached: Promise<GuestMode> | null = null
export function useGuestMode(): GuestMode {
  const [mode, setMode] = useState<GuestMode>({ guest: false, llm: true })
  useEffect(() => {
    cached ??= api<{ guestMode?: boolean; guestLlm?: boolean }>('/config')
      .then(v => ({ guest: !!v.guestMode, llm: !!v.guestLlm })).catch(() => ({ guest: false, llm: true }))
    let live = true
    void cached.then(value => { if (live) setMode(value) })
    return () => { live = false }
  }, [])
  return mode
}

export function GuestBanner() {
  const { t } = useUI()
  const mode = useGuestMode()
  if (!mode.guest) return null
  return <div className="bf-guest-banner" role="note">
    <strong>{t('guestBannerTitle')}</strong>
    <span>{t('guestBannerData')}</span>
    <span>{t('guestBannerFeishu')}</span>
    <span>{t(mode.llm ? 'guestBannerLlmOn' : 'guestBannerLlmOff')}</span>
  </div>
}

/** The top bar's reminder; the full note sits at the top of the Sources pane. */
export function GuestPill() {
  const { t } = useUI()
  return <span className="bf-guest-pill" title={`${t('guestBannerData')} ${t('guestBannerFeishu')}`}>{t('guestBannerTitle')}</span>
}

/** Where a Feishu feature would be: says it is not available here instead of failing. */
export function GuestUnavailable({ feature }: { feature: string }) {
  const { t } = useUI()
  return <p className="bf-hint bf-guest-off"><span aria-hidden="true">⊘</span> {feature} · {t('guestUnavailable')}</p>
}
