# 06 — Using deepseek-harness (`dsh`) as the agent framework

[`deepseek-ai/deepseek-harness`](https://github.com/deepseek-ai/deepseek-harness) is an
open-source, plugin-based agent framework from DeepSeek AI (`dsh`), built on Cordis. It is
TypeScript-first (installed via npm, `npx @deepseek-ai/dsh web` for the Web UI) with Python
support, and is in **developer preview with breaking changes expected**.

## How it fits our architecture

Our four agents are Python because the work they do is Python work — pandas cleaning,
fuzzy entity matching, dataframe joins. `dsh` is an orchestration and plugin layer. So:

```
        dsh (TypeScript)                    BridgeFlow backend (Python)
┌──────────────────────────────┐        ┌──────────────────────────────┐
│  dsh-plugin: sanitize        │──HTTP─▶│  POST /agents/sanitize       │
│  dsh-plugin: resolve         │──HTTP─▶│  POST /agents/resolve        │
│  dsh-plugin: evaluate        │──HTTP─▶│  POST /agents/evaluate       │
│  dsh-plugin: quote           │──HTTP─▶│  POST /agents/quote          │
│                              │        │                              │
│  routing, retries, Web UI    │        │  pandas, rapidfuzz, prompts  │
└──────────────────────────────┘        └──────────────────────────────┘
```

Each agent becomes one thin `dsh` plugin that calls one backend endpoint. The Pydantic
models in `bridgeflow.schemas` are the contract; the TypeScript mirrors live in
`frontend/src/lib/api.ts`.

## Why we did not build directly on it

`bridgeflow.pipeline.Orchestrator` deliberately contains no framework — it is a plain
`async def run()` that calls four agents in order. That is the seam. Adopting `dsh` means
writing plugins that hit the endpoints; it does not mean touching agent code. If `dsh`'s
preview status bites us mid-hackathon, we drop back to the orchestrator and lose nothing.

## What still needs deciding

- [ ] Confirm `dsh`'s plugin API shape against its `AGENTS.md` — the README does not
      show code samples, so this needs a real read of the repo before we commit.
- [ ] Decide whether `dsh` also owns model access, or whether it calls our
      `bridgeflow.llm` provider layer. Two model-routing layers would be one too many.
- [ ] Pin a `dsh` version. "Breaking changes expected" plus a 4-day hackathon is a risk
      worth a pin.

## Task to expose agents individually

The backend currently exposes `/analyze` (whole pipeline) and `/quote`. Per-agent
endpoints are needed before `dsh` plugins can drive the stages separately — tracked on
the project board.
