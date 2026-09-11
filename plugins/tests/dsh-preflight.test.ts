import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { mkdtemp, mkdir, writeFile, chmod, rm, access } from 'node:fs/promises'
import { createServer } from 'node:http'
import { tmpdir } from 'node:os'
import { join, delimiter } from 'node:path'
import { test } from 'node:test'
import { assertClientModulesServed } from './dsh.mjs'

const moduleUrl = new URL('./dsh.mjs', import.meta.url).href

test('venv-first PATH skips the packed wrapper; an explicit unsupported runtime fails closed', async () => {
  const root = await mkdtemp(join(tmpdir(), 'bf-runtime-selection-'))
  try {
    const venv = join(root, 'venv'), native = join(root, 'native'), marker = join(root, 'executed')
    await mkdir(venv); await mkdir(native)
    await writeFile(join(venv, 'dsh'), `#!/bin/sh\ntouch '${marker}'\n`)
    await writeFile(join(native, 'dsh'), `#!${process.execPath}\nconsole.log('0.1.2-rc.1')\n`)
    await chmod(join(venv, 'dsh'), 0o755); await chmod(join(native, 'dsh'), 0o755)
    const env = { ...process.env, PATH: [venv, native, process.env.PATH].join(delimiter) }
    delete env.BRIDGEFLOW_DSH
    const probe = `import {resolveDsh} from ${JSON.stringify(moduleUrl)}; console.log(resolveDsh())`
    const run = (extra = {}) => execFileSync(process.execPath, ['--input-type=module', '-e', probe],
      { env: { ...env, ...extra }, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim()
    assert.equal(run(), join(native, 'dsh'))
    assert.throws(() => run({ BRIDGEFLOW_DSH: join(venv, 'dsh') }), /Install the native CLI/)
    await assert.rejects(access(marker))
    await writeFile(join(native, 'dsh'), `#!${process.execPath}\nconsole.log('unsupported')\n`)
    assert.throws(() => run({ BRIDGEFLOW_DSH: join(native, 'dsh') }), /Install the native CLI/)
  } finally { await rm(root, { recursive: true, force: true }) }
})

test('client preflight redeems auth and refuses missing modules, redirect loops and cookie forwarding', async () => {
  const server = createServer((req, res) => {
    if (req.url === '/login') { res.writeHead(302, { location: '/', 'set-cookie': 'session=test; HttpOnly' }); res.end(); return }
    if (req.url === '/loop') { res.writeHead(302, { location: '/loop' }); res.end(); return }
    if (req.url === '/external') { res.writeHead(302, { location: 'https://example.invalid/' }); res.end(); return }
    if (req.url === '/stall') { res.writeHead(200); res.write('<html>'); return }
    if (req.url === '/missing') { res.end('<html></html>'); return }
    if (req.headers.cookie !== 'session=test') { res.writeHead(401); res.end(); return }
    res.end('<script src="@deepseek-ai/dsh-client-modules/client.js"></script>')
  })
  await new Promise<void>(resolve => server.listen(0, '127.0.0.1', resolve))
  const addr = server.address()
  assert(addr && typeof addr !== 'string')
  const base = `http://127.0.0.1:${addr.port}`
  try {
    assert.match(await assertClientModulesServed(base + '/login'), /dsh-client-modules/)
    await assert.rejects(assertClientModulesServed(base + '/'), /HTTP 401/)
    await assert.rejects(assertClientModulesServed(base + '/missing'), /without the official client modules/)
    await assert.rejects(assertClientModulesServed(base + '/loop'), /redirect limit/)
    await assert.rejects(assertClientModulesServed(base + '/external'), /cross-origin redirect/)
    await assert.rejects(assertClientModulesServed(base + '/stall'), (error: Error) => ['TimeoutError', 'AbortError'].includes(error.name))
  } finally { server.closeAllConnections(); await new Promise<void>(resolve => server.close(() => resolve())) }
})
