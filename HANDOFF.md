# 交接说明

**更新于 2026-09-06。** 本文独占**易变状态**：当前进度、怎么把它跑起来、下一步、已知缺陷。

分工（见 [`docs/README.md`](docs/README.md)）：硬约束在 [`CLAUDE.md`](CLAUDE.md)，
架构决策在 [`docs/13-golden-standard.md`](docs/13-golden-standard.md)，
**所有实测数字在 [`docs/00-status.md`](docs/00-status.md)——本文引用，不复写**。

**情况变化后请更新本文**，但不要把内容抄回上面三处。

---

## 一句话现状

**能跑，但没有上传界面。** 四部门 CSV 进去、对齐后的 Master Table 加风险发现出来，
整条链路真实可用；唯一存在的图形界面是审批控制台。rubric 7 项中 2 项达标
（第 1、第 4），逐条比对见 `docs/00-status.md` 第五节。

第一周除两条等业务方外全部完成，第二周进行中。

---

## 怎么把它跑起来

### 启动

```bash
source ~/Hackathon2026/.venv/bin/activate
source ~/Hackathon2026/BridgeFlow-AI/env.sh      # DSH_* 只能由启动 shell 导出
cd ~/Hackathon2026/BridgeFlow-AI/backend
uvicorn bridgeflow.api.main:app --port 8000
```

浏览器开 <http://127.0.0.1:8000/console> 并**留着别关**。任何要写入的动作都会停在那里
等人；没人看着就是拒绝，不是放行。

### 三件今天就能做的事

**一、跑一整个月的四部门对账**（⚠️ **真实计费**，实测 2m25s）

```bash
cd data/samples
curl -X POST localhost:8000/analyze \
  -F period=2025-11 \
  -F departments=production  -F files=@production_2025-11.csv \
  -F departments=procurement -F files=@procurement_2025-11.csv \
  -F departments=finance     -F files=@finance_2025-11.csv \
  -F departments=marketing   -F files=@marketing_2025-11.csv \
  -o /tmp/analyze.json
```

回来的是 `clean_tables` / `graph` / `master_table` / `risk_report` 四段。
实测这一次：**33 条清洗修正、0 条隔离、15 个实体、1 条已确认关系、6 条待裁决、
9 行 Master Table、6 条发现、8 处张力、1 张卡片**。

结果落在 `data/outputs/2025-11.json`，历史版本在 `data/outputs/versions/`——
已发布的批次不会被静默重算（FR 11）。

> ⚠️ **上面那组数和那份落盘结果都是修复前产出的，里面带着两个已知错误**：
> `material_spend` 报的 13,540 是把一整列**单价**加起来当支出（PR #91 修，真值 117,250
> 且第四张 PO 没价、因此这个月没有可辩护的总额）；Master Table 那 9 行里 `SKU-A1` 因两种
> 拼法占了 2 行、`RM-Alu-6061` 三张 PO 只剩最后一张（PR #93 修）。
> **重跑才会反映出来**——重跑真实计费；而且 #79（`2025-03`）没修，重跑它还在。

**二、问一个能被追回单元格的数字**（不计费，纯规则）

```bash
curl -X POST localhost:8000/tools/aggregate-metric \
  -H 'content-type: application/json' \
  -d '{"metric":"total_output","period":"2025-11","department":"production"}'
```

`4030 units`，并附上它加了哪几个单元格。`list-metrics` 列出当前字段字典**支持**的全部
指标——问一个没声明的指标会 409 拒绝，不会编一个数出来。

**三、让 agent 停下来等你批**（⚠️ 真实计费，约 4 秒）

控制台开着，跑一次会调 `confirm_mapping` 的 turn。它会停住，控制台出现待确认，
点「允许一次」或「拒绝」。批准则映射写入 `data/outputs/mappings.json` 并带上
`authorised_by`；拒绝则文件不动。**拒绝时在理由框里写一句**——那句话会原样进模型收到的
拒绝文本，并由它复述出来（#94）；这一拍现在有了可看见的后果。**两条路径都在真实运行时上量过**
（`docs/00-status.md` 第五节）。

### 你现在**做不到**的事

| 想做的 | 现状 |
| --- | --- |
| 网页上传 XLS | **没有上传界面**，只能走 `curl`（#40 第三周） |
| 看实体图并点确认 | 确认能做（控制台），**图没有**（#40） |
| 看 Master Table 的表格视图 | 只有 JSON |
| 真实 XLS（多 sheet / 表头不在第一行 / 合并单元格） | **未验证**（#47） |
| 报价模拟 | 价格带是模型断言的，不是算出来的（#7），**演示时建议整拍砍掉** |
| 处理被隔离的行 | 没有接口（#88），而且样本里 `0 quarantined`，这条路径从没被走过 |

---

## 做完了什么

**第一周**（除两条外全完成）：#4 #13 #14 #16 #26 #27 #28 #32 #37 #42 #44 #45 #51 #58 #59 #65 #67
剩 #23、#75——都在等业务方，不是开发问题。

**第二周**（进行中）：#12 #18 #29 #30 #39 #79 已做：#91 #93（算术，见下）

按能力说，这些加起来是：

- **工具真的到达 Python**：`defineTool` 在 TypeScript，函数体在 pandas，中间走 HTTP
- **拒绝真的发生**：字段字典没声明的东西，一律 409，不猜
- **人真的能介入**：批准 / 拒绝 / 无人应答，三条路径都实测过
- **注入真的被挡**：`ctx.tools.guard()` 是单调拒绝，后面的监听器翻不了案
- **记忆真的跨月**：确认过的映射下个月不再问，证据变了会重新问
- **算术真的对过**：Master Table 现在按实体身份 join、按字典声明的口径折叠多行
  （#93）；支出按声明派生而不是把单价列当金额列加（#91）。两处都是**证据齐全、
  单元格可回溯、数字仍然错**那一类——`rollups` 缺声明就拒绝整张表，不猜

