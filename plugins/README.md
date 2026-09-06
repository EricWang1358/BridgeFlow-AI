# plugins — BridgeFlow's dsh plugins

**The shell is TypeScript, the body is Python.**

A model-facing tool has two halves, and they cannot both live in Python:

| | Where | Why |
| --- | --- | --- |
| Declaration — name, parameter schema, output schema, card rendering | **TypeScript, here** | This is what the model sees and what the runtime validates in both directions |
| Body — read a table, aggregate a metric, look up the field dictionary | **Python, `backend/`** | pandas is there, and #13 is about to lean on it harder |

The Python SDK cannot close this gap. It is a JSON-RPC *client* — 911 lines with no
mention of `tool` — so `defineTool`, guards, `ctx.approval` and the toolview slot are
unreachable from it. That is why rubric items 3, 4, 5 and 7 sat at ❌ while the
pipeline itself worked: they all live on the plugin side of the runtime boundary.

## The direction of control reverses here

Before: Python drove the runtime (`harness.run(prompt)`) and dsh was, in effect, a
completion provider — the mistake `CLAUDE.md` names in its first hard constraint.

Now: **dsh runs the loop** and its tools call back into Python for the data work. The
existing agents keep their logic; they stop being the top of the stack.

## Layout

```
src/
  tools/          One file per domain tool. Declaration only — execute() calls Python.
  guards/         The injection boundary: a monotonic deny (#26)
  approval/       The escalation checkpoint: the gate that asks, the answerer that
                  puts the question in front of a person, and the summary they read (#30)
  backend.ts      The one place that knows how to reach Python
  index.ts        Plugin entry: registers everything
```

## Loading it

```bash
uvicorn bridgeflow.api.main:app        # the bodies, and the operator console
# then run dsh with all three patch layers:
#   dsh/no-shell.patch.yml     takes the shells away
#   dsh/approval.patch.yml     loads ctx.approval with policy: ask
#   dsh/bridgeflow.patch.yml   inserts this plugin
```

Open <http://127.0.0.1:8000/console> before starting a turn that may write. A mutating
tool call blocks there; with nobody watching it fails closed.

No fork and no published package: a patch layer applies after every bundle layer.

## What the runtime taught us, the hard way

Four things that cost a boot failure each. They are written down because the error
messages do not say what to do about them.

1. **Import sibling modules with `.ts`, not `.js`.** The loader transpiles TypeScript
   but does not rewrite extensions, so `./backend.js` is simply missing. `tsconfig`
   needs `allowImportingTsExtensions`.
2. **`output.schema` uses the same DSL as `parameters`.** A top-level
   `required: ['a','b']` array fails the load with *"schema.required is not supported
   by the value schema DSL"*; requiredness is a per-property `required: true`.
3. **A `!!js` expression is not evaluated in the `name` position.** It arrives as an
   object and the loader dies on `name.startsWith is not a function`. A plain relative
   path works and resolves against the patch file's own directory, which keeps the
   patch portable — no absolute path per machine.
4. **A value schema takes one type per property.** There is no `['string','null']`
   union; an answer that may be absent is an absent property.

## Rules that bite

- **Presenters must be pure.** `presentCall` / `presentResult` run on live streaming
  *and* on session-log replay: no I/O, no session reads, no clock, no random. Anything
  needing result-time facts goes through `output.presentationMeta`.
- **dsh web does not consume `presentCall` / `presentResult`.** The Web Client derives
  its card from a Client plugin registered in the `tool.call.toolview` slot plus the
  persisted `result.meta`. Host presenters alone add no Web card (#40). The rest of
  the UI is equally open — `docs/subsystems/slots.md` lists about fifty slots, and
  `conversation.approval.detail` is where a Web Client would render the correlated
  tool call. **We do not use it.** `@deepseek-ai/dsh-client-ui-approval` ships that
  panel, but it is a browser plugin for the `web` profile, and this project drives
  `sdk-minimal` headless. The answerable seam underneath is a plain Host-side cordis
  waterfall — `ctx.on('approval/request', (req, next) => …)` — so `src/approval/`
  listens on it directly and sends the question to our own console (#30).
- **Return one canonical JSON value**, not content blocks and not prose to be parsed.
  `output.render` owns the model-facing wording.
- **Honor `exec.signal`.** Cancel in-flight work when it fires.

## Verified end to end

With both patches applied and the Python service running, asking for the November
production total returns **4,030 units and names the five rows it came from**. That is
the shape `docs/04` beat 5 needs and did not have: a figure a judge can follow back to
a cell.

Refusals work too. The model tried two invented metric names first, was refused with
409, and was told to call `list_metrics` — rather than being handed a plausible number.

And a write waits for a person. In one live turn the model called `confirm_mapping`,
the question reached the console in 3.1s, a click released it, and the turn ended at
4.0s with the mapping on disk carrying `authorised_by`. Clicking 拒绝 instead ended the
turn just as cleanly with nothing written. The third path — nobody there at all — is the
one #39 measured: `requires approval, but no approval channel is available`.
