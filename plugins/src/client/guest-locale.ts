/**
 * The public demo opens in English whatever the browser says (docs/37).
 *
 * The #110 default in index.tsx only fires once the Host settings document has loaded, and dsh
 * withholds that scope on non-loopback pages — so on the public apex it never fires and a zh-CN
 * browser opens in Chinese. Guest mode therefore sets the language itself, through setLocale,
 * the locale plugin's only write entry.
 *
 * Default, not a lock: a guest who picks another language in Settings → General keeps it. On a
 * non-loopback page dsh holds that choice only for the page's lifetime, so it is remembered in
 * this browser's own storage and restored on the next load.
 *
 * No imports on purpose: the rules are testable without a browser or a running host.
 */

export const GUEST_LOCALE_KEY = 'bridgeflow.guest.locale'
const DEFAULT = 'en'

export interface LocaleLike {
  getLocale(): { active: string; locales: readonly { id: string }[] }
  setLocale(id: string): void
}
export type StorageLike = Pick<Storage, 'getItem' | 'setItem'>

/** The guest's own earlier choice when it is still a selectable language, else English. */
export function guestLocale(stored: string | null, available: readonly string[]): string {
  return stored && available.includes(stored) ? stored : DEFAULT
}

/** Storage can be absent or refuse (private modes, blocked site data): never fatal. */
function read(storage: StorageLike | undefined): string | null {
  try { return storage?.getItem(GUEST_LOCALE_KEY) ?? null } catch { return null }
}
function write(storage: StorageLike | undefined, id: string): void {
  try { storage?.setItem(GUEST_LOCALE_KEY, id) } catch { /* Remembering is best effort. */ }
}

/**
 * Apply the guest default, then remember every later switch. Call once guest mode is known.
 * `onChange` subscribes to the host's `locale/change` event; switches made before this call
 * (the browser-derived provisional locale) are deliberately not remembered.
 */
export function applyGuestLocale(locale: LocaleLike, storage: StorageLike | undefined,
                                 onChange: (listener: (active: string) => void) => void): void {
  const target = guestLocale(read(storage), locale.getLocale().locales.map(l => l.id))
  locale.setLocale(target)
  onChange(active => write(storage, active))
}
