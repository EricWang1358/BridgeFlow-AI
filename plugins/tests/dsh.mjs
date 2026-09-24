/**
 * Resolve the dsh executable the browser smokes are allowed to boot, and a
 * serve-time assertion that the host actually composed the official client
 * tree.
 *
 * Why this exists (#97): the Python SDK ships a `dsh` console script that
 * wraps a pkg-packed single-file executable. When a venv-activated shell puts
 * it first on PATH, a bare `spawn('dsh', …)` boots the packed runtime, which
 * rewrites `$DSH_HOME/profiles/node_modules` into ESM proxies whose manifests
 * strip the `dsh.client` declaration. ClientModuleRegistry then scans every
 * official client package as "not a client package", the served HTML preloads
 * only bridgeflow-plugins, and the browser dies with
 * `client-modules: HTML did not preload @deepseek-ai/dsh-client-modules/client.js`.
 * The native npm CLI self-heals such a polluted home on boot, so selecting it
 * here is the whole fix. This mirrors `backend/src/bridgeflow/dsh_runtime.py`
 * (`native_command`); the two implementations must keep rejecting the same
 * candidates.
 */
import { execFileSync } from 'node:child_process'
import { accessSync, closeSync, constants, openSync, readSync, realpathSync } from 'node:fs'
import { delimiter, join } from 'node:path'

const PINNED_VERSION = '0.1.2-rc.1'
const INSTALL_HINT = 'Install the native CLI: npm install -g @deepseek-ai/dsh@0.1.2-rc.1; ' +
  'or set BRIDGEFLOW_DSH to its executable. Web and SDK must use this same installation.'

let resolved
export function resolveDsh() {
  if (resolved) return resolved
  const configured = process.env.BRIDGEFLOW_DSH
  const candidates = configured
    ? [configured]
    : (process.env.PATH ?? '').split(delimiter).filter(Boolean).map(dir => join(dir, 'dsh'))
  for (const candidate of candidates) {
    let path
    try {
      accessSync(candidate, constants.X_OK)
      path = realpathSync(candidate)
      const fd = openSync(path, 'r')
      const prefix = Buffer.alloc(256)
      let header
      try { header = prefix.subarray(0, readSync(fd, prefix)).toString('utf8').split('\n', 1)[0] }
      finally { closeSync(fd) }
      if (!header.startsWith('#!') || !header.includes('node')) continue
      const version = execFileSync(path, ['--version'], { encoding: 'utf8', timeout: 10_000 }).trim()
      if (version === PINNED_VERSION) return (resolved = path)
    } catch {
      continue
    }
  }
  throw new Error(INSTALL_HINT)
}

/**
 * Fail fast when the host composed a partial client graph, before spending a
 * browser launch and a 15s locator timeout on an environment error. The first
 * GET redeems the token into an auth cookie and redirects; the jar follows.
 */
export async function assertClientModulesServed(url) {
  const origin = new URL(url).origin
  const jar = new Map()
  const signal = AbortSignal.timeout(10_000)
  let target = new URL(url)
  let html
  for (let redirects = 0; redirects <= 5; redirects++) {
    const res = await fetch(target, { redirect: 'manual', signal,
      headers: jar.size ? { cookie: [...jar.values()].join('; ') } : {} })
    for (const cookie of res.headers.getSetCookie()) {
      const pair = cookie.split(';')[0]
      jar.set(pair.split('=')[0], pair)
    }
    if ([301, 302, 303, 307, 308].includes(res.status)) {
      await res.body?.cancel()
      const location = res.headers.get('location')
      if (!location) throw new Error('DSH client preflight: redirect without Location')
      target = new URL(location, target)
      if (target.origin !== origin) throw new Error('DSH client preflight: cross-origin redirect refused')
      continue
    }
    if (!res.ok) {
      await res.body?.cancel()
      throw new Error(`DSH client preflight: HTTP ${res.status}`)
    }
    html = await res.text()
    break
  }
  if (html === undefined) throw new Error('DSH client preflight: redirect limit exceeded')
  if (!html.includes('@deepseek-ai/dsh-client-modules/client.js')) {
    throw new Error(
      'dsh web served a page without the official client modules; the browser would fail with ' +
      '"client-modules: HTML did not preload @deepseek-ai/dsh-client-modules/client.js". ' +
      'The likely cause is that `dsh` resolved to the Python SDK\'s packed executable, which rewrites ' +
      '$DSH_HOME/profiles/node_modules into proxies whose manifests strip the dsh.client declaration. ' +
      'Diagnose with: ls $DSH_HOME/profiles/node_modules/@deepseek-ai/cordis ' +
      '(a symlink is healthy; an entry-0.js proxy directory means a packed-runtime boot polluted the home). ' +
      INSTALL_HINT)
  }
  return html
}

/**
 * The model a live (billed) run should use: the operator's DSH_PROVIDER / DSH_MODEL from
 * env.sh. A journey starts dsh on a fresh DSH_HOME with no settings.yaml, so without this
 * the agent falls back to dsh's built-in default model id — which only the official DeepSeek
 * endpoint accepts (2026-09-24: a gateway endpoint refused it and every live turn failed).
 */
export function liveModelPatch() {
  const model = process.env.DSH_MODEL
  if (!model) return ''
  const provider = process.env.DSH_PROVIDER || 'deepseek-official'
  return `\n- id: agent-default-model\n  name: '@deepseek-ai/dsh-agent-default-model'\n  config:\n    provider: ${JSON.stringify(provider)}\n    model: ${JSON.stringify(model)}\n`
}
