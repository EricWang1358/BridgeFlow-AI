import { useSyncExternalStore } from 'react'
import type { SubagentListEntry } from '@deepseek-ai/dsh-subagent/client'
import type { SessionId } from '@deepseek-ai/dsh-session/types'
import type { ISessions } from '@deepseek-ai/dsh-api-session-controller/client'
import type { Context } from '@deepseek-ai/cordis'
import type {} from '@deepseek-ai/dsh-client-locale/client'

let locale: Context['locale']
export function configureLocale(value: Context['locale']) { locale = value }
const subscribe = (fn: () => void) => locale.subscribe(fn)
const current = () => locale.getSnapshot().active.startsWith('zh') ? 'zh' : 'en'
const labels = {
  sources: ['来源', 'Sources'], studio: ['结果与核对', 'Studio'], workArea: ['工作区', 'Workspace'],
  sourceHelp: ['依据与归属', 'Evidence and ownership'], studioHelp: ['状态、责任与下一步', 'Status, owners and next steps'],
  quotationWorkspace: ['报价工作区', 'Quotation workspace'], quotation: ['报价', 'Quotation'], quotationHelp: ['从客户需求与采购依据形成报价，与月度对账并列。', 'Build quotations from customer requirements and procurement evidence, alongside monthly review.'],
  quotationSourceHelp: ['所需依据由人工字典声明；原件先抽取为带出处的结构化事实。', 'Required evidence comes from the human dictionary. Originals must first become structured facts with citations.'],
  awaitingEvidence: ['待补充真实依据', 'Awaiting source evidence'], awaitingSamples: ['等待业务样板', 'Awaiting business samples'],
  quotationUnconfigured: ['尚未配置报价声明', 'No quotation declaration configured'],
  quotationConfigureHelp: ['请管理员在字段字典中配置报价契约；样板到达后再确认输入格式与抽取方式。', 'Ask the administrator to configure the quotation contract in the field dictionary. Input formats and extraction follow business samples.'],
  quotationStage: ['当前：声明与算术准备', 'Current stage: declaration and arithmetic'],
  quotationStageHelp: ['缺成本、产能或付款历史会明确拒绝。客户文件抽取与外发将在样板确认后接入。', 'Missing cost, capacity or payment history refuses a quote. Document extraction and sending follow sample confirmation.'],
  decisionOwners: ['决策负责人', 'Decision owners'], quotationChecks: ['出数前核对', 'Checks before pricing'],
  quotationApprovalHelp: ['报价草稿须经人工批准才可外发；此页不会发送报价。', 'A draft requires human approval before external use. This page does not send quotations.'],
  declaredTemplate: ['声明模板', 'Declared template'], declaredFormulas: ['查看声明公式', 'View declared formulas'], declarationSource: ['查看字典出处', 'View dictionary source'],
  quotationNoDraft: ['模板预览，尚未生成交易报价。', 'Template preview; no transaction quotation has been generated.'],
  sessionApprovals: ['下方审批属于当前会话，不代表所选批次的批准状态。', 'Approvals below belong to this session; they do not approve the selected batch.'],
  batchAudit: ['所选批次派活记录', 'Dispatches for selected batch'],
  followSession: ['跟随当前会话批次', 'Use current session batch'],
  waitingReview: ['本次研判尚未汇总；旧报告不会作为本次结果展示。', 'This review has not finalized. Earlier reports are not shown as its result.'],
  dispatchCount: ['工具派发尝试', 'Tool dispatch attempts'],
  captainFlow: ['队长派活 → 四部门研判 → 规则校验', 'Captain dispatch → departments → validation'], batchHint: ['选择上方入口查看批次数据；已校验报告不代表映射已获批准。', 'Open a source view above. A validated report does not imply approved mappings.'],
  files: ['部门文件', 'Department files'], submitted: ['意见已提交到队长会话', 'Note submitted to captain session'], audit: ['当前会话审计', 'Current session audit'], loadedWindow: ['仅统计已加载的会话事件，可加载更早记录。', 'Counts cover loaded events only; older events may be loaded.'], loadOlder: ['加载更早记录', 'Load older events'], stateHelp: ['图为静态规则；高亮与计数来自当前批次和原生会话记录。点击节点筛选，下方可打开原始视图。', 'The diagram shows fixed rules. Highlights and counts come from the selected batch and native session records. Select a node to filter, then open its source view.'],
  data: ['导入与数据', 'Import & data'], workspace: ['BridgeFlow 数据工作区', 'BridgeFlow data workspace'], close: ['关闭', 'Close'],
  title: ['批次数据与业务研判', 'Batch data & business review'], intro: ['把四部门数据放在一起', 'Bring four departments together'],
  newBatch: ['导入新批次', 'Import a new batch'], uploadHelp: ['CSV 或单工作表 XLSX；保留独立批次。', 'CSV or single-sheet XLSX; each import keeps an independent batch.'],
  month: ['业务月份', 'Business month'], production: ['生产', 'Production'], procurement: ['采购', 'Procurement'], finance: ['财务', 'Finance'], marketing: ['市场', 'Marketing'],
  import: ['导入并检查', 'Import & check'], busy: ['正在处理…', 'Processing…'], loading: ['正在加载…', 'Loading…'],
  saved: ['批次已保存。清洗和聚合由规则执行，未调用模型。', 'Batch saved. Rules cleaned and aggregated the data; no model call.'],
  existing: ['打开已有批次', 'Open an existing batch'], batchId: ['批次编号', 'Batch ID'], open: ['打开', 'Open'], copyId: ['复制批次编号', 'Copy batch ID'], copied: ['已复制', 'Copied'],
  startReview: ['发起研判', 'Start the review'],
  startReviewHint: ['直接把研判请求发到当前会话，不用复制粘贴。没有会话就新建一个。',
                    'Sends the review request straight into the current conversation. A session is created if none is open.'],
  copy: ['改一改再发（复制）', 'Copy instead'], copiedRequest: ['研判请求已复制，关闭此面板后粘贴到会话。', 'Request copied. Close this panel and paste it into the conversation.'],
  master: ['主表', 'Master table'], corrections: ['清洗记录', 'Corrections'], mappings: ['待确认映射', 'Pending mappings'], quarantine: ['隔离行', 'Quarantined rows'], review: ['四部门报告', 'Department report'], tabs: ['批次数据视图', 'Batch data views'],
  ready: ['可研判', 'Ready'], needs_configuration: ['需要配置字段字典', 'Configuration required'], needs_review: ['需要人工复核', 'Review required'], empty: ['没有可用数据', 'No usable data'],
  validated: ['已校验', 'Validated'], partial: ['研判未完成', 'Incomplete review'], attention: ['需要处理', 'Attention'], ok: ['正常范围', 'Within threshold'], unvalidated: ['未完成', 'Unvalidated'], running: ['处理中', 'Running'], dispatching: ['正在派活', 'Dispatching'],
  rows: ['行', 'rows'], total: ['共', 'Total'], previous: ['上一页', 'Previous'], next: ['下一页', 'Next'],
  noRows: ['此视图暂无记录。检查其他视图，或修正源文件后导入新批次。', 'No records here. Check another view or correct the source and import a new batch.'],
  noReport: ['此批次尚无研判报告。复制研判请求到会话，完成后刷新。', 'No report yet. Copy a review request into the conversation, then refresh.'], refresh: ['刷新', 'Refresh'],
  mappingHelp: ['通过 confirm_mapping 和原生审批确认关系；决定用于后续导入，旧批次不改。', 'Use confirm_mapping and native approval. Decisions apply to later imports; old batches remain unchanged.'],
  quarantineHelp: ['隔离行未进入计算。修正源表后重新导入，不自动放行。', 'Quarantined rows are excluded. Correct the source and import again; no automatic release.'],
  evidenceHint: ['引用 N 次不等于 N 个不同单元格；展示封顶不等于只算样本。', 'N references do not mean N distinct cells. Capped display does not mean sampled arithmetic.'],
  reportRegion: ['四部门研判报告', 'Four-department review report'], roleReview: ['研判', ' review'], responsibility: ['职责', 'Responsibility'], owner: ['决策负责人', 'Decision owner'],
  operations_director: ['运营负责人', 'Operations director'], procurement_manager: ['采购负责人', 'Procurement manager'], finance_controller: ['财务负责人', 'Finance controller'], sales_director: ['销售负责人', 'Sales director'],
  proposals: ['仅形成建议，未执行业务变更。模型解释须由业务负责人复核。', 'Proposals only; no business changes executed. Business owners must review model explanations.'],
  action: ['建议', 'Proposal'], formula: ['公式', 'Formula'], evidence: ['解释与原始来源', 'Explanation & original sources'], modelAdvice: ['模型解释（待复核）', 'Model explanation (needs review)'], threshold: ['关注阈值', 'Attention threshold'],
  refs: ['引用次数', 'Input references'], shown: ['展示来源', 'Sources shown'], sourceRow: ['原表行', 'Original row'], scope: ['研判范围', 'Review scope'], reportId: ['报告编号', 'Report ID'], parent: ['队长会话', 'Captain session'], child: ['部门会话', 'Department session'],
  partialHelp: ['缺失判断不能代签。可先提交人工复核意见，或修正输入后启动新批次。', 'Missing findings cannot be signed off. Submit a human review note, or correct inputs and start a new batch.'],
  humanNote: ['人工复核意见', 'Human review note'], sendNote: ['交给队长复核', 'Send to captain'], noteSent: ['复核话术已复制。粘贴到原生会话；不会自动重跑。', 'Review note copied. Paste into native chat; no automatic rerun.'],
  state: ['业务状态', 'Business state'], nativeDetails: ['原生工具详情', 'Native tool details'], unknown: ['尚无记录', 'No recorded state'], approval: ['映射审批', 'Mapping approval'],
  allowed_once: ['允许一次', 'Allow once'], rejected: ['已拒绝', 'Rejected'], cancelled: ['已取消/超时', 'Cancelled / timed out'], unavailable: ['审批不可用', 'Approval unavailable'],
  reason: ['拒绝理由', 'Rejection reason'], approvalTitle: ['确认跨部门映射', 'Confirm cross-department mapping'], allow: ['允许一次', 'Allow once'], reject: ['拒绝', 'Reject'],
  optionalReason: ['拒绝理由（可选，最多 240 字符）', 'Rejection reason (optional, up to 240 characters)'], noteHelp: ['批准才写映射；拒绝不写入，以后仍可能询问。', 'Only approval writes the mapping. Rejection writes nothing; later imports may ask again.'],
  noteFail: ['理由未保存，尚未提交决定。重试或清空理由后拒绝。', 'Reason was not saved; no decision submitted. Retry or clear it to reject.'], expired: ['审批已结束或备注通道不可用', 'Approval ended or notes unavailable'],
  timeout: ['审批期限', 'Approval deadline'], seconds: ['秒', 'seconds'], inspect: ['查看调用轨迹', 'Inspect native trace'], details: ['查看摘要', 'Show summary'], failed: ['失败 / 已拒绝', 'Failed / rejected'], completed: ['已完成', 'Completed'],
  limits: ['文件上限', 'File limit'], transport: ['请求上限', 'Request limit'], invalidUpload: ['请选择至少一个 CSV/XLSX，文件总大小不得超过上限。', 'Select at least one CSV/XLSX; total size must fit the limit.'],
  // --- orientation on a blank session ---------------------------------------
  // A judge or an operator opening this sees the host's own "explore the unknown"
  // hero, which says nothing about what this product does or what to do first.
  heroTitle: ['四个部门的月度数据，对到一张表上', 'Four departments, one reconciled table'],
  heroLead: ['先导入本月四份表，规则会先跑一遍；模型只解释算出来的数，不替你算。',
             'Import this month\'s four sheets first. Rules run before any model call; the model explains the figures, it does not compute them.'],
  heroStep1: ['导入四部门文件', 'Import the four sheets'],
  heroStep1Hint: ['CSV 或单工作表 XLSX，不调用模型', 'CSV or single-sheet XLSX. No model call.'],
  heroStep2: ['检查清洗与隔离', 'Check corrections and quarantine'],
  heroStep2Hint: ['看规则改了什么、扣下了什么', 'See what the rules changed and what they held back'],
  heroStep3: ['在会话里发起研判', 'Ask for a review in the conversation'],
  heroStep3Hint: ['队长派活给四个部门，逐条带证据', 'The captain dispatches four departments; every finding cites its rows'],
  heroStep4: ['审批要写入的决定', 'Approve anything that writes'],
  heroStep4Hint: ['没人点，就不写', 'Nothing is written unless a person clicks'],
  heroOpen: ['开始导入', 'Start an import'],

  // --- a state is only useful next to the action it implies -------------------
  nextTitle: ['下一步', 'Next step'],
  next_needs_configuration: ['字段字典没有声明可用于连接的列，所以主表没有建，研判也起不来。核对下面这份字典是不是你以为的那份，补齐后重新导入一次——旧批次不会被改。',
                             'The dictionary declares no joinable column, so no Master Table was built and the review cannot start. Check the dictionary below is the one you think it is, complete it, and import again — the old batch is left alone.'],
  askCaptain: ['让 captain 看这批数据', 'Ask the captain to look'],
  askCaptainHint: ['它会读各列的形状与跨部门重合度（不读数据行），然后给出字段字典候选和理由。你仍然是决定的人。',
                   'It reads column shapes and cross-department overlap — never the rows — then proposes dictionary candidates with its reasoning. You still decide.'],
  dictionaryInForce: ['本批次冻结的字典', 'Dictionary frozen into this batch'],
  declaresEntities: ['它为各部门声明的可连接列', 'Joinable columns it declares'],
  declaresNothing: ['未声明任何可连接列', 'declares none'],
  next_needs_review: ['有行被扣下或有映射待确认。先看隔离行和待确认映射两个页签，再发起研判。',
                      'Rows were held back or mappings are unconfirmed. Check the quarantine and pending-mapping tabs before asking for a review.'],
  next_ready: ['数据可用了。复制研判请求，粘贴到会话里发起四部门研判。',
               'The data is usable. Copy the review request and paste it into the conversation.'],
  next_empty: ['这一批没有可用数据。修正源文件后重新导入。', 'This batch has no usable data. Correct the source files and import again.'],
  whyEmpty: ['为什么主表是空的', 'Why the Master Table is empty'],
  whyRefused: ['规则拒绝出数的原因', 'Why the rules refused to produce a figure'],

  // --- import form ------------------------------------------------------------
  stepMonth: ['选择业务月份', 'Choose the business month'],
  stepFiles: ['放入部门文件', 'Add the department sheets'],
  stepGo: ['导入并让规则检查', 'Import and let the rules check'],
  stepFilesHint: ['至少一个；四个都放才能对齐跨部门关系。', 'At least one. All four are needed to align cross-department relations.'],
  stepGoHint: ['导入不调用模型，也不覆盖已有批次。', 'Import makes no model call and never overwrites an existing batch.'],
  chooseFile: ['选择文件', 'Choose a file'],
  noFile: ['尚未选择', 'None selected'],
  batchIdShort: ['批次', 'Batch'],
  columnsFrom: ['来自', 'from'],
  moreValues: ['项', 'values'],

  aggregate_metric: ['可追溯指标', 'Traceable metric'], confirm_mapping: ['映射决定', 'Mapping decision'], batch_summary: ['批次检查', 'Batch summary'], list_metrics: ['可用指标', 'Metric catalogue'], lookup_field_dictionary: ['字段口径', 'Field dictionary'], review_context: ['队长派活准备', 'Captain dispatch preparation'], review_finalize: ['队长汇总', 'Captain finalization'],
} as const
export function useUI() {
  const language = useSyncExternalStore(subscribe, current)
  const t = (key: string): string => labels[key as keyof typeof labels]?.[language === 'zh' ? 0 : 1] ?? key
  return { t, language }
}
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/bridgeflow${path}`, { ...init, credentials: 'same-origin' })
  if (!response.ok) {
    const text = await response.text()
    let detail = text
    try { detail = JSON.parse(text).detail ?? text } catch { /* Plain transport error. */ }
    throw new Error(String(detail))
  }
  return response.json() as Promise<T>
}
export type Route = { batch?: string; view?: string; report?: string; parent?: string; child?: string }
export function route(): Route { return location.hash.startsWith('#bridgeflow?') ? Object.fromEntries(new URLSearchParams(location.hash.slice(12))) : {} }
export function navigate(value: Route) {
  const query = new URLSearchParams(Object.entries(value).filter((x): x is [string, string] => !!x[1]))
  const hash = `#bridgeflow?${query}`
  if (location.hash === hash) window.dispatchEvent(new HashChangeEvent('hashchange'))
  else location.hash = hash
}
/**
 * Ask the captain to diagnose a batch that cannot be joined.
 *
 * The counterpart to `reviewRequest`, for the state the review cannot start from.
 * It names the tool and what a proposal has to carry, because a diagnosis that
 * arrives without the column it applies to is another dead end wearing a longer
 * sentence.
 */
