import { tourLabels } from './tour/copy.ts'
import type { WorkspaceId } from '@deepseek-ai/dsh-workspace'
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
  guestBannerTitle: ['访客模式', 'Guest mode'],
  guestBannerData: ['只有示例数据，与正式环境隔离，每晚清空。', 'Sample data only, separate from the real service, cleared every night.'],
  guestBannerFeishu: ['飞书登录、导入与上传在访客模式下不可用。', 'Feishu sign-in, import and upload are not available in guest mode.'],
  guestBannerLlmOff: ['AI 对话已关闭：工作室里的页面都能用，队长不会调用模型。', 'AI chat is off: every Studio page works, but the captain does not call a model.'],
  guestBannerLlmOn: ['AI 对话已开启，由运营方承担费用，请勿输入真实数据。', 'AI chat is on at the operator\u2019s cost; please do not enter real data.'],
  guestUnavailable: ['访客模式下不可用', 'not available in guest mode'],
  sampleHistory: ['载入前两个月的示例', 'Load the two earlier sample months'],
  sampleHistoryHelp: ['趋势至少要两个月。示例只有 2024-07，可以补上同一家供应商的 5 月和 6 月（没有埋错）。', 'A trend needs at least two months. The sample has only 2024-07; add the same supplier\u2019s May and June (nothing planted).'],
  ovNoRuns: ['今天还没有代理运行。在对话里让队长做一件事，这里会出现它用了多少 token。', 'No agent runs yet today. Ask the captain for something in the chat and its token use shows up here.'],
  overview: ['总览', 'Overview'],
  overviewIntro: ['这个月各处的进展一页看完。点任何一块，去负责它的页面处理。', 'Where the month stands across every page. Open any block to act on it where it lives.'],
  overviewHow: ['总览只读取各页面自己用的数据接口，不做任何决定或审批，所以它和各页面不会对不上。读不到的来源会直接说读不到，而不是显示 0。红色只用来表示「超时」或「被拒绝」，旁边总有符号和文字。', 'The overview reads the same endpoints each page reads and never decides or approves anything, so it cannot disagree with those pages. A source it cannot read says so instead of showing zero. Red only means overdue or refused, and always comes with a mark and a word.'],
  ovShowTables: ['以表格显示数字', 'Show numbers as tables'],
  ovHideTables: ['隐藏表格', 'Hide tables'],
  ovNoBatch: ['先在左侧打开一个批次，月结进度、待办和指标趋势才会出现；下面是不依赖批次的部分。', 'Open a batch on the left to see close progress, open items and metric trends. Below are the parts that do not depend on a batch.'],
  ovUnreadable: ['读不到：', 'Could not read:'],
  ovNothing: ['暂时没有。', 'Nothing yet.'],
  ovClose: ['月结进度', 'Close progress'],
  ovReady: ['可以月结', 'Ready to close'],
  ovNotReady: ['还不能月结', 'Not ready to close'],
  ovOpenItems: ['待处理事项', 'Open items'],
  ovOpenItemsNote: ['等人处理的事项', 'waiting on someone'],
  ovWorkflow: ['流转中的记录', 'Records in flight'],
  ovNoneOverdue: ['没有超时', 'none overdue'],
  ovRuns: ['最近的代理运行', 'Recent agent runs'],
  ovRefused: ['次拒绝', 'refused'],
  ovNoRefusals: ['没有拒绝', 'no refusals'],
  ovTrends: ['关键指标', 'Key metrics'],
  ovMetric: ['指标', 'Metric'],
  ovByDepartment: ['各部门待处理事项', 'Open items by department'],
  ovDepartment: ['部门', 'Department'],
  ovStages: ['流程各环节', 'Workflow stages'],
  ovStage: ['环节', 'Stage'],
  ovRecords: ['记录数', 'Records'],
  ovOverdue: ['超时', 'Overdue'],
  ovRunTokens: ['每次运行的 token', 'Tokens per run'],
  ovSteps: ['步', 'steps'],
  ovStarted: ['开始时间', 'Started'],
  linkAccepted: ['填报流程已按这个决策运行。', 'The filling workflow runs under this decision.'],
  linkOutdated: ['填报流程接收的是这个决策的旧版本，需要重新接收。', 'The filling workflow accepted an earlier version of this decision and needs to accept this one.'],
  linkWaiting: ['批准后还要在填报流程里接收，范围才生效。', 'After approval, the filling workflow still has to accept it before the scope applies.'],
  openHandoff: ['去填报与流转', 'Open Filling & handoff'],
  scopeTitle: ['流程范围', 'Workflow scope'],
  scopeCurrent: ['按已批准的立项决策运行', 'Running under an approved MVP decision'],
  scopeDecision: ['立项决策', 'MVP decision'],
  scopeAcceptedBy: ['接收人', 'accepted by'],
  scopeExclusions: ['不在范围内', 'Out of scope'],
  scopeStale: ['立项决策已变更', 'The MVP decision has changed'],
  scopeStaleHelp: ['流程依据的决策已被修订或撤回，新记录会被拒绝，直到接收当前的决策。', 'The decision this workflow runs under was revised or withdrawn. New records are refused until the current decision is accepted.'],
  scopeWaiting: ['有一条已批准的立项决策等待接收', 'An approved MVP decision is waiting to be accepted'],
  scopeNone: ['还没有关联立项决策', 'Not linked to an MVP decision yet'],
  scopeNoneHelp: ['在立项页批准一个决策后，可以把它接收为流程范围。也可以先载入示例项目，看一条从材料到批准的完整链路。', 'Once an MVP decision is approved on the Discovery page, it can be accepted as the scope of this workflow. Or load the sample project to see a full chain from material to approval.'],
  loadDiscoverySample: ['载入立项示例项目', 'Load the sample discovery project'],
  askAcceptScope: ['请队长接收这个范围', 'Ask the captain to accept this scope'],
  requestAcceptScope: ['请用 workflow_scope 读取项目 {project} 的决策 {decision}，列出批准范围和排除项，然后用 workflow_accept_scope（decision_seq={seq}）接收。审批卡就是我的确认。', 'Read decision {decision} of project {project} with workflow_scope, list its scope and exclusions, then accept it with workflow_accept_scope (decision_seq={seq}). The approval card is my confirmation.'],
  timeline: ['时间线', 'Timeline'],
  timelineBy: ['由', 'by'],
  event_material_received: ['收到填报', 'Submission received'],
  event_answer_provided: ['补充了回答', 'Answer added'],
  event_reviewed: ['审核批准', 'Reviewed and approved'],
  event_submission_started: ['开始提交', 'Submitting'],
  event_submission_succeeded: ['已入库', 'Recorded'],
  event_submission_failed: ['提交失败', 'Submission failed'],
  event_handoff_opened: ['已交接给下游', 'Handed over'],
  event_handoff_started: ['下游开始处理', 'Work started'],
  event_handoff_completed: ['下游已完成', 'Completed'],
  event_handoff_returned: ['退回上游', 'Returned upstream'],
  event_revision_acknowledged: ['已确认上游修订', 'Revision acknowledged'],
  event_upstream_revised: ['上游已修订', 'Upstream revised'],
  dueIn: ['{h} 小时内到期', 'due in {h} h'],
  overdueBy: ['已超时 {h} 小时', 'overdue by {h} h'],
  flowOverdue: ['{n} 条超时', '{n} overdue'],
  approval_workflow_accept_scope: ['接收立项范围', 'Accept MVP scope'], approvalTitle_workflow_accept_scope: ['把这条已批准的立项决策作为流程范围', 'Run the workflow under this approved MVP decision'],
  workflow_scope: ['流程范围', 'Workflow scope'], workflow_accept_scope: ['接收立项范围', 'Accept MVP scope'],
  draftUnavailable: ['读不到这份草稿；请在「填报与流转」页核对后再决定。', 'This draft could not be read; check it on the Filling & handoff page before deciding.'],
  runTokens: ['tokens（发起工具调用的模型步骤）', 'tokens (model steps that called tools)'],
  sampleCases: ['更多示例', 'More sample cases'],
  sampleCasesHelp: ['同一家虚构公司的 2024-07，分别展示不同的问题；有些状态不能放在同一个批次里。每个示例打开成一个新笔记本。', 'The same fictional company in 2024-07, each showing different problems, because some states cannot share one batch. Each opens in a new notebook.'],
  reviewBlockers: ['研判会被拒绝，原因：', 'The review would refuse this batch:'],
  next_blocked: ['请修正源表，再用「单部门补传」替换出错部门的文件，这会生成新批次。', 'Correct the source file, then replace that department\'s file; that creates a new batch.'],
  workflowFlow: ['填报与流转流程', 'Filling and handoff flow'],
  flowStage_input: ['补齐缺项', 'Fill in what is missing'], flowStage_review: ['待审核', 'Awaiting review'], flowStage_approved: ['已批准', 'Approved'],
  flowStage_recorded: ['已入库', 'Recorded'], flowStage_handed: ['已交接', 'Handed over'], flowStage_working: ['下游处理中', 'Being worked on'], flowStage_done: ['已完成', 'Done'],
  flowActorPerson: ['填报人', 'Submitter'], flowActorYou: ['你审批', 'You approve'], flowActorSystem: ['系统', 'System'], flowActorDownstream: ['下游部门', 'Next team'],
  workflowSample: ['载入示例工作流', 'Load the sample workflow'],
  workflowSampleHelp: ['放入两条虚构的生产记录：一条缺实际量，一条待审核。只做接收；审核、提交和交接仍要你在对话里批准。', 'Adds two fictional production records: one missing its actual quantity, one ready for review. It only receives them; reviewing, submitting and handing over still need your approval in chat.'],
  workflowNext: ['下一步', 'Next step'],
  askNeedsInput: ['请队长补问', 'Ask the captain to fill the gaps'], askReview: ['请队长送审', 'Ask the captain to submit for approval'],
  askStart: ['请队长开始处理', 'Ask the captain to start it'], askComplete: ['请队长标记完成', 'Ask the captain to complete it'],
  requestNeedsInput: ['请用 workflow_draft 读取草稿 {id}，告诉我还缺哪些项；我回答后，用 workflow_record（artifact_id={id}）记录我的原话。我会在审批卡里确认。', 'Read draft {id} with workflow_draft and tell me what is still missing. When I answer, record my words with workflow_record (artifact_id={id}); I will confirm in the approval card.'],
  requestReview: ['请用 workflow_draft 读取草稿 {id}，把全部值和检查结果列给我，然后直接用 workflow_approve_submit 提交。审批卡就是我的确认。', 'Read draft {id} with workflow_draft, list every value and check for me, then submit it with workflow_approve_submit. The approval card is my confirmation.'],
  requestStart: ['请在 workflow_board 上找到交接 {id}，列出它的输入，然后用 workflow_handoff 执行 start。审批卡就是我的确认。', 'Find handoff {id} on workflow_board, list its inputs, then run workflow_handoff with action start. The approval card is my confirmation.'],
  requestComplete: ['我确认：下游团队已完成交接 {id} 的工作。请在 workflow_board 上找到它，用 workflow_handoff 执行 complete，并把这句确认写进理由。审批卡就是我的确认。', 'I confirm the next team has finished the work on handoff {id}. Find it on workflow_board and run workflow_handoff with action complete, citing this confirmation as the reason. The approval card is my confirmation.'],
  heroActor1: ['规则', 'Rules'], heroActor2: ['你', 'You'], heroActor3: ['队长 + 四个部门代理', 'Captain + 4 agents'], heroActor4: ['你', 'You'],
  howItWorks: ['这是怎么运作的', 'How this works'],
  how_tasks: ['每一步的状态都取自办理它的那个页面，所以这里和那个页面永远一致。\n读不到状态的步骤显示「未知」，不算完成。\n结账由你决定：所有必需步骤完成时这里会提示，但系统从不替你标记「已结账」。', 'Each step\'s status comes from the page that handles it, so this list and that page always agree.\nIf a status cannot be read, the step shows Unknown and does not count as done.\nClosing the month is your call. BridgeFlow tells you when every required step is done but never marks the month closed.'],
  how_data: ['导入只运行固定规则，不调用 AI，也不会覆盖已有批次。\n修正某一个部门的文件会生成新批次，其他三个部门的文件原样沿用。\n旧批次和它们的报告永远不变，所以之前的结论始终可以追溯。', 'Importing runs fixed rules only. It never calls the AI and never overwrites an existing batch.\nFixing one department\'s file creates a new batch that reuses the other three departments\' files as they are.\nOld batches and their reports never change, so earlier conclusions stay traceable.'],
  how_records: ['每个决定都在持有证据和审批的那个页面里做出，这里只汇总。\n记录只追加、不覆盖，改决定会新增一条。', 'Every decision is made on the page that holds its evidence and approval; this page only collects them.\nRecords are only ever added. Changing a decision adds a new entry.'],
  how_runs: ['一次运行 = 向模型发出的一次请求，以及它引出的全部工具调用，包括四个部门代理。\n你浏览器自己的读取不算运行；这里只显示代理做了什么。', 'A run is one request to the model and every tool call it led to, including the four department agents.\nReads made by your own browser are not runs; this view shows only what the agents did.'],
  how_journal: ['所有接口都在同一处记日志，新功能不会漏记。\n条目里只有编号、计数和版本号，从不包含表格数据。\n按天保存，保留 14 天。', 'Every endpoint is logged in one place, so a new feature cannot skip it.\nEntries hold IDs, counts and versions only, never spreadsheet data.\nOne file per day, kept for 14 days.'],
  how_eval: ['报告由 python -m bridgeflow.eval --json 生成，本页只负责展示。\n红色行会写明跟踪它的 issue。', 'The report is generated by python -m bridgeflow.eval --json; this page only displays it.\nA red row names the issue that tracks it.'],
  how_brief: ['数字由规则按字典公式算出，AI 只写解释，不参与计算。\n每个数字都能追到原始单元格：展开「出处」即可看到文件、行号和列名。\n依据等级说明数字有多可靠：G1 直接来自单元格，G2 由公式算出，G3 用到了尚未确认的口径，G4 是模型建议。', 'Figures are computed by rules using the dictionary formulas. The AI writes the explanations; it never does the arithmetic.\nEvery figure traces back to source cells. Open Sources to see the file, row and column.\nThe evidence grade says how firm a figure is: G1 is read straight from a cell, G2 is computed by a formula, G3 depends on a convention nobody has confirmed yet, and G4 is model advice.'],
  gradeName_G1: ['原始', 'source'],
  gradeName_G2: ['公式', 'formula'],
  gradeName_G3: ['假设', 'assumed'],
  gradeName_G4: ['建议', 'advice'],
  briefWhy: ['{value}，{relation}关注阈值 {threshold}', '{value} is {relation} the {threshold} threshold'],
  relationAbove: ['高于', 'above'],
  relationBelow: ['低于', 'below'],
  briefDecides: ['由 {owner} 决定', '{owner} decides'],
  briefComputed: ['计算方式', 'Computed as'],
  briefCells: ['{count} 个出处单元格', '{count} source cells'],
  ...tourLabels,
  notebookKind: ['笔记本用途', 'Notebook purpose'], monthlyNotebook: ['月度对账', 'Monthly review'], quotationNotebook: ['报价', 'Quotation'], mixedNotebook: ['综合工作', 'Combined work'],
  monthlyProgress: ['月度对账进度', 'Monthly review progress'], quotationProgress: ['报价进度', 'Quotation progress'],
  notStarted: ['尚未开始', 'Not started'], quotationNext: ['查看声明与待补依据', 'View declaration and missing evidence'],
  notebookPurposeHelp: ['选择这个笔记本的用途，它决定你看到哪些步骤和提示。', 'Choose what this notebook is for. It decides which steps and guidance you see.'],
  untitledNotebook: ['未命名笔记本', 'Untitled notebook'], notebookName: ['笔记本名称', 'Notebook name'],
  notebooks: ['笔记本', 'Notebooks'], saveNotebook: ['保存笔记本', 'Save notebook'], exitNotebook: ['退出笔记本', 'Exit notebook'],
  leaveNotebook: ['离开前保存笔记本？', 'Save this notebook before leaving?'],
  noPendingApproval: ['当前没有待处理审批。需要您确认时，会在对话中提示。', 'No approval is pending. Chat will prompt you when a decision is needed.'],
  saveNotebookHelp: ['保存名称和来源选择，之后可从笔记本列表重新打开。不保存仅放弃本次名称和来源选择；已记录的对话、已上传文件和报告仍保留。', 'Save the name and sources so you can reopen this from Notebooks. Discarding only drops these edits; conversations, uploaded files and reports are kept.'],
  saveAndContinue: ['保存并继续', 'Save and continue'], discardAndContinue: ['不保存并继续', 'Discard and continue'], cancelLeave: ['取消，继续编辑', 'Cancel, keep editing'],
  notebookTitleRequired: ['请填写笔记本名称', 'Enter a notebook name'],
  notebookHistoryHelp: ['从 DSH 已保存的会话中打开笔记本；来源及产物按保存的批次恢复。未保存的空白笔记本不列入历史。', 'Reopen a saved notebook with its sources and results. Empty notebooks that were never saved are not listed.'],
  sampleNotebook: ['打开示例笔记本', 'Open sample notebook'], sampleNotebookTitle: ['业务演示 · 月度对账（模拟商砼公司 2024-07）', 'Business demo · monthly review (fictional concrete supplier, 2024-07)'],
  sampleNotebookHelp: ['虚构的混凝土供应商数据。可以浏览文件、主表和跨部门总表；发起研判会调用 AI 模型。', 'Fictional data from a concrete supplier. Browse the files, the master table and the combined table. Starting a review calls the AI model.'],
  draftNotebook: ['空白草稿', 'Empty draft'],
  unsavedNotebook: ['未保存', 'Unsaved'], savedNotebook: ['已保存', 'Saved'],
  resizeSources: ['调整来源栏宽度', 'Resize Sources'], resizeStudio: ['调整工作室宽度', 'Resize Studio'],
  newNotebook: ['新建笔记本', 'Create notebook'],
  previewUnavailable: ['无法加载此预览，请检查批次或重新选择来源。', 'This preview could not be loaded. Check the batch or select a source again.'],
  studioStateHelp: ['导入和报告状态属于所选批次，审批属于当前会话。详细过程在中间的轨迹里。', 'Import and report status belong to the selected batch; approvals belong to the current session. The trace in the middle has the details.'],
  welcomeTitle: ['从这里开始你的业务笔记本', 'Let’s start your business notebook'],
  welcomeHelp: ['把部门文件放到左侧，在这里与队长核对，在右侧查看产物与依据。', 'Add department files on the left, work with your captain here, and preview outputs and evidence on the right.'],
  monthlySteps: ['月度对账怎么开始', 'How to start a monthly review'],

  notebookTitle: ['业务笔记本', 'Business notebook'], sessionsSettings: ['会话与设置', 'Sessions & settings'],
  addSources: ['添加来源', 'Add sources'], sourceUploadHelp: ['上传的部门文件列在这里，点击即可预览。', 'Uploaded department files appear here. Click one to preview it.'],
  emptySources: ['保存的来源会显示在这里', 'Saved sources will appear here'], emptySourcesHelp: ['添加本月部门文件，开始核对与分析。', 'Add this month’s department files to start your review.'],
  originalUnavailable: ['旧批次未保留原件预览', 'Original preview unavailable for this older batch'],
  sourceDetails: ['文件来源信息', 'File provenance'], sourceFilename: ['上传文件', 'Uploaded file'], sourceSheet: ['工作表', 'Worksheet'],
  sourceFingerprint: ['文件指纹（SHA-256）', 'File fingerprint (SHA-256)'],
  sourceFingerprintHelp: ['上传文件的指纹，用来区分不同版本，不是业务结论。上面的表格是清洗前的原样；计算结果请看主表或研判报告。', 'A fingerprint of the uploaded file, used to tell versions apart; it is not a business finding. The table above shows the file as uploaded, before cleaning. See the master table or the review for results.'],
  allRowsShown: ['已显示全部数据，无需翻页', 'All rows are shown; no additional pages'], sourcePagination: ['来源分页', 'Source pagination'], pageLabel: ['页', 'Page'], retry: ['重试', 'Retry'],
  sourcePreview: ['来源预览', 'Source preview'], parsedOriginal: ['原始表格的解析视图，未经清洗；数据仅供浏览器分页预览。', 'Parsed original table before cleaning; paginated browser preview only.'],
  tools: ['工具', 'Tools'], artifacts: ['产物', 'Artifacts'], refreshArtifacts: ['刷新产物', 'Refresh artifacts'],
  emptyArtifacts: ['完成研判后，报告会保存在这里。', 'Completed review reports will appear here.'],
  studioStartHelp: ['添加部门文件后即可开始月度研判。报价工作区现在就能用。', 'Add department files to start a monthly review. The quotation workspace works without them.'],
  preview: ['预览', 'Preview'], expandPreview: ['展开预览', 'Expand preview'],

  sources: ['来源', 'Sources'], studio: ['工作室', 'Studio'], workArea: ['工作区', 'Workspace'],
  sourceHelp: ['依据与归属', 'Evidence and ownership'], studioHelp: ['状态、责任与下一步', 'Status, owners and next steps'],
  handoffWorkspace: ['填报与流转', 'Filling & handoff'],
  approval_confirm_column_match: ['列匹配审批', 'Column match approval'], approvalTitle_confirm_column_match: ['确认上传列对应的已声明字段', 'Confirm which declared column this upload column is'],
  approval_discovery_propose: ['候选提案确认', 'Confirm opportunity proposal'], approvalTitle_discovery_propose: ['保存提案，不代表批准立项', 'Save proposal, not project approval'],
  approval_discovery_register: ['材料登记确认', 'Confirm material registration'], approvalTitle_discovery_register: ['确认文件及来源声明', 'Confirm file and provenance'],
  discovery_register: ['登记材料', 'Register material'],
  discoveryWorkspace: ['立项材料与候选', 'Discovery materials and opportunities'],
  discovery_graph_save: ['保存流程草图', 'Save flow draft'],
  approval_discovery_graph_save: ['流程草图确认', 'Confirm flow draft'], approvalTitle_discovery_graph_save: ['核对节点、关系与依据', 'Review nodes, edges and evidence'],
  discovery_decision_propose: ['保存决策提案', 'Save decision proposal'],
  discovery_decision_vote: ['记录本人投票', 'Record own vote'],
  discovery_decision_resolve: ['确认决策条件', 'Confirm decision condition'],
  discovery_decision_finalize: ['记录立项决定', 'Record project decision'],
  approval_discovery_decision_propose: ['决策提案确认', 'Confirm decision proposal'], approvalTitle_discovery_decision_propose: ['修订会清空旧选票和条件确认', 'Revision clears votes and confirmations'],
  approval_discovery_decision_vote: ['本人投票确认', 'Confirm own vote'], approvalTitle_discovery_decision_vote: ['投票绑定当前验签员工', 'Vote uses the verified employee identity'],
  approval_discovery_decision_resolve: ['决策条件确认', 'Confirm decision condition'], approvalTitle_discovery_decision_resolve: ['核对条件与来源依据', 'Review condition and source evidence'],
  approval_discovery_decision_finalize: ['立项决定确认', 'Confirm project decision'], approvalTitle_discovery_decision_finalize: ['条件未满足不会交付批准范围', 'Unmet conditions withhold approved scope'],
  discovery_meeting_save: ['保存会议记录', 'Save meeting record'],
  approval_discovery_meeting_save: ['会议记录确认', 'Confirm meeting record'], approvalTitle_discovery_meeting_save: ['核对范围、假设、阶段与纪要', 'Review scope, assumptions, stages and minutes'],
  discovery_score_save: ['保存候选评分', 'Save opportunity ratings'],
  approval_discovery_score_save: ['候选评分确认', 'Confirm opportunity ratings'], approvalTitle_discovery_score_save: ['核对量表、分数与依据', 'Review policy, ratings and evidence'],
  discovery_materials: ['材料来源目录', 'Material source catalogue'],
  discovery_propose: ['保存候选提案', 'Save opportunity proposal'],
  approval_workflow_handoff: ['下游处理确认', 'Confirm downstream action'], approvalTitle_workflow_handoff: ['确认此版本的下游操作', 'Confirm action on this handoff version'],
  approval_workflow_record: ['填报内容确认', 'Confirm recorded answers'], approvalTitle_workflow_record: ['确认这些值就是你说的', 'Confirm these values are what you said'],
  approval_workflow_approve_submit: ['复核提交审批', 'Review and submit approval'], approvalTitle_workflow_approve_submit: ['批准这些值并提交到目标系统', 'Approve these values and submit them'],
  routeParentUnavailable: ['链接指向的队长会话不存在或已不可用，已停留在当前页面。', 'The linked captain session does not exist or is unavailable; you stayed on the current page.'],
  routeChildUnavailable: ['链接指向的部门子会话不存在或不属于该队长会话，已停留在当前页面。', 'The linked department session does not exist or does not belong to that captain session; you stayed on the current page.'],
  approval_quarantine_decide: ['隔离行处置审批', 'Quarantine decision approval'], approvalTitle_quarantine_decide: ['确认这一隔离行放行或丢弃', 'Confirm releasing or discarding this quarantined row'],
  approval_quarantine_apply: ['隔离处置应用审批', 'Apply quarantine decisions'], approvalTitle_quarantine_apply: ['按已记录的决定生成新批次（原批次不变）', 'Create a new batch from the recorded decisions (this batch stays unchanged)'],
  approval_convention_decide: ['口径决定审批', 'Convention decision approval'], approvalTitle_convention_decide: ['确认或替换一条字典未写明的口径', 'Confirm or replace a convention the dictionary does not state'],
  file: ['文件', 'File'],
  closeChecklist: ['本月对账进度', 'This month\u2019s close'],
  checklistHint: ['按顺序往下走，每一步都能直接跳到办理它的地方。', 'Work down the steps in order. Each one opens the place where it gets done.'],
  readyToClose: ['本月可结账', 'Ready to close'],
  readyToCloseHint: ['所有必需步骤都已完成，可以结账了。', 'Every required step is done. You can close the month.'],
  stepOwner: ['负责人', 'Owner'], stepOutstanding: ['还差', 'Outstanding'],
  stepState_done: ['已完成', 'Done'], stepState_open: ['未完成', 'Open'], stepState_blocked: ['受阻', 'Blocked'], stepState_unknown: ['状态未知', 'Unknown'],
  step_files_submitted: ['四部门文件已提交', 'Department files submitted'],
  step_intake_accepted: ['提交前自检通过', 'Intake checks accepted'],
  step_quarantine_cleared: ['隔离行已处置', 'Quarantined rows settled'],
  step_open_items_cleared: ['总表待确认事项清零', 'Master open items cleared'],
  step_review_validated: ['四部门研判完成', 'Department review complete'],
  step_brief_ready: ['本月结论已生成', 'Monthly brief ready'],
  stepGo_import: ['去导入', 'Import files'], stepGo_state: ['查看批次状态', 'Open batch state'],
  stepGo_quarantine: ['处理隔离行', 'Settle quarantined rows'], stepGo_integration: ['打开跨部门总表', 'Open the master table'],
  stepGo_artifact: ['查看研判报告', 'Open the review'], stepGo_brief: ['打开本月结论', 'Open the brief'],
  monthly_checklist: ['月度对账进度', 'Monthly close checklist'], monthly_inbox: ['待确认事项', 'Open items'],
  openItems: ['待确认事项', 'Open items'],
  metricCharts: ['指标图', 'Metric charts'],
  briefLayerOne: ['一眼看完', 'Read and leave'],
  briefLayerTwo: ['数字', 'The numbers'],
  briefLayerThree: ['展开核对', 'Expand to check'],
  monthlyTasks: ['本月任务', 'This month\u2019s tasks'],
  monthlyTasksHelp: ['左边是本月要走的步骤，右边是还在等人处理的事项。点一个步骤，右边只留它在等的那几条。', 'This month\'s steps are on the left and the items still waiting on someone are on the right. Pick a step to see only what it is waiting for.'],
  dataWorkspace: ['数据', 'Data'],
  dataHelp: ['每个部门一行：取模板、自检、导入，再处理被标出的问题。', 'One row per department: get the template, check the file, import it, then fix anything flagged.'],
  records: ['记录', 'Records'],
  batchTables: ['批次数据表', 'Batch tables'],
  wideReading: ['宽屏', 'Wide'],
  shownWide: ['本页正在全宽面板中显示。', 'This page is showing in the full-width panel.'],
  backToColumn: ['放回侧栏', 'Back to the column'],
  wideReadingHelp: ['总是以全宽方式打开页面，并记住这个选择。', 'Always open pages in the full-width view. Your choice is remembered.'],
  agentRuns: ['代理运行', 'Agent runs'],
  agentRunsHelp: ['每张图是队长的一次运行：每个代理一条泳道，每次工具调用一个标记。标记越宽越耗时，✕ 表示调用被拒绝。', 'Each chart is one run of the captain: one lane per agent, one mark per tool call. Wider marks took longer; ✕ marks a refused call.'],
  agentRunsEmpty: ['今天还没有代理运行。', 'No agent runs yet today.'],
  runSteps: ['步', 'steps'], runAgents: ['个代理', 'agents'], agentUnknown: ['未具名代理', 'unnamed agent'],
  decisionJournal: ['决策日志', 'Decision journal'],
  decisionJournalHelp: ['今天服务处理过的每个请求：做了什么决定、用了多久，被拒绝时写明原因。', 'Every request the service handled today: what it decided, how long it took, and the exact reason whenever it refused.'],
  journalDecisions: ['决策数', 'Decisions'], journalRefused: ['其中拒绝', 'Refused'],
  journalWrote: ['其中写入', 'Writes'], journalLatency: ['耗时 中位 / 最慢', 'Latency, median / slowest'],
  journalTopRefusals: ['今天拒绝了什么', 'What it refused today'],
  journalAll: ['全部', 'All'], journal_refused: ['拒绝', 'Refused'], journal_wrote: ['写入', 'Wrote'], journal_served: ['读取', 'Served'],
  journalThisBatch: ['只看本批次', 'This batch only'],
  journalEmpty: ['这个范围内还没有记录。', 'Nothing recorded in this scope yet.'],
  journalTrace: ['链路编号，与响应头 x-bridgeflow-trace 相同', 'Trace id, the same one the response header carries'],
  evalReport: ['验收评测', 'Acceptance report'],
  evalReportHelp: ['自动验收测试的结果：三个行业的正常用例，加上攻击与拒绝用例。', 'Results of the automated acceptance tests: normal cases from three industries, plus attack and refusal cases.'],
  evalTrack_golden: ['正常路径', 'Golden path'], evalTrack_adversarial: ['对抗与拒绝', 'Adversarial and refusals'],
  evalGenerated: ['生成于', 'Generated'], evalAllGreen: ['全部通过。红行会写明由哪个 issue 认领。', 'All green. A red row names the issue that owns it.'],
  recordsHelp: ['谁在什么时候做了什么决定。本页只读。', 'Who decided what, and when. This page is read-only.'],
  recordsLineage: ['批次版本链', 'Batch lineage'],
  recordsNoConventions: ['本批次的声明没有按通用做法补的口径。', 'This batch\u2019s declaration fills no gaps by convention.'],
  recordsNoReview: ['本批次还没有已保存的研判，因此没有处置记录。', 'No review is saved for this batch yet, so there are no dispositions.'],
  recordsReadOnly: ['要改某个决定，请回到做出它的地方：口径在主表里，关注项在本月结论里。', 'To change a decision, go back to where it was made: conventions in the master table, findings in the monthly brief.'],
  otherWorkspaces: ['其他工作区', 'Other workspaces'],
  batchFacts: ['当前批次的事实', 'About this batch'],
  batchFactsHint: ['所选批次的关键数字。要修改什么，请打开它所属的页面。', 'Key numbers for the selected batch. To change anything, open the page it belongs to.'],
  batchQuality: ['本批次的数据质量', 'Data quality in this batch'],
  batchQualityHint: ['点开一项去处理；处理完它会自动从这里消失。', 'Open an item to fix it. It drops off this list once it is resolved.'],
  stepTemplate: ['取模板', 'Take the template'], stepTemplateHint: ['本月批准的表格，已填入上月数字', 'This month\'s approved form, with last month\'s figures filled in'],
  stepSelfCheck: ['提交前自检', 'Self-check'], stepSelfCheckHint: ['按导入规则检查，但不保存', 'Runs the import checks without saving anything'],
  stepImport: ['导入成批次', 'Import'], stepImportHint: ['四个部门到齐后生成主表', 'The master table is built once all four are in'],
  stepFix: ['修问题', 'Fix what is open'], stepFixHint: ['被扣下的行、未匹配的列，或单个部门的文件', 'Held-back rows, unmatched columns, or one department\'s file'],
  departmentMissing: ['本月尚未提交', 'Not submitted this month'],
  fileSubmitted: ['已交', 'Submitted'], notSubmitted: ['未交', 'Not submitted'],
  upload: ['上传', 'Upload'],
  workflowProgress: ['工作流状态', 'Workflow state'],
  inboxFocused: ['只显示所选步骤在等的事项。', 'Showing only the items the focused step is waiting on.'],
  inboxClearFocus: ['显示全部', 'Show all'],
  stepShowItems: ['只看这几条', 'Show its items'],
  briefSources: ['这个数字的出处', 'Where this figure came from'],
  briefSourcesMore: ['共引用来源单元格', 'Source cells cited in total:'],
  exportReport: ['导出月度报告（Word）', 'Export the monthly report (Word)'],
  templateDownload: ['下载本月模板', 'Download this month\u2019s template'],
  templateDownloadHelp: ['下载本月模板。沿用上月的数字已预填，并标注「请核对」。', 'Download this month\'s template. Figures carried over from last month are pre-filled and marked for checking.'],
  templatePrefilled: ['已预填自', 'Prefilled from'],
  chart_sign_rate_trend: ['现场签收率趋势', 'Sign-off rate trend'],
  chart_net_margin_trend: ['项目净利率趋势', 'Net margin trend'],
  chart_output_variance: ['实际量变化分解', 'Output variance decomposition'],
  chart_project_output_bars: ['各项目实际量', 'Output by project'],
  chartThreshold: ['阈值', 'Threshold'], chartGap: ['无批次', 'no batch'],
  chartNeedsPeriods: ['至少需要两期数据才画趋势线', 'A trend needs at least two periods'],
  chartUnavailable: ['本图暂不可用', 'This chart is not available'],
  chartShowTable: ['看表格', 'Show the table'], chartHideTable: ['收起表格', 'Hide the table'],
  chartPoint: ['数据点', 'Point'], chartState: ['状态', 'State'],
  chartBreach: ['超出声明阈值', 'Past the declared threshold'], chartWithin: ['在阈值内', 'Within the threshold'],
  chartGapCell: ['该月无批次，不插值', 'No batch that month; not interpolated'], allDepartments: ['全部部门', 'All departments'],
  openItemsHint: ['本月还在等人处理的事项。点开一项，直接去处理它的地方。', 'Everything still waiting on someone this month. Open an item to go straight to where it is resolved.'],
  inboxEmpty: ['当前范围内没有待确认事项。', 'Nothing is waiting in this scope.'],
  inboxUnreadable: ['有一个来源读不到', 'One source could not be read'],
  openToSettle: ['打开处理', 'Open to settle'],
  item_master_disagreement: ['跨部门不一致', 'Departments disagree'],
  item_master_derived_mismatch: ['公式与填报不符', 'Formula and value disagree'],
  item_master_missing_column: ['模板缺列', 'Template lacks a column'],
  item_master_missing_key: ['行缺主键', 'Row cannot be placed'],
  item_master_needs_rollup: ['需要汇总口径', 'Needs a roll-up rule'],
  item_master_undeclared_constant: ['缺常数声明', 'Undeclared constant'],
  item_master_check_failed: ['跨部门核对未通过', 'Cross-department check failed'],
  item_master_invalid_number: ['数值不可用', 'Unusable number'],
  item_master_invalid_period: ['期间不可读', 'Unreadable period'],
  item_master_cannot_compute: ['无法计算', 'Cannot compute'],
  item_master_missing_department: ['部门未提交', 'Department has not submitted'],
  item_quarantined_row: ['隔离行待处置', 'Quarantined row'],
  item_column_question: ['上传列待匹配', 'Column to match'],
  item_stale_report: ['研判基于已更正的数据', 'Review rests on corrected data'],
  item_missing_provenance: ['出处缺失', 'Provenance missing'],
  risk_dispositions: ['预警处置', 'Risk dispositions'],
  resupply: ['补传单个部门', 'Replace one department\u2019s file'],
  resupplyHelp: ['只有一个部门的文件有错？只替换这一份。其他部门沿用已上传的文件，系统生成一个新批次，当前批次保持不变。', 'Only one department\'s file is wrong? Replace just that file. The other departments keep what they uploaded, you get a new batch, and this one stays as it is.'],
  resupplyDepartment: ['补传部门', 'Department'], resupplyReason: ['更正原因', 'Reason for the correction'],
  resupplyDone: ['已生成新批次', 'A new batch was derived'],
  resupplyDiff: ['与原批次相比', 'Compared with the original batch'],
  resupplyChangedCells: ['变化单元格', 'changed cells'], resupplyChangedFields: ['涉及字段', 'in fields'],
  resupplyRows: ['总表行数', 'master rows'], resupplyIssues: ['待确认事项变化', 'open items'],
  superseded: ['数据已更新，可重新研判', 'Data has been updated; run the review again'],
  supersededHint: ['本批次之后已有更正批次。本批次与它的报告不会改变，但要用最新数据下结论，请打开新批次重新研判。',
    'A corrected batch was derived from this one. This batch and its report do not change, but conclusions should be drawn on the newest batch.'],
  openNewest: ['打开最新批次', 'Open the newest batch'],
  convention_list: ['口径清单', 'Conventions'], convention_preview: ['口径影响试算', 'Convention impact preview'], convention_decide: ['口径决定', 'Convention decision'],
  quarantine_list: ['隔离行清单', 'Quarantined rows'], quarantine_decide: ['隔离行处置', 'Quarantine decision'], quarantine_apply: ['应用隔离处置', 'Apply quarantine decisions'],
  view_department: ['部门', 'Department'], view_column: ['上传列', 'Uploaded column'], view_original: ['原始表头', 'Header as written'], view_candidate: ['已声明候选列', 'Declared candidate'], view_role: ['声明角色', 'Declared role'], view_type_fits: ['类型相符', 'Type fits'], view_shared_values: ['值重合', 'Shared values'], view_decision: ['决定', 'Decision'], view_index: ['序号', 'Index'],
  columns: ['列匹配', 'Column matches'], columnsHelp: ['字典不认识的上传列，以及它们最可能对应的已定义列和依据。请队长提议匹配，你逐列审批；匹配从下一次导入起生效。原始数据可在来源预览里查看。', 'Uploaded columns the dictionary does not recognise, with the defined columns they most likely match and why. Ask the captain to propose matches and approve each one; they apply from the next import. The original data is in the source preview.'],
  requestFailed: ['操作未完成', 'Not completed'], networkFailed: ['连接不上服务，请检查服务是否在运行后重试。', 'Could not reach the service. Check that it is running, then retry.'],
  loginRequired: ['这份数据需要先登录。请通过飞书登录后再试。', 'This data needs a signed-in user. Log in with Feishu, then retry.'],
  loginWithFeishu: ['飞书登录', 'Log in with Feishu'],
  approval_feishu_import: ['飞书文件导入审批', 'Feishu import approval'], approvalTitle_feishu_import: ['从飞书下载这些文件并导入为新批次', 'Download these Feishu files into a new batch'],
  approval_feishu_upload_report: ['上传到飞书审批', 'Feishu upload approval'], approvalTitle_feishu_upload_report: ['把这份研判报告上传到飞书文件夹', 'Upload this review report to the Feishu folder'],
  feishu_import: ['从飞书导入', 'Import from Feishu'], feishu_upload_report: ['上传报告到飞书', 'Upload report to Feishu'],
  feishuPick: ['从飞书选择', 'Choose from Feishu'],
  feishuPickHelp: ['浏览你有权访问的飞书云文档，选中文件、在线表格或多维表格并指定部门后导入；表格需再选工作表与表头行，多维表格需再选数据表。只能看到你自己有权限的内容。', 'Browse the Feishu files your own account can access; pick files, sheets or bitables, assign departments, then import. A sheet also needs its worksheet and header row; a bitable needs its data table. You only see what your own account may access.'],
  feishuRoot: ['我的空间', 'My space'], feishuEmpty: ['这个文件夹是空的', 'This folder is empty'], feishuMore: ['加载更多', 'Load more'],
  feishuUpOne: ['返回上级', 'Up one level'],
  feishuChosen: ['已选择的来源', 'Chosen sources'], feishuChosenHelp: ['取消某个来源后再浏览或重新选择；至少保留一个才能导入。', 'Remove any source and keep browsing; at least one is needed to import.'],
  feishuCancelPick: ['取消这个来源', 'Remove this source'],
  feishuUnsupported: ['此类型暂不支持导入', 'This type cannot be imported yet'], feishuAssign: ['部门', 'Department'],
  feishuImportGo: ['导入选中文件', 'Import selected files'], feishuPickFolder: ['选择当前文件夹', 'Choose this folder'],
  feishuUpload: ['上传报告到飞书', 'Upload report to Feishu'], feishuUploadHere: ['上传到当前文件夹', 'Upload to this folder'],
  feishuUploaded: ['已上传到飞书', 'Uploaded to Feishu'], feishuNoReport: ['先完成一次研判，才能把报告传回飞书。', 'Finish a review before sending a report back to Feishu.'],
  feishuTarget: ['目标', 'Target'], feishuWiki: ['知识库', 'Wiki'],
  feishuWikiHelp: ['浏览你有权访问的知识库（个人文档库与团队知识库）。选中文件、在线表格或多维表格节点并指定部门后导入；表格需再选工作表与表头行，多维表格需再选数据表。', 'Browse the wiki spaces your own account can access (personal library and team spaces); pick file, sheet or bitable nodes, assign departments, then import. A sheet also needs its worksheet and header row; a bitable needs its data table.'],
  feishuTablePick: ['数据表', 'Data table'],
  feishuSpaces: ['选择知识库', 'Choose a wiki space'], feishuSpacesEmpty: ['没有可见的知识库', 'No wiki spaces visible'],
  feishuUploadFileWiki: ['上传本地文件到知识库', 'Upload a local file to wiki'], feishuPickFile: ['选择文件', 'Choose file'],
  feishuWikiUploaded: ['已上传到知识库', 'Uploaded to wiki'], feishuUploadWikiHere: ['上传到当前位置', 'Upload here'],
  integrationMaster: ['跨部门总表', 'Cross-department master'], downloadMaster: ['下载总表 xlsx', 'Download master xlsx'],
  integrationAssumptions: ['字典没写明、暂按惯例处理的口径（业务方确认后可替换）', 'Conventions assumed where the dictionary is silent (replaceable once the business confirms)'],
  conventionState_unconfirmed: ['未确认', 'Unconfirmed'],
  conventionState_confirmed: ['业务方已确认', 'Confirmed by the business side'],
  conventionState_replacement_requested: ['业务方要求替换', 'Replacement requested'],
  conventionKind_constant: ['常数', 'constant'], conventionKind_derived: ['公式', 'formula'],
  conventionKind_classification: ['判定规则', 'rule table'], conventionKind_rollup: ['汇总口径', 'roll-up'],
  conventionKind_field: ['字段', 'field'],
  conventionAffects: ['影响字段', 'Affects'],
  conventionSource: ['依据', 'Source'],
  conventionDeclarationChange: ['需由字典维护人改声明', 'The dictionary owner must edit the declaration'],
  conventionHelp: ['要确认或替换某条口径，在对话里告诉队长并说明依据。确认后，用到它的数字从 G3 升为 G2；本批次不会重算。', 'To confirm or replace a convention, tell the captain in chat and name your source. Confirming upgrades the figures that use it from G3 to G2; this batch is not recalculated.'],
  integrationHelp: ['按字典把四个部门的模板合成一张表。悬停单元格可看出处；✓ 表示该值与字典公式核对一致。', 'The four department templates combined by the dictionary. Hover a cell to see where it came from; ✓ means it matches the dictionary formula.'],
  integrationNoRows: ['没有可对齐的行。请检查待确认项，通常是模板缺连接键列。', 'No rows could be placed. Check the open items; usually a template lacks a join key column.'],
  integrationRowState: ['行状态', 'Row'], integration_summary: ['跨部门总表摘要', 'Master table summary'],
  issue_missing_department: ['缺部门', 'Missing department'], issue_missing_column: ['模板缺列', 'Template lacks column'], issue_needs_rollup: ['需声明汇总规则', 'Roll-up rule needed'],
  issue_disagreement: ['部门间不一致', 'Departments disagree'], issue_invalid_number: ['不是数字', 'Not a number'], issue_invalid_period: ['期间无法识别', 'Unreadable period'],
  issue_undeclared_constant: ['字典未声明的常量', 'Undeclared constant'], issue_derived_mismatch: ['与字典公式不符', 'Contradicts dictionary formula'],
  issue_check_failed: ['跨部门核对未通过', 'Cross-department check failed'], issue_cannot_compute: ['无法计算', 'Cannot compute'], issue_missing_key: ['缺连接键', 'Missing join key'],
  approvalDetailFailed: ['决定摘要加载失败。下面是工具给出的原始说明；可以重试加载摘要后再决定。', 'The decision summary failed to load. The tool\'s raw reason is shown below; retry loading the summary before deciding.'],
  imageNoticeTitle: ['这里读不了图片里的数字', 'Numbers in images cannot be read here'],
  imageNotice: ['本部署的模型只读文字，且图片里的数字无法追溯到单元格。表格请通过「添加来源」导入；说明性文字可以直接粘贴。移除图片后即可发送。', 'This deployment\'s model reads text only, and numbers in an image cannot be traced to a cell. Import tables with Add sources; paste explanatory text directly. Remove the image to send.'],
  reviewEnded: ['本次研判未正常完成', 'This review did not complete'],
  openSource: ['打开这份来源的原件预览', 'Open this source preview'], reviewUsage: ['本次研判用量（按阶段）', 'Review usage by stage'], orchestration: ['队长编排', 'Captain orchestration'], steps: ['步', 'steps'],
  ended_deadline_exceeded: ['超过统一期限（派活、部门研判与汇总共用），已停止并保存为未完成。', 'The single deadline for dispatch, departments and finalization passed; the review was stopped and saved as incomplete.'],
  ended_captain_ended: ['队长回合在汇总前结束，已保存为未完成。', 'The captain turn ended before finalization; saved as incomplete.'],
  ended_captain_disposed: ['会话在汇总前关闭，已保存为未完成。', 'The session closed before finalization; saved as incomplete.'],
  ended_host_restarted: ['服务在汇总前重启，无法继续，已明确结束。请重新发起研判。', 'The host restarted before finalization and could not continue; start a new review.'],
  handoffHelp: ['来自已批准模板的标准记录，以及交给下一个团队的内容。每个阶段分开记录：已收到、已就绪、已通知、已完成。', 'Standard records from approved templates, and what was handed to the next team. Each stage is tracked on its own: received, ready, notified, done.'],
  handoffBoard: ['流转看板', 'Handoff board'], handoffEmpty: ['还没有填报记录。下面是一条记录会走的流程。', 'No records yet. Here is how a record will flow.'],
  handoffEmptyHelp: ['在对话里请队长按模板帮你填报：它会逐项补问，你在审批里确认每个值。', 'Ask the captain in chat to help fill a template: it asks for each missing item and you confirm every value in the approval.'],
  handoffWriteHelp: ['此页只读。记录与提交都在对话中经审批完成。', 'This page is read-only. Recording and submitting happen in chat, through approval.'],
  catalogueVersion: ['声明版本', 'Declaration version'], fieldLineage: ['字段血缘', 'Field lineage'], integrations: ['接入', 'Integrations'],
  optional: ['选填', 'optional'], adoptionSignals: ['落地信号', 'Adoption signals'], noAdoptionSignals: ['暂无需要关注的落地问题。', 'No adoption issues to review.'],
  decidedBy: ['由谁决定', 'Decided by'], viewDraft: ['查看草稿', 'View draft'], field: ['字段', 'Field'], value: ['值', 'Value'],
  asWritten: ['原始写法', 'As written'], pleaseProvide: ['请提供', 'Please provide '],
  invalid: ['格式不符', 'Invalid'], ambiguous: ['含义不明确', 'Ambiguous'], needs_evidence: ['缺少依据', 'Needs evidence'], unmapped: ['未声明写法', 'Undeclared label'], upstream_revised: ['上游已修订', 'Upstream revised'], provenance: ['出处', 'Source'], receipt: ['入库回执', 'Receipt'],
  needs_input: ['待补充', 'Needs input'], ready_for_review: ['待复核', 'Ready for review'], reviewed: ['已复核', 'Reviewed'],
  submitting: ['提交中', 'Submitting'], submit_failed: ['提交失败', 'Submit failed'], data_ready: ['数据已就绪', 'Data ready'],
  waiting: ['待下游处理', 'Awaiting downstream'], in_progress: ['下游处理中', 'In progress'], returned: ['已退回', 'Returned'],
  notice_pending: ['通知待发送', 'Notice pending'], notice_sent: ['通知已发送', 'Notice sent'], notice_failed: ['通知失败待重试', 'Notice failed'], notice_abandoned: ['通知失败需跟进', 'Notice abandoned'],
  approved: ['已批准', 'Approved'], draft: ['草案', 'Draft'], proposed: ['待确认', 'Proposed'],
  confirmed: ['已确认', 'Confirmed'], inferred: ['推断待确认', 'Inferred'], missing: ['缺失', 'Missing'], conflict: ['冲突', 'Conflict'],
  technical: ['技术', 'Technical'], template: ['模板', 'Template'], flow: ['流程', 'Flow'], resource: ['资源', 'Resource'],
  quotationWorkspace: ['报价工作区', 'Quotation workspace'], quotation: ['报价', 'Quotation'], quotationHelp: ['从客户需求与采购依据形成报价，与月度对账并列。', 'Build quotations from customer requirements and procurement evidence, alongside monthly review.'],
  quotationSourceHelp: ['所需依据由人工字典声明；原件先抽取为带出处的结构化事实。', 'The evidence a quote needs is defined in the dictionary. Original documents are first turned into facts with citations.'],
  awaitingEvidence: ['待补充真实依据', 'Awaiting source evidence'], awaitingSamples: ['等待业务样板', 'Awaiting business samples'],
  quotationUnconfigured: ['尚未配置报价声明', 'No quotation declaration configured'],
  quotationConfigureHelp: ['请管理员在字段字典中配置报价契约；样板到达后再确认输入格式与抽取方式。', 'Ask the administrator to configure the quotation contract in the field dictionary. Input formats and extraction follow business samples.'],
  quotationStage: ['当前：声明与算术准备', 'Current stage: declaration and arithmetic'],
  quotationStageHelp: ['缺成本、产能或付款历史会明确拒绝。客户文件抽取与外发将在样板确认后接入。', 'A quote is refused while cost, capacity or payment history is missing. Reading documents and sending quotes come after the business confirms its samples.'],
  decisionOwners: ['决策负责人', 'Decision owners'], quotationChecks: ['出数前核对', 'Checks before pricing'],
  quotationApprovalHelp: ['报价草稿须经人工批准才可外发；此页不会发送报价。', 'A draft requires human approval before external use. This page does not send quotations.'],
  declaredTemplate: ['声明模板', 'Declared template'], declaredFormulas: ['查看声明公式', 'View declared formulas'], declarationSource: ['查看字典出处', 'View dictionary source'],
  quotationNoDraft: ['模板预览，尚未生成交易报价。', 'Template preview; no transaction quotation has been generated.'],
  sessionApprovals: ['下方审批属于当前会话，不代表所选批次已获批准。', 'The approvals below belong to this session. They do not mean the selected batch is approved.'],
  batchAudit: ['所选批次派活记录', 'Dispatches for selected batch'],
  followSession: ['跟随当前会话批次', 'Use current session batch'],
  waitingReview: ['本次研判尚未汇总；旧报告不会作为本次结果展示。', 'This review has not finalized. Earlier reports are not shown as its result.'],
  dispatchCount: ['工具派发尝试', 'Tool dispatch attempts'],
  captainFlow: ['队长派活 → 四部门研判 → 规则校验', 'Captain dispatch → departments → validation'], batchHint: ['在上方打开一个来源视图。报告校验通过不代表映射已获批准。', 'Open a source view above. A validated report does not mean the mappings are approved.'],
  files: ['部门文件', 'Department files'], submitted: ['意见已提交到队长会话', 'Note submitted to captain session'], audit: ['当前会话审计', 'Current session audit'], loadedWindow: ['仅统计已加载的会话事件，可加载更早记录。', 'Counts cover loaded events only; older events may be loaded.'], loadOlder: ['加载更早记录', 'Load older events'], stateHelp: ['图上是固定的流程；高亮和计数来自所选批次。点一个节点即可筛选。', 'The diagram shows the fixed process; highlights and counts come from the selected batch. Click a step to filter.'],
  close: ['关闭', 'Close'],
  title: ['批次数据与业务研判', 'Batch data & business review'], intro: ['把四部门数据放在一起', 'Bring four departments together'],
  newBatch: ['导入新批次', 'Import a new batch'], uploadHelp: ['CSV 或 XLSX；多工作表或表头不在第 1 行时，按提示填写表格位置。每次导入保留独立批次。', 'CSV or XLSX; for several sheets or a header below row 1, fill in the table position when asked. Each import keeps an independent batch.'],
  sheetLayout: ['表格位置（可选）', 'Table position (optional)'], sheetName: ['工作表名', 'Sheet name'], headerRow: ['表头行号', 'Header row'],
  month: ['业务月份', 'Business month'], production: ['生产', 'Production'], procurement: ['采购', 'Procurement'], finance: ['财务', 'Finance'], marketing: ['市场', 'Marketing'],
  import: ['导入并检查', 'Import & check'], busy: ['正在处理…', 'Processing…'], loading: ['正在加载…', 'Loading…'],
  saved: ['批次已保存。清洗和聚合由规则执行，未调用模型。', 'Batch saved. Rules cleaned and totalled the data; the AI was not used.'],
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
  mappingHelp: ['通过队长确认对应关系，每一条都需要你审批。确认结果从下一次导入起生效，旧批次不变。', 'Confirm relationships through the captain; each one needs your approval. They apply from the next import; older batches stay unchanged.'],
  quarantineHelp: ['这些行没通过检查，没有参与任何计算。可以请队长逐行处理：重新通过检查才能放行（可附上你确认的更正值），丢弃要写明理由；应用后生成新批次。也可以修正源表后重新导入。', 'These rows failed a check and were left out of every calculation. Ask the captain to go through them: a row is released only after it passes the check again (with any corrections you confirm), and discarding needs a reason. Applying your decisions creates a new batch. You can also fix the source file and import again.'], derivedFrom: ['由批次派生（已应用隔离处置）', 'Derived from batch (quarantine decisions applied)'],
  evidenceHint: ['同一单元格可能被引用多次；这里只列出前几条引用，但所有符合条件的行都参与了计算。', 'A cell can be cited more than once. Only the first few citations are listed here, but every matching row was counted.'],
  reportRegion: ['四部门研判报告', 'Four-department review report'], roleReview: ['研判', ' review'], responsibility: ['职责', 'Responsibility'], owner: ['决策负责人', 'Decision owner'],
  operations_director: ['运营负责人', 'Operations director'], procurement_manager: ['采购负责人', 'Procurement manager'], finance_controller: ['财务负责人', 'Finance controller'], sales_director: ['销售负责人', 'Sales director'],
  proposals: ['以下都是建议：业务上什么都没改，由各负责人复核。', 'These are recommendations only. Nothing in the business has changed; each owner reviews them.'],
  action: ['建议', 'Proposal'], formula: ['公式', 'Formula'], evidence: ['解释与原始来源', 'Explanation & original sources'], modelAdvice: ['模型解释（待复核）', 'Model explanation (needs review)'], threshold: ['关注阈值', 'Attention threshold'],
  refs: ['引用次数', 'Input references'], shown: ['展示来源', 'Sources shown'], sourceRow: ['原表行', 'Original row'], scope: ['研判范围', 'Review scope'], reportId: ['报告编号', 'Report ID'], parent: ['队长会话', 'Captain session'], child: ['部门会话', 'Department session'],
  partialHelp: ['有部门的结论缺失，无法签核。可以补一条人工复核意见，或修正输入后导入新批次。', 'Some findings are missing, so this cannot be signed off. Add a review note, or fix the inputs and import a new batch.'],
  humanNote: ['人工复核意见', 'Human review note'], sendNote: ['交给队长复核', 'Send to captain'], noteSent: ['复核意见已复制。粘贴到对话里即可，不会自动重跑。', 'Review note copied. Paste it into the chat; nothing reruns automatically.'],
  state: ['业务状态', 'Business state'], nativeDetails: ['原生工具详情', 'Native tool details'], unknown: ['尚无记录', 'No recorded state'], approval: ['映射审批', 'Mapping approval'],
  allowed_once: ['允许一次', 'Allow once'], rejected: ['已拒绝', 'Rejected'], cancelled: ['已取消/超时', 'Cancelled / timed out'], unavailable: ['审批不可用', 'Approval unavailable'],
  reason: ['拒绝理由', 'Rejection reason'], approvalTitle: ['确认跨部门映射', 'Confirm cross-department mapping'], allow: ['允许一次', 'Allow once'], reject: ['拒绝', 'Reject'],
  optionalReason: ['拒绝理由（可选，最多 240 字符）', 'Rejection reason (optional, up to 240 characters)'], noteHelp: ['只有批准才会写入；拒绝不写入任何内容，之后还可以再提出。', 'Only approval writes this. Rejecting writes nothing, and it can be proposed again later.'],
  noteFail: ['理由未保存，尚未提交决定。重试或清空理由后拒绝。', 'Reason was not saved; no decision submitted. Retry or clear it to reject.'], expired: ['审批已结束或备注通道不可用', 'Approval ended or notes unavailable'],
  timeout: ['审批期限', 'Approval deadline'], seconds: ['秒', 'seconds'], inspect: ['查看调用轨迹', 'Inspect native trace'], details: ['查看摘要', 'Show summary'], failed: ['失败 / 已拒绝', 'Failed / rejected'], completed: ['已完成', 'Completed'],
  limits: ['文件上限', 'File limit'], transport: ['请求上限', 'Request limit'], invalidUpload: ['请选择至少一个 CSV/XLSX，文件总大小不得超过上限。', 'Select at least one CSV/XLSX; total size must fit the limit.'],
  // --- orientation on a blank session ---------------------------------------
  // A judge or an operator opening this sees the host's own "explore the unknown"
  // hero, which says nothing about what this product does or what to do first.
  heroTitle: ['四个部门的月度数据，对到一张表上', 'Four departments, one reconciled table'],
  heroLead: ['先导入本月四个部门的文件。计算由规则完成，AI 负责解释结果。', 'Start by importing this month\'s four department files. Rules do the arithmetic; the AI explains the results.'],
  heroStep1: ['导入四部门文件', 'Import the four sheets'],
  heroStep1Hint: ['CSV 或单工作表 XLSX，不调用 AI', 'CSV or single-sheet XLSX. No AI involved.'],
  heroStep2: ['检查清洗与隔离', 'Check corrections and quarantine'],
  heroStep2Hint: ['看规则改了什么、扣下了什么', 'See what the rules changed and what they held back'],
  heroStep3: ['在会话里发起研判', 'Ask for a review in the conversation'],
  heroStep3Hint: ['队长把任务分给四个部门代理，每条结论都注明出处', 'The captain hands the work to four department agents; every finding cites its rows'],
  heroStep4: ['审批要写入的决定', 'Approve anything that writes'],
  heroStep4Hint: ['你不点批准，什么都不会写入', 'Nothing is written until you approve it'],
  heroOpen: ['开始导入', 'Start an import'],

  // --- a state is only useful next to the action it implies -------------------
  nextTitle: ['下一步', 'Next step'],
  next_needs_configuration: ['字典里没有定义部门之间怎么关联，所以没能生成主表，也还不能研判。请队长起草缺少的定义，你审批并发布后重新导入；旧批次不受影响。', 'The dictionary does not say how the departments link up, so no master table was built and the review cannot start. Ask the captain to draft the missing definitions, approve and publish them, then import again. Older batches are not affected.'],
  askCaptain: ['让 captain 看这批数据', 'Ask the captain to look'],
  askCaptainHint: ['队长会找出字典不认识的列，并给出带依据的匹配建议；你逐条审批后重新导入。如果字典本身缺少定义，它会带你起草。', 'The captain finds columns the dictionary does not recognise and suggests matches with evidence. Approve each one, then import again. If the dictionary itself is missing definitions, it walks you through drafting them.'],
  columnQuestions: ['个上传列可能对应字典已声明的列', 'uploaded column(s) may match a declared column'],
  matchedColumns: ['按已批准的决定匹配的列', 'Columns matched by approved decisions'],
  staleMatches: ['列的形状变了，之前的决定没有沿用，需要重新确认', 'Column shape changed, so these earlier decisions were not reused and need confirming again'],
  droppedColumns: ['导入时剔除的列（无可提取的显示值）', 'Columns dropped at import (no displayable value)'],
  dictionaryInForce: ['本批次冻结的字典', 'Dictionary frozen into this batch'],
  draftHint: ['有些列字典里还没有定义。请队长起草定义，你逐条审核并发布，然后重新导入。', 'Some columns are not defined in the dictionary yet. Ask the captain to draft the definitions, review each one, publish, then import again.'],
  declaresEntities: ['它为各部门声明的可连接列', 'Joinable columns it declares'],
  declaresNothing: ['未声明任何可连接列', 'declares none'],
  next_needs_review: ['{quarantined} 行被扣下、{unresolved} 条映射待确认。先处置隔离行、确认映射，再发起研判。',
                      '{quarantined} row(s) held back, {unresolved} mapping(s) unconfirmed. Settle the quarantined rows and the mappings, then ask for a review.'],
  nextStepTitle: ['下一步', 'Next step'],
  goQuarantine: ['处理隔离行', 'Settle quarantined rows'], goMappings: ['确认待确认映射', 'Confirm pending mappings'],
  copyReviewRequest: ['复制研判请求', 'Copy review request'],
  // The inbox filter's label: named here only because the guard test proved the call
  // had been rendering the raw key's English spelling in both locales (#244).
  department: ['部门', 'Department'],
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
  comparisonField: ['字段', 'Field'], percentagePoints: ['个百分点', 'pp'],
  periodComparison: ['较上期', 'Against the base period'], comparisonBase: ['基期', 'Base period'],
  comparisonNoBase: ['没有基期批次，不显示为 0 或 −100%', 'No batch for the base period; not shown as 0 or −100%'],
  comparisonUnusable: ['基期批次无法按同一口径读取', 'The base batch cannot be read the same way'],
  comparisonChanged: ['两期声明的字段不同，差额会比较两个不同的东西', 'The periods declare different fields; a change would compare different things'],
  comparisonUnavailable: ['该基准不可用', 'That base is not available'],
  comparisonTotals: ['合计变化（新增 / 消失 / 持续）', 'Total change (new / discontinued / continuing)'],
  comparisonBreaches: ['超过声明阈值的变化', 'Changes past a declared threshold'],
  comparisonNotComputable: ['基期为 0，无法计算比例', 'Zero base; ratio not computable'],
  comparisonMissingBase: ['基期没有这一项', 'Not present in the base period'],
  monthlyBrief: ['本月结论', 'Conclusions'], briefNeedsReview: ['还没有研判报告', 'No review yet'],
  briefNeedsReviewHelp: ['本月结论基于已保存的四部门研判生成，请先发起研判。生成结论本身不调用 AI。', 'The brief is built from a saved four-department review, so start the review first. Building the brief itself does not call the AI.'],
  briefStale: ['有更新的研判报告，本页展示的是较早的一份。', 'A newer review exists; this page shows an earlier one.'],
  briefMissing: ['以下部门研判未通过，其指标不参与排序，也不显示为正常', 'These departments did not validate; their metrics are neither ranked nor shown as OK'],
  briefAttention: ['项需关注', 'need attention'], briefOk: ['项正常', 'OK'], briefOpenItems: ['待确认事项', 'Open items'],
  briefKeyMetrics: ['关键指标', 'Key metrics'], briefAttentionItems: ['需关注事项（按声明的严重度排序）', 'Attention items (declared severity order)'],
  briefNoAttention: ['没有触及声明阈值的检查。', 'No check reached a declared threshold.'],
  briefAction: ['建议动作', 'Proposed action'], briefCompleteness: ['完整性', 'Completeness'], briefDecisionAndLimits: ['管理决定与限制', 'Management decision and limitations'],
  pendingColumnQuestions: ['待确认列匹配', 'Pending column matches'],
  evidenceGrades: ['依据等级', 'Evidence grades'], evidenceGrade: ['依据等级', 'Evidence grade'], gradeMissing: ['出处缺失', 'Provenance missing'],
  gradeLegend: ['G1 来自原始单元格 · G2 由公式算出 · G3 依赖未确认的口径 · G4 模型建议', 'G1 read from a source cell · G2 computed by a formula · G3 relies on an unconfirmed convention · G4 model advice'],
  selfCheck: ['先自检', 'Check first'], selfCheckHelp: ['用与正式导入相同的规则检查所选文件，不创建批次。', 'Checks the chosen files with the same rules as import, without creating a batch.'],
  selfCheckMustFix: ['必须修改', 'Must fix'], selfCheckReview: ['建议核对', 'Review'], selfCheckAccepted: ['可以提交', 'Ready to submit'],
  selfCheckNeedsPeriod: ['请先选择业务月份。', 'Choose the business month first.'],
  stepGoHint: ['导入不调用模型，也不覆盖已有批次。', 'Import makes no model call and never overwrites an existing batch.'],
  chooseFile: ['选择文件', 'Choose a file'],
  noFile: ['尚未选择', 'None selected'],
  batchIdShort: ['批次', 'Batch'],
  columnsFrom: ['来自', 'from'],
  moreValues: ['项', 'values'],

  aggregate_metric: ['可追溯指标', 'Traceable metric'], confirm_mapping: ['映射决定', 'Mapping decision'], column_candidates: ['列匹配候选', 'Column match candidates'], confirm_column_match: ['列匹配决定', 'Column match decision'], workflow_catalogue: ['模板目录', 'Template catalogue'], workflow_draft: ['填报草稿', 'Draft record'], workflow_board: ['流转看板', 'Handoff board'], workflow_guidance: ['岗位操作指引', 'Role guidance'], workflow_handoff: ['下游处理', 'Downstream action'], workflow_record: ['记录填报内容', 'Record answers'], workflow_approve_submit: ['复核并提交', 'Approve and submit'], batch_summary: ['批次检查', 'Batch summary'], list_metrics: ['可用指标', 'Metric catalogue'], lookup_field_dictionary: ['字段口径', 'Field dictionary'], review_context: ['队长派活准备', 'Captain dispatch preparation'], review_finalize: ['队长汇总', 'Captain finalization'],

  // --- approval body: business semantics, not button labels (#110) ---------------
  // The prose mirrors askReason in ../approval/gate.ts; the reason string stays in
  // the approval request as the console fallback, this card renders it localized.
  approvalIntro: ['这个决定会被保存、下个月继续沿用，并出现在审计记录里。你批准之前，什么都不会写入。', 'This decision is saved, reused next month and shown in audits. Nothing is written until you approve.'],
  approvalTool: ['工具', 'Tool'], approvalArgs: ['决定内容', 'Decision details'],
  // Keys below are this plugin's own tool argument names (tools/confirm-mapping.ts),
  // a closed set we declared — never spreadsheet field names. Values stay verbatim.
  arg_source: ['来源实体', 'Source entity'], arg_target: ['目标实体', 'Target entity'],
  arg_relation: ['关系', 'Relation'], arg_accepted: ['决定', 'Decision'],
  arg_evidence: ['决定时展示的依据', 'Evidence shown when deciding'], arg_period: ['业务期间', 'Period'],
  acceptMapping: ['接受映射', 'Accept mapping'], rejectMapping: ['拒绝映射', 'Reject mapping'],
  countSuffix: [' 条', ''],
} as const
/** Language outside React: slot labels are callbacks, not components. */
export function currentLanguage(): 'zh' | 'en' { return current() }
/** Every defined label key. For the guard test that keeps copy from dying unwired (#244). */
export function labelKeys(): string[] { return Object.keys(labels) }
export function labelText(key: string): string {
  return labels[key as keyof typeof labels]?.[current() === 'zh' ? 0 : 1] ?? key
}
export function useUI() {
  const language = useSyncExternalStore(subscribe, current)
  const t = (key: string): string => labels[key as keyof typeof labels]?.[language === 'zh' ? 0 : 1] ?? key
  // Punctuation follows the language too: a full-width colon or bracket inside English
  // text reads as a rendering fault, and an English one inside Chinese reads as a typo.
  const zh = language === 'zh'
  const colon = zh ? '：' : ': '
  const paren = (value: unknown) => zh ? `（${String(value)}）` : ` (${String(value)})`
  const list = (items: readonly string[]) => items.join(zh ? '、' : ', ')
  return { t, language, colon, paren, list }
}
/** Display formatting only: the domain value never changes, the rendering follows the active language. */
export function formatDateTime(value: number | string | Date, language: string): string {
  return new Date(value).toLocaleString(language === 'zh' ? 'zh-CN' : 'en')
}
export function formatTime(value: number | string | Date, language: string): string {
  return new Date(value).toLocaleTimeString(language === 'zh' ? 'zh-CN' : 'en')
}
export function formatNumber(value: number, language: string, options?: Intl.NumberFormatOptions): string {
  return value.toLocaleString(language === 'zh' ? 'zh-CN' : 'en', options)
}
/**
 * A failure as a person reads it (#110): what went wrong in their language, then the
 * service's own words verbatim, because those name the field or rule and must not be
 * paraphrased away. A lost connection gets an actionable sentence instead of a stack.
 */
