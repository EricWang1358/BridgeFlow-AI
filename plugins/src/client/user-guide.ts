/**
 * The BridgeFlow user guide, in both languages: one source for the page under Sessions & settings
 * and for docs/user-guide.{zh,en}.md (`pnpm docs:guide`; a test keeps the files in step).
 *
 * Every button named here is quoted exactly as the interface shows it, so a reader can find it by
 * its words. `tests/user-guide.test.ts` checks the 「」-quoted Chinese names against the labels.
 */
type Text = readonly [zh: string, en: string]
export type GuideSection = {
  readonly id: string
  readonly title: Text
  readonly intro?: Text
  readonly steps?: readonly Text[]
  readonly points?: readonly Text[]
  readonly faq?: readonly (readonly [Text, Text])[]
  readonly terms?: readonly (readonly [Text, Text])[]
  readonly note?: Text
}

export const guideTitle: Text = ['BridgeFlow 使用说明书', 'BridgeFlow user guide']
export const guideLead: Text = [
  '这份说明写给第一次用 BridgeFlow 的你。不需要懂技术，也不需要先准备文件：照着“五分钟上手”点一遍，就知道它能做什么。每个按钮都用界面上的原字写出来，照着找就行。',
  'This guide is for your first time with BridgeFlow. You need no technical background and no files to start: follow "Five minutes to your first result" once and you will know what it does. Every button is written exactly as it appears on screen, so you can find it by its words.',
]

