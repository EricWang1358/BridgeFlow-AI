# E14 — 月度流程便民：进度、模板、自检、补传与待办

# E14 — Monthly workflow convenience: progress, templates, self-check, corrections and inbox

需求来源 / Sources: [2026-09-17 需求盘点 / requirements review](00-foundations.md#1-进展盘点三个视角--progress-review-from-three-perspectives)；[#140](https://github.com/EricWang1358/BridgeFlow-AI/issues/140) 飞书文件；[#144](https://github.com/EricWang1358/BridgeFlow-AI/issues/144) 补问与交接。

基线 / Baseline: `692d3d5`, reviewed 2026-09-17. [状态规则 / Status rules](README.md)；[角色、非功能需求与呈现规范 / Actors, quality attributes and presentation standards](00-foundations.md)；[类设计 / Class design](class-design.md)。

## 目标与角色 / Goal and actors

让每个月重复的对账工作少走弯路：汇总负责人一眼看到进度，员工拿到预填模板、提交前自检，出错只补一个部门，所有待确认事项集中到各自的收件箱，飞书文件夹一次导入。
主要角色：部门填报员（A01）、部门负责人（A02）、月度汇总负责人（A03）、字典与标准维护人（A05）。

Remove the repeated friction of each monthly close: visible progress, prefilled templates with self-check, single-department corrections, one inbox per owner and one-step Feishu folder import. Actors: Department contributor (A01), Department owner (A02), Monthly consolidation lead (A03), Dictionary and standards steward (A05).

便民不放宽约束：自检与补传仍走与正式导入相同的声明与拒绝规则；沿用上月的值只是预填建议，提交时仍要本人确认；收件箱只聚合，不替人决定。

Convenience never relaxes constraints: self-check and corrections use the same declarations and refusals as import; carried-over values are suggestions the contributor confirms; the inbox aggregates and never decides.

## UC 索引 / UC index

| UC | 中文 / English | Status | 优先级 / Priority |
| --- | --- | --- | --- |
| E14-UC01 | 月度对账进度清单 / Monthly close checklist | PARTIAL | Must |
| E14-UC02 | 模板下载与上月预填 / Template download with carry-over | DESIGNED | Should |
| E14-UC03 | 提交前自检 / Self-check before submission | PARTIAL | Must |
| E14-UC04 | 单部门补传生成新版本 / Replace one department's file as a new version | DESIGNED | Must |
| E14-UC05 | 待确认事项收件箱 / Open-item inbox by owner | DESIGNED | Should |
| E14-UC06 | 飞书文件夹批量导入 / Import from a Feishu folder | DESIGNED | Could |

## E14-UC01 — 月度对账进度清单 / Monthly close checklist

**Status: PARTIAL**

### 中文需求与验收

- 参与者：月度汇总负责人（A03）。
- 触发：进入新月份，汇总负责人需要知道对账走到哪一步、还差谁什么。
- 前置：月份已选定；声明了本月需要的部门文件与步骤（导入、待确认清零、研判、结论、导出）。
- 主流程：
  1. 汇总负责人打开某月份的进度清单。
  2. 系统按声明步骤显示状态：每个部门文件是否已交、是否通过自检、是否被隔离；总表待确认数；研判状态；结论页与报告是否生成。
  3. 每个未完成步骤显示负责人角色与下一步按钮，例如「提醒生产部补交」「打开待确认事项」。
  4. 所有必需步骤完成后，清单显示「本月可结账」，并记录完成时间。
- 异常：步骤状态读取失败时显示「状态未知」，不显示为完成；声明中没有的步骤不出现。
- 验收：
  - AC-1 Given 2024-07 只导入了三个部门 When 打开进度清单 Then 显示「市场部未提交」，研判步骤不可发起，并说明原因。
  - AC-2 Given 总表有 1 条客户名称不一致 When 查看清单 Then「待确认清零」步骤未完成，显示 1 条并可跳转处理。
  - AC-3 Given 研判状态接口超时 When 打开清单 Then 研判步骤显示「状态未知」，整体不显示「可结账」。
- 后置：清单是只读投影；完成记录绑定批次与报告版本。
- 依赖：E04-UC01、E06-UC03、E07-UC06、E13-UC01、E14-UC05。
- 当前证据与缺口：批次弹窗已有「下一步」提示与笔记本状态指引（[workspace.tsx](../../plugins/src/client/workspace.tsx) `NEXT_STEP`、[state.tsx](../../plugins/src/client/state.tsx)）；没有按月、按部门的步骤清单与完成记录。

### English requirements and acceptance

- Actors: Monthly consolidation lead (A03).
- Trigger: a new month starts and the consolidation lead needs progress and who still owes what.
- Preconditions: a period is selected; required department files and steps are declared.
- Main flow: open the period checklist; show declared step states (files submitted, self-checked or quarantined, open items, review, brief, export); each incomplete step names its owner role and next action; when all required steps are done, show “ready to close” with a timestamp.
- Exceptions: unreadable states show “unknown”, never done; undeclared steps do not appear.
- Acceptance: AC-1 a missing marketing file blocks review with a reason; AC-2 one open disagreement keeps the step open with a link; AC-3 an unknown review state prevents “ready to close”.
- Postcondition: read-only projection; completion bound to batch and report versions.
- Evidence and gap: next-step hints and notebook status guidance exist; no per-month, per-department checklist or completion record.

## E14-UC02 — 模板下载与上月预填 / Template download with carry-over

**Status: DESIGNED**

### 中文需求与验收

- 参与者：部门填报员（A01）、字典与标准维护人（A05）。
- 触发：部门员工每月要填同一张模板，且部分字段可沿用上月。
- 前置：部门模板有批准版本；声明了哪些字段可从上期沿用及沿用规则（例如本月「上月实际量」取上期「实际量」）。
- 主流程：
  1. 员工在工作面选择月份与部门，下载模板。
  2. 系统生成当前批准版本的工作簿：表头与版本号；可沿用字段按声明预填上期值，单元格标注「预填自 2024-06，请核对」；必填字段标记；填写说明页列出字段含义、单位与示例。
  3. 员工填写后按 E14-UC03 自检、提交。
- 异常：上期批次不存在或上期该值被隔离时，不预填并在说明页注明原因；模板没有批准版本时拒绝下载。
- 验收：
  - AC-1 Given 2024-06 批次中项目 PRJ2024011 的实际量为 5,650.0 When 下载生产部 2024-07 模板 Then 该项目「上月实际量」预填 5,650.0，并有「预填自 2024-06」标注。
  - AC-2 Given 没有 2024-06 批次 When 下载 2024-07 模板 Then 不预填任何沿用字段，说明页写明「无上期批次」。
  - AC-3 Given 下载的模板 When 读取表头 Then 与该部门批准模板版本逐列一致，并包含版本号。
- 后置：下载记录模板版本与预填来源批次；预填值在导入时仍按普通单元格校验。
- 依赖：E02-UC02（模板版本）、E04-UC01、E14-UC03。
- 当前证据与缺口：业务方模板以文件形式存在于 [data/company_templates/source](../../data/company_templates/source)；没有下载入口、沿用声明与预填。

### English requirements and acceptance

- Actors: Department contributor (A01), Dictionary and standards steward (A05).
- Trigger: staff fill the same template monthly and some fields carry over from last month.
- Preconditions: an approved template version; declared carry-over rules (e.g. this month's “previous actual” from last month's “actual”).
- Main flow: choose period and department; download a workbook with the approved headers and version, carry-over fields prefilled and annotated “prefilled from 2024-06, please verify”, required fields marked and an instructions sheet with meanings, units and examples; then self-check and submit.
- Exceptions: no prior batch or a quarantined prior value means no prefill with the reason stated; no approved version refuses the download.
- Acceptance: AC-1 PRJ2024011 previous actual prefilled 5,650.0 with annotation; AC-2 no prior batch means no prefill with a note; AC-3 headers match the approved version.
- Postcondition: downloads record template version and prefill source; prefilled values are validated like any cell at import.
- Evidence and gap: business templates exist as files; no download, carry-over declaration or prefill.

## E14-UC03 — 提交前自检 / Self-check before submission

**Status: PARTIAL**

### 中文需求与验收

- 参与者：部门填报员（A01）。
- 触发：员工提交前想先知道文件能不能被系统接受。
- 前置：部门与月份已选定；使用与正式导入相同的字典、模板版本与工作表声明。
- 主流程：
  1. 员工上传文件到「自检」，不创建批次。
  2. 系统运行与导入相同的检查：工作表与表头位置、必填列、连接键、数字与日期格式、字典公式核对、同键多行汇总规则。
  3. 结果按「必须修改」「建议核对」「通过」分组，每条给出行号、列名与原因，不回显无关单元格内容。
  4. 全部「必须修改」清零后，提供「正式提交」一步完成导入。
- 异常：自检结果与正式导入结果不一致视为缺陷，而不是可接受的差异。
- 验收：
  - AC-1 Given 物资部 v1 模板（表头上方有合并标题行） When 自检 Then「必须修改」列出「表头不在第 1 行，疑似第 2 行」，并提示在表格位置中填写。
  - AC-2 Given 市场部表「可争取」填了「待定」 When 自检 Then 列出行号与列名「可争取：不是数字」。
  - AC-3 Given 同一文件 When 分别自检与正式导入 Then 两者报告的必须修改项完全一致。
  - AC-4 Given 自检完成 When 查看批次列表 Then 没有新增批次。
- 后置：自检结果按配置声明的保留期限保存，到期删除，不保存文件本身；正式提交走 E04-UC01。
- 依赖：E04-UC02、E04-UC03、E06-UC03、NFR01。
- 当前证据与缺口：导入时已有明确拒绝原因（[batches.py](../../backend/src/bridgeflow/api/batches.py) 工作表、表头、公式缓存；[integration.py](../../backend/src/bridgeflow/integration.py) 缺列、非数字、不一致）；只能在创建批次时得到，员工无法单独自检，也没有分组与「正式提交」。

### English requirements and acceptance

- Actors: Department contributor (A01).
- Trigger: a staff member wants to know before submitting whether the file will be accepted.
- Preconditions: department and period chosen; the same dictionary, template version and sheet declarations as import.
- Main flow: upload for self-check without creating a batch; run the same checks as import (sheet and header, required columns, keys, number and date formats, formulas, roll-up rules); group results as must-fix, review or pass with row, column and reason, without echoing unrelated cells; once must-fix items are clear, submit in one step.
- Exceptions: any disagreement between self-check and import results is a defect, not an accepted difference.
- Acceptance: AC-1 v1 procurement title row flagged; AC-2 text in a number column located; AC-3 self-check and import agree exactly; AC-4 no batch created.
- Postcondition: results are kept for a configured retention period and then deleted; the file itself is not kept; submission uses E04-UC01.
- Evidence and gap: explicit refusal reasons already exist at import time; there is no separate self-check, grouping or one-step submission.

## E14-UC04 — 单部门补传生成新版本 / Replace one department's file as a new version

**Status: DESIGNED**

### 中文需求与验收

- 参与者：月度汇总负责人（A03）、部门填报员（A01）。
- 触发：批次导入后只有一个部门的文件需要更正。
- 前置：原批次已冻结；补传文件属于同一月份与部门，通过 E14-UC03 自检。
- 主流程：
  1. 汇总负责人或该部门填报员选择原批次与部门，上传更正文件。
  2. 系统派生新批次：其余三个部门沿用原批次的来源与清洗结果，被替换部门重新导入；新批次记录派生来源与替换原因。
  3. 重新生成总表，并展示新旧批次差异：新增、消失与变化的单元格数，以及受影响的待确认事项。
  4. 已有研判报告绑定旧批次，标为「数据已更新，可重新研判」。
- 异常：月份或部门不一致时拒绝；原批次不存在或无权访问时返回 404；补传文件与原文件摘要相同时提示「文件未变化」，不派生。
- 验收：
  - AC-1 Given 2024-07 批次中生产部客户名写了简称 When 补传更正后的生产部文件 Then 生成新批次，总表客户名称不一致从 1 条变为 0 条，其余三部门来源摘要与原批次相同。
  - AC-2 Given 原批次 When 派生完成 Then 原批次、其总表与报告均未改变。
  - AC-3 Given 补传文件与原文件逐字节相同 When 提交 Then 提示「文件未变化」，不创建新批次。
  - AC-4 Given 补传的是 2024-06 的文件 When 提交到 2024-07 批次 Then 拒绝并说明月份不一致。
- 后置：新旧批次形成版本链；进度清单与收件箱改用最新批次。
- 依赖：E04-UC01、E14-UC03、E06-UC02、E07-UC06。
- 当前证据与缺口：隔离行处置已有派生批次机制（[quarantine.py](../../backend/src/bridgeflow/quarantine.py)，同一处置重复应用返回同一派生批次），可复用；没有按部门替换来源的派生。

### English requirements and acceptance

- Actors: Monthly consolidation lead (A03), Department contributor (A01).
- Trigger: after import only one department's file needs correcting.
- Preconditions: the original batch is frozen; the replacement matches period and department and passes self-check.
- Main flow: choose batch and department and upload the corrected file; derive a new batch reusing the other departments' sources and cleaning, reimporting only the replaced department, recording lineage and reason; rebuild the master and show a diff of added, removed and changed cells and affected open items; mark reports bound to the old batch “data updated, review again”.
- Exceptions: period or department mismatch is refused; an unknown or unauthorized batch returns 404; an identical file reports “unchanged” without deriving.
- Acceptance: AC-1 correcting production clears the disagreement while other sources keep their digests; AC-2 the original batch, master and report are unchanged; AC-3 an identical file derives nothing; AC-4 a wrong-period file is refused.
- Postcondition: batches form a version chain; checklist and inbox follow the latest.
- Evidence and gap: quarantine disposal already derives idempotent batches and can be reused; per-department replacement does not exist.

## E14-UC05 — 待确认事项收件箱 / Open-item inbox by owner

**Status: DESIGNED**

### 中文需求与验收

- 参与者：部门负责人（A02）、月度汇总负责人（A03）。
- 触发：待确认事项分散在总表、隔离行、列匹配和填报草稿里，没人知道自己该处理什么。
- 前置：各模块的待确认事项带有声明的负责角色或部门；访问范围按 E09 授权。
- 主流程：
  1. 用户打开「我的待办」。
  2. 系统聚合本人有权处理的事项：总表不一致与公式不符、隔离行、待审批列匹配、填报草稿补问、出处缺失、过期结论；每项显示来源模块、所属批次、负责角色、创建时间与处理入口。
  3. 可按月份、部门、类型筛选；点击后跳到原模块处理。
  4. 事项在原模块处理完成后自动从收件箱消失。
- 异常：收件箱不提供替原模块决定的按钮；无权访问的事项不出现，也不计入总数。
- 验收：
  - AC-1 Given 2024-07 批次有 1 条客户名称不一致、2 行隔离、1 个待审批列匹配 When 汇总负责人打开待办 Then 显示 4 项，类型与数量正确。
  - AC-2 Given 生产部负责人 When 打开待办 Then 只看到指派给生产部的事项，总数只计可见项。
  - AC-3 Given 隔离行在隔离模块被放行 When 刷新待办 Then 该事项消失。
  - AC-4 Given 收件箱中的任意事项 When 查看可用操作 Then 只有「打开处理」，没有批准或拒绝按钮。
- 后置：收件箱是事件投影，不保存独立的处理状态。
- 依赖：E06-UC03、E04-UC06、E05-UC03、E02-UC04、E09-UC05、E13-UC06。
- 当前证据与缺口：各模块分别有待确认计数（总表 issues、隔离行、`column_questions`、填报草稿待补项）；没有跨模块聚合与按负责人过滤。

### English requirements and acceptance

- Actors: Department owner (A02), Monthly consolidation lead (A03).
- Trigger: open items are scattered across modules and nobody knows what is theirs.
- Preconditions: items carry declared owner roles or departments; access follows E09.
- Main flow: open “My items”; aggregate authorized items (master disagreements and formula mismatches, quarantined rows, pending column matches, filling clarifications, missing provenance, stale briefs) with source module, batch, owner, time and a link; filter by period, department and type; items disappear once handled in their module.
- Exceptions: the inbox never decides on a module's behalf; unauthorized items are neither shown nor counted.
- Acceptance: AC-1 four items of the right types; AC-2 department scoping including counts; AC-3 released rows disappear; AC-4 only “open” actions.
- Postcondition: the inbox is an event projection without its own handling state.
- Evidence and gap: each module has its own open-item counts; no cross-module aggregation or owner filtering.

## E14-UC06 — 飞书文件夹批量导入 / Import from a Feishu folder

**Status: DESIGNED**

### 中文需求与验收

- 参与者：月度汇总负责人（A03）、外部系统（S03）。
- 触发：部门文件都放在一个飞书文件夹里，逐个选择太慢。
- 前置：飞书快捷调用已配置并通过实测（E02-UC10）；文件命名或文件夹结构声明了部门识别规则。
- 主流程：
  1. 用户选择飞书文件夹与月份。
  2. 系统列出文件夹中的表格文件，按声明规则识别部门，展示「识别结果与未识别文件」供确认。
  3. 用户确认后，一次原生审批导入全部已识别文件，走 E14-UC03 自检与 E04-UC01 导入。
- 异常：一个部门匹配到多个文件时要求用户选择；未识别文件不导入；凭据未配置时返回「未配置」。
- 验收：
  - AC-1 Given 模拟租户文件夹中有「生产部-2024-07.xlsx」等四个文件 When 选择该文件夹 Then 四个部门全部识别，一次审批后生成一个批次。
  - AC-2 Given 文件夹里有两个物资部文件 When 识别 Then 物资部标为「需要选择」，未选择前不能导入。
  - AC-3 Given 未配置飞书凭据 When 打开文件夹导入 Then 显示「未配置」，不显示空列表。
- 后置：批次来源记录飞书文件 token 与文件名。
- 依赖：E02-UC10（真实联调受外部凭据阻塞）、E14-UC03、E09-UC01。
- 当前证据与缺口：飞书按文件 token 下载与导入已实现（[feishu.py](../../backend/src/bridgeflow/feishu.py)、[feishu_tools.py](../../backend/src/bridgeflow/api/feishu_tools.py)，一次最多 4 个文件）；没有列出文件夹与按规则识别部门。

### English requirements and acceptance

- Actors: Monthly consolidation lead (A03), External system (Feishu, target API) (S03).
- Trigger: department files sit in one Feishu folder and picking them one by one is slow.
- Preconditions: Feishu shortcuts configured and verified (E02-UC10); declared department recognition rules.
- Main flow: choose folder and period; list spreadsheet files and recognise departments, showing recognised and unrecognised files; after confirmation, import all recognised files under one native approval through self-check and import.
- Exceptions: several files for one department require a choice; unrecognised files are not imported; missing credentials report “not configured”.
- Acceptance: AC-1 four files recognised and imported under one approval; AC-2 duplicates need a choice; AC-3 unconfigured shows “not configured”.
- Postcondition: batch sources record Feishu tokens and names.
- Evidence and gap: token-based download and import of up to four files exist; folder listing and recognition do not.

## Epic 数据与实现设计 / Epic data and implementation design

对象、模式与时序见 [class-design.md](class-design.md) 第 3 节。要点：进度清单与收件箱是事件投影（CQRS 读模型）；自检与正式导入共用同一条检查链，保证 AC「两者一致」；补传是不可变批次上的派生命令，复用隔离处置的幂等派生；模板预填是由批准模板版本和上期批次生成工作簿的工厂。

See class-design.md §3. The checklist and inbox are event projections (CQRS read models); self-check and import share one check chain so their results cannot diverge; replacement is a derive command over immutable batches reusing the idempotent quarantine derivation; template prefill is a factory from an approved template version and the prior batch.

建议实施顺序：E14-UC03（共用检查链，收益最大）→ E14-UC04 → E14-UC01 → E14-UC05 → E14-UC02 → E14-UC06。

Suggested order: UC03 (shared check chain, highest payoff), UC04, UC01, UC05, UC02, UC06.

## 发布与状态维护 / Release and status maintenance

每实现一个 UC，先跑主流程与每条拒绝路径的行为测试，再同步更新本文件索引、UC 正文状态、实现路径与剩余缺口，以及 [README](README.md) 的状态汇总与 [追溯矩阵](traceability.md)。界面改动需要浏览器旅程；真实业务验收单独记录。

For each delivered UC, run behavioral tests for the main flow and every refusal path, then update this index, the UC body, README totals and the traceability matrix together. UI changes need a browser journey; real business acceptance is recorded separately.
