/**
 * How each kind of open item gets settled: who decides, where, and which step the captain can
 * start. One source for both the Tasks page (in the reader's language) and the captain's
 * `monthly_inbox` result (English, answered in the person's language).
 *
 * This is process, not business data: no field name appears here, and nothing here settles
 * anything. A person decides every item where it lives; the captain may only suggest and start
 * a step that still passes through its own approval.
 */
type Text = readonly [zh: string, en: string]
export type Settle = { readonly how: Text; readonly captain?: readonly string[] }

const resupply: Text = ['「数据」页该部门一行里的「补传单个部门」', 'Replace one department’s file, on that department’s row of the Data page']

export const settlePlaybook: Record<string, Settle> = {
  master_disagreement: {
    how: [`各部门对同一字段写法不同。由负责人确认哪个是对的；错在某个部门时，用${resupply[0]}上传改好的文件（生成新批次，旧批次不变）。`,
      `Departments wrote the same field differently. The owner confirms which is right; if one department is wrong, upload its corrected file with ${resupply[1]} (a new batch; this one stays as it is).`],
  },
  master_derived_mismatch: {
    how: [`部门填的值和字典公式算出的不一致。核对原表里的输入或口径，改好后用${resupply[0]}重新提交。`,
      `A department’s value disagrees with the dictionary formula. Check the inputs or convention in the original file, then resubmit it with ${resupply[1]}.`],
    captain: ['convention_list'],
  },
  master_missing_column: {
    how: ['模板缺一个必需列。若只是列名改了，按列匹配处理；否则请该部门按模板补上这一列后重新提交。',
      'The template lacks a required column. If it was only renamed, match it; otherwise the department adds the column from the template and resubmits.'],
    captain: ['column_candidates', 'confirm_column_match'],
  },
  master_missing_key: {
    how: [`这一行缺字典声明的主键，放不进总表。请该部门补全后用${resupply[0]}重新提交。`,
      `This row lacks a key the dictionary declares, so it cannot be placed. The department completes it and resubmits with ${resupply[1]}.`],
  },
  master_needs_rollup: {
    how: ['同一键有多行，字典没写汇总方式。请字典负责人声明汇总规则（求和、平均或取期末），之后重新导入。',
      'Several rows share a key and the dictionary names no roll-up. The dictionary owner declares one (sum, average or period end), then the files are imported again.'],
  },
  master_undeclared_constant: {
    how: ['公式需要的常数没有声明。请字典负责人补上；可以先预览另一个取值会改动多少单元格。',
      'A formula needs a constant nobody declared. The dictionary owner adds it; a preview first shows how many cells another value would change.'],
    captain: ['convention_list', 'convention_preview'],
  },
  master_check_failed: {
    how: [`跨部门核对没有通过。找出哪一边错了，用${resupply[0]}更正那个部门的文件。`,
      `A cross-department check failed. Find which side is wrong and correct that department’s file with ${resupply[1]}.`],
  },
  master_invalid_number: {
    how: [`数值栏里是文字或读不出的数。请该部门改成数字后用${resupply[0]}重新提交。`,
      `A number field holds text or an unreadable figure. The department corrects it and resubmits with ${resupply[1]}.`],
  },
  master_invalid_period: {
    how: [`年、月凑不成一个期间。请该部门更正日期后用${resupply[0]}重新提交。`,
      `The year and month do not form a period. The department corrects the date and resubmits with ${resupply[1]}.`],
  },
  master_cannot_compute: {
    how: [`缺少计算需要的输入。补齐所缺的列或值后用${resupply[0]}重新提交。`,
      `An input the calculation needs is missing. Supply it and resubmit with ${resupply[1]}.`],
  },
  master_missing_department: {
    how: ['这个部门还没交本月的文件。请它从左侧「添加来源」上传。',
      'This department has not submitted this month’s file. It uploads it with Add sources on the left.'],
  },
  quarantined_row: {
    how: ['这一行被隔离了（例如负数或混入了别的月份）。逐行决定：给出改正后的值放行，或丢弃；处理完生成新批次。',
      'This row was quarantined (a negative figure, a row from another month…). Decide row by row: release it with corrected values, or discard it; applying creates a new batch.'],
    captain: ['quarantine_list', 'quarantine_decide', 'quarantine_apply'],
  },
  column_question: {
    how: ['上传的列名和字典对不上。从已声明的候选里选一个匹配并审批，批准后重新导入才生效。',
      'An uploaded column matches nothing the dictionary declares. Pick a match from the declared candidates and approve it; it applies when the files are imported again.'],
    captain: ['column_candidates', 'confirm_column_match'],
  },
  stale_report: {
    how: ['本月的研判做在更正前的数据上。在当前批次上重新研判。',
      'This month’s review was made on data that has since been corrected. Run the review again on the current batch.'],
    captain: ['review_context'],
  },
  missing_provenance: {
    how: ['这些单元格追不到来源。看是缺了来源列，还是依赖业务方未确认的口径；口径确认后在「口径」里记录。',
      'These cells cannot be traced to a source. See whether a source column is missing or they rest on an unconfirmed convention; record the business’s decision on it.'],
    captain: ['convention_list', 'convention_decide'],
  },
}
