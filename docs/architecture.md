# Architecture

## Components

| Component | Responsibility |
| --- | --- |
| Official DeepSeek Harness | Web UI, sessions, tool dispatch, native approvals and department subagents |
| `plugins/` | Typed domain tools, guards, approval integration and the Web workspace |
| `backend/` | Deterministic imports, business-rule calculations, validation, provenance, workflows and API |
| `portal/` | Optional Feishu OAuth login and short-lived application identity tokens |
| `data/` | Declared example dictionaries, templates and sample datasets |
| `deploy/` | Self-hosting templates and deployment helpers |

The default entry point is `scripts/start_web.py`. The launcher starts the backend and the native Web runtime using the same installation and host credential. The project extends the official runtime; it does not fork it.

## Data and review flow

1. Import department files under a declared dictionary and preserve source provenance.
2. Clean and validate data, isolate invalid rows, and record unresolved questions.
3. Produce a master table and bounded metric summaries using deterministic Python code.
4. Dispatch four department agents through the official subagent mechanism.
5. Validate findings against evidence and declared calculation rules before accepting them.
6. Present findings, approval requests, reports and exports in the workspace.

AI agents receive bounded summaries and source references rather than entire raw data tables. A dictionary declares fields, joins, aggregation and derived metrics. Missing declarations cause a configuration or review question rather than an invented rule.

## Human decisions

Model-initiated writes require native approval and host-side permission checks. The approval receipt is bound to the request. A rejection must not perform the write. Dictionary drafts require entry-by-entry decisions before publication; publishing affects later imports, while existing batches keep their frozen snapshots.

Discovery decisions may define the scope of a filling-and-handoff workflow. Revised or withdrawn decisions invalidate stale scope. Notebook-specific sources and batches are separate from shared discovery and workflow records.

## Identity and hosting

The optional portal verifies Feishu identity and issues short-lived signed application tokens. Role grants derive from explicitly configured wiki membership. The public source contains a placeholder access-control example; actual wiki IDs and seat assignments remain installation-local.

Guest mode has its own data and runtime home. When guest AI is enabled, a local model gate applies configured model, request-size, token, rate and concurrency limits; provider credentials stay in the gate process.

See [Deployment](deployment.md) for configuration and [Limitations](limitations.md) for the boundaries of the implementation.
