import test from 'node:test'
import assert from 'node:assert/strict'
import { stageOf } from '../src/client/state-guide.tsx'

const batch = (status: string) => ({ status }) as never
test('Business state names the stage from the same facts the tab shows', () => {
  assert.equal(stageOf({ batch: null, running: false, report: null, approvalWaiting: false }), 'empty')
  assert.equal(stageOf({ batch: batch('needs_configuration'), running: false, report: null, approvalWaiting: false }), 'configure')
  assert.equal(stageOf({ batch: batch('needs_review'), running: false, report: null, approvalWaiting: false }), 'settle')
  assert.equal(stageOf({ batch: batch('ready'), running: false, report: null, approvalWaiting: false }), 'review')
  assert.equal(stageOf({ batch: batch('ready'), running: true, report: null, approvalWaiting: false }), 'running')
  assert.equal(stageOf({ batch: batch('ready'), running: false, report: { id: 'r', status: 'partial', attention: 0 }, approvalWaiting: false }), 'partial')
  assert.equal(stageOf({ batch: batch('ready'), running: false, report: { id: 'r', status: 'validated', attention: 3 }, approvalWaiting: false }), 'decide')
  assert.equal(stageOf({ batch: batch('ready'), running: false, report: { id: 'r', status: 'validated', attention: 0 }, approvalWaiting: false }), 'close')
  // A waiting approval card comes first, whatever else is going on.
  assert.equal(stageOf({ batch: batch('ready'), running: true, report: null, approvalWaiting: true }), 'approval')
})
