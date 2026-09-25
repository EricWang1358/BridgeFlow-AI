/**
 * The Chinese reading of sentences the backend writes in English (open items, issue messages,
 * checklist and journal reasons, cleaning notes, evidence gaps).
 *
 * The backend keeps one language on purpose: the model reads these same sentences. The Chinese
 * interface matches each known template and renders it in Chinese, keeping every name, value and
 * number exactly as written; a sentence no template matches is shown unchanged. Department ids
 * inside a sentence read as department names.
 */
const departments: Record<string, string> = { production: '生产部', procurement: '物资部', finance: '财务部', marketing: '市场部' }
const dept = (text: string) => text.replace(/\b(production|procurement|finance|marketing)\b/g, id => departments[id]!)
const rollups: Record<string, string> = { sum: '求和', average: '取平均', period_end: '取期末值', disagreed: '各行不一致', concat: '拼接', first: '取首行' }

type Rule = [RegExp, (...groups: string[]) => string]
const rules: Rule[] = [
  // Cross-department master (integration issues)
  [/^(.+) differs between departments \((.+)\); confirm which is right$/, (f, list) => `${f} 在各部门填写不一致（${dept(list!)}）；请确认哪个正确`],
  [/^(.+): department wrote (.+), the dictionary formula gives (.+)$/, (f, a, b) => `${f}：部门填写 ${a}，按字典公式应为 ${b}`],
  [/^(.+): department wrote (.+), the declared rule gives (.+)$/, (f, a, b) => `${f}：部门填写 ${a}，按声明的规则应为 ${b}`],
  [/^(.+) needs the undeclared constant 「(.+)」$/, (f, c) => `${f} 需要一个未声明的常数「${c}」`],
  [/^(.+) needs (.+)$/, (f, list) => `${f} 缺少计算所需的：${list}`],
  [/^(.+): (.+) row (\d+) is not a number$/, (f, file, row) => `${f}：${file} 第 ${row} 行不是数字`],
  [/^(.+) row (\d+): year and month do not form a period$/, (file, row) => `${file} 第 ${row} 行：年份和月份凑不成一个期间`],
  [/^(.+) row (\d+): a grain field is empty; the row cannot be placed$/, (file, row) => `${file} 第 ${row} 行：主键字段为空，这一行放不进总表`],
  [/^(.+) template lacks: (.+)$/, (label, list) => `${label}模板缺少：${list}`],
  [/^(.+) has (\d+) rows for this key and no roll-up rule is declared$/, (label, n) => `${label}在同一个键下有 ${n} 行，字典没有声明汇总方式`],
  [/^(.+) has (\d+) rows for this key that differ in (.+), which the roll-up does not sum, join or recompute$/, (label, n, list) => `${label}在同一个键下有 ${n} 行，在 ${list} 上不一致，汇总规则无法求和、拼接或重算`],
  [/^(.+): a row has no value; a partial sum is not a total$/, f => `${f}：有一行没有值，部分求和不能当合计`],
  // Evidence grades and the open items built on them
  [/^(\d+) cell\(s\): (.+)$/, (n, rest) => `${n} 个单元格：${translate(rest!)}`],
  [/^(.+): departments disagree or the formula contradicts the value$/, f => `${f}：各部门不一致，或公式与值矛盾`],
  [/^(.+): no provenance$/, f => `${f}：没有出处`],
  [/^(.+): provenance has no source or formula$/, f => `${f}：出处里既没有来源也没有公式`],
  [/^(.+): no cited cells$/, f => `${f}：没有引用任何单元格`],
  [/^(\d+) unrecognised uploaded column\(s\) could be it$/, n => `上传件里有 ${n} 个未识别的列可能是它`],
  [/^A review of this month was saved on a batch that has since been corrected$/, () => '本月的研判保存在一个后来被更正的批次上'],
  // Checklist and journal reasons
  [/^No department review has been saved for this batch$/, () => '这个批次还没有保存的四部门研判'],
  [/^No departments are declared for this step$/, () => '这一步没有声明任何部门'],
  [/^The brief is built from a saved review$/, () => '月度简报要在保存研判之后生成'],
  [/^The current period could not be compared$/, () => '当前期间无法对比'],
  [/^The saved review is partial; the brief will say which departments are missing$/, () => '保存的研判不完整，简报会写明缺了哪些部门'],
  [/^The two periods declare different fields; a change would compare different things$/, () => '两个期间声明的字段不同，对比会比较不同的东西'],
  [/^This batch predates the intake check chain$/, () => '这个批次早于导入检查流程'],
  [/^No batch has been imported for (.+)$/, p => `${p} 还没有导入任何批次`],
  [/^This batch has no saved review$/, () => '这个批次没有保存的研判'],
  [/^Complete the review before building the brief$/, () => '先完成研判，再生成简报'],
  [/^No acceptance report has been generated; run `(.+)`$/, cmd => `还没有生成验收报告；运行 \`${cmd}\``],
  // Cleaning notes (corrections)
  [/^header snake-cased for stable downstream keys$/, () => '表头统一成下划线小写，方便后续稳定引用'],
  [/^mixed date formats normalised to ISO$/, () => '混用的日期格式统一为 ISO（年-月-日）'],
  [/^stripped currency symbols and thousands separators$/, () => '去掉了货币符号和千分位分隔符'],
  [/^an exact repeat would double every total computed over it$/, () => '完全重复的一行会让所有合计翻倍'],
  [/^day-first and month-first both parse this; quarantined\. Declare the locale or supply an unambiguous ISO date$/, () => '按日在前和月在前都能读通，已隔离。请声明日期习惯，或改用不会混淆的 ISO 日期'],
  [/^read as (.+) per the dictionary's date_order$/, order => `按字典声明的日期顺序（${order}）读取`],
  [/^not a valid date when read (.+) as declared; quarantined rather than read the other way$/, order => `按声明的顺序（${order}）读不成有效日期，已隔离，不会换一种顺序去猜`],
  [/^(\d+) numeric column\(s\) hold text on this row, which is what a shifted header row looks like; quarantined rather than guessed at, because we cannot know which way it slid$/, n => `这一行有 ${n} 个数值列里是文字，像是表头错了一行；已隔离，不去猜它往哪边错`],
  // Where a correction came from, and how a master cell was rolled up
  [/^batch = (\w+); department = (\w+); period = (.+)$/, (b, d, p) => `批次 ${b}；${departments[d!] ?? d}；期间 ${p}`],
  [/^(.+ = (?:sum|average|period_end|disagreed|concat|first))(; .+ = (?:sum|average|period_end|disagreed|concat|first))*$/, () => ''],
]

export function translate(text: string): string {
  for (const [pattern, render] of rules) {
    const match = pattern.exec(text)
    if (!match) continue
    const out = render(...match.slice(1))
    if (out) return out
    // Roll-up summaries ("出厂量 = sum; 实际签收率 = disagreed"): translate each method in place.
    return text.replace(/ = (sum|average|period_end|disagreed|concat|first)\b/g, (_, m: string) => ` = ${rollups[m]}`)
  }
  return text
}
