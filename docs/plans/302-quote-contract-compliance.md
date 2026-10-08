# #302 计划：报价单合同条款 + 全局法务要求 + Agent 逐条合规判断（演示版）

状态：已实现，待提交（2026-10-08 定：工期紧，首期只做**内置样板演示**；文本条款用**冻结的模型结论**；内置**两张**报价单；**样板数据全英文**）。
分支：`feature/quote-contract-compliance-302`

## 0. 现状（读代码结论）

- issue 提到的 `agents/quote_simulator.py` 是**旧路径**：`POST /quote` 在 `bridgeflow_enable_legacy_pipeline` 关闭时直接 403。不在它上面建。
- 真正的报价链路是 `documents.py`：字典 `quotation:` 声明 `DocumentContract`，`evaluate_document` 无 LLM、全有或全无出内部草稿；每个输入带 `SourceRef`。
  `evaluate_document` 没有 API 暴露；前端 `quotation.tsx` 是模板预览。**仓库里没有"报价单"实体。**
- `--demo` 的字典 `data/mock_business/demo/dictionary.yaml` 的 `quotation:` 与 `data/mock_business/quotation/dictionary.yaml` **完全相同** → 样板 BJ-2024-0715 在演示环境能直接出草稿。
  guest / demo_en / quotation_demo 的报价声明都不同。
- 演示环境模型是 `MockProvider`（"The demo must always run on this"），只会造最小合法实例 → 现场判文本条款没意义，用冻结结论。
- 合同范本 `02-混凝土供货合同范本.md` 没有责任上限、质保期、知识产权条款 → 天然的"无法判断 / 不合规"用例。

## 1. 范围

### 做
- 样板数据：法务要求 v1、两张报价单（各自询价、合同、结构化字段）、冻结的文本条款模型结论、人工逐条答案。
- 后端只读：`GET /quotation/cases`、`GET /quotation/cases/{id}`——报价草稿 + 合同条款 + 合规结果。
- 合规：规则层现场算（数值字段）+ 冻结模型结论**每次加载都经 host 校验** + 报价↔合同一致性。
- Agent 类 + 冻结脚本：以后换真模型重新生成结论。
- 前端：`quotation.tsx` 内展示两张单（切换），不新开页。

### 不做（首期砍掉）
报价单增删改、条款修订历史、上传/切分 UI、法务要求编辑/发布/审批、版本过期重检流程、权限范围、现场调模型、`quote_simulator.py`。
数据结构按完整版设计（`ContractTerms` / `LegalRequirement` / `RequirementResult`），以后加存储只是外面包一层。

## 2. 样板数据（`data/quote_compliance_demo/`，**全英文**，2026-10-08 定）

自成一套，不放 `data/demo_en/`（那里由 `make_english_samples.py` 生成，`--check` 会把手写文件判为过期）。
报价算术沿用 `data/demo_en/demo/dictionary.yaml`；中文原件 `data/mock_business/demo/dictionary.yaml` 公式相同。

| 文件 | 内容 |
|---|---|
| `quotes.yaml` | 样板入口：声明文件、法务要求、冻结结论路径；两张单的 id / 标题 / 客户 / 抽取记录 / 合同文件 / 结构化字段 |
| `legal-requirements.yaml` | 法务要求 `version: 1`：5 条要求 + 一致性映射 |
| `01-customer-enquiry-A.md` / `03-customer-enquiry-B.md` | 两张单的询价（B：同客户新项目，4000 m³，期望 440 CNY/m³，付款 75%） |
| `02-supply-contract-A.md` | A 单合同：标准范本（译自 `mock_business/quotation/02` 范本，无责任上限 / 质保 / 知识产权条款） |
| `04-supply-contract-B.md` | B 单合同：45 日付款 70%、违约金上限 30%、责任以合同额为限、质保 24 个月、知识产权条款 |
| `05-cost-and-capacity-basis.md` | 成本、产能、回款依据（与中文工作簿同数，写成文本） |
| `extraction-A.yaml` / `extraction-B.yaml` | 两张单抽取记录 |
| `clause-judgements.yaml` | 冻结的文本条款模型结论，记 `legal_version` + 合同 sha256 |
| `expected-compliance.md` | 人工逐条答案 |

两张单各自独立评估，**不互相扣减产能**（演示简化，README 注明）。

### 2.1 法务要求 v1

| id | 要求 | kind | 判定层 |
|---|---|---|---|
| `payment_days_max` | 付款账期不超过 60 天 | `field_max payment_days 60` | 规则 |
| `penalty_cap_max` | 供方违约金累计不超过合同总额 20% | `field_max penalty_cap_ratio 0.20` | 规则 |
| `no_unlimited_liability` | 不接受无限责任 | `field_in liability [capped]` | 规则 |
| `ip_clause_required` | 须含知识产权归属条款 | `clause_required` | 模型（冻结） |
| `warranty_clause_required` | 须含质保期条款 | `clause_required` | 模型（冻结） |

一致性：报价草稿 `payment_ratio` ↔ 合同 `monthly_payment_ratio`。

### 2.2 预期结果