---

## 下一步

### 建议顺序

1. **#89 —— evaluator 反复请求不存在的指标。** 一次 `/analyze` 运行内 `aggregate_metric`
   被全拒（次数以 [`docs/00-status.md`](docs/00-status.md) 第四节为准，不在这里复写）。
   拒绝机制工作得很好，代价是时间和钱。**注意 409 已经写着「Call list_metrics」而模型
   十几次没听**，所以修法是把候选指标名**内联进错误体**，不是再补一句提示。
2. **#87 里那条分钟级的** —— 控制台标一行「此记录为声明，非认证身份」。
   评委看到我们自己标边界，比看到一个假装严谨的字段强。
3. **#79 —— 月度轴。** 实测 Master Table 里出现了 `2025-03` 这个期间：`03/11/2025`
   被读成 3 月 11 日。行里带着 `period_from` 解释了原因，**但没人被挡住**。
4. **#92（新开）—— 财务格把销售与成本净成一个数。** #93 之后暴露的，要等真实科目表。
5. **#82 / #46 —— 映射记忆的入口。** 记忆能用，但没有产生记忆的界面。

**刚做完**：#91 支出按声明派生（不再加单价列）、#93 Master Table 按实体身份 join 并按
`rollups` 折叠、#94 拒绝的理由进入模型叙述（就是原来的 #86）。

### 第二周剩下的

#5 #38 #46 #47 #55 #61 #63 #69 #72 #77 #82 #84 #87 #88（#86 已由 #94 关闭）

看板：<https://github.com/users/EricWang1358/projects/1>

---

## 已经确认过、不要再试的事

| 事实 | 出处 |
| --- | --- |
| DeepSeek 直连**不支持** `response_format: {"type":"json_schema"}` | 实测报 `This response_format type is unavailable now`，改用 `json_object` |
| 可用 model id：`deepseek-v4-flash` / `deepseek-v4-pro` / `deepseek-v4-flash-vision-exp` | `GET https://api.deepseek.com/models` |
| `DeepSeekHarnessConfig` **没有任何工具/权限开关** | 工具集归 profile bundle 管，用 `--patch` 改 |
| `deepseek_base_url` 的默认值不能放 `settings` | 它同时喂给 dsh，dsh 把显式 base URL 当覆盖 |
| **审批的可应答接缝是 Host 侧 cordis waterfall** | `ctx.on('approval/request', (req, next) => …)`。`dsh-client-ui-approval` 只是 `web` profile 的浏览器插件，**headless 不需要换 profile** |
| `permission-presets` **不控制工具册**，`sandbox` 只管写不管读 | `docs/13` §7，四条先前假设已证伪 |
| `workflow` 跑的是**模型写的**脚本，自称「containment, not a security boundary」 | 同上。这是我们**主动拒绝**的东西，不是缺的能力 |
| `.env` 里放 `DSH_*` 会被 dsh 拒绝 | 这是安全边界，不要绕 |

---

## 已知缺陷

按「演示当天会不会咬人」排：

1. **拒绝之后模型说 `done`**（#86）——**最会咬人的一个**，见上。
2. **13 次 409 的指标循环**（#89）——不影响正确性，影响时间和钱。
3. **歧义日期没人被挡住**（#79）——`03/11/2025` 变成 2025-03，行里有解释但流程不停。
4. **`quoted_price` 的价格带是模型断言的**（#7）——演示时**砍掉这一拍**，别讲一个推不出来的数。
5. **`0 quarantined`**（#88）——隔离路径从没被真正走过，演示当天可能第一次执行。
6. **`decided_by` 是自称不是身份**（#87）——本地演示够用，别声称它是审计级的。
7. **测试绿不证明判断质量**——`LLM_PROVIDER=mock` 时返回 `mock-justification-<hash>`。
   离线 185 全绿只说明代码不崩。

`CLAUDE.md` 有完整的硬约束列表。

---

## 与用户协作的方式

- **工作语言：中文。** 代码、注释、commit message、issue 标题用英文；`docs/` 与 issue
  正文中文。
- **方向由用户定，定了就做完。** 先查证、给带数据的选项、让用户选；**选完不要再逐步请示**，
  代码、看板、issue 一路做到 PR merge。
- **不要绕过缺陷。** 用户拦下过「换 mock 让测试变绿」和「把 739 秒记成开发成本」——
  异常是线索，不是预算项。先量出来、找到机制，再谈怎么改。
- **省着花 token。** 真实调用会计费，跑之前想清楚值不值，跑完告诉用户花了多少。
- **不要扩大范围。** Docker、CI、自建前端都是自作主张加的，已全部删除。
- **每完成一个子任务，从 rubric 和交付视角提一条复核 issue**（含 UI）。
  已提：#55 #61 #63 #67 #69 #72 #75 #77 #79 #82 #84 #86 #87 #88 #89。

---

## 决策历史在哪

| | |
| --- | --- |
| `CLAUDE.md` | 硬约束（每次会话自动加载） |
| `docs/13` | 架构权威：7 问 7 答、已纠正的错误、官方能力边界、rubric 比对 |
| `docs/00` | 所有实测数字的唯一来源 |
| `docs/04` | 六分钟演示脚本，每一拍标注今天能不能真跑 |
| `plugins/README.md` | 运行时踩过的坑（每一条都换过一次启动失败） |
| `data/README.md` | 开发集 / 验收集的红线 |
| #25 | dsh 位置错误的完整测量数据 —— 重构的证据基础 |
| GitHub issues | 关闭的都写了理由 |
