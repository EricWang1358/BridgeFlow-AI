# BridgeFlow AI

> A multi-agent engine that turns messy monthly spreadsheets from Production, Procurement,
> Finance and Marketing into one aligned Master Table — with real-time risk warnings and
> dynamic quote simulation.

**How might we** build a multi-agent AI engine for Singaporean SMEs to align unstructured
monthly data across production, procurement, finance and marketing, in order to eliminate
data silos, trigger real-time risk warnings, and optimize dynamic quotes?

---

## The problem

A typical Singaporean SME runs on four disconnected spreadsheets:

| Department  | What they track            | Granularity        | Key that never matches |
| ----------- | -------------------------- | ------------------ | ---------------------- |
| Production  | Output, capacity, downtime | Per SKU, per day   | `SKU-A1`               |
| Procurement | Raw material purchases     | Per material, weekly  | `RM-Alu-6061`          |
| Finance     | Revenue, cost, AR ageing   | Per GL account     | `4000-Sales`           |
| Marketing   | Orders, customers, quotes  | Per customer/month | `Acme Pte Ltd`         |

Nobody can answer "is this customer actually profitable at our current aluminium price and
capacity?" without a week of manual reconciliation. BridgeFlow AI answers it in minutes.

## Architecture

```
[Messy multi-department data]  (Production / Procurement / Finance / Marketing — monthly CSV & Excel)
                │
                ▼
┌──────────────────────────────────────────────────────────────────┐
│ 1. Data Sanitizer Agent                                          │
│    - Fixes typos, mixed formats, shifted columns, missing values  │
│    - Parallel monthly ingest; time-series gap-fill & normalization│
└──────────────────────────────────────────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────────────────────────┐
│ 2. Semantic Resolver Agent            ★ core                     │
│    - Cross-department entity & time mapping                       │
│    - SKU ↔ raw material ↔ GL account ↔ capacity consumption       │
└──────────────────────────────────────────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────────────────────────┐
│ 3. Multi-Role Evaluator Agent         ★ core                     │
│    - Production view : order trend, capacity utilisation & headroom│
│    - Finance view    : loss-making projects, AR ageing, bad debt   │
│    - Procurement view: material price trend, purchase cost drift   │
│    - Marketing view  : customer tiering under capacity constraints │
└──────────────────────────────────────────────────────────────────┘
                │
        ┌───────┴────────┐
        ▼ (core output)   ▼ (triggered sub-feature)
┌────────────────────┐  ┌────────────────────────────────────┐
│ 4. SOP & Flow      │  │ ✨ Dynamic Quote Simulator          │
│    Engine          │  │    Marketing-facing: simulates      │
│  - Month/Qtr/Year  │  │    material price × capacity to      │
│    Master Table    │  │    output an optimal price and       │
│  - Risk report &   │  │    payment-term recommendation       │
│    approval cards  │  └────────────────────────────────────┘
└────────────────────┘
```

Full detail: [`docs/02-architecture.md`](docs/02-architecture.md). If we adopt
[deepseek-harness](https://github.com/deepseek-ai/deepseek-harness) as the agent framework,
see [`docs/06-deepseek-harness.md`](docs/06-deepseek-harness.md) for how it layers on top.

## Repo layout

```
backend/          Python 3.12 — agents, LLM provider layer, FastAPI
  src/bridgeflow/
    agents/       One module per agent in the diagram
    llm/          Pluggable provider layer (hermes / deepseek / openclaw / mock)
    schemas/      Pydantic data contracts shared across agents
    pipeline/     Orchestrator wiring agents 1→2→3→4
    api/          FastAPI app
plugins/          TypeScript dsh plugins — tools, guards, UI cards (to be written)
data/samples/     Deliberately messy sample CSVs for the demo
docs/             Problem framing, architecture, data contracts, demo plan
```

There is no `frontend/` directory. The UI is dsh web, customised through Client
plugins rather than rebuilt — see [`docs/13-golden-standard.md`](docs/13-golden-standard.md).
The one screen that exists today is the operator console at `/console`, served by the
backend because it has to answer a tool call that is blocked waiting on it.

## Quick start

Development happens inside WSL or on Linux. Full setup, with a verification step
for each stage: [`docs/14-wsl-setup.md`](docs/14-wsl-setup.md).

```bash
source ~/Hackathon2026/.venv/bin/activate
source ~/Hackathon2026/BridgeFlow-AI/env.sh    # DSH_* must come from the shell

cd backend
pytest -q && ruff check src tests
python ../scripts/smoke_dsh.py                 # checks the dsh runtime end to end
uvicorn bridgeflow.api.main:app --reload
```

Then open <http://127.0.0.1:8000/console> and leave it open. Anything that writes stops
there for a decision; if nobody is watching, it is refused rather than performed.

`DSH_*` and `DEEPSEEK_BASE_URL` belong in `env.sh`, never in `backend/.env` — dsh
scans that file and refuses bootstrap and network variables read from it, because a
checked-in file must not be able to decide where code loads from or where traffic
goes.

The default `LLM_PROVIDER=mock` runs the whole pipeline with deterministic canned
responses — no API key, no network — so tests and rehearsal never depend on
connectivity. Its output is placeholder text, so it is not what you demo.

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
state in this codebase — roughly 25% covered, concentrated in the agent pipeline rather
than in the auditability the PRD actually centres on. Read it before picking up work.

## Status

Early hackathon scaffold. Track work on the
[project board](https://github.com/users/EricWang1358/projects/1).
