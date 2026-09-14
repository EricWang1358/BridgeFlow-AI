import test from 'node:test'
import assert from 'node:assert/strict'
import { acceptEvent, canFinish, fresh, parseProgress, observeTour, startTour, tourEvent, tourSnapshot, exitTour, resetTour } from '../src/client/tour/state.ts'
import { required, tours } from '../src/client/tour/steps.ts'
import { placeCard } from '../src/client/tour/position.ts'

test('corrupt, stale or forged completion never resumes as a successful task', () => {
  for (const value of ['{', JSON.stringify({...fresh(),version:0}), JSON.stringify({...fresh(),track:'__proto__'}), JSON.stringify({...fresh(),index:999}), JSON.stringify({...fresh(),status:'completed'}), JSON.stringify({...fresh(),batch:'../secret'})]) assert.deepEqual(parseProgress(value), fresh())
})
test('completion requires every actual event from the same batch', () => {
  let p = {...fresh(),status:'inProgress' as const}
  assert.equal(acceptEvent(p, 'saved', 'a'.repeat(32)), p)
  p = acceptEvent(p, 'sample', 'a'.repeat(32)) as typeof p
  for (const event of required.filter(x => x !== 'sample' && x !== 'saved')) p = acceptEvent(p, event, 'a'.repeat(32)) as typeof p
  assert.equal(canFinish(p), false)
  assert.equal(acceptEvent(p, 'saved', 'b'.repeat(32)), p)
  p = acceptEvent(p, 'saved', 'a'.repeat(32)) as typeof p
  assert.equal(canFinish(p), true)
  const replacement = acceptEvent(p, 'sample', 'c'.repeat(32))
  assert.deepEqual(replacement.done, ['sample'])
  assert.equal(canFinish(replacement), false)
  assert.equal(acceptEvent({...p,status:'skipped'},'saved','a'.repeat(32)).status, 'skipped')
})
test('notebook-scoped progress, safe resume and supplement return survive interruption', () => {
  const entries = new Map<string,string>()
  Object.defineProperty(globalThis, 'sessionStorage', {configurable:true,value:{getItem:(k:string)=>entries.get(k)??null,setItem:(k:string,v:string)=>entries.set(k,v),removeItem:(k:string)=>entries.delete(k)}})
  observeTour('one','',false,true); startTour()
  tourEvent('sample','a'.repeat(32),'one'); observeTour('one','a'.repeat(32),true,true); tourEvent('master','a'.repeat(32))
  assert.equal(tours.core[tourSnapshot().progress.index]!.id,'result')
  startTour('review'); startTour('core',true)
  assert.equal(tours.core[tourSnapshot().progress.index]!.id,'result')
  exitTour(); assert.equal(tourSnapshot().progress.status,'skipped')
  observeTour('two','',false,true); assert.equal(tourSnapshot().progress.status,'notStarted')
  observeTour('one','a'.repeat(32),true,true); assert.equal(tourSnapshot().progress.status,'skipped')
  startTour('core',true); assert.equal(tours.core[tourSnapshot().progress.index]!.id,'result')
  resetTour(); assert.deepEqual(tourSnapshot().progress,fresh())
})
test('denied storage leaves the current tour usable', () => {
  Object.defineProperty(globalThis,'sessionStorage',{configurable:true,get(){throw Error('blocked')}})
  observeTour('private','',false,true); startTour(); assert.equal(tourSnapshot().mode,'active'); assert.equal(tourSnapshot().storageOK,false); exitTour()
})
test('cards fit desktop, narrow and visual viewport offsets without covering controls', () => {
  for (const vp of [{x:0,y:0,width:1440,height:1000},{x:0,y:0,width:390,height:844},{x:30,y:100,width:340,height:500}]) {
    const target = {x:vp.x+24,y:vp.y+140,width:200,height:42}
    const box = placeCard(target,350,400,vp)
    assert(box.x>=vp.x && box.y>=vp.y)
    assert(box.x+box.width<=vp.x+vp.width && box.y+box.height<=vp.y+vp.height)
    assert(box.x>=target.x+target.width || box.x+box.width<=target.x || box.y>=target.y+target.height || box.y+box.height<=target.y)
  }
})
