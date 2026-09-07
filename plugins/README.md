# BridgeFlow DSH plugins

DSH owns the agent loop, the native Web UI, sessions, approvals and child runs. These local
Host/Client plugins add three things on top: domain tools, policy, and business views. Python executes
spreadsheet arithmetic and stores immutable batches; on the default path it is not a model provider.

## Build and run

From the repository root, follow [HANDOFF](../HANDOFF.md) for the pinned dependencies, shell
configuration and `python scripts/start_web.py`. Build the Client module with
`pnpm --dir plugins run build`. The launcher loads `dsh/enterprise.patch.yml` through the official npm
Web CLI. There is no separate frontend server and no legacy console on by default.

## What lives where

| Entry | Purpose |
| --- | --- |
| `src/index.ts` | Register domain tools and enforce the final host allowlist |
| `src/web.ts` | Reuse native cookie/Host/Origin authentication; expose narrow data and note routes |
| `src/tools/` | Typed input/output boundaries, and the sealed `review_context` / `review_finalize` boundary around model-facing delegation |
| `src/approval/` | Native approval gate, scoped notes, one-use payload-bound write receipts |
| `src/client/` | Native slots for import/data, report cards and mapping rejection notes |
| `tests/` | Real ToolRuntime contracts and Chromium end-to-end verification |

Two behaviours worth knowing before you touch this code:

The mapping approval form overrides presentation through the official composer slot and calls the
official pending request's `answer` method, so native settlement and paired audit events stay intact.
A note is saved against the current session/call ticket before the rejection is recorded; it cannot
authorise a write. The old answerer exists only for the explicit legacy mode, which is off by default.

`review_context` prepares four sealed tasks. The captain model calls the official `subagent` tool four
times in one response, and `review_finalize` collects the actual child results. Reviewers run through
official `spawn`: no lateral communication, no arbitrary code execution, and each child may only submit
structured output inside the configured step and time budget. Python then checks each result against
the batch's frozen contract. A failed child produces an incomplete report, not a synthetic finding,
and proposed business actions stay proposals.

The Business state page is an additive `conversation.view` after the native Trajectory tab; department
files open from a header utility into a small overlay. There is no DSH fork and no replacement of the
native details panel. Report and batch links use `#bridgeflow?...`; child links resolve through the
native catalogue. See [implementation and governance](../docs/18-native-captain-and-state.md).

Evidence export defaults to `--keep 2` complete runs. Real session pruning is a manual
`pnpm sessions:prune --keep 2 --dry-run` operation and never runs at startup.
The [one-stop demo](../demo-walkthrough/README.md) links to the retained evidence.

## Runtime contracts

- Sibling imports use `.ts`: the runtime transpiles without rewriting extensions.
- Tool value schemas use per-property `required: true`; child JSON schemas use the supported JSON
  Schema subset. Length keywords the runtime ignores have to be enforced by the host or backend instead.
- Return canonical values. `output.render` supplies the model-facing text, and public tool output must
  not leak private Python evaluator fields.
- Web cards register under `tool.call.toolview`; a Host presenter alone does not create a Web UI.
  Client output is built for the official module loader.
- Honour cancellation, fail closed, and test policy at actual dispatch. Hiding a Web control does not
  remove the capability underneath it.

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

Browser tests default to an explicitly test-only offline adapter with isolated data. Export model
credentials and set `BRIDGEFLOW_LIVE=1` to run the real model, which can incur charges. Results,
measured numbers and remaining limits belong in [status](../docs/00-status.md) rather than here;
the current demo guide is [docs/17](../docs/17-business-mvp-acceptance.md).
