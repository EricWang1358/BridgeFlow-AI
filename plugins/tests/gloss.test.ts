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

test('the Chinese interface reads backend sentences in Chinese, keeping names and values as written', async () => {
  const { translate } = await import('../src/client/zh-messages.ts')
  assert.equal(translate('客户名称 differs between departments (production: 示例城建集团; procurement/finance/marketing: 示例城建集团有限公司); confirm which is right'),
    '客户名称 在各部门填写不一致（生产部: 示例城建集团; 物资部/财务部/市场部: 示例城建集团有限公司）；请确认哪个正确')
  assert.equal(translate('1 cell(s): 客户名称: departments disagree or the formula contradicts the value'), '1 个单元格：客户名称：各部门不一致，或公式与值矛盾')
  assert.equal(translate('batch = abc123; department = finance; period = 2024-07'), '批次 abc123；财务部；期间 2024-07')
  assert.equal(translate('上月实际量 = average; 出厂量 = sum; 实际签收率 = disagreed'), '上月实际量 = 取平均; 出厂量 = 求和; 实际签收率 = 各行不一致')
  assert.equal(translate('The brief is built from a saved review'), '月度简报要在保存研判之后生成')
  // Anything without a template is shown exactly as written.
  assert.equal(translate('something new from the backend'), 'something new from the backend')
  applyGlossary({ names: {}, texts: {} })
  assert.equal(makeGloss(false).message('This batch has no saved review'), '这个批次没有保存的研判')
})
