import { useEffect, useState } from 'react'
import { api, useUI } from './ui.ts'
import { Icon } from './icons.tsx'

/**
 * Guest mode: an isolated instance with sample data only, for people without a Feishu
 * account (evaluators). Feishu is never available here, and the AI model only when the
 * operator switched it on. Read once from the host's /config and shared.
 */
export type GuestMode = { guest: boolean; llm: boolean; staffUrl: string }
let cached: Promise<GuestMode> | null = null
/** The one /config read, shared by React (useGuestMode) and plugin activation (index.tsx). */
export function guestMode(): Promise<GuestMode> {
  cached ??= api<{ guestMode?: boolean; guestLlm?: boolean; staffUrl?: string }>('/config')
    .then(v => ({ guest: !!v.guestMode, llm: !!v.guestLlm, staffUrl: v.staffUrl ?? '' }))
    .catch(() => ({ guest: false, llm: true, staffUrl: '' }))
  return cached
}
export function useGuestMode(): GuestMode {
  const [mode, setMode] = useState<GuestMode>({ guest: false, llm: true, staffUrl: '' })
  useEffect(() => {
    let live = true
    void guestMode().then(value => { if (live) setMode(value) })
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
    {/^https:\/\//.test(mode.staffUrl) && <a href={mode.staffUrl} rel="noopener">{t('guestStaffSignIn')}</a>}
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
  return <p className="bf-hint bf-guest-off"><span aria-hidden="true"><Icon name="block" size={14} /></span> {feature} · {t('guestUnavailable')}</p>
}
