import test from 'node:test'
import assert from 'node:assert/strict'
import { applyGlossary, makeGloss } from '../src/client/ui.ts'

test('English glosses keep the original name, compose department prefixes and never touch file names or Chinese', () => {
  applyGlossary({ names: { 财务: 'Finance', 财务部: 'Finance', 期初金额: 'Opening balance', 客户名称: 'Customer name', 材料A: 'Material A', 单价: 'Unit price', 方: 'm³' },
    texts: { '字典 v2': 'Dictionary v2' } })
  const en = makeGloss(true), zh = makeGloss(false)
  assert.equal(en.label('客户名称'), 'Customer name (客户名称)')
  assert.equal(en.english('财务_期初金额'), 'Finance · Opening balance')
  // Cleaned column keys read back to the declared name.
  assert.equal(en.english('材料a'), 'Material A')
  assert.equal(en.english('单价_2'), 'Unit price 2')
  assert.equal(en.text('字典 v2'), 'Dictionary v2')
  assert.equal(en.message('finance · 模拟-财务部-2024-07.xlsx · row 5 · 期初金额'), 'finance · 模拟-财务部-2024-07.xlsx · row 5 · Opening balance (期初金额)')
  // A one-character unit is never replaced inside running text.
  assert.equal(en.message('东方 客户名称'), '东方 Customer name (客户名称)')
  assert.equal(en.formula('sum(期初金额) / 2'), 'sum(Opening balance) / 2')
  // Unknown names and values stay exactly as declared.
  assert.equal(en.label('示例城建集团'), '示例城建集团')
  assert.equal(zh.label('客户名称'), '客户名称')
  assert.equal(zh.message('客户名称 differs'), '客户名称 differs')
})
