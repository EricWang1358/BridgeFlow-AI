# 19 — 跨操作链路审计与修复

这一轮针对一个具体的怀疑：页面都在、单次脚本能跑，但连续操作还会出错。结论是成立的，
原因是批次、研判运行、报告、会话、审批这几层身份与结束条件没有贯穿到所有入口。
跑通一个正常样本，替代不了「切换、取消、断网、重启」这一类验收。实测数字见
[00 的各轮验收记录](00-status.md)。

## 链条与每层的权威来源

```text
启动器 → 官方 DSH Web → 同源鉴权代理 → 私有 FastAPI
                                 ↓
本地 CSV/XLSX → 导入/字典/清洗 → 不可变 batch_id
                                 ↓
review_context → review_id + 父会话 + 四个角色票据
                                 ↓
父模型同一响应四次官方 subagent → 四个真实 child session
                                 ↓
structured_output → 宿主收集 → Python 按冻结字典校验
                                 ↓
report_id（validated / partial）→ 报告卡 / 弹窗 / 业务状态页

confirm_mapping → 官方审批 + callId / approvalId → 一次性回执 → mappings.json
                                                        ↓
                                                   后续新导入
```

| 身份或状态 | 谁是权威 | 不能推出什么 |
| --- | --- | --- |
| batch_id、导入状态 | Python 的不可变批次快照 | 不代表本次会话、最新研判或已批准 |
| review_id、派活状态 | 宿主生命周期与 `bridgeflow/review` 事件 | 工具调用尝试不等于成功 Spawn；事件未结束不等于仍在运行 |
| parent / child | 官方会话头与目录 | 切换批次不能借用另一单的派活数 |
| report_id、validated / partial | Python 保存的特定报告 | 最新的历史报告不能填补当前运行；validated 不是业务签发 |
| approvalId / callId、审批决定 | 官方 asked / decided 与一次性回执 | 会话里的审批累计不是所选批次的批准状态；批准不改旧快照 |
| attention / 正常 | 已校验报告里的阈值比较 | 不代表已经执行过采购、调价、授信或签核 |

有两组状态可以并存，值得单独说：导入是 `needs_review`、报告是 `validated` 同时成立是合法的，
因为本案例直接计算声明列，不依赖待确认的跨部门关系；而只要有隔离行或配置拒绝，就禁止研判。
所以实际实现不是 `ready → validated → approved` 这样一条直线。界面必须分清各自的作用域，
不能用一个绿色块表示整条业务链已完成。

## 已复现并修好的

| 故障 | 根因与修复 | 验证到哪为止 |
| --- | --- | --- |
| 从 A 的特定报告去导入 B，B 的报告请求仍带着 A 的 report_id | 上传时清除报告身份，并统一写批次路由 | 同一浏览器同一会话连续上传两批：修复前返回错误的「报告不属于该批次」，修复后提示尚无报告 |
| 手选 B 后点刷新，跳回 A | 刷新不再清除选择；「跟随当前会话批次」拆成独立操作；监听状态页路由 | 浏览器断言刷新后仍是 B |
| B 显示 A 的四次派活 | 派活记录按所选批次约束，并注明这是工具派发尝试；审批另标当前会话作用域 | 浏览器跨批次断言与投影测试 |
| 不存在的批次链接仍展示旧批次，加载提示与错误并存 | 切换时清空旧内容与成功提示，取消未完成请求，出错后停止加载提示 | 浏览器访问格式合法但不存在的批次 ID |
| 同批次新研判仍加载旧成功报告 | 用 review_id / report_id 选本次结果；本次没有汇总时不去请求历史 latest | 投影回归测试；未声称完成真实模型连续重跑验收 |
| 前端改过但启动仍展示旧包 | 启动前比较客户端源码、构建脚本、锁文件与产物的新旧，并给出构建命令 | 临时目录测试缺失、过期、有效三种产物 |
| 后端退出而 Web 继续挂着；Web 异常退出被启动器当成功 | 启动器监视两个进程并传播失败，通过已有 finally 清理自身子进程 | 模拟进程退出测试；未做真机中途杀进程演练 |
| 坏 YAML 或字典结构让导入返回泛化 500 | 配置读取与字典构建异常返回明确 503，要求管理员修复；不落盘猜测结果 | 修复前用 TestClient 复现；修复后覆盖语法、根类型、字段结构、关系缺字段；缺字典的原有语义保留 |
| 报告与计量已写出，但后面的 UI 断言失败 | business smoke 在全部断言之后才写 `acceptance.json`；失败明确 `passed=false`；采集器保留该结果 | 采集测试确保失败标记不会被转换成通过；旧证据缺这个文件时不补造通过标记 |