export function diagnoseRequest(batch: string, period = '') {
  return `批次 ${batch}（${period}）没有可连接的列，主表建不起来。请调用一次 profile_batch，` +
    `然后针对每个 undeclared 的部门提出一条字段字典候选：写明哪个部门的哪一列应当被声明为` +
    `哪种实体，并用 overlaps 里的重合比例作为理由。两个 string 列高度重合是同一实体的证据，` +
    `两个 number 列重合通常只是巧合。不要猜列名以外的东西，不要读取数据行，不要执行任何写入。`
}

export function reviewRequest(batch: string, period = '') {
  return `请研判 ${period} 批次 ${batch}：review_context → 同一响应四次官方 subagent（production/procurement/finance/marketing）→ review_finalize。缺口如实标 partial，不重试，不执行业务动作。`
}
export type Summary = { batch_id: string; period: string; status: string; master_rows: number; unresolved: number; refusal: string;
  departments: { department: string; rows: number; quarantined: number; corrections: number }[]
  /** The dictionary this batch was frozen against, and what it declares per department. */
  dictionary?: string
  declared_entities?: Record<string, string[]> }

let runtime: { sessions: ISessions; conversation: Context['conversation'] }
export function configureRuntime(ctx: Context) { runtime = ctx as unknown as typeof runtime; configureLocale(ctx.locale) }
export async function openSession(parent: string, child?: string) {
  await runtime.sessions.refresh()
  if (child) {
    await runtime.sessions.refreshSubagents(parent as SessionId)
    const entry = runtime.sessions.list.getSnapshot().subagentsByParent[parent as SessionId]?.entries.find((e: SubagentListEntry) => e.kind === 'child' && e.id === child)
    if (!entry || entry.kind !== 'child') throw new Error('Child is absent from the native parent catalogue')
    runtime.sessions.openSubagent({ parentSessionId: parent as SessionId, childSessionId: child as SessionId, mode: entry.mode })
  } else runtime.sessions.open(parent as SessionId)
}
/**
 * Start the review from the panel the batch is already open in.
 *
 * Copying a prompt, closing the panel and pasting it into the composer is three
 * steps of clerical work between "the data is ready" and "review it", and every one
 * of them can be got wrong — the request names a batch id, so a stale paste reviews
 * last month. The panel knows the batch; it should be able to ask.
 *
 * A session is created when none is open, because the first thing a person does
 * after their first import must not be a dead button.
 */
