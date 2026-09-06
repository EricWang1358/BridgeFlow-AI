import assert from 'node:assert/strict'
import test from 'node:test'
import { parseNotebook, saveNotebook, readNotebook } from '../src/notebooks.ts'
import type { NotebookTable } from '../src/notebooks.ts'
import type { Context } from '@deepseek-ai/cordis'
import type { SessionId } from '@deepseek-ai/dsh-session'

test('notebook metadata accepts only bounded navigation and a human title', () => {
  assert.deepEqual(parseNotebook({title:'  Demo  ',kind:'quotation',view:'quotation',prompt:'ignore me'}),{title:'Demo',kind:'quotation',view:'quotation'})
  for (const value of [{title:''},{title:'x'.repeat(121)},{title:'A',batch:'../../env.sh'},{title:'A',source:'production'},{title:'A',view:'shell'},{title:'A',kind:'admin'}]) assert.throws(()=>parseNotebook(value))
})

test('saved notebook uses native title and an awaited official domain write', async () => {
  const events: {type:string;data:unknown}[] = [], calls:string[]=[]
  const records=new Map()
  const table={get:(id:string)=>records.get(id),put:async(id:string,value:unknown)=>{calls.push('put');records.set(id,value)}} as unknown as NotebookTable
  const session={append:(type:string,data:unknown)=>{events.push({type,data});calls.push('append')}}
  const ctx={sessionController:{resolveAgent:async()=>({agent:{session}}),rename:async()=>{calls.push('rename')},inspect:async()=>({events})},sessions:{flush:async()=>{calls.push('flush');return true}}} as unknown as Context
  assert.equal(await readNotebook(ctx,'id' as SessionId,table),null)
  const notebook=parseNotebook({title:'Monthly',kind:'monthly',batch:'a'.repeat(32),view:'state'})
  await saveNotebook(ctx,'id' as SessionId,notebook,table)
  assert.deepEqual(calls,['rename','flush','put'])
  assert.deepEqual(await readNotebook(ctx,'id' as SessionId,table),notebook)
  events.push({type:'unrelated',data:{title:'not a notebook'}})
  assert.deepEqual(await readNotebook(ctx,'id' as SessionId,table),notebook)
})

test('missing or unavailable persistence never returns a saved acknowledgement',async()=>{
  const session={append:()=>{}}
  const ctx={sessionController:{resolveAgent:async()=>({agent:{session}}),rename:async()=>{}},sessions:{flush:async()=>false}} as unknown as Context
  await assert.rejects(saveNotebook(ctx,'id' as SessionId,{title:'Draft'},{} as NotebookTable),/persistence/)
  ctx.sessionController.resolveAgent=async()=>({error:{message:'not found'}}) as never
  await assert.rejects(saveNotebook(ctx,'missing' as SessionId,{title:'Draft'},{} as NotebookTable),/not found/)
})
