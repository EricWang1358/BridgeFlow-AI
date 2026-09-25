/**
 * Where every feature lives in the interface, so the captain can answer "is there a …?" and
 * "where do I …?" with the exact clicks instead of guessing (and never invents a feature that
 * is not here). Shared by the `app_guide` tool and the chat card that renders its answer.
 *
 * Each step's words are the labels the interface shows; `tests/app-guide.test.ts` checks them
 * against `client/ui.ts` so the guide cannot drift from the screen. `view` is the Studio page
 * the card can open directly; features without one are reached from the chat or the top bar.
 */
export type GuideView = 'overview' | 'tasks' | 'data' | 'integration' | 'master' | 'brief' | 'records' | 'quotation' | 'discovery' | 'handoff'
type Text = readonly [zh: string, en: string]
export type GuideEntry = {
  readonly what: Text
  readonly steps: readonly Text[]
  /** Studio page the card can open; `batch` when it only makes sense with a batch open. */
  readonly view?: GuideView
  readonly needsBatch?: boolean
  readonly note?: Text
  /** Read tools that answer whether the current notebook already has it. */
  readonly check?: readonly string[]
}

// Interface words used in more than one path.
const studio: Text = ['右侧「工作室」', 'The Studio pane on the right']
const other: Text = ['「其他工作区」', 'Other workspaces']
const discovery: Text = ['「立项材料与候选」', 'Discovery materials and opportunities']
const discoveryProject: Text = ['在页面顶部点「载入示例项目」，或填项目标识后点「打开项目」', 'At the top of the page, click Load the sample project, or enter a project ID and click Open project']

