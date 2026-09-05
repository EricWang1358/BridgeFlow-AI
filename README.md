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
frontend/         TypeScript / Next.js — Master Table dashboard + quote simulator
data/samples/     Deliberately messy sample CSVs for the demo
docs/             Problem framing, architecture, data contracts, demo plan
```

## Quick start

Target runtime is **Linux (AWS EC2)**. Docker is the path that behaves the same on
Windows, WSL and the server:

```bash
cp backend/.env.example backend/.env
docker compose up --build
# backend  http://localhost:8000/health
# frontend http://localhost:3000
```

Running natively instead:

```bash
# Backend — Linux / WSL / macOS
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn bridgeflow.api.main:app --reload

# Backend — Windows PowerShell
#   py -3.12 -m venv .venv; .venv\Scripts\Activate.ps1

# Frontend
cd frontend
npm install
npm run dev
```

Run the tests with `pytest` from `backend/`.

The default `LLM_PROVIDER=mock` runs the whole pipeline with deterministic canned
responses — no API key, no network — so the demo always works offline.

### Cross-platform notes

- `.gitattributes` normalises everything to LF, so files authored on Windows don't
  arrive on the EC2 box with CRLF.
- No `os.path` string joining, no drive letters, no Windows-only dependencies — the
  backend runs unchanged on Linux.
- The Dockerfiles build from the repo root as context; `docker compose` sets that up.

## Requirements baseline

The business requirements live in [`docs/07-prd-v0.1.md`](docs/07-prd-v0.1.md) (PRD v0.1).
[`docs/08-prd-traceability.md`](docs/08-prd-traceability.md) maps every FR to its current
state in this codebase — roughly 25% covered, concentrated in the agent pipeline rather
than in the auditability the PRD actually centres on. Read it before picking up work.

## Status

Early hackathon scaffold. Track work on the
[project board](https://github.com/users/EricWang1358/projects/1).