export const userGuide: readonly GuideSection[] = [
  {
    id: 'what',
    title: ['它是做什么的', 'What it does'],
    intro: [
      '每个月，生产、物资、财务、市场四个部门各交一张表。同一个客户、同一个项目，四张表的写法、列名、单位常常对不上，于是每月都有人手工核对。BridgeFlow 把四张表合成一张对得上的总表，把对不上的地方逐条列出来，再由 AI 按部门出结论。表格指标可以追溯到原表；代理发起的业务写入需要你在审批卡上确认。',
      'Every month, production, procurement, finance and marketing each hand in their own spreadsheet. The same customer or project is spelled differently, columns are named differently, units differ, so someone reconciles them by hand every month. BridgeFlow combines the four into one table that adds up, lists every place they disagree, and has AI agents review it department by department. Table metrics can be traced to their sources, and agent-initiated business writes require your approval on an approval card.',
    ],
  },
  {
    id: 'quick',
    title: ['五分钟上手', 'Five minutes to your first result'],
    intro: ['先用内置示例浏览表格和来源，不用准备文件，也不调用 AI。最后一步的 AI 研判是可选的，需要已配置的模型并产生费用。', 'Explore the built-in sample tables and sources without preparing files or calling AI. The final AI review step is optional, requires a configured model and incurs usage charges.'],
    steps: [
      ['在左侧「来源」里点「打开示例笔记本」。四份部门文件会自动导入。', 'In Sources on the left, choose Open sample notebook. Four department files are imported for you.'],
      ['点左侧任意一个文件，右侧会显示它的原始内容。', 'Choose any file on the left; its original content appears on the right.'],
      ['在右侧「工作室」点「本月任务」：这里写着本月还差什么、谁来处理。', 'In Studio on the right, choose This month’s tasks: it says what this month still needs and who handles it.'],
      ['再点「数据」→「跨部门总表」：四张表合成的一张表。打开「待确认事项」，能看到唯一一处对不上：生产部把一个客户名写短了。', 'Then choose Data → Cross-department master: the four files as one table. Open the open questions to see the one mismatch: production shortened a customer’s name.'],
      ['点表里任意一个数字，下面会显示它来自哪个文件、哪一行、哪一列。', 'Choose any figure in the table; below it you see which file, row and column it came from.'],
      ['想看 AI 研判（会调用模型、产生费用）：回到「本月任务」点「发起研判」，完成后报告出现在「产物」里，用时取决于模型和数据。', 'To see the AI review (it calls the model and costs money): go back to This month’s tasks and choose Start the review; the report appears under Artifacts when it finishes; timing depends on the model and data.'],
    ],
    note: ['想有人带着走？点右上角「帮助与引导」→「首次任务 · 整合与追溯」。', 'Prefer to be walked through? Choose Help & guided tours at the top right → First task · combine & verify.'],
  },
  {
    id: 'layout',
    title: ['认识界面', 'Finding your way around'],
    intro: ['页面分三栏，顶部一排按钮。', 'The page has three panes and a row of buttons along the top.'],
    points: [
      ['左栏「来源」：这个笔记本的部门文件。「添加来源」上传新文件；「打开示例笔记本」「更多示例」打开现成的示例；「笔记本用途」决定你看到哪些步骤。', 'Sources (left): this notebook’s department files. Add sources uploads new ones; Open sample notebook and More sample cases open ready-made examples; Notebook purpose decides which steps you see.'],
      ['中栏「对话」：和队长（AI）说话的地方。上方的「轨迹」显示每一步调用了什么工具，「业务状态」告诉你本月走到哪一步、下一步点哪里。', 'Chat (middle): where you talk to the captain (the AI). Above it, Trajectory shows each tool call step by step, and Business state tells you where the month stands and what to click next.'],
      ['右栏「工作室」：「总览」看全月，「本月任务」看待办，「数据」看表格和清洗，「本月结论」看研判结论，「记录」看谁在什么时候做了什么。下面的「其他工作区」有「报价工作区」「立项材料与候选」「填报与流转」。', 'Studio (right): Overview for the whole month, This month’s tasks for what is open, Data for tables and cleaning, Conclusions for the review’s findings, Records for who did what and when. Under Other workspaces: Quotation workspace, Discovery materials and opportunities, and Filling & handoff.'],
      ['顶部：「新建笔记本」「保存笔记本」「笔记本」（打开以前的）「退出笔记本」；「来源」「工作室」可以收起或展开两侧；「会话与设置」里有历史会话、模型、语言和这份说明书；「帮助与引导」打开分步引导。', 'Top bar: Create notebook, Save notebook, Notebooks (reopen an earlier one) and Exit notebook; Sources and Studio fold or unfold the side panes; Sessions & settings holds earlier sessions, the model, the language and this guide; Help & guided tours opens step-by-step tours.'],
    ],
  },
  {
    id: 'month',
    title: ['每个月怎么用', 'Your monthly routine'],
    intro: ['一个月分五步。任何时候不知道下一步，点对话上方的「业务状态」，最上面的「现在做什么」会写清楚。', 'A month has five steps. Whenever you are unsure what comes next, open Business state above the chat: What to do now at the top spells it out.'],
    steps: [
      ['交文件：左侧「添加来源」，选月份，为四个部门各选一份文件（xlsx 或 csv），导入。导入会自动清洗和核对，不调用 AI。没有模板？在「数据」页每个部门一行里点「下载本月模板」。', 'Add files: Add sources on the left, pick the month, choose one file per department (xlsx or csv) and import. Import cleans and checks everything itself, with no AI. No template? On the Data page, choose Download this month’s template on each department’s row.'],
      ['清理数据：打开「本月任务」。「待确认事项」里每一项都写着「怎么处理」，点「打开处理」直接去它的页面。拿不准就点「让队长给建议」。某个部门的文件有错，改好后在「数据」页该部门一行点「补传单个部门」，会生成新批次，旧批次保持不变。', 'Clean up: open This month’s tasks. Each open item says How to settle; Open to settle takes you to its page. Unsure? Ask the captain for a suggestion. If one department’s file is wrong, fix it and choose Replace one department’s file on its row of the Data page; that makes a new batch and leaves the old one as it was.'],
      ['研判：数据齐了，「本月任务」右上角的「发起研判」会亮起。点它，队长会同时派出生产、物资、财务、市场四个部门代理；在「轨迹」里能看到它们。完成后报告出现在「产物」里，用时取决于模型和数据。', 'Review: once the data is ready, Start the review lights up at the top right of This month’s tasks. The captain sends four department agents at once; you can watch them under Trajectory. The report appears under Artifacts when it finishes; timing depends on the model and data.'],
      ['处理结论：打开「本月结论」，从标红的结论看起。每条都写着公式、阈值和依据的单元格。决定怎么处理后，在对话里告诉队长，它会用审批卡记录你的决定。', 'Decide: open Conclusions and start with the flagged findings. Each shows its formula, threshold and source cells. Once you decide, tell the captain in the chat; it records your decision through an approval card.'],
      ['收口：回到「本月任务」，核对收口清单每一步都已完成；月度简报在「本月结论」里查看或下载，总表可以在「数据」→「跨部门总表」里「下载总表 xlsx」。', 'Close: back in This month’s tasks, check that every close step is done; read or download the monthly brief under Conclusions, and download the table with Download master xlsx under Data → Cross-department master.'],
    ],
  },
  {
    id: 'captain',
    title: ['和队长（AI）一起工作', 'Working with the captain (the AI)'],
    intro: ['队长是对话里的 AI 助手。它会查、会算、会给建议，但不会替你做决定，也不会自己读原始数据行。', 'The captain is the AI assistant in the chat. It looks things up, computes and suggests, but it never decides for you and never reads raw data rows itself.'],
    points: [
      ['可以直接问：“这个月还有哪些待办？每项给我建议”“生产量合计是多少”“对这个批次做一次四部门研判”“四象限图在哪”。问“在哪”时，它会写出点击路径，并直接打开右侧页面。', 'Ask it directly: "What is still open this month, and how would you settle each item?", "What is the total production volume?", "Review this batch across the four departments", "Where is the quadrant chart?". When you ask where something is, it lists the clicks and opens the page on the right.'],
      ['队长知道你在哪个笔记本：“这个批次”“这个月”指的就是当前笔记本的批次。', 'The captain knows which notebook you are in: "this batch" and "this month" mean the current notebook’s batch.'],
      ['队长发起业务写入时，会弹出审批卡。先核对卡上的值和出处；不同意就在「拒绝理由」里写明原因再点「拒绝」，队长会收到你的理由；同意就点「允许一次」。在你决定之前，什么都不会写入。', 'Business writes initiated by the captain come to you as approval cards. Check the values and where they came from; to refuse, write why in Rejection reason and choose Reject, and the captain hears your reason; to accept, choose Allow once. Nothing is written until you decide.'],
      ['它的建议都会标明是“模型建议”。拿不准时让它说出依据，依据应该能在表里找到。', 'Its suggestions are marked as model advice. When unsure, ask for its basis; the basis should be something you can find in the table.'],
    ],
  },
  {
    id: 'workspaces',
    title: ['其他工作区', 'Other workspaces'],
    points: [
      ['「报价工作区」：一张报价需要哪些事实、由谁提供、按声明公式怎么算价格带。缺依据时不会报价。', 'Quotation workspace: which facts a quote needs, who provides each, and how the price band is computed from declared formulas. Without the evidence, no quote is produced.'],
      ['「立项材料与候选」：部门材料、改进候选、流程图、「评分四象限」、会议和决策。点「载入示例项目」可以看一个完整例子。', 'Discovery materials and opportunities: department materials, improvement ideas, flow graphs, Rating quadrants, meetings and decisions. Choose Load the sample project to see a complete example.'],
      ['「填报与流转」：按已批准的立项范围填部门模板、审核、交给下一个部门。点「载入示例工作流」看示例。', 'Filling & handoff: fill department templates under the approved scope, review them and hand them to the next department. Choose Load the sample workflow to see an example.'],
    ],
    note: ['「填报与流转」和「立项」是全公司共享的，每个笔记本看到的都一样；来源、任务、数据、结论和产物才属于当前笔记本。', 'Filling & handoff and discovery are shared across the company, so every notebook sees the same records; sources, tasks, data, conclusions and artifacts belong to the current notebook.'],
  },
  {
    id: 'notebooks',
    title: ['笔记本与保存', 'Notebooks and saving'],
    points: [
      ['一个笔记本对应一次工作，比如“2024 年 7 月对账”。顶部标题可以直接改名，旁边显示「已保存」或「未保存」。', 'A notebook is one piece of work, such as "July 2024 reconciliation". Rename it in the title at the top; next to it you see Saved or Unsaved.'],
      ['「保存笔记本」后，可以在「笔记本」里重新打开，来源、批次和产物都会恢复。离开未保存的笔记本前会问你要不要保存。', 'After Save notebook, you can reopen it from Notebooks with its sources, batch and artifacts restored. Leaving an unsaved notebook asks whether to save first.'],
      ['「笔记本用途」（月度对账、报价、综合工作）决定这个笔记本显示哪些步骤和引导。', 'Notebook purpose (Monthly review, Quotation, Combined work) decides which steps and guidance the notebook shows.'],
    ],
  },
  {
    id: 'help',
    title: ['引导与示例', 'Tours and samples'],
    points: [
      ['右上角「帮助与引导」里有四条分步引导：「首次任务 · 整合与追溯」「深入了解 · 四部门研判」「深入了解 · 报价工作区」「深入了解 · 从立项到部门交接」。引导不会替你提交任何东西。', 'Help & guided tours at the top right has four step-by-step tours: First task · combine & verify, Explore · department review, Explore · quotation workspace, and Explore · from an idea to a handoff between departments. A tour never submits anything for you.'],
      ['左侧「更多示例」有三套故意放了不同问题的示例。打开后，在「本月任务」顶部点「带我走一遍这套示例」。', 'More sample cases on the left holds three samples, each with different problems planted on purpose. After opening one, choose Walk me through this sample at the top of This month’s tasks.'],
      ['引导卡住、提示「这一步在弹出的窗口后面」时，点「关闭窗口并继续」。', 'If a tour says This step is behind an open window, choose Close this window and continue.'],
    ],
  },
  {
    id: 'settings',
    title: ['设置', 'Settings'],
    points: [
      ['「会话与设置」里可以切换中文或英文。英文界面里，业务方的中文字段名旁边会显示英文名，比如 Customer name (客户名称)。', 'Sessions & settings switches between Chinese and English. In English, the business’s Chinese field names show an English name beside them, such as Customer name (客户名称).'],
      ['在这里选的模型会一直用下去，直到你改。研判提示“没有凭据”时，说明所选模型的密钥没有配置，换一个已配置的模型即可。', 'The model you choose here stays until you change it. If a review says a credential is missing, the chosen model has no key configured; pick one that does.'],
    ],
  },
  {
    id: 'faq',
    title: ['常见问题', 'Common questions'],
    faq: [
      [['「发起研判」是灰的？', 'Start the review is greyed out?'], ['先看按钮旁边的原因。数据未准备好时，照「本月任务」里的「待确认事项」处理；访客 AI 未开放时，需要管理员启用后才能研判。', 'Read the reason beside the button. If data is not ready, settle the open items in This month’s tasks. If guest AI is disabled, an administrator must enable it before you can run a review.']],
      [['研判报告标着「研判未完成」？', 'The report says Incomplete review?'], ['有部门没给出结论。打开报告看缺了哪些；能线下确认的写「人工复核意见」再点「交给队长复核」，数据有问题的改好文件后「补传单个部门」。', 'A department returned no findings. Open the report to see which; if it can be confirmed offline, write a Human review note and choose Send to captain; if the data is wrong, fix the file and use Replace one department’s file.']],
      [['上传后提示有列不认识？', 'Some uploaded columns are not recognised?'], ['在「业务状态」里点「打开列匹配」看候选，或点「让队长提出匹配」。批准的匹配在重新导入后生效。', 'In Business state choose Open column matches to see the candidates, or Ask the captain to propose matches. An approved match applies after the files are imported again.']],
      [['为什么有些值还是中文？', 'Why are some values still Chinese?'], ['公司名、项目名这类是数据本身，保持原样，方便和原表对照。', 'Company and project names are the data itself and stay as written, so you can match them to the original files.']],
      [['看不到飞书导入？', 'No Feishu import?'], ['飞书功能需要管理员配置集成并使用飞书登录。访客模式只能使用内置样例，不能上传文件；AI 功能默认关闭，是否可用由部署配置决定。', 'Feishu features require an administrator-configured integration and Feishu sign-in. Guest mode uses built-in samples, blocks file uploads and has AI disabled by default; availability depends on the deployment.']],
      [['数字会不会是 AI 编的？', 'Could the AI make numbers up?'], ['表格指标由系统按声明公式计算，研判结论需要通过数字与依据校验。但模型的文字回答和建议仍可能出错，请核对来源和口径后再采用。', 'Table metrics are computed from declared formulas, and review findings must pass numeric and evidence checks. Model-written answers and recommendations can still be wrong; verify their sources and assumptions before acting.']],
    ],
  },
  {
    id: 'terms',
    title: ['术语', 'Terms'],
    terms: [
      [['批次', 'Batch'], ['一次导入的四份部门文件。改文件会生成新批次，旧的保留。', 'One import of the four department files. Changing a file creates a new batch and keeps the old one.']],
      [['跨部门总表', 'Cross-department master'], ['按字典把四张表合成的一张表，每个单元格都有出处。', 'The four files combined into one table by the dictionary; every cell has a source.']],
      [['待确认事项', 'Open items'], ['需要人来决定的问题，比如各部门写法不一致。', 'Questions a person must decide, such as departments spelling something differently.']],
      [['口径', 'Convention'], ['字典没写清时按通用做法补上的规则，业务方确认后才算正式。', 'A common-practice rule used where the dictionary is silent; it counts as declared once the business confirms it.']],
      [['证据等级 G1–G4', 'Evidence grade G1–G4'], ['G1 直接来自原表，G2 按公式算出，G3 依赖未确认的口径，G4 是模型建议。', 'G1 read straight from a file, G2 computed by a formula, G3 resting on an unconfirmed convention, G4 model advice.']],
      [['审批卡', 'Approval card'], ['代理发起业务写入前的确认卡，由你选「拒绝」或「允许一次」。', 'The card shown before an agent-initiated business write; you choose Reject or Allow once.']],
      [['队长 / 部门代理', 'Captain / department agents'], ['队长是对话里的 AI；研判时它派出四个部门代理，每个只看本部门的指标。', 'The captain is the AI in the chat; for a review it sends four department agents, each reading only its own department’s metrics.']],
    ],
  },
]