export function describeError(error: unknown, t: (key: string) => string): string {
  const detail = error instanceof Error ? error.message : String(error)
  if (/failed to fetch|networkerror|load failed/i.test(detail)) return t('networkFailed')
  return `${t('requestFailed')}：${detail.replace(/^Error:\s*/, '')}`
}

/**
 * The login portal (docs/27): the portal proves who the user is via Feishu and
 * signs a short-lived token; every backend request carries it in x-portal-token,
 * and the backend verifies the signature. Empty portalUrl = identity layer off.
 */
const PORTAL_TOKEN_KEY = 'bridgeflow.portal-token'
let portalBase = ''
export function portalToken(): string { return sessionStorage.getItem(PORTAL_TOKEN_KEY) ?? '' }
export function setPortalToken(token: string) { token ? sessionStorage.setItem(PORTAL_TOKEN_KEY, token) : sessionStorage.removeItem(PORTAL_TOKEN_KEY) }
export function portalLoginUrl(): string { return portalBase ? `${portalBase}/login?app=bridgeflow` : '' }
async function ensurePortalBase(): Promise<string> {
  if (portalBase) return portalBase
  try {
    const config = await (await fetch('/bridgeflow/config', { credentials: 'same-origin' })).json()
    portalBase = String(config.portalUrl ?? '')
  } catch { /* No portal configured: the identity layer stays off. */ }
  return portalBase
}
/** Trade the portal session cookie for a fresh app token. False = not signed in. */
async function refreshPortalToken(): Promise<boolean> {
  const base = await ensurePortalBase()
  if (!base) return false
  try {
    const response = await fetch(`${base}/token?app=bridgeflow`, { credentials: 'include' })
    if (!response.ok) return false
    setPortalToken(String((await response.json()).token ?? ''))
    if (!portalToken()) return false
    // The host is holding the token we just replaced. Re-claim, or the reads the model
    // triggers would keep relaying an expired one until it fell out of the binding.
    for (const sessionId of claimedSessions) void claimActor(sessionId)
    return true
  } catch { return false }
}

