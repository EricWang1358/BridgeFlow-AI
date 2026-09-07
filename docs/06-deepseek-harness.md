# 06 — DeepSeek Harness（`dsh`）作为 Agent 运行时

> 参考文档：这一页只放 dsh 的版本事实与 API 形状。架构结论看
> [`13-golden-standard.md`](13-golden-standard.md)，实测数字看
> [`00-status.md`](00-status.md)，这里不复写数字。
>
> 两处曾经的错误留在这里，免得有人再走一遍：
>
> 1. 初版依据 README 摘要判断 dsh 是 "TypeScript-first"，据此设计了「TS 插件 + HTTP 调 Python 后端」
>    的双层结构。错的：官方有 Python SDK，可以直接驱动运行时，没有 HTTP 这一层。
> 2. 初版把 dsh 当成 provider 层的一员（「第一层 / 第二层」的说法）。错的：它是基座本身。
>    代价见 issue #25 与 [`13` 第三节](13-golden-standard.md)。

## 事实基线

| 项 | 值 | 怎么核对 |
| --- | --- | --- |
| 仓库 | [deepseek-ai/deepseek-harness](https://github.com/deepseek-ai/deepseek-harness) | — |
| Python 包 | `deepseek-harness-sdk==0.1.2rc1` | PyPI |
| 运行时包 | `deepseek-harness-runtime-bin`（同版本，随 SDK 自动安装） | PyPI |
| SDK 的 Python 要求 | `>=3.10`；本项目 `requires-python = ">=3.11"`（代码用了 `datetime.UTC`），实际跑 3.12 | PyPI metadata、`backend/pyproject.toml` |
| 平台 wheel | `win_amd64`、`manylinux_2_28_x86_64`、`manylinux_2_28_aarch64`、`macosx_14_0_arm64` | PyPI |
| npm `latest` | `0.1.2-rc.1` | `npm view` |
| 发布状态 | 所有已发布版本均为 rc / alpha，没有正式版 | `npm view versions` |

平台 wheel 覆盖本机（Windows x86_64）与 AWS EC2（Linux x86_64），部署路径上没有阻碍。
跑 Python SDK 不需要系统装 Node.js，运行时是打包好的可执行文件。

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

`RunResult` 的字段：`session_id`、`final_response`、`finish_reason`、`events`、`notifications`。

SDK 把打包的 `dsh` CLI 以 `--profile sdk` 拉起为子进程，通过 stdio 上换行分隔的 JSON-RPC 通信。
profile 拥有 JSON-RPC 服务、agent 组合、凭据、持久化、工具与关闭行为。

## 三条必须知道的约束

**一、`dsh_home` 必填，SDK 刻意不去发现 `~/.dsh`。** 没有可以偷懒的默认值。所以我们把它当成必填配置项，
缺失时直接抛错，而不是静默用一个猜出来的路径。

**二、`run()` 是同步阻塞的。** 我们的 agent 全是 async，所以适配器把每次调用交给工作线程
（`asyncio.to_thread`），并用一把锁防止并发 agent 在同一个运行时上交错 turn。
四角色并发（`asyncio.gather`）在没有这把锁时会串输出。要真并发得开多个 runtime 实例，
或者像现在这样：判断类调用不走 dsh，四角色交给官方 subagent 的独立子会话。

**三、`run()` 返回自由文本，没有 schema 参数。** 不像 Messages API 有结构化输出，dsh 只给
`final_response` 字符串，所以结构化输出靠提示词要求加本地解析：先找以三个反引号起头的 `json` 围栏代码块，
找不到就取最外层花括号，再交给 Pydantic 校验。解析失败直接抛错，不把 `None` 悄悄传给下游。
空结论看起来像「没发现问题」，是这类系统最难查的错。

## 版本固定，不用范围

`pyproject` 里写死 `deepseek-harness-sdk==0.1.2rc1`。理由很直接：所有已发布版本都是预发布版，
而且项目自己说明会有破坏性变更。写成 `>=` 意味着某天 `pip install` 会悄悄换掉运行时行为，
这在 hackathon 期间不可接受。升级要作为一次显式的改动去做。

## 遗留的 provider 接法（不要再往这个方向加东西）

`backend/src/bridgeflow/llm/providers/dsh.py` 把 dsh 实现成一个 `LLMProvider`。
配置项长这样：

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

安装：`pip install -e ".[dsh]"`。

这么接的唯一好处是 agent 代码一行没改，换运行时只是换一个环境变量，连按 agent 覆盖都可以
（`LLM_PROVIDER_SANITIZER=deepseek`）。但它也正是 [`13` 第三节记录的错误一](13-golden-standard.md)：
把基座降级成补全后端，工具执行、会话、子代理、策略层全部闲置。
现状是 resolver 的纯判断类调用已经撤回到 `deepseek` 直连（#25、PR #34），
默认入口走原生工具与官方子代理（`13` 第九节）。这个文件留着是为了迁移时能对照，
不是因为它是范例。

## 两个曾被误归因的缺陷

整条 pipeline 在真实 provider 上跑得很慢，当时被归因为「与 dsh 无关」，那个归因是错的。
两条相关记录：[#24](https://github.com/EricWang1358/BridgeFlow-AI/issues/24)
（拿字符串相似度做跨部门对齐，产出 0 条映射）与
[#25](https://github.com/EricWang1358/BridgeFlow-AI/issues/25)（一次裁决慢到四个数量级）。
两者的根因后来都归到「dsh 位置放错」，见 [`13` 第三节](13-golden-standard.md) 与
[`00`](00-status.md) 的耗时记录。

## 保留退路

`LLM_PROVIDER=mock` 仍是默认值，整条 pipeline 不依赖 dsh 也能跑完并通过离线回归。
mock 的输出是占位文本，所以它是回退方案，不是演示对象，也不是判断质量的证据。
如果预发布的 dsh 在关键一天出问题，切回 mock 或直连 API 是改一个环境变量的事。

## 接入 dsh 之前要读的官方文档

四份（`13` 第七节记了读完之后的结论，其中四条推翻了我们原来的假设）：

- `docs/AGENTS.md`：agent 怎么定义
- `docs/agent-lifecycle.md`：生命周期与时序，工具注册的时机就藏在这里
- `docs/capability-seams.md`：扩展点在哪
- `docs/cordis-primer.md`：底层的 Cordis 组合模型

本地插件的打包与装载方式（不 fork dsh）：`dsh plugin --profile sdk-minimal add file:<绝对路径>`，
细节与 `--patch` 路径的未确认差异见 `13` §7.8。