浏览器回归现在默认包含跨批次操作，不再需要额外开关；step-limit 故障场景单独执行。
修复前后作为同一场景保留，最多两轮：

- [修复前失败明细](evidence/business-mvp/chain-regression/runs/1788700374086086706/chain-audit.json)
- [修复后连续操作明细](evidence/business-mvp/chain-regression/chain-audit.json)
- [修复后最终验收结果](evidence/business-mvp/chain-regression/acceptance.json)
- [仅对应父子会话的审计](evidence/business-mvp/chain-regression/session-audit.json)

这些是离线模型适配器驱动的真实官方 Web、工具派发与浏览器操作：验证的是交互与协议，
不代表本轮又付费验证了模型表现。之前真实模型的费用与延迟基线仍然保留，没有被这轮离线数据覆盖。

## 还没收尾的链路

下面是代码审查确认的实现缺口。没有把「还没做故障注入」写成「实测失败」。

**2026-09-23 复核**：本表最初写于 #115 之前，此后 #111–#113 已关闭。逐条对照当前代码与测试，
结论如下；「已收尾」只指离线测试与脚本化浏览器旅程成立，不代表真实模型下复验过。

| 优先级 | 缺口与位置 | 现状 | 证据 |
| --- | --- | --- | --- |
| P0 | partial 的人工意见走普通聊天，「禁止重跑」只是一句文本 | **已收尾**（#111）：带 `HUMAN_NOTE_MARKER` 的轮次由宿主 guard 拒绝 `review_context` / `subagent` / 写工具，只许读 | `runtime.test.ts`「a human-note turn cannot start a review or write」；`test_review_runs.py` 人工意见只追加、不改报告；`business-smoke` 故障变体断言人工意见后会话数仍为 5（没有再派一组部门） |
| P0 | 超时只中止子代理，父模型等待与汇总不受期限约束 | **已收尾**（#112）：一个期限覆盖派活、各部门与汇总；到期由宿主以 `deadline_exceeded` 结束 | `runtime.test.ts`「registered with its deadline before any department」「a captain that never dispatches is ended by the host at the deadline」；`test_review_runs.py` 超时后迟到的成功不能覆盖 |
| P0 | `ReviewPolicy.states` 只在内存，重启无法还原；`finish()` 缓存失败 promise | **已收尾**（#113）：宿主启动时调 `review-recover`，把遗留的 dispatching 运行以可读报告显式结束；失败的汇总不缓存、可重试；按 review_id 幂等 | `test_review_runs.py`「a restarted host ends open reviews」「finalizing twice returns the same report」；`runtime.test.ts`「a finalize that fails is not cached」 |
| P1 | 输出 token 上限是单次请求上限，不是整名子代理的额度 | **仍开放**：现有的是每部门 `CHILD_STEP_LIMIT = 3` 步数上限与按阶段分开记录的用量，没有跨步骤累计 token 的硬停 | `review-batch.ts`；`test_review_runs.py` 用量按阶段记数 |
| P1 | 拒绝备注先写事件、决定后提交，竞争下可能留下未成为最终理由的备注 | **已收尾**：备注在正式决定前是草稿，只有拒绝才成为最终理由 | `runtime.test.ts`「a saved approval note is a draft until the official decision」 |
| P1 | 父子会话链接失败只记客户端日志，页面无提示 | **部分收尾**：不存在的子会话链接在页面上显示「部门会话不存在」；状态页 URL 与原生页签激活仍不是同一个操作 | `business-smoke`（#40）英文界面断言该提示 |

P0 的意思是它影响「本次业务操作是否完成」的可信度，必须在稳定的演示验收之前收尾，
不是说已经证明存在越权写入。审批回执、领域拒绝、角色校验这些既有保护，与上面的恢复缺口要分开评估。

## 下一轮应该怎么验

先把运行时收尾契约做完，再跑一次连续操作验收，顺序是：导入 A 并研判 → 导入 B 但不研判 →
来回切换、刷新、深链接 → A 第二次研判 → 子步骤失败 → 人工意见且模型故意违令 → 审批拒绝与超时 →
汇总时断网或重启宿主 → 明确恢复或明确失败。

每一步核对 `batch_id`、`review_id`、`report_id`、parent/child、approval/call 五类归属，
检查页面显示、落盘内容与真实调用三者是否一致。测试的最终退出状态、`acceptance.json` 与证据清单必须互相对得上。
上面的「已收尾」来自离线测试与脚本化模型下的浏览器旅程；真实模型下的连续操作验收仍未做，也不能把模拟意见算成部门负责人的签核。
