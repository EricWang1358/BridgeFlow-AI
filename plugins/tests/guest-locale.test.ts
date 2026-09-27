import assert from 'node:assert/strict'
import test from 'node:test'
import { GUEST_LOCALE_KEY, applyGuestLocale, guestLocale, type LocaleLike, type StorageLike } from '../src/client/guest-locale.ts'

/**
 * The public demo opens in English whatever the browser says (docs/37): judges on a zh-CN
 * browser saw a Chinese console because dsh withholds the settings scope the #110 default
 * waits for. A guest's own switch still wins, and broken storage never breaks the page.
 */

function fakeLocale(active: string, ids = ['zh', 'en']) {
  const calls: string[] = []
  const locale: LocaleLike = {
    getLocale: () => ({ active, locales: ids.map(id => ({ id })) }),
    setLocale: id => { calls.push(id); active = id },
  }
  return { locale, calls }
}

function memoryStorage(initial?: string): StorageLike & { value: string | null } {
  const store = { value: initial ?? null,
    getItem: (key: string) => key === GUEST_LOCALE_KEY ? store.value : null,
    setItem: (key: string, value: string) => { if (key === GUEST_LOCALE_KEY) store.value = value } }
  return store
}

test('a guest with no earlier choice opens in English, whatever the browser derived', () => {
  const { locale, calls } = fakeLocale('zh')
  applyGuestLocale(locale, memoryStorage(), () => {})
  assert.deepEqual(calls, ['en'])
})

test("a guest's own earlier switch is restored", () => {
  const { locale, calls } = fakeLocale('en')
  applyGuestLocale(locale, memoryStorage('zh'), () => {})
  assert.deepEqual(calls, ['zh'])
})

test('a remembered language that is no longer selectable falls back to English', () => {
  assert.equal(guestLocale('ja', ['zh', 'en']), 'en')
  assert.equal(guestLocale('', ['zh', 'en']), 'en')
  assert.equal(guestLocale(null, ['zh', 'en']), 'en')
})

test('switches after the default are remembered; the provisional browser locale is not', () => {
  const { locale } = fakeLocale('zh')
  const storage = memoryStorage()
  let emit: (active: string) => void = () => { throw new Error('listener not registered') }
  applyGuestLocale(locale, storage, listener => { emit = listener })
  assert.equal(storage.value, null, 'applying the default must not store it as a choice')
  emit('zh')
  assert.equal(storage.value, 'zh')
})

test('storage that is missing or refuses never blocks the English default', () => {
  const refusing: StorageLike = {
    getItem: () => { throw new Error('SecurityError') },
    setItem: () => { throw new Error('QuotaExceededError') },
  }
  for (const storage of [undefined, refusing]) {
    const { locale, calls } = fakeLocale('zh')
    let emit: (active: string) => void = () => {}
    applyGuestLocale(locale, storage, listener => { emit = listener })
    assert.deepEqual(calls, ['en'])
    assert.doesNotThrow(() => emit('zh'))
  }
})
