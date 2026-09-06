# BridgeFlow DSH plugins

DSH owns the agent loop, native Web, sessions, approvals and child runs. These local
Host/Client plugins add domain tools, policy and business views. Python executes
spreadsheet arithmetic and stores immutable batches; it is not a model provider on
the default path.

## Build and run

From the repository root, follow [HANDOFF](../HANDOFF.md) for the pinned dependencies,
shell configuration and `python scripts/start_web.py`. Build the Client module with
`pnpm --dir plugins run build`. The launcher loads `dsh/enterprise.patch.yml` using
the official npm Web CLI. There is no separate frontend server or legacy console.

## Responsibilities

| Entry | Purpose |
| --- | --- |
| `src/index.ts` | Register domain tools and enforce the final host allowlist |
| `src/web.ts` | Reuse native cookie/Host/Origin authentication; expose narrow data and note routes |
| `src/tools/` | Typed input/output boundaries and sealed `review_context` / `review_finalize` boundaries around native model-facing delegation |
| `src/approval/` | Native approval gate, scoped notes and one-use payload-bound write receipts |
| `src/client/` | Native slots for import/data, report cards and mapping rejection notes |
| `tests/` | Actual ToolRuntime contracts and Chromium end-to-end verification |

The mapping approval form overrides presentation through the official composer slot.
It calls the official pending request's `answer` method, preserving native settlement
and paired audit events. A note is saved against the current session/call ticket
before rejecting. It cannot authorize a write. The old answerer exists only for the
explicit legacy mode, which is disabled by default.

`review_context` prepares four sealed tasks. The captain model calls the official
`subagent` tool four times in one response; `review_finalize` collects the actual
child results. Reviewers run using official `spawn`, without
lateral communication or arbitrary code execution. Each child can only submit
structured output within the configured step/time budget. Python checks the result
against the batch's frozen contract. A failed child produces an incomplete report,
not a synthetic successful finding. Business actions remain proposals.

The **Business state** page is an additive `conversation.view` after native
Trajectory. Department files open from a header utility into a small overlay;
there is no DSH fork or replacement of the native details panel. Report/batch
links use `#bridgeflow?...`; child links resolve through the native catalogue.
See [implementation and governance](../docs/18-native-captain-and-state.md).

Evidence export defaults to `--keep 2` complete runs. Real session pruning is a
manual `pnpm sessions:prune --keep 2 --dry-run` operation, never run on startup.
The [one-stop demo](../demo-walkthrough/README.md) links to retained evidence.

## Runtime contracts

- Sibling imports use `.ts`: the runtime transpiles without rewriting extensions.
- Tool value schemas use per-property `required: true`; child JSON schemas use the
  supported JSON Schema subset. Unsupported length keywords must be enforced by
  the host/backend contract instead.
- Return canonical values. `output.render` supplies model-facing text; public
  tool output must not accidentally include private Python evaluator fields.
- Web cards register under `tool.call.toolview`; Host presenters alone do not
  create a Web UI. Client output is built for the official module loader.
- Honor cancellation, fail closed, and test policy at actual dispatch. Hiding a
  Web control does not remove its underlying capability.

## Verification

```bash
cd plugins
pnpm run typecheck
pnpm test
pnpm run build
pnpm run smoke:web
pnpm run smoke:business
BRIDGEFLOW_TEST_FAULT=step-limit pnpm run smoke:business
```

Browser tests default to an explicitly test-only offline adapter and isolated data.
Set `BRIDGEFLOW_LIVE=1` after exporting model credentials to run the actual model;
this can incur charges. Results, measured numbers and remaining limits belong in
[status](../docs/00-status.md), with the current [business demo guide](../docs/17-business-mvp-acceptance.md).