export async function startReview(batch: string, period: string): Promise<void> {
  return ask(reviewRequest(batch, period))
}

/** Send the captain a diagnosis request for a batch nothing can be built from. */
export async function startDiagnosis(batch: string, period: string): Promise<void> {
  return ask(diagnoseRequest(batch, period))
}

async function ask(text: string): Promise<void> {
  await runtime.sessions.refresh()
  const current = runtime.sessions.list.getSnapshot().current
  const target = current ?? (await runtime.sessions.create())
  const binding = runtime.sessions.binding(target)
  if (!binding) throw new Error('No session is available to work in')
  const result = await binding.session.prompt([{ type: 'text', text }], 'queue')
  if (!result.ok) throw new Error(result.error.message)
  runtime.sessions.open(target)
}

export async function sendHumanNote(parent: string, report: string, note: string) {
  await runtime.sessions.refresh()
  const binding = runtime.sessions.binding(parent as SessionId)
  if (!binding) throw new Error('Captain session unavailable')
  const result = await binding.session.prompt([{ type: 'text', text: `人工复核意见（报告 ${report}）：${note}。仅记录并说明尚缺哪些部门签核。禁止调用 review_context/subagent/review_finalize，禁止重跑或执行业务动作。` }], 'queue')
  if (!result.ok) throw new Error(result.error.message)
  runtime.sessions.open(parent as SessionId)
}