/**
 * Tell the host which person is driving this session (#231).
 *
 * Model-initiated reads have no browser behind them, so the host relays this token on
 * them and the backend verifies it per request. Best effort on purpose: a failure costs
 * attribution on those reads — the journal records them as the host's, as it did before
 * — and must never block the page or provoke a login prompt.
 */
const claimedSessions = new Set<string>()
export async function claimActor(sessionId: string): Promise<void> {
  const token = portalToken()
  if (!sessionId || !token) return
  claimedSessions.add(sessionId)
  try {
    await fetch(`/bridgeflow/actor?session_id=${encodeURIComponent(sessionId)}`,
                { method: 'POST', headers: { 'x-portal-token': token }, credentials: 'same-origin' })
  } catch { /* Attribution is not worth a broken view. */ }
}

/**
 * The signed-in user's own Feishu access token (docs/30), cached until near expiry.
 * It rides one header per Drive call and is never persisted beyond this page's memory.
 * Throws 'loginRequired' when the portal asks for a fresh sign-in.
 */
let feishuToken = { value: '', expiresAt: 0 }
export async function feishuUserToken(): Promise<string> {
  if (feishuToken.value && feishuToken.expiresAt > Date.now() / 1000 + 120) return feishuToken.value
  const base = await ensurePortalBase()
  if (!base) throw new Error('The login portal is not configured')
  const response = await fetch(`${base}/feishu/user-token`, { credentials: 'include' })
  if (response.status === 401) { reportRouteError('loginRequired'); throw new Error('Sign in again to grant Feishu Drive access') }
  if (!response.ok) {
    const detail = (await response.json().catch(() => ({}))) as { detail?: string }
    throw new Error(String(detail.detail ?? `portal answered ${response.status}`))
  }
  const body = (await response.json()) as { access_token?: string; expires_at?: number }
  if (!body.access_token) throw new Error('The portal returned no Feishu token')
  feishuToken = { value: body.access_token, expiresAt: Number(body.expires_at ?? 0) }
  return feishuToken.value
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  return request(path, init, true)
}
async function request<T>(path: string, init: RequestInit | undefined, mayRetry: boolean): Promise<T> {
  const token = portalToken()
  const headers = { ...(init?.headers as Record<string, string> | undefined), ...(token ? { 'x-portal-token': token } : {}) }
  const response = await fetch(`/bridgeflow${path}`, { ...init, headers, credentials: 'same-origin' })
  if (response.status === 401) {
    // One refresh-and-retry; a second 401 (or no portal at all) is the login prompt.
    if (mayRetry && await refreshPortalToken()) return request(path, init, false)
    if (await ensurePortalBase()) reportRouteError('loginRequired')
  }
  if (!response.ok) {
    const text = await response.text()
    let detail = text
    try { detail = JSON.parse(text).detail ?? text } catch { /* Plain transport error. */ }
    throw new Error(String(detail))
  }
  return response.json() as Promise<T>
}
/** The last session-link failure, kept until the shell shows it (it may mount after the failure). */
let routeError = ''
export function reportRouteError(key: string) { routeError = key; window.dispatchEvent(new CustomEvent('bridgeflow:route-error', { detail: key })) }
export function takeRouteError() { const key = routeError; routeError = ''; return key }
export type Route = { kind?: string; source?: string; batch?: string; view?: string; report?: string; parent?: string; child?: string }
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
  return `批次 ${batch}（${period}）没有可连接的列。请先调用 column_candidates 查看字典不认识的上传列，` +
    `以及每列只能匹配到的、本部门字典已声明的候选列。每个上传列至多提出一个匹配，` +
    `说明依据（类型是否相符、与其他部门同类列的值重合比例）和不确定项；重合比例不是跨实体关系的证明。` +
    `然后对每个提议调用 confirm_column_match，由人通过原生审批决定，不要替人决定。` +
    `批准后告诉用户：当前批次保持冻结，需要重新导入文件才会生效。` +
    `没有合适候选时明确说需要字典负责人决定；禁止创造字段、实体或字典，禁止读取数据行，` +
    `除 confirm_column_match 外不执行任何写入。`
}

