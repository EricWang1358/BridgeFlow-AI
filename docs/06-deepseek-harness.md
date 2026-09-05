# 06 — DeepSeek Harness (`dsh`) 作为 Agent 运行时

> **本文已更正。** 初版依据 README 摘要判断 dsh 是 "TypeScript-first"，据此设计了
> "TS 插件 + HTTP 调 Python 后端" 的双层结构。**那个判断是错的**——官方提供 Python SDK，
> Python 可以直接驱动 dsh 运行时，不需要那层 HTTP 转接。以下为核对源码与 PyPI 后的事实。

## 事实基线

| 项 | 值 | 核对方式 |
| --- | --- | --- |
| 仓库 | [deepseek-ai/deepseek-harness](https://github.com/deepseek-ai/deepseek-harness) | — |
| Python 包 | `deepseek-harness-sdk==0.1.2rc1` | PyPI |
| 运行时包 | `deepseek-harness-runtime-bin`（同版本，随 SDK 自动安装） | PyPI |
| Python 要求 | `>=3.10`（本项目 3.12 ✓） | PyPI metadata |
| 平台 wheel | `win_amd64`、`manylinux_2_28_x86_64`、`manylinux_2_28_aarch64`、`macosx_14_0_arm64` | PyPI |
| npm `latest` | `0.1.2-rc.1` | `npm view` |
| 发布状态 | **所有已发布版本均为 rc / alpha，无正式版** | `npm view versions` |

两个平台 wheel 覆盖了本机（Windows x86_64）和 AWS EC2（Linux x86_64），部署路径没有阻碍。
运行 Python SDK **不需要系统 Node.js**——运行时是打包好的可执行文件。

## 真实 API

```python
from deepseek_harness import DeepSeekHarness

with DeepSeekHarness(
    dsh_home="/absolute/path/to/isolated-dsh-home",   # 必填
    cwd="/absolute/path/to/workspace",
    provider="deepseek-official",
    model="deepseek-v4-flash",
    reasoning_effort="max",
    max_tokens=49_152,
) as harness:
    result = harness.run("Say hi.", session_id="example-001")

print(result.final_response)
```

`RunResult` 字段：`session_id`、`final_response`、`finish_reason`、`events`、`notifications`。

SDK 把打包的 `dsh` CLI 以 `--profile sdk` 拉起为子进程，通过 stdio 上的换行分隔 JSON-RPC 通信。
Profile 拥有 JSON-RPC 服务、agent 组合、凭据、持久化、工具和关闭行为。

## 三个必须知道的约束

**一、`dsh_home` 必填，SDK 刻意不去发现 `~/.dsh`。** 没有可以偷懒的默认值，所以
`DSH_HOME` 在我们这里是必填配置项，缺失时 `DshProvider.__init__` 直接抛错，而不是
静默用一个猜出来的路径。

**二、`run()` 是同步阻塞的。** 我们的 Agent 全是 async，所以适配器把每次调用交给
工作线程（`asyncio.to_thread`），并用一把锁防止并发 Agent 在同一个运行时上交错。
`MultiRoleEvaluatorAgent` 四个角色是 `asyncio.gather` 并发跑的——没有这把锁会串。

**三、`run()` 返回自由文本，没有 schema 参数。** 不像 Messages API 有结构化输出，
dsh 只给 `final_response` 字符串。所以结构化输出靠提示词要求 + 本地解析校验：
先找 ```` ```json ```` 代码块，找不到就取最外层花括号，然后用 Pydantic 校验。
**解析失败直接抛错**，不会把 `None` 悄悄传给下游——那会让空结论看起来像"没发现问题"。

## 我们的接入方式

`backend/src/bridgeflow/llm/providers/dsh.py` 实现了现有的 `LLMProvider` 协议：

```
LLM_PROVIDER=dsh  →  DshProvider  →  DeepSeekHarness 子进程  →  DeepSeek
```

这样接的好处是**Agent 代码一行没改**。四个 Agent 仍然只认 `self.llm.complete(...)`，
换运行时只是换一个环境变量。同样可以按 Agent 指定：

```bash
LLM_PROVIDER=dsh                  # 全局用 dsh
LLM_PROVIDER_SANITIZER=deepseek   # 清洗这类脏活用便宜的直连
```

### 配置项

```bash
LLM_PROVIDER=dsh
DSH_HOME=/absolute/path/to/isolated-dsh-home   # 必填
DSH_PROFILE=sdk                                 # 或 sdk-minimal
DSH_PROVIDER=deepseek-official
DSH_MODEL=deepseek-v4-flash
# DSH_REASONING_EFFORT=max
# DSH_MAX_TOKENS=49152
DEEPSEEK_API_KEY=...      # 覆盖子进程环境里的 DEEPSEEK_API_KEY
```

安装：`pip install -e ".[dsh]"`（已固定为 `==0.1.2rc1`，见下）。

### 版本固定，不用范围

pyproject 里写死 `deepseek-harness-sdk==0.1.2rc1`。理由：**所有已发布版本都是预发布版，
且项目明示会有破坏性变更**。用 `>=` 范围意味着某天 `pip install` 会悄悄换掉运行时行为——
在 hackathon 期间这是不可接受的。升级要作为一次明确的改动去做。

## 当前接入深度，以及下一步

现在做到的是**第一层：把 dsh 当模型调用后端**。这是最小的正确一步，Agent 代码零改动，
今天就能跑。但它**没有用到 dsh 真正的价值**——工具执行、会话持久化、子 agent、上下文压缩
这些能力现在都闲置着，我们只用了它的一次 `run()`。

**第二层才是真正意义上的"基座"**：把四个 Agent 做成 dsh 的 profile / 插件，让 dsh 拥有
工具执行与会话生命周期，我们的 Python 只提供数据处理工具（pandas 清洗、模糊匹配、
dataframe 合并）。这需要先读三份文档：

- `docs/AGENTS.md` — agent 定义方式
- `docs/agent-lifecycle.md` — 生命周期
- `docs/capability-seams.md` — 扩展点在哪
- `docs/cordis-primer.md` — 底层的 Cordis 组合模型

以及 `dsh plugin --profile sdk add file:...` 的本地插件打包方式。

### 尚未验证的部分

**`DshProvider` 目前只做了导入与配置校验的验证，没有跑通一次真实 turn。** 需要
`DSH_HOME` 和 `DEEPSEEK_API_KEY` 才能端到端测试，这两个我这边没有。JSON 提取逻辑
有单元测试覆盖（`tests/test_dsh_provider.py`），但 JSON-RPC 握手、profile 引导、
超时行为都还没实测过。

**下一步该做的第一件事，是拿真实凭据跑通一次 `harness.run()`。** 在此之前不要
把任何排期建立在 dsh 之上。

### 保留退路

`LLM_PROVIDER=mock` 仍然是默认值，整条 pipeline 不依赖 dsh 也能完整跑通并通过测试。
`Orchestrator` 里没有任何框架痕迹。如果 dsh 的预发布状态在 hackathon 中途出问题，
切回 mock 或直连 API 是改一个环境变量的事。
