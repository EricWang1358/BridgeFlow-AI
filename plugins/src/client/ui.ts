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
  ...tourLabels,
  notebookKind: ['笔记本用途', 'Notebook purpose'], monthlyNotebook: ['月度对账', 'Monthly review'], quotationNotebook: ['报价', 'Quotation'], mixedNotebook: ['综合工作', 'Combined work'],
  monthlyProgress: ['月度对账进度', 'Monthly review progress'], quotationProgress: ['报价进度', 'Quotation progress'],
  notStarted: ['尚未开始', 'Not started'], quotationNext: ['查看声明与待补依据', 'View declaration and missing evidence'],
  notebookPurposeHelp: ['选择用途可调整状态指引；月度对账和报价保持独立。', 'Purpose tailors the status guidance; monthly review and quotation remain separate.'],
  untitledNotebook: ['未命名笔记本', 'Untitled notebook'], notebookName: ['笔记本名称', 'Notebook name'],
  notebooks: ['笔记本', 'Notebooks'], saveNotebook: ['保存笔记本', 'Save notebook'], exitNotebook: ['退出笔记本', 'Exit notebook'],
  leaveNotebook: ['离开前保存笔记本？', 'Save this notebook before leaving?'],
  noPendingApproval: ['当前没有待处理审批。需要您确认时，会在对话中提示。', 'No approval is pending. Chat will prompt you when a decision is needed.'],
  saveNotebookHelp: ['保存名称和来源选择，之后可从笔记本列表重新打开。不保存仅放弃本次名称和来源选择；已记录的对话、已上传文件和报告仍保留。', 'Save the name and source selection to reopen from Notebooks. Discard only drops these edits; recorded conversations, uploaded files and reports remain.'],
  saveAndContinue: ['保存并继续', 'Save and continue'], discardAndContinue: ['不保存并继续', 'Discard and continue'], cancelLeave: ['取消，继续编辑', 'Cancel, keep editing'],
  notebookTitleRequired: ['请填写笔记本名称', 'Enter a notebook name'],
  notebookHistoryHelp: ['从 DSH 已保存的会话中打开笔记本；来源及产物按保存的批次恢复。未保存的空白笔记本不列入历史。', 'Open saved DSH sessions with their saved sources and artifacts. Unsaved empty notebooks are omitted.'],
  sampleNotebook: ['打开示例笔记本', 'Open sample notebook'], sampleNotebookTitle: ['业务演示 · 月度对账（模拟商砼公司 2024-07）', 'Business demo · monthly review (fictional concrete supplier, 2024-07)'],
  sampleNotebookHelp: ['虚构数据，按业务方 v2 四部门模板填写；可预览来源、主表和跨部门总表。研判需手动发起，会使用配置的模型。', 'Fictional data on the business side\'s v2 department templates; preview sources, the master table and the cross-department table. Starting a review uses the configured model.'],
  draftNotebook: ['空白草稿', 'Empty draft'],
  unsavedNotebook: ['未保存', 'Unsaved'], savedNotebook: ['已保存', 'Saved'],
  resizeSources: ['调整来源栏宽度', 'Resize Sources'], resizeStudio: ['调整工作室宽度', 'Resize Studio'],
  newNotebook: ['新建笔记本', 'Create notebook'],
  previewUnavailable: ['无法加载此预览，请检查批次或重新选择来源。', 'This preview could not be loaded. Check the batch or select a source again.'],
  studioStateHelp: ['导入与报告来自所选批次；审批来自当前原生会话。详细轨迹可在中栏查看。', 'Import and report state belong to the selected batch; approvals belong to the current native session. Open the center trace for details.'],
  welcomeTitle: ['从这里开始你的业务笔记本', 'Let’s start your business notebook'],
  welcomeHelp: ['把部门文件放到左侧，在这里与队长核对，在右侧查看产物与依据。', 'Add department files on the left, work with your captain here, and preview outputs and evidence on the right.'],
  monthlySteps: ['月度对账怎么开始', 'How to start a monthly review'],

  notebookTitle: ['业务笔记本', 'Business notebook'], sessionsSettings: ['会话与设置', 'Sessions & settings'],
  addSources: ['添加来源', 'Add sources'], sourceUploadHelp: ['月度对账 · 上传的部门文件保留在这里，点击即可预览。', 'Monthly review · Uploaded department files appear here. Select a file to preview.'],
  emptySources: ['保存的来源会显示在这里', 'Saved sources will appear here'], emptySourcesHelp: ['添加本月部门文件，开始核对与分析。', 'Add this month’s department files to start your review.'],
  originalUnavailable: ['旧批次未保留原件预览', 'Original preview unavailable for this older batch'],
  sourceDetails: ['文件来源信息', 'File provenance'], sourceFilename: ['上传文件', 'Uploaded file'], sourceSheet: ['工作表', 'Worksheet'],
  sourceFingerprint: ['文件指纹（SHA-256）', 'File fingerprint (SHA-256)'],
  sourceFingerprintHelp: ['用于核对上传文件的内容是否一致，不是业务结论。上面的表格是清洗前的解析预览；计算口径请查看主表或研判报告。', 'Identifies the uploaded file content; it is not a business finding. The table above previews parsed data before cleaning. See the master table or review for calculations.'],
  allRowsShown: ['已显示全部数据，无需翻页', 'All rows are shown; no additional pages'], sourcePagination: ['来源分页', 'Source pagination'], pageLabel: ['页', 'Page'], retry: ['重试', 'Retry'],
  sourcePreview: ['来源预览', 'Source preview'], parsedOriginal: ['原始表格的解析视图，未经清洗；数据仅供浏览器分页预览。', 'Parsed original table before cleaning; paginated browser preview only.'],
  tools: ['工具', 'Tools'], artifacts: ['产物', 'Artifacts'], refreshArtifacts: ['刷新产物', 'Refresh artifacts'],
  emptyArtifacts: ['完成研判后，报告会保存在这里。', 'Completed review reports will appear here.'],
  studioStartHelp: ['添加来源后可发起月度研判。报价声明可直接查看。', 'Add sources to start a monthly review. The quotation declaration is available now.'],
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
  quarantine_list: ['隔离行清单', 'Quarantined rows'], quarantine_decide: ['隔离行处置', 'Quarantine decision'], quarantine_apply: ['应用隔离处置', 'Apply quarantine decisions'],
  view_department: ['部门', 'Department'], view_column: ['上传列', 'Uploaded column'], view_original: ['原始表头', 'Header as written'], view_candidate: ['已声明候选列', 'Declared candidate'], view_role: ['声明角色', 'Declared role'], view_type_fits: ['类型相符', 'Type fits'], view_shared_values: ['值重合', 'Shared values'], view_decision: ['决定', 'Decision'], view_index: ['序号', 'Index'],
  columns: ['列匹配', 'Column matches'], columnsHelp: ['字典不认识的上传列，以及它们只能对应的本部门已声明列和依据（类型、与其他部门同类列的值重合）。请在对话中让队长提议，你在审批里逐列决定；决定只对之后的新导入生效，本批次保持不变。原始数据可在来源预览中查看。', 'Uploaded columns the dictionary does not know, the declared columns of that department they could be, and the evidence (type, shared values with the same kind elsewhere). Ask the captain in chat to propose; you decide each in the approval. Decisions apply to later imports only; this batch stays unchanged. Original data is in the source preview.'],
  requestFailed: ['操作未完成', 'Not completed'], networkFailed: ['连接不上服务，请检查服务是否在运行后重试。', 'Could not reach the service. Check that it is running, then retry.'],
  loginRequired: ['这份数据需要先登录。请通过飞书登录后再试。', 'This data needs a signed-in user. Log in with Feishu, then retry.'],
  loginWithFeishu: ['飞书登录', 'Log in with Feishu'],
  approval_feishu_import: ['飞书文件导入审批', 'Feishu import approval'], approvalTitle_feishu_import: ['从飞书下载这些文件并导入为新批次', 'Download these Feishu files into a new batch'],
  approval_feishu_upload_report: ['上传到飞书审批', 'Feishu upload approval'], approvalTitle_feishu_upload_report: ['把这份研判报告上传到飞书文件夹', 'Upload this review report to the Feishu folder'],
  feishu_import: ['从飞书导入', 'Import from Feishu'], feishu_upload_report: ['上传报告到飞书', 'Upload report to Feishu'],
  feishuPick: ['从飞书选择', 'Choose from Feishu'],
  feishuPickHelp: ['浏览你有权访问的飞书云文档，选中文件、在线表格或多维表格并指定部门后导入；表格需再选工作表与表头行，多维表格需再选数据表。只能看到你自己有权限的内容。', 'Browse the Feishu files your own account can access; pick files, sheets or bitables, assign departments, then import. A sheet also needs its worksheet and header row; a bitable needs its data table. You only see what your own account may access.'],
  feishuRoot: ['我的空间', 'My space'], feishuEmpty: ['这个文件夹是空的', 'This folder is empty'], feishuMore: ['加载更多', 'Load more'],
  feishuUnsupported: ['此类型暂不支持导入', 'This type cannot be imported yet'], feishuAssign: ['部门', 'Department'],
  feishuDeptAuto: ['部门由该知识库决定', 'Department follows this wiki space'],
  feishuImportGo: ['导入选中文件', 'Import selected files'], feishuPickFolder: ['选择当前文件夹', 'Choose this folder'],
  feishuUpload: ['上传报告到飞书', 'Upload report to Feishu'], feishuUploadHere: ['上传到当前文件夹', 'Upload to this folder'],
  feishuUploaded: ['已上传到飞书', 'Uploaded to Feishu'], feishuNoReport: ['先完成一次研判，才能把报告传回飞书。', 'Finish a review before sending a report back to Feishu.'],
  feishuTarget: ['目标', 'Target'], feishuWiki: ['知识库', 'Wiki'],
  feishuWikiHelp: ['浏览你有权访问的知识库（个人文档库与团队知识库）。已映射部门的知识库会自动确定部门；未映射的知识库（总经办、个人文档库）仍需手动指定部门。选中文件、在线表格或多维表格节点并导入；表格需再选工作表与表头行，多维表格需再选数据表。', 'Browse the wiki spaces your own account can access (personal library and team spaces); mapped spaces decide the department automatically, unmapped ones (master office, personal library) keep the manual pick. Pick file, sheet or bitable nodes, then import. A sheet also needs its worksheet and header row; a bitable needs its data table.'],
  feishuTablePick: ['数据表', 'Data table'],
  feishuSpaces: ['选择知识库', 'Choose a wiki space'], feishuSpacesEmpty: ['没有可见的知识库', 'No wiki spaces visible'],
  feishuUploadFileWiki: ['上传本地文件到知识库', 'Upload a local file to wiki'], feishuPickFile: ['选择文件', 'Choose file'],
  feishuWikiUploaded: ['已上传到知识库', 'Uploaded to wiki'], feishuUploadWikiHere: ['上传到当前位置', 'Upload here'],
  integrationMaster: ['跨部门总表', 'Cross-department master'], downloadMaster: ['下载总表 xlsx', 'Download master xlsx'],
  integrationAssumptions: ['按通用做法补的口径（业务方确认后可在声明里替换）', 'Conventions filled in where the dictionary is silent (replaceable once the business side confirms)'],
  integrationHelp: ['按业务字典对齐四部门模板生成；悬停单元格可看出处（部门、文件、行、表头，或公式），✓ 表示部门填写值已按字典公式核对。', 'Built from the four department templates by the business dictionary; hover a cell for its source (department, file, row, header, or formula); ✓ means a department value was checked against the dictionary formula.'],
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
  handoffHelp: ['按已批准模板形成的标准记录、下游交接与通知状态。已收到 ≠ 数据就绪 ≠ 已通知 ≠ 下游已完成。', 'Standard records from approved templates, downstream handoffs and notifications. Received ≠ ready ≠ notified ≠ done.'],
  handoffBoard: ['流转看板', 'Handoff board'], handoffEmpty: ['还没有填报记录', 'No records yet'],
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
  newBatch: ['导入新批次', 'Import a new batch'], uploadHelp: ['CSV 或 XLSX；多工作表或表头不在第 1 行时，按提示填写表格位置。每次导入保留独立批次。', 'CSV or XLSX; for several sheets or a header below row 1, fill in the table position when asked. Each import keeps an independent batch.'],
  sheetLayout: ['表格位置（可选）', 'Table position (optional)'], sheetName: ['工作表名', 'Sheet name'], headerRow: ['表头行号', 'Header row'],
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
  quarantineHelp: ['隔离行未进入计算，也不会自动放行。可以请队长逐行处置：放行必须通过重新校验（可附上你确认的更正值），丢弃需写明理由；应用后生成新批次，本批次及其报告保持不变。也可以修正源表后重新导入。', 'Quarantined rows are excluded and never released automatically. Ask the captain to decide each row: release must pass revalidation (with any corrected cells you confirm), discard needs a reason; applying creates a new batch and leaves this batch and its reports unchanged. You can also correct the source and import again.'], derivedFrom: ['由批次派生（已应用隔离处置）', 'Derived from batch (quarantine decisions applied)'],
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
  askCaptainHint: ['它会找出字典不认识的上传列，只在本部门字典已声明的列里提出匹配和依据；每个匹配都要你在审批里决定，批准后重新导入即生效。没有候选时需要字典负责人决定。',
                   'It finds uploaded columns the dictionary does not know and proposes matches only to columns already declared for that department, with evidence. You decide each one in the approval; re-import to apply. No candidate means the dictionary owner decides.'],
  columnQuestions: ['个上传列可能对应字典已声明的列', 'uploaded column(s) may match a declared column'],
  matchedColumns: ['按已批准的决定匹配的列', 'Columns matched by approved decisions'],
  staleMatches: ['列的形状变了，之前的决定没有沿用，需要重新确认', 'Column shape changed, so these earlier decisions were not reused and need confirming again'],
  droppedColumns: ['导入时剔除的列（无可提取的显示值）', 'Columns dropped at import (no displayable value)'],
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
  monthlyBrief: ['本月结论', 'This month'], briefNeedsReview: ['还没有研判报告', 'No review yet'],
  briefNeedsReviewHelp: ['本月结论由已保存的四部门研判生成；请先发起研判。生成结论不调用模型。', 'The brief is built from a saved four-department review; start the review first. Building the brief calls no model.'],
  briefStale: ['有更新的研判报告，本页展示的是较早的一份。', 'A newer review exists; this page shows an earlier one.'],
  briefMissing: ['以下部门研判未通过，其指标不参与排序，也不显示为正常', 'These departments did not validate; their metrics are neither ranked nor shown as OK'],
  briefAttention: ['项需关注', 'need attention'], briefOk: ['项正常', 'OK'], briefOpenItems: ['待确认事项', 'Open items'],
  briefKeyMetrics: ['关键指标', 'Key metrics'], briefAttentionItems: ['需关注事项（按声明的严重度排序）', 'Attention items (declared severity order)'],
  briefNoAttention: ['没有触及声明阈值的检查。', 'No check reached a declared threshold.'],
  briefAbove: ['高于阈值', 'Above threshold'], briefBelow: ['低于阈值', 'Below threshold'], briefOwner: ['决定人', 'Decision owner'],
  briefAction: ['建议动作', 'Proposed action'], briefCompleteness: ['完整性', 'Completeness'], briefDecisionAndLimits: ['管理决定与限制', 'Management decision and limitations'],
  pendingColumnQuestions: ['待确认列匹配', 'Pending column matches'],
  evidenceGrades: ['依据等级', 'Evidence grades'], evidenceGrade: ['依据等级', 'Evidence grade'], gradeMissing: ['出处缺失', 'Provenance missing'],
  gradeLegend: ['G1 原件 · G2 公式 · G3 未确认口径 · G4 模型建议', 'G1 source · G2 formula · G3 unconfirmed convention · G4 model advice'],
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
  approvalIntro: ['此操作记录的决定将在下个月复用并进入审计。它会改变已存数据；未经批准不会写入。',
                  'This records a decision that will be reused next month and cited in an audit. It changes stored state; nothing is written without approval.'],
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
export function labelText(key: string): string {
  return labels[key as keyof typeof labels]?.[current() === 'zh' ? 0 : 1] ?? key
}
export function useUI() {
  const language = useSyncExternalStore(subscribe, current)
  const t = (key: string): string => labels[key as keyof typeof labels]?.[language === 'zh' ? 0 : 1] ?? key
  return { t, language }
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
    return !!portalToken()
  } catch { return false }
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
  departments: { department: string; rows: number; quarantined: number; corrections: number }[]
  /** The dictionary this batch was frozen against, and what it declares per department. */
  dictionary?: string
  declared_entities?: Record<string, string[]>
  /** `department.column → declared column`, applied from remembered human decisions. */
  matched_columns?: string[]
  stale_matches?: string[]
  column_questions?: number
  derived_from?: string | null
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