export function reviewRequest(batch: string, period = '') {
  return `请研判 ${period} 批次 ${batch}：review_context → 同一响应四次官方 subagent（production/procurement/finance/marketing）→ review_finalize。缺口如实标 partial，不重试，不执行业务动作。`
}
export type Summary = { demo_case?: string | null; batch_id: string; period: string; status: string; master_rows: number; unresolved: number; refusal: string;
  /** Row-level problems the review would refuse, in its own words; they keep the batch out of ready. */
  review_blockers?: string[]
  departments: { department: string; rows: number; quarantined: number; corrections: number }[]
  /** The dictionary this batch was frozen against, and what it declares per department. */
  dictionary?: string
  declared_entities?: Record<string, string[]>
  /** `department.column → declared column`, applied from remembered human decisions. */
  matched_columns?: string[]
  stale_matches?: string[]
  column_questions?: number
  derived_from?: string | null
  /** Batches derived from this one (E14-UC04): this batch's report rests on corrected data. */
  superseded_by?: string[]
  /** Intake columns dropped as unrepresentable (docs/33): names and types, never values. */
  dropped_columns?: { department: string; column: string; field_type: string; reason: string }[] }

let runtime: { sessions: ISessions; conversation: Context['conversation'] }
export function configureRuntime(ctx: Context) { runtime = ctx as unknown as typeof runtime; configureLocale(ctx.locale) }
export async function openSession(parent: string, child?: string) {
  await runtime.sessions.refresh()
  if (child) {
    await runtime.sessions.refreshSubagents(parent as SessionId)
    const entry = runtime.sessions.list.getSnapshot().subagentsByParent[parent as SessionId]?.entries.find((e: SubagentListEntry) => e.kind === 'child' && e.id === child)
    if (!entry || entry.kind !== 'child') throw new Error('Child is absent from the native parent catalogue')
    runtime.sessions.openSubagent({ parentSessionId: parent as SessionId, childSessionId: child as SessionId, mode: entry.mode })
  } else {
    // Opening an id nobody has would otherwise do nothing, silently (#40).
    const known = runtime.sessions.list.getSnapshot().byId[parent as SessionId] ?? runtime.sessions.binding(parent as SessionId)
    if (!known) throw new Error('Parent is absent from the native session catalogue')
    runtime.sessions.open(parent as SessionId)
  }
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
export async function createNotebookSession(sessions: ISessions) {
  const { workspaceId } = await api<{workspaceId: string}>('/config')
  if (!workspaceId) throw new Error('BridgeFlow workspace is unavailable')
  return sessions.create({workspaceId: workspaceId as WorkspaceId})
}

export async function startReview(batch: string, period: string): Promise<void> {
  return ask(reviewRequest(batch, period))
}

/** Send the captain a diagnosis request for a batch nothing can be built from. */
export async function startDiagnosis(batch: string, period: string): Promise<void> {
  return ask(diagnoseRequest(batch, period))
}

/** Put a prepared request in front of the captain, in the current session (or a new one). */
export async function askCaptain(text: string): Promise<void> { return ask(text) }

async function ask(text: string): Promise<void> {
  await runtime.sessions.refresh()
  const current = runtime.sessions.list.getSnapshot().current
  const target = current ?? (await createNotebookSession(runtime.sessions))
  const binding = runtime.sessions.binding(target)
  if (!binding) throw new Error('No session is available to work in')
  const result = await binding.session.prompt([{ type: 'text', text }], 'queue')
  if (!result.ok) throw new Error(result.error.message)
  runtime.sessions.open(target)
}

export async function sendHumanNote(parent: string, batch: string, report: string, note: string) {
  const noteId = crypto.randomUUID()
  // Recorded by the host first: the note exists even if the turn that follows goes wrong.
  await api('/human-note', { method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ batch_id: batch, report_id: report, session_id: parent, note_id: noteId, note }) })
  await runtime.sessions.refresh()
  const binding = runtime.sessions.binding(parent as SessionId)
  if (!binding) throw new Error('Captain session unavailable')
  // The marker is what the host guard reads to keep this turn to recording (#111).
  const result = await binding.session.prompt([{ type: 'text', text: `[bridgeflow:human-note:${noteId}] 人工复核意见（报告 ${report}）：${note}。意见已由系统记录。请说明尚缺哪些部门签核；不要重跑研判或执行业务动作。` }], 'queue')
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
  // Structural keys of our own views translate; business field names never do (they come
  // from the customer's dictionary and are shown as declared).
  const structural = t(`view_${column}`)
  if (dot < 0 && structural !== `view_${column}`) return { group: '', label: structural }
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
  if (typeof value === 'number') {
    const text = value.toLocaleString(undefined, { maximumFractionDigits: 4 })
    // Display may shorten a figure; it must never silently change it (#110). When the
    // shown digits are not the value, say so and keep the exact value one hover away.
    const exact = Number(value.toFixed(4)) === value
    return exact ? { text, numeric: true, empty: false } : { text: `≈${text}`, full: String(value), numeric: true, empty: false }
  }
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
