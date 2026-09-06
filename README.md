# BridgeFlow AI

BridgeFlow turns monthly Production, Procurement, Finance and Marketing spreadsheets
into immutable batches and evidence-backed business reviews. The MVP reuses the
official DeepSeek Harness Web, approvals, sessions and four concurrent subagents.
Python computes declared metrics; each department proposes actions within a stated
responsibility, and the host validates its structured findings.

The current demo covers production load, purchase spend against budget, project
margin, weighted payment terms and order/output gaps. Generated risk and balanced
cases have independent standard answers. Quoting, customer tiers, bad-debt decisions,
SSO and formal report release are outside the delivered MVP.

See the [business demo and acceptance guide](docs/17-business-mvp-acceptance.md),
[measured results](docs/00-status.md), and [architecture decisions](docs/13-golden-standard.md).

## Architecture

```text
Official DSH Web: native chat, sessions, approvals, trajectory
  └─ BridgeFlow slots: import/data, rejection note, review cards
       └─ Typed domain tools + host policy
            ├─ Python: immutable batches, dictionary, arithmetic, validation
            ├─ Official DSH spawn: production / procurement / finance / marketing
            └─ Native approval → one-use receipt → mapping memory
```

Reports preserve the batch, source locations and child session identities. Failed
reviewers remain visibly incomplete. Proposed business actions are not executed.

## Repo layout

```text
backend/          Python domain computation, persistence and private FastAPI service
plugins/          DSH tools, guards, native approval integration and Client UI slots
dsh/              Pinned Web policy patch and restricted analyst preset
scripts/          Native Web launcher and runtime checks
data/samples/     Historical development spreadsheets
data/business_demo/ Generated visible business cases and independent answers
docs/             Requirements, architecture, measured status and review
```

## Quick start

From the repository root, with the Python dependencies installed:

```bash
source ../.venv/bin/activate
source ./env.sh
npm install -g @deepseek-ai/dsh@0.1.2-rc.1
cd plugins
pnpm install --frozen-lockfile
pnpm run build
cd ..
python scripts/start_web.py
```

Open the authenticated URL printed by DSH. Use the sidebar data action to upload
CSV or a single-sheet XLSX, inspect the batch, then copy its analysis request into
the native conversation. Import is deterministic; sending a conversation request
can incur model charges. Declare `FIELD_DICTIONARY_PATH` in the launching shell;
for the business MVP rehearsal use `data/business_demo/dictionary.yaml`.

The launcher uses the official npm CLI, pinned to the Python SDK version. The rc1
Python-packed executable failed to resolve the built-in Web client manifests in
our browser test. `BRIDGEFLOW_DSH` can select a compatible npm executable.

`DSH_*` and `DEEPSEEK_BASE_URL` belong in the launching shell, never `.env`.
The launcher generates a private host-service credential, reuses native Web
authentication, and defaults legacy console/pipeline/sample fallback off. Mapping
writes require a native approval and a one-use payload-bound receipt. Authentication
currently identifies a shared DSH session, not an individual employee or tenant.

Full setup and reproducible checks: [`HANDOFF.md`](HANDOFF.md).

### Portability

- `.gitattributes` normalises everything to LF, so files authored on Windows do not
  arrive on a Linux box with CRLF.
- Bind address, port and CORS origins are settings, defaulting to `127.0.0.1` —
  nothing is exposed unless asked for explicitly.
- No absolute paths, drive letters or Windows-only dependencies in tracked source.

Deployment is not configured: no Dockerfiles, no CI. The target is undecided, and
adding either before that is settled was a mistake this repository already made
once.

## Requirements baseline

The business requirements live in [`docs/07-prd-v0.1.md`](docs/07-prd-v0.1.md) (PRD v0.1).
[`docs/08-prd-traceability.md`](docs/08-prd-traceability.md) maps every FR to its current
state at its review date. Current evidence and remaining rubric gaps are recorded in
[`docs/00-status.md`](docs/00-status.md) and [`docs/16-dsh-web-review.md`](docs/16-dsh-web-review.md).

## Status

Business-use-case demonstration MVP with live-model and browser evidence. Real customer data and enterprise deployment still require validation. Track work on the
[project board](https://github.com/users/EricWang1358/projects/1).

业务演示入口：[一站式 Demo](demo-walkthrough/README.md)；界面为「对话｜轨迹｜业务状态」，右上角可选取部门文件。原生队长与会话保留策略见 [18](docs/18-native-captain-and-state.md)，最新实测见 [00](docs/00-status.md)。
