# 交接说明

**更新于 2026-09-06。** 这是**当前状态**的快照，会过期。长期约束在 [`CLAUDE.md`](CLAUDE.md)，
架构权威在 [`docs/13-golden-standard.md`](docs/13-golden-standard.md)。
**情况变化后请更新或删除本文**，不要让它变成第二份互相矛盾的事实来源。

---

## 一句话现状

**架构重构开始落地了。** 第一刀已经切下去：resolver 从 dsh 上撤到 DeepSeek 直连（#25）。
剩下的骨架仍是按错误架构写的，下一阶段继续重构，不是加功能。

rubric 7 项目前仍只有第 1 项达标（`docs/13` 第六节有逐条比对）。

---

## 环境

```
~/Hackathon2026/
├── BridgeFlow-AI/     仓库
├── .venv/             Python 3.12.8（仓库外）
└── .dsh-bridgeflow/   DSH_HOME（仓库外，与日常 dsh 隔离）
```

**`env.sh` 是 gitignored 的，换机器要重建**：`cp env.sh.example env.sh` 然后填
`DEEPSEEK_API_KEY`。上一版交接说「setup 全部走完并验证」，但 `env.sh` 根本不存在——
上个会话是在 shell 里临时 export 的，从没落盘。缺了它 dsh 起不来，测试直接红。

每次开工：

```bash
source ~/Hackathon2026/.venv/bin/activate
source ~/Hackathon2026/BridgeFlow-AI/env.sh
cd ~/Hackathon2026/BridgeFlow-AI/backend
```

`scripts/smoke_dsh.py` 可以确认 dsh 还活着，但**它会真的调用 API**，别随手跑。

---

## 上一个会话（2026-09-06）做了什么

查清了「21 行数据跑 627 秒」到底是什么，结论推翻了原来的定性：

1. **不是性能问题，是架构问题。** 6 次调用、每次提示词 590 字符、运行时启动 0.6 秒。
   单次 turn 却要 5.3–212.5 秒。
2. **时间花在 dsh 自发跑 bash 上。** 一次映射裁决跑了 12 步 shell，读了 README、源码、
   `test_resolver.py`、`git log`、`CLAUDE.md`、`HANDOFF.md`——**读整个仓库来回答一个
   提示词里已经写全答案的是非题**，而且是**读测试文件抄的答案**。
3. **token 账单：发出去 548 字符，工具输出灌回来 28,431 字符 ≈ 7,100 token，52 倍。**
   dsh 是多步循环，后续步骤连同前面所有工具输出重发，实际计费是这个数的数倍。
4. **安全结论比 #26 原来写的严重**：`sdk-minimal` 给的 bash 没有目录约束，而喂进去的
   `row_support` 派生自表格单元格内容。注入的落点不是提示词，是 shell。
5. **修了 #25 和 #33**（PR #34）：resolver 改走 DeepSeek 直连，解析器提取到
   `llm/json_reply.py` 共用并修掉 schema 外壳。

**测试状态：`3 failed / 16 passed in 739.6s` → `21 passed in 587.0s`。**
`test_resolver.py` 单独看是 `426.7s / 2 failed` → `207.6s / 9 passed`。
全套仍要 587 秒，因为 evaluator 还在 dsh 上。

---

## 已经确认过、不要再试的事

| 事实 | 出处 |
| --- | --- |
| DeepSeek 直连**不支持** `response_format: {"type":"json_schema"}` | 实测报 `This response_format type is unavailable now`，改用 `json_object` |
| 可用 model id：`deepseek-v4-flash` / `deepseek-v4-pro` / `deepseek-v4-flash-vision-exp` | `GET https://api.deepseek.com/models` |
| `DeepSeekHarnessConfig` **没有任何工具/权限开关** | 只有 provider/model/reasoning_effort/max_tokens/cwd/profile/patches/base_url/api_key。工具集归 profile bundle 管 |
| `deepseek_base_url` 的默认值不能放 `settings` | 它同时喂给 dsh，dsh 把显式 base URL 当覆盖。默认值放在 `DeepSeekProvider` 里 |
| `provider_for()` 早就支持按 agent 覆盖 | `config.py:60`，`LLM_PROVIDER_RESOLVER` 等 |

---

## 建议的下一步

### 优先级最高：evaluator 还在 dsh 上