/** A column header a person can read, split into its department and its field.
 *
 * The view hands back machine paths — `finance.ar_days`, `production.output_qty`,
 * `period_from`. Rendered raw into a narrow column they wrapped one character per
 * line, which is not a styling problem: a header nobody can read makes the table
 * useless. Splitting the department off lets the field name keep the width.
 */
export function columnLabel(column: string, t: (key: string) => string): { group: string; label: string } {
  const dot = column.indexOf('.')
  const group = dot > 0 ? column.slice(0, dot) : ''
  const field = dot > 0 ? column.slice(dot + 1) : column
  return { group: group ? t(group) : '', label: field.replace(/_/g, ' ') }
}

/** How one cell reads, and whether it is a figure.
 *
 * Values arrive as they are stored: entity ids like `customer:acme-pte-ltd`, rollup
 * decisions as objects, multi-source accounts as arrays. Printing `JSON.stringify`
 * into a business table — which is what happened before — shows an operator a data
 * structure and asks them to sign off on it.
 *
 * Nothing is dropped: the machine form stays available as the cell's `note`, so the
 * readable form never becomes the only form.
 */
export function cellText(value: unknown): { text: string; note?: string; full?: string; numeric: boolean; empty: boolean } {
  if (value == null || value === '') return { text: '—', numeric: false, empty: true }
  if (typeof value === 'number') return { text: value.toLocaleString(undefined, { maximumFractionDigits: 4 }), numeric: true, empty: false }
  if (typeof value === 'boolean') return { text: String(value), numeric: false, empty: false }
  if (Array.isArray(value)) {
    const parts = value.map(item => cellText(item).text)
    return parts.length <= 3
      ? { text: parts.join('、'), numeric: false, empty: false }
      : { text: parts.slice(0, 3).join('、'), note: `+${parts.length - 3}`, numeric: false, empty: false }
  }
  if (typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>)
    const shown = entries.slice(0, 3).map(([key, item]) => `${key.replace(/^[a-z]+\./, '')} = ${cellText(item).text}`)
    return { text: shown.join('; '), ...(entries.length > 3 ? { note: `+${entries.length - 3}` } : {}), numeric: false, empty: false }
  }
  let text = String(value)
  // Explanatory prose belongs in a cell only in summary. `period_from` repeats the
  // same sentence on every row; at full length it becomes the widest column in the
  // table and buries the figures it was meant to qualify.
  if (text.length > 72) return { text: `${text.slice(0, 71)}…`, note: '', full: text, numeric: false, empty: false }
  // `kind:identifier` is how entities are stored. The identifier is the part a person
  // recognises; the kind is context, so it becomes the caption rather than the label.
  const entity = /^([a-z_]+):(.+)$/.exec(text)
  if (entity) return { text: entity[2]!, note: entity[1]!.replace(/_/g, ' '), numeric: false, empty: false }
  return { text, numeric: /^-?[\d,]+(\.\d+)?$/.test(text), empty: false }
}
