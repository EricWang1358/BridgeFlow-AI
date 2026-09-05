# 交接说明

**写于 2026-09-05，交接对象：WSL (Ubuntu 22.04) 里的新会话。**

这是**当前状态**的快照，会过期。长期约束在 [`CLAUDE.md`](CLAUDE.md)，架构权威在
[`docs/13-golden-standard.md`](docs/13-golden-standard.md)。
**情况变化后请更新或删除本文**，不要让它变成第二份互相矛盾的事实来源。

---

## 一句话现状

**项目处在"架构已定、尚未落地"的时点。** 骨架代码能跑，但它是按错误的架构写的，
黄金文档已经定下正确形态。下一阶段是重构，不是加功能。

rubric 7 项目前**只有第 1 项达标**（`docs/13` 第六节有逐条比对）。

---

## 环境：已就绪且验证过

上一个会话在 Windows 上工作，仓库已迁到 WSL。**setup 全部走完并验证。**

```
~/Hackathon2026/
├── BridgeFlow-AI/     仓库
├── .venv/             Python 3.12（仓库外）
└── .dsh-bridgeflow/   DSH_HOME（仓库外，与日常 dsh 隔离）
```

实测结果：

| 项 | 值 |
| --- | --- |
| dsh 运行时启动 | **0.5s**（Windows 上同一运行时是 3.6s） |
| 单次 turn | 0.7s，`finish_reason='completed'` |
| 结构化输出 | 一次解析成功 |
| 测试 | 19 passed，`ruff` clean |

每次开工：

```bash
source ~/Hackathon2026/.venv/bin/activate
source ~/Hackathon2026/BridgeFlow-AI/env.sh
cd ~/Hackathon2026/BridgeFlow-AI/backend
python ../scripts/smoke_dsh.py     # 确认 dsh 还活着
```

---

## 上一个会话做了什么

按时间顺序，因为后面的结论推翻了前面的：

1. 建了完整脚手架（5 个 Agent、provider 层、schema、测试）——**过早**，用户明确指出
2. 接入 dsh，但**塞进了 `LLMProvider` 协议** ——架构性错误，用户纠正
3. 语义对齐用字符串相似度，实测产出 **0 条映射** ——推翻重写为「声明 + 共现」
4. 对照 rubric 自评，发现方向偏了：一直在按 PRD 补功能，而 rubric 考 Agent 工程
5. 核实 dsh 官方 vs experimental 边界，确定 `subagent` 可用、`agent-team` 不用
6. 写下黄金文档，rubric 重新量化为 1/7
7. 迁移到 WSL，删掉自建前端、Dockerfile、compose、CI

**教训已固化进 `CLAUDE.md` 的七条硬约束。请先读它。**

---

## 建议的下一步（需与用户确认）

### 第一步：读完这六份 dsh 文档

设计插件形态之前必须读，上个会话只读了三份半：

- `docs/subsystems/plan.md` / `goal.md` —— 可能直接给出 rubric 第 2 项的 planning pattern
- `docs/subsystems/permission-presets.md` —— least-privilege 的现成预设
- `docs/subsystems/session-query.md` —— 追踪能力的查询面
- `packages/workflow/README.md` —— 工作流的表达能力边界，决定能否取代 `Orchestrator`
- `docs/user/develop/basic/tool.md` —— 第一个工具的有序教程，决定 TS→Python 怎么连

用 `gh api repos/deepseek-ai/deepseek-harness/contents/<path> --jq '.content' | base64 -d` 读。

### 然后：用户选定的优先级

来自 `docs/09` 与 `docs/13`，按性价比：

1. **注入防御做成 guard 插件**（rubric 第 5 项，当前 0 分且有真实漏洞）
2. **数据操作暴露为 typed tools**（第 3+7 项，顺带解决 627 秒）
3. **eval 套件 golden + adversarial**（第 6 项，rubric 明写）
4. **跨月映射记忆**（第 2 项 state/memory）

看板：https://github.com/users/EricWang1358/projects/1 —— Ready 栏就是该动的。

---

## 待验证的开放问题

这些没有答案，**不要假设**：

| 问题 | 为什么重要 |
| --- | --- |
| `dsh plugin add file:` 是拷贝还是可 link/watch？ | 直接决定插件开发循环的速度 |
| `sdk-minimal` 够不够用？ | 它只带 Bash + 编辑器 + 本地执行 + JSONL 会话 |
| subagent 是否受「单 runtime 不能交错 turn」限制？ | 决定四角色能否真并发 |
| dsh web 的端口与 Client 插件注册机制 | `tool.call.toolview` 的具体用法未验证 |

---

## 与用户协作的方式

- **工作语言：中文。** 代码、注释、commit message 用英文。
- **用户是决策者。** 上个会话犯的最大错误是"激进的实现"——在需求没搞清楚时
  直接写代码，导致返工。**动手前先确认。**
- 用户会直接指出错误，且通常是对的。**核实之后承认，不要辩解，也不要无条件附和** ——
  有一次用户说 agent-team 是"第三方插件"，实际是 `packages/experimental/`，
  核实后结论一致但理由不同，这种区别值得说清楚。
- **不要扩大范围。** Docker、CI、自建前端都是自作主张加的，已全部删除。

---

## 已知缺陷（`CLAUDE.md` 有完整列表）

最容易误判的三个：

1. **19 个测试全绿，但全在 mock provider 下跑，而 mock 返回随机占位符。**
   测试只证明代码不崩，**不证明任何判断质量**。
2. **`evaluator.py` 把单元格内容原样拼进提示词** —— 真实注入漏洞，未修。
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
| GitHub issues | 25 个已开 + 7 个已关，关闭的都写了理由 |