#26 的 shell 暴露面**没有消失**，只是缩小了。evaluator 仍然把单元格内容原样拼进提示词，
仍然跑在带 bash 的 dsh 上。这条链路 = 不可信输入 + 无约束 shell。

但 evaluator 还欠 #13 的「规则算数、模型解释」改造，两件事应该一起做。

### 然后：还没读的 dsh 文档

设计插件形态之前必须读，至今没人读过：

- `docs/subsystems/permission-presets.md` —— **最要紧的一份**，「定制版 dsh」的入口就在这里
- `docs/subsystems/plan.md` / `goal.md` —— 可能直接给出 rubric 第 2 项的 planning pattern
- `docs/subsystems/session-query.md` —— 追踪能力的查询面
- `packages/workflow/README.md` —— 决定能否取代 `Orchestrator`
- `docs/user/develop/basic/tool.md` —— 决定 TS→Python 怎么连

用 `gh api repos/deepseek-ai/deepseek-harness/contents/<path> --jq '.content' | base64 -d` 读。

### 看板上按性价比排的

1. **注入防御做成 guard 插件**（#26，rubric 第 5 项，当前 0 分且有真实漏洞）
2. **数据操作暴露为 typed tools**（#27，第 3+7 项）
3. **eval 套件 golden + adversarial**（#28，第 6 项，rubric 明写）
4. **跨月映射记忆**（#29，第 2 项 state/memory）

看板：https://github.com/users/EricWang1358/projects/1

**注意**：`gh` 的 token 缺 `read:project` scope，命令行加不了 item。跑
`gh auth refresh -s project` 补上。

---

## 待验证的开放问题

| 问题 | 为什么重要 |
| --- | --- |
| `dsh plugin add file:` 是拷贝还是可 link/watch？ | 直接决定插件开发循环的速度 |
| 能不能做一个**没有 bash** 的 profile？ | #26 的收口手段，SDK 层没有开关 |
| subagent 是否受「单 runtime 不能交错 turn」限制？ | 决定四角色能否真并发 |
| dsh web 的端口与 Client 插件注册机制 | `tool.call.toolview` 的具体用法未验证 |

---

## 与用户协作的方式

- **工作语言：中文。** 代码、注释、commit message、issue 标题用英文；`docs/` 与 issue
  正文已经是中文，跟随即可。
- **方向由用户定，定了就做完。** 先查证、给带数据的选项、让用户选；**选完不要再逐步请示**，
  代码、看板、issue 一路做到 PR merge。上个会话在这两头都犯过错——先是没问就写代码，
  后来又问得太碎。
- **不要绕过缺陷。** 用户两次拦下「换 mock 让测试变绿」和「把 739 秒记成开发成本」——
  异常是线索，不是预算项。先量出来、找到机制，再谈怎么改。
- **省着花 token。** 真实调用会计费，跑之前想清楚值不值，跑完告诉用户花了多少。
- **不要扩大范围。** Docker、CI、自建前端都是自作主张加的，已全部删除。

---

## 已知缺陷（`CLAUDE.md` 有完整列表）

最容易误判的三个：

1. **测试里只有 `test_resolver.py` 打真实模型。** 其余仍在 mock 下跑，而 mock 返回
   `mock-justification-<hash>`。绿色**不证明判断质量**。
2. **`evaluator.py` 把单元格内容原样拼进提示词** —— 真实注入漏洞，未修，且它还在 dsh 上。
3. **样本只有 2025-11 一个月共 22 行。** 无法验证跨月记忆，也无法测规模。

**仓库看起来比实际健康**，绿色的测试是这个错觉的主要来源。

---

## 决策历史在哪

| | |
| --- | --- |
| `CLAUDE.md` | 硬约束 + 已知缺陷（每次会话自动加载） |
| `docs/13` | 架构权威：7 问 7 答、已纠正的错误、官方能力边界、rubric 比对 |
| `docs/14` | WSL 环境搭建（已完成，留作参考与重装用） |
| `docs/09` | rubric 自评（第 4 项评价已被 13 修正） |
| `docs/07` | 业务方 PRD |
| `docs/12` | 提交表单内容（Owner 栏待填真人姓名） |
| #25 | dsh 位置错误的完整测量数据 —— 重构的证据基础 |
| GitHub issues | 26 个已开 + 7 个已关，关闭的都写了理由 |