/** The guide as Markdown in one language (docs/user-guide.{zh,en}.md). */
export function guideMarkdown(language: 'zh' | 'en'): string {
  const i = language === 'zh' ? 0 : 1
  const out = [`# ${guideTitle[i]}`, '', guideLead[i], '']
  out.push(language === 'zh' ? '> 由 `plugins/src/client/user-guide.ts` 生成（`pnpm --dir plugins docs:guide`），与产品内「会话与设置」→「使用说明书」同源。请改源文件，不要直接改本文件。' : '> Generated from `plugins/src/client/user-guide.ts` (`pnpm --dir plugins docs:guide`), the same source as Sessions & settings → User guide in the product. Edit the source, not this file.', '')
  for (const section of userGuide) {
    out.push(`## ${section.title[i]}`, '')
    if (section.intro) out.push(section.intro[i], '')
    if (section.steps) out.push(...section.steps.map((s, n) => `${n + 1}. ${s[i]}`), '')
    if (section.points) out.push(...section.points.map(p => `- ${p[i]}`), '')
    if (section.faq) for (const [q, a] of section.faq) out.push(`**${q[i]}**`, '', a[i], '')
    if (section.terms) out.push(...section.terms.map(([term, meaning]) => `- **${term[i]}**：${meaning[i]}`.replace('：', language === 'zh' ? '：' : ': ')), '')
    if (section.note) out.push(`> ${section.note[i]}`, '')
  }
  return out.join('\n')
}
