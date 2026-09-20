/**
 * Who a model-initiated read belongs to (issue #231).
 *
 * The rules under test are the two judgement calls, not the plumbing: an expired
 * binding is gone rather than relayed, and two people bound at once means nobody is
 * named — a wrong attribution is worse than an absent one.
 */
import assert from 'node:assert/strict'
import test from 'node:test'
import { ActorBindings, DEFAULT_BINDING_MS } from '../src/actor.ts'

const NOW = 1_700_000_000_000
const alice = { token: 'jwt-alice', subject: 'ou_alice', expiresAt: NOW + 60_000 }
const bob = { token: 'jwt-bob', subject: 'ou_bob', expiresAt: NOW + 60_000 }

test('a bound session relays the browser\'s own token, not a host assertion', () => {
  const actors = new ActorBindings()
  actors.bind('session-1', alice)
  assert.deepEqual(actors.header(NOW), { 'x-bridgeflow-user': 'jwt-alice' })
  assert.equal(actors.subjectForSession('session-1', NOW), 'ou_alice')
})

test('an expired binding is dropped instead of relayed', () => {
  const actors = new ActorBindings()
  actors.bind('session-1', { ...alice, expiresAt: NOW - 1 })
  assert.deepEqual(actors.header(NOW), {})
  assert.equal(actors.forSession('session-1', NOW), undefined)
  assert.equal(actors.subjectForSession('session-1', NOW), '')
})

test('two people bound at once means no name at all', () => {
  const actors = new ActorBindings()
  actors.bind('session-1', alice)
  actors.bind('session-2', bob)
  // Attaching either token would attribute one person's run to the other.
  assert.deepEqual(actors.header(NOW), {})
  // Per-session facts stay exact — it is only the ambient question that is unanswerable.
  assert.equal(actors.subjectForSession('session-1', NOW), 'ou_alice')
  assert.equal(actors.subjectForSession('session-2', NOW), 'ou_bob')
})

test('the same person in several sessions is still unambiguous', () => {
  const actors = new ActorBindings()
  actors.bind('session-1', alice)
  actors.bind('session-2', { ...alice, token: 'jwt-alice-refreshed' })
  assert.equal(Object.keys(actors.header(NOW)).length, 1)
})

test('ambiguity clears when the other binding expires', () => {
  const actors = new ActorBindings()
  actors.bind('session-1', alice)
  actors.bind('session-2', { ...bob, expiresAt: NOW + 10 })
  assert.deepEqual(actors.header(NOW), {})
  assert.deepEqual(actors.header(NOW + 20), { 'x-bridgeflow-user': 'jwt-alice' })
})

test('releasing a session removes its claim', () => {
  const actors = new ActorBindings()
  actors.bind('session-1', alice)
  actors.release('session-1')
  assert.deepEqual(actors.header(NOW), {})
})

test('an incomplete claim is refused rather than stored', () => {
  const actors = new ActorBindings()
  actors.bind('', alice)
  actors.bind('session-1', { ...alice, token: '' })
  actors.bind('session-2', { ...alice, subject: '' })
  assert.deepEqual(actors.header(NOW), {})
})

test('a claim without a stated lifetime still expires', () => {
  assert.ok(DEFAULT_BINDING_MS > 0 && DEFAULT_BINDING_MS <= 15 * 60 * 1000)
})