export const guide = {
  overview: {
    what: ['总览：收口进度、待办、流转中的记录、代理运行与关键指标趋势', 'Overview: close progress, open items, records in flight, agent runs and metric trends'],
    steps: [[`${studio[0]} → 「总览」`, `${studio[1]} → Overview`]],
    view: 'overview',
    note: ['只有一个月时趋势图只有一个点；总览里点「载入前两个月的示例」可补齐。', 'With one month the trends have one point; click Load the two earlier sample months on the Overview to add history.'],
  },
  tasks: {
    what: ['本月任务：还在等谁、数据能否研判、各部门待办', 'This month’s tasks: what is waiting on whom, whether the data can be reviewed, open items by department'],
    steps: [[`${studio[0]} → 「本月任务」`, `${studio[1]} → This month’s tasks`]],
    view: 'tasks', needsBatch: true, check: ['monthly_inbox', 'monthly_checklist'],
  },
  data: {
    what: ['数据：清洗记录、隔离行、数据质量计数与跨部门总表入口', 'Data: corrections, quarantined rows, data-quality counts and the way into the cross-department master'],
    steps: [[`${studio[0]} → 「数据」`, `${studio[1]} → Data`]],
    view: 'data', needsBatch: true, check: ['batch_summary'],
  },
  cross_department_master: {
    what: ['跨部门总表：四部门按字典合成一张表，含待确认项、口径假设和单元格出处', 'Cross-department master: the four departments combined by the dictionary, with open questions, assumed conventions and the source of every cell'],
    steps: [[`${studio[0]} → 「数据」`, `${studio[1]} → Data`], ['点「跨部门总表」', 'Click Cross-department master'],
      ['悬停或点击单元格看出处；「下载总表 xlsx」可导出', 'Hover or click a cell for its source; Download master xlsx exports it']],
    view: 'integration', needsBatch: true, check: ['integration_summary'],
  },
  download_master: {
    what: ['下载总表：导出带待确认项和口径假设的 Excel', 'Download the master: an Excel workbook with the open questions and assumptions'],
    steps: [[`${studio[0]} → 「数据」 → 「跨部门总表」`, `${studio[1]} → Data → Cross-department master`], ['点「下载总表 xlsx」', 'Click Download master xlsx']],
    view: 'integration', needsBatch: true,
  },
  batch_tables: {
    what: ['批次数据表：主表、清洗记录、待确认映射、列匹配、隔离行、部门报告', 'Batch tables: master table, corrections, pending mappings, column matches, quarantined rows, department report'],
    steps: [[`${studio[0]} → 「产物」里的「主表」`, `${studio[1]} → the Master table item under Artifacts`], ['在弹窗顶部切换各个标签', 'Switch between the tabs at the top of the dialog']],
    view: 'master', needsBatch: true,
  },
  review: {
    what: ['四部门研判：队长派出生产、物资、财务、市场四个子代理，结论带公式和来源', 'Four-department review: the captain sends production, procurement, finance and marketing agents; every finding carries its formula and sources'],
    steps: [['在中间对话框里请队长“研判本月批次”', 'In the chat, ask the captain to review this month’s batch'],
      [`完成后在${studio[0]} → 「产物」打开报告；对话顶部「轨迹」看四个子代理`, 'When it finishes, open the report under Artifacts in the Studio pane; the Trajectory tab above the chat shows the four agents']],
    needsBatch: true,
    note: ['会调用模型、产生费用；访客关闭 AI 时不可用。', 'This calls the model and costs money; unavailable when a guest instance has AI turned off.'],
  },
  conclusions: {
    what: ['本月结论：研判后的月度简报与上月对比', 'Conclusions: the monthly brief after a review, compared with the month before'],
    steps: [[`${studio[0]} → 「本月结论」`, `${studio[1]} → Conclusions`]],
    view: 'brief', needsBatch: true,
    note: ['需要先完成一次四部门研判。', 'Needs a finished four-department review first.'],
  },
  records: {
    what: ['记录：每次代理运行的泳道、token 用量、被拒绝的调用与决策日志', 'Records: each agent run’s swim lanes, token use, refused calls and the decision journal'],
    steps: [[`${studio[0]} → 「记录」`, `${studio[1]} → Records`]],
    view: 'records',
  },
  quotation: {
    what: ['报价工作区：报价需要哪些事实、由谁提供、按声明公式算出的价格带', 'Quotation workspace: which facts a quote needs, who owes each one, and the price band computed from declared arithmetic'],
    steps: [[`${studio[0]} → ${other[0]} → 「报价工作区」`, `${studio[1]} → ${other[1]} → Quotation workspace`]],
    view: 'quotation',
  },
  discovery: {
    what: ['立项：部门材料、改进候选、流程图、评分四象限、会议与决策', 'Discovery: department materials, improvement opportunities, flow graphs, rating quadrants, meetings and decisions'],
    steps: [[`${studio[0]} → ${other[0]} → ${discovery[0]}`, `${studio[1]} → ${other[1]} → ${discovery[1]}`], discoveryProject,
      ['用项目名下方的标签切换：材料、候选、流程图、评分四象限、会议、决策', 'Use the tabs under the project name: Materials, Opportunities, Flow graphs, Rating quadrants, Meetings, Decisions']],
    view: 'discovery', check: ['discovery_materials'],
  },
  quadrant_chart: {
    what: ['评分四象限：各改进候选按投入与价值落在四个象限', 'Rating quadrants: each improvement opportunity placed by effort and value'],
    steps: [[`${studio[0]} → ${other[0]} → ${discovery[0]}`, `${studio[1]} → ${other[1]} → ${discovery[1]}`], discoveryProject,
      ['点标签「评分四象限」，图在评分列表上方', 'Click the Rating quadrants tab; the chart is above the score list']],
    view: 'discovery',
    note: ['候选至少有一条评分后才画点；示例项目已带评分。', 'Points appear once an opportunity has a score; the sample project already has scores.'],
  },
  flow_graph: {
    what: ['流程图：部门之间的信息与文件怎么流转', 'Flow graph: how information and files move between departments'],
    steps: [[`${studio[0]} → ${other[0]} → ${discovery[0]}`, `${studio[1]} → ${other[1]} → ${discovery[1]}`], discoveryProject,
      ['点标签「流程图」', 'Click the Flow graphs tab']],
    view: 'discovery',
  },
  handoff: {
    what: ['填报与流转：按已批准的立项范围填部门模板、审核、交给下一个部门，含七段流程条和每条记录的时间线', 'Filling & handoff: fill department templates under the approved scope, review, hand to the next department; a seven-stage flow strip and a timeline per record'],
    steps: [[`${studio[0]} → ${other[0]} → 「填报与流转」`, `${studio[1]} → ${other[1]} → Filling & handoff`],
      ['没有记录时点「载入示例工作流」', 'With no records yet, click Load the sample workflow']],
    view: 'handoff', check: ['workflow_board', 'workflow_scope'],
  },
  add_sources: {
    what: ['添加来源：上传四个部门的月度表格（配置了飞书时也可从飞书导入）', 'Add sources: upload the four departments’ monthly spreadsheets (or import from Feishu when it is configured)'],
    steps: [['左侧「来源」 → 「添加来源」', 'The Sources pane on the left → Add sources']],
  },
  sample_notebook: {
    what: ['示例笔记本：虚构商砼公司 2024-07 的四部门数据，另有三套不同问题的样例', 'Sample notebooks: a fictional concrete supplier’s four department files for 2024-07, plus three samples with different problems'],
    steps: [['左侧「来源」 → 「打开示例笔记本」', 'The Sources pane on the left → Open sample notebook'], ['其他样例在它下面的「更多示例」里', 'The other samples are under More sample cases just below']],
    note: ['不调用模型，不产生费用。', 'No model calls, no charge.'],
  },
  source_file: {
    what: ['原件预览：解析后的原始表格、工作表与文件指纹', 'Source preview: the parsed original table, its sheet and file fingerprint'],
    steps: [['左侧「来源」里点某个文件', 'Click a file in the Sources pane on the left']],
    needsBatch: true,
  },
  notebooks: {
    what: ['笔记本：新建、保存、打开历史笔记本、退出', 'Notebooks: create, save, reopen an earlier one, exit'],
    steps: [['顶栏「新建笔记本」「保存笔记本」「笔记本」「退出笔记本」', 'The top bar: Create notebook, Save notebook, Notebooks, Exit notebook']],
  },
  guided_tours: {
    what: ['引导：一步步带你做完合并与核对、研判、报价、立项到流转', 'Guided tours: step by step through combining and checking, review, quotation, and discovery to handoff'],
    steps: [['顶栏右上「帮助与引导」', 'The top bar, top right: Help & guided tours']],
  },
  settings: {
    what: ['会话与设置：历史会话、模型选择与语言', 'Sessions & settings: earlier sessions, model choice and language'],
    steps: [['顶栏「会话与设置」', 'The top bar: Sessions & settings']],
  },
  trajectory: {
    what: ['轨迹：这次对话里每一步工具调用、子代理与审批', 'Trajectory: every tool call, sub-agent and approval in this conversation'],
    steps: [['中间对话区顶部的「轨迹」标签', 'The Trajectory tab at the top of the chat']],
  },
} as const satisfies Record<string, GuideEntry>

export type GuideFeature = keyof typeof guide
export const guideFeatures = Object.keys(guide) as GuideFeature[]