| | BJ-2024-0715（范本合同） | BJ-2024-0718（B 合同） |
|---|---|---|
| 账期 ≤ 60 天 | 无法判断（合同只写"次月底前"，无天数） | 合规（45 日） |
| 违约金上限 ≤ 20% | 无法判断（无供方违约金上限） | **不合规**（30%） |
| 不接受无限责任 | 无法判断（无责任上限条款） | 合规（以合同总额为限） |
| 知识产权条款 | **不合规**（全文已录入，未见） | 合规（第六条） |
| 质保期条款 | **不合规**（第五条只有质量标准） | 合规（5.2） |
| 付款比例一致性 | 无法判断（合同写"比例见报价单"） | **不一致**（报价 75% vs 合同 70%） |
| 总体 | 不合规 | 不合规 |

## 3. 后端（新 `quote_compliance.py`）

- **条款切分**：读合同 md，`## Article N 标题`（或 `## 第N条`）为条；条内 `N.M ` 开头的行为子条款（id `N.M`），没有子条款则整条为一款（id `N`）。
- **结构化字段**：`{value, clause, excerpt}`，加载时校验 clause 存在、excerpt 是该款原文逐字子串、数值可解析、比例在 0–1、`liability ∈ {capped, unlimited}`。不合法 → 503。
- **报价草稿**：按抽取记录打开原件取片段/单元格构造 `SourceRef`（核对原文与数值），用**当前字典**的 `quotation` 跑 `evaluate_document`。
- **门槛**：当前字典 `quotation` 的**算术形状**（输入键、公式、检查、输出；不含标题/单位）≠ 样板声明 → `status: not_applicable`，页面照旧显示模板预览。中文 `--demo` 与英文 guest 字典形状相同，都显示。
- **规则层**：字段缺失 → `undetermined / missing_field`；`field_max` / `field_min` 闭区间；依据 = 字段的 clause + excerpt。
- **冻结结论校验**（仿 `validate_role`，逐条降级不整单失败）：
  - 结论的 `legal_version` 或合同 sha256 与当前不符 → 全部 `undetermined / judgement_stale`。
  - 未知 / 重复 requirement_id 丢弃；缺的那条 `undetermined / judgement_missing`。
  - 引用的款不存在或 excerpt 不是原文子串 → `undetermined / model_rejected`。
  - `compliant` 必须 ≥1 条引用；`clause_required` 的 `non_compliant` 仅在合同 `complete: true` 时允许，否则 `undetermined / clause_absent_terms_incomplete`。
  - `explanation` 为空、超 240 字或含数字 → `model_rejected`。
- **一致性**：草稿被拒 → 全部 `undetermined / quote_draft_refused`；任一侧缺 → `undetermined`；Decimal 相等 → `consistent`，否则 `inconsistent`。
- **总体**：任一要求 `non_compliant` 或任一一致性 `inconsistent` → `non_compliant`；否则有 `undetermined` → `undetermined`；否则 `compliant`。固定附文案"仅供参考，不替代法务审核"。
- `config.quotation_cases_path` 默认指向样板 `quotes.yaml`（同 `demo_cases_path` 的做法）；置空 → `not_applicable`。

## 4. Agent（`agents/contract_compliance.py`）+ 冻结脚本

- packet：`clause_*` 要求（id / title / topic / guidance）+ 本单全部条款 + `complete`。不给价格、不给其它单。
- 输出 `ClauseJudgements{judgements: [ClauseJudgement]}`，与冻结文件同结构。
- `scripts/freeze_clause_judgements.py`：对样板每张单跑 Agent，经同一校验报告被拒条目，写 `clause-judgements.yaml`（记 provider、时间、法务版本、合同 sha256）。provider 为 `mock` 时拒绝运行。
- 初版冻结结论由开发时的 Claude 按同一 packet 生成、人工核对，文件头注明。

## 5. 前端

- `quotation.tsx`：`/quotation/cases` 为 `available` 时，模板预览上方加报价单切换（两张）。每张显示：
  - 报价草稿：价格带数字、检查结果（关注项标出）。
  - 合规检查：总体徽章、逐条（状态、要求 + 出处、合同原文引用、修改建议、判定来源 规则/模型），`non_compliant` 高亮，`undetermined` 单独颜色。
  - 一致性：两边值 + 出处。
  - 合同条款（折叠）：逐款原文。
  - 注明"法务要求 v1"与"文本条款为预生成的模型结论，仅供参考，不替代法务审核"。
- 文案进 `ui.ts`；后端 reason code 在前端映射为文字；`user-guide.ts` 报价章节补一段，跑 `pnpm --dir plugins docs:guide`。

## 6. 测试（`backend/tests/test_quote_compliance.py`）

- 两张单结果 == `expected-compliance.md`（§2.2 表逐格）。
- 两张单条款互不串（验收 1）；结果带 `legal_version`（验收 2）；每条都有结论，缺字段 / 未全文录入时缺条款 → `undetermined`（验收 3）。
- 冻结结论：伪造 excerpt、`compliant` 无引用、文字含数字、法务版本不符、合同被改 → 对应降级。
- 字段 excerpt 不在原文 → 加载失败。
- 字典不同 → `not_applicable`。
- API：列表与详情 200，未知 id 404。
