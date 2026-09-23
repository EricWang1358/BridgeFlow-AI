<p align="center"><strong>English</strong> · <a href="README.zh.md">简体中文</a></p>

# BridgeFlow AI

BridgeFlow reads the monthly spreadsheets that Production, Procurement, Finance and Marketing each
keep in their own way, and turns them into an immutable batch plus a business review that shows its
evidence. It runs on the official DeepSeek Harness: native Web UI, sessions, approvals and four
concurrent subagents. Python does the arithmetic the field dictionary declares; each department agent
proposes actions inside its stated responsibility, and the host checks the structured findings before
anything lands in a report.

This README is a guided walkthrough. Follow it top to bottom and you will have the product running,
one review completed end to end, and one mapping decision recorded, on a machine you have never used
before. Nothing is assumed beyond "you can open a terminal".

- [What is built today, and what is not](#what-is-built-today-and-what-is-not)
- [Before you start](#before-you-start)
- [1 Set up the machine](#1-set-up-the-machine)
- [2 Install](#2-install)
- [3 Configure the launching environment](#3-configure-the-launching-environment)
- [4 Build the plugins](#4-build-the-plugins)
- [5 Start it](#5-start-it)
- [6 Tour of the workspace](#6-tour-of-the-workspace)
- [7 The fastest complete loop](#7-the-fastest-complete-loop-the-sample-notebook)
- [8 Import your own files](#8-import-your-own-files)
- [9 Run the review](#9-run-the-review)
- [10 Read the report and trace one number](#10-read-the-report-and-trace-one-number)
- [11 Mapping approval](#11-put-a-human-in-the-loop-mapping-approval)
- [12 Save, leave, come back](#12-save-leave-come-back)
- [13 The quotation workspace](#13-the-quotation-workspace)
- [14 Check your install](#14-check-that-your-install-is-healthy)
- [15 When something does not work](#15-when-something-does-not-work)
- [16 Worked examples](#16-worked-examples)
- [Where the real documentation is](#where-the-real-documentation-is)

## Project status (2026-09-23, due 27 September)

"Offline" means the scripted test model (free and repeatable, used for regression); "real model" means the DeepSeek model configured in `env.sh` (`deepseek-v4-flash` this round). Every number and how to reproduce it is in [`docs/00-status.md`](docs/00-status.md); evidence files are in `docs/evidence/`.

| Area | Status | Evidence | Still missing |
| --- | --- | --- | --- |
| Monthly review: import four department files, clean, quarantine, build the master table | ✅ Built | All offline journeys pass; each of the three demo cases shows its intended state | Real customer exports (#141) |
| Cross-department master table aligned by the dictionary, every cell traceable | ✅ Built | Guided tour 12/12 steps; `test_demo_cases.py` | — |
| Four-department review: the captain dispatches four department sub-agents in parallel; the host validates | ✅ Passes on the real model | Risk / balanced / cell-injection cases all validated 4/4, 12–19 s, 70–110k tokens each (`docs/evidence/live-2026-09-23/`) | Real samples from more industries |
| Monthly brief: one-line conclusion, attention-item logic chains, evidence grades, Word export | ✅ Built (offline) | round1 journey; a test pins each attention formula to its key metric | Reviewing briefs on the real model |
| Dictionary drafted by the model, reviewed entry by entry, published as a version (#205) | ✅ Built (offline) | Draft lifecycle tests | A real drafting run; three open business questions |
| Filling and handoff workflow (Agent 2): ask for missing items → approve and submit → record → hand over → next team starts / completes; notices go out on submission | ✅ Runs end to end on the real model | Workflow journey: 4 native approvals, 12 model requests, 42.5 s; the flow strip and the sample workflow | Template-governance consumer; a real notification channel |
| Materials → candidates → flow graph → scoring → meeting → MVP decision (Agent 1) | ✅ Built (offline) | web journey, whole chain | Real business materials |
| Adoption (Agent 3): role guidance, adoption signals | 🟡 Partial | Guidance generated from declared templates | Pilot pages, feedback handling, retrospectives |
| Quotation workspace | 🟡 Declared drafts | quotation journey | Extraction from real files; external release |
| Human in the loop: every write needs a native approval; a rejection writes nothing | ✅ Built | Every write tool; approvals exercised in the real-model review and workflow runs | Risk tiers (today: read / approval only) |
| Safety: raw data rows never enter model context (three layers), prompt-injection defence | ✅ Built | Injected cell text reached no model session on the real model; bilingual injection cases | Third-party penetration test |
| Observability: decision journal, per-run swimlanes with tokens, generated acceptance report 31/31 | ✅ Built | Records page; `test_journal.py` | — |
| Tool-selection evaluation (real model; first step among ~50 tools) | ✅ 15/18 (83%) | All 18 cases ran; median 3 steps, ~39k tokens; the three misses each have a reasoned explanation (docs/00) | More cases |
| Model choice | ✅ dsh's own picker | Chooses among operator-configured models; adding providers or keys stays off | — |
| Deployment: merge triggers tests and deploy, 7 seats | ✅ Live | GitHub Actions | Manual steps such as enabling the console gate (see HANDOFF) |
| Feishu sheets / wiki / permissions | 🟡 In integration | Metadata and membership reads verified on the real tenant | End-to-end import, large-sheet paging (out of this round) |
| 200k-row scale | 🟡 Measured; does not fit current limits | CSV is 34 MiB, over the upload cap; XLSX expands to 176 MiB, over the guard; with limits raised CSV imports in 81–86 s at 1.2–1.6 GB peak, tool outputs ≤37 KB | Limits and memory budget are the owner's call (#228) |

All sample data is fictional. Real customer exports, business confirmation of the assumed conventions and real enterprise acceptance are still outstanding.

## Demo cases and tests

Some states conflict (a batch that is ready cannot also be held back), so the demo is several cases, each opened from Sources → Open sample notebook / More sample cases into its own notebook.

| Case | Shows | What you should see |
| --- | --- | --- |
| Guided sample (concrete supplier, 2024-07) | The in-page tour "combine & verify" | Ready; one customer-name mismatch in the master; three metrics over threshold |
| Many problems at once | Several kinds of problem together | Needs review; one row quarantined (text in a money field); missing-department, cannot-compute and other open items together; review held back |
| A different set of problems | Errors that do not overlap the previous case | Needs review; three named review blockers (negative quantity, a June row, a renamed column), one column question, a missing template column |
| All clear | What everything-right looks like | Ready; nothing open; all 10 checks inside their thresholds |
| Sample workflow ("Load the sample workflow" on Filling & handoff) | The workflow end to end | One record missing its actual quantity, one awaiting review; the captain asks, submits and hands over, each step on your approval |
| Try it yourself (`data/mock_business/try-it-2024-08/`) | Manual upload, one-department correction, refusals | See that folder's README |

| Test | Checks | Mode | Result |
| --- | --- | --- | --- |
| Backend `pytest` | Rules, contracts, demo-case expectations, workflow state machine | Offline | All pass (counts in docs/00) |
| Plugin unit tests | Tool catalogue, copy keys, ids and versions in tool output | Offline | All pass |
| `tour-smoke` / `round1-journey` / `web-smoke` / `quotation-smoke` / `cases-journey` | Tour, brief, discovery chain, quotation and notebooks, the three cases | Offline browser | All pass |
| `business-smoke` (risk / balanced / injection / department failure) | Four-department review and cross-operation chain | Offline browser; the first three also on the real model | All pass |
| `workflow-journey` | Filling and handoff end to end | Real model | Passes |
| `tool-selection-live` | Does the captain pick the right first tool | Real model | 15/18 |

## Before you start

**Public demo.** The deployed instance lives at <https://47.130.178.176.sslip.io/> (AWS Lightsail,
`47.130.178.176`), with the sign-in portal at <https://portal.47.130.178.176.sslip.io/>. Merges to
`main` deploy to it automatically ([docs/22](docs/22-lightsail-deploy.md)).

**What this is.** A business-use-case demonstration built for a hackathon. The data on screen is
generated and labelled synthetic. It is not a certified enterprise deployment. On the deployed
instance, sign-in is per-employee Feishu OAuth through the portal; data routes carry that identity,
and an access-control map resolved live from Feishu wiki membership decides which batches and
operations each employee may touch — an invisible batch answers 404, and every write still waits on
a native approval. Still missing: per-employee isolation of the native chat session and of
model-side reads, personal audit of rejections, and formal report sign-off — no full multi-tenant
boundary is claimed. Locally, following this guide without the portal keeps the identity layer off
(one shared DSH session, recorded as `dsh-authenticated-session`).

**What costs money.** Importing files and computing the master table are deterministic and free.
Starting a review sends a request to the configured model, and that bills. One review of the sample
case takes tens of seconds and tens of thousands of tokens; measured figures live in
[`docs/00-status.md`](docs/00-status.md), which is the only place a measured number is written.

**About the screenshots.** All were retaken on 2026-09-24 on the current interface. Most come from an
English-locale offline run; 05–07 and 08 come from runs on the real model and show the Chinese UI. The mapping: 来源 = Sources, 工作室 = Studio,
对话 = Chat, 轨迹 = Trajectory, 业务状态 = Business state, 发起研判 = Start the review, 主表 = Master
table, 待确认映射 = Mappings awaiting confirmation, 隔离行 = Quarantined rows, 清洗记录 = Cleaning log,
添加来源 = Add sources, 打开示例笔记本 = Open sample notebook, 新建笔记本 = Create notebook,
保存笔记本 = Save notebook, 退出笔记本 = Exit notebook, 会话与设置 = Sessions & settings,
允许一次 = Allow once, 拒绝 = Reject, 拒绝理由 = Rejection reason.
[`docs/images/README.md`](docs/images/README.md) records the provenance of every image.

## 1 Set up the machine

Works on Linux and on WSL2 (Ubuntu). On Windows, use WSL2 and read
[`docs/14-wsl-setup.md`](docs/14-wsl-setup.md), which gives every step a verification command.

One rule saves you days: keep everything inside the Linux filesystem (`/home/...`), never under
`/mnt/...`. Across `/mnt`, inotify silently stops working, permission bits are lost and I/O is an
order of magnitude slower; the same runtime takes seconds longer to boot.

The layout this guide assumes:

```text
~/Hackathon2026/
├── BridgeFlow-AI/     the repository (source only)
├── .venv/             Python virtualenv, deliberately outside the repo
└── .dsh-bridgeflow/   DSH_HOME, outside the repo and outside your everyday dsh
```

Virtualenv and DSH_HOME sit outside the repository so they can never be committed by accident.
Source goes in; runtime state does not.

## 2 Install

```bash
mkdir -p ~/Hackathon2026 && cd ~/Hackathon2026
gh repo clone EricWang1358/BridgeFlow-AI      # private repo: run `gh auth login -s project` first
                                                 # (no gh? `git clone https://github.com/EricWang1358/BridgeFlow-AI` with a token)
cd BridgeFlow-AI

python3.12 -m venv ../.venv && source ../.venv/bin/activate
pip install -U pip
cd backend && pip install -e ".[dev]" && cd ..

npm install -g @deepseek-ai/dsh@0.1.2-rc.1    # the pinned npm CLI, not the Python-packed binary
```

The virtualenv is created at `~/Hackathon2026/.venv` while you are inside the repository, and every
later command in this guide assumes both `source ../.venv/bin/activate` and `source ./env.sh` have
been run in the current shell. A new terminal window means doing both again.

Check it worked:

```bash
python -c "import bridgeflow, pandas, fastapi, deepseek_harness; print('imports ok')"
dsh --version
```

The project runs on Python 3.12 (`requires-python = ">=3.11"`, because the code uses
`datetime.UTC`). Running the SDK needs no system Node.js, but building the Client plugins needs npm
and pnpm.

## 3 Configure the launching environment

```bash
cp env.sh.example env.sh
$EDITOR env.sh        # set DEEPSEEK_API_KEY, and DSH_HOME if the default is not what you want
source env.sh
```

| Variable | What it does |
| --- | --- |
| `DSH_HOME` | Where dsh keeps profiles, plugins, credentials and sessions. Absolute path, outside the repository. Required: the SDK deliberately never discovers `~/.dsh` |
| `DSH_PROFILE` / `DSH_PROVIDER` / `DSH_MODEL` | Which composition, provider and model the runtime boots with |
| `DEEPSEEK_API_KEY` | The model credential |
| `FIELD_DICTIONARY_PATH` | The domain dictionary: which column of which department holds which entity, what may be computed, and how it rolls up |

`DSH_*` and `DEEPSEEK_BASE_URL` may only come from the launching shell. dsh scans `.env` in its
working directory and refuses to read them from a file, and that is a security boundary: if a
checked-in file could decide where code loads from and which host it reaches, cloning a hostile
repository would be enough to redirect both. Do not work around it, for example by changing the
runtime's working directory. An empty line `DEEPSEEK_BASE_URL=` still counts as set.

`FIELD_DICTIONARY_PATH` defaults to `data/mappings/field-dictionary.yaml`. That file is gitignored
and holds real master data, so a fresh clone does not have it, and the product says so instead of
guessing. To follow this guide with the sample case, either start with `--demo` (step 5) or export:

```bash
export FIELD_DICTIONARY_PATH=data/mock_business/demo/dictionary.yaml
```

## 4 Build the plugins

```bash
cd plugins
pnpm install --frozen-lockfile
pnpm run build
cd ..
```

The Client bundle has to exist before the Web starts; the launcher tells you if it is older than the
sources.

## 5 Start it

```bash
python scripts/start_web.py --demo --port 3082
```

`--demo` points the domain service at the sample case's own dictionary and prints which one it froze:

```text
BridgeFlow field dictionary: /home/you/Hackathon2026/BridgeFlow-AI/data/mock_business/demo/dictionary.yaml
```

The launcher starts a private Python service on port 8000 (localhost only) and the official
`dsh web` on the port you passed. It prints a URL carrying a one-time credential: open that URL in
your browser. `Ctrl-C` stops both processes it started.

Why `--demo` matters: the sample case only holds together under its own dictionary, the only one
that declares the finance join column (`project`) and the `business_review` contract. With the
default dictionary the import still succeeds, the batch comes back `needs_configuration` and the
review refuses. Step 1 passes, step 2 cannot. That is by design: the product states what is missing
rather than inventing a join.

## 6 Tour of the workspace

![The three-pane workspace, empty](docs/images/01-notebook-empty.png)

Three columns, and the split between them is the design:

| Pane | Holds | Who owns it |
| --- | --- | --- |
| Left · 来源 Sources | The files you actually uploaded here, previewable | BridgeFlow panel |
| Middle · Chat | The native DSH conversation, composer and approvals | DSH, untouched |
| Right · 工作室 Studio | Domain tools on top, saved artifacts below, previews underneath | BridgeFlow panel |

Top bar, left to right: 新建笔记本 Create notebook (a fresh session with its own sources) ·
保存笔记本 Save notebook (explicit; nothing is saved silently) · 笔记本 Notebooks (list and resume) ·
退出笔记本 Exit notebook · 来源 / 工作室 (show or hide the two side panels) · 会话与设置 Sessions &
settings (the native drawer; sessions and settings stay native).

The 笔记本用途 / Notebook purpose selector at the top of Sources decides which status guidance the
right pane shows: 月度对账 monthly review, 报价 quotation, or 综合工作 combined. Monthly review and
quotation stay separate paths; choosing one does not disable the other.

Drag the dividers to resize, focus one and use the arrow keys, double-click to reset. Panel
preferences are stored in the browser only.

![Guided tour welcome card](docs/images/14-guided-tour.png)

The first time you open the workspace, a welcome card offers a guided task: open the sample notebook,
read the cross-department master table, follow one number to its original file, download the workbook
and save the notebook. Each step only advances when the real action succeeded. **Help & guided tours**
in the top bar resumes it, replays it, or explains the department review and the quotation path. The
tour covers the monthly review only; the workflow features (discovery, filling & handoff) are not in it.

## 7 The fastest complete loop: the sample notebook

Click **Open sample notebook** in the left pane. It imports four department workbooks of a fictional
concrete supplier for `2024-07`, filled in on the business side's v2 department templates, runs the
normal import and rule computation, and freezes the sample dictionary for that batch. No model call
happens, so this costs nothing.

![Sample notebook: four sources and the master table artifact](docs/images/02-sample-sources.png)

What you should see:

1. Left: four sources, `模拟-生产部-2024-07.xlsx` (production, 21 daily rows) and procurement, finance
   and marketing with 4 rows each (one per project), the period `2024-07`, a **Ready** badge, and the
   batch id.
2. Right: under **Artifacts**, `2024-07 · Master table` with 4 rows.
3. A **Preview** of the selected source: the parsed original with its row numbers and column names.

Open the file provenance to see which file, batch, worksheet and SHA-256 digest the preview belongs to.

![Source provenance labels](docs/images/03-source-provenance.png)

### The cross-department master table

Click **Cross-department master** in Studio.

![Cross-department master table with an open question and one cell's evidence](docs/images/12-cross-department-master.png)

This is the 76-column table the business side designed, built from the four templates exactly as
their dictionary (v2) says: rows meet on project code, customer code and report month; the formulas the
dictionary states are computed and compared with what departments wrote; nothing the dictionary does
not state is invented.

- **3 / 4 complete rows · 1 open question.** Production wrote the customer's short name for one
  project. The cell is left empty and the question lists what each department wrote, so a person
  decides; the system does not pick a spelling.
- **Conventions filled in where the dictionary is silent (4).** VAT rate 13%, the collection-gap
  formula, the customer-diagnosis thresholds and how daily production rows roll up. Each is written in
  `data/company_templates/integration.yaml` and marked on every cell that depends on it, until the
  business side confirms or replaces it.
- Click a number to see its evidence: department, file, sheet, row and header, or the formula and its
  inputs. **Open original source** shows that row in the uploaded file. **Download master xlsx** exports
  the table with an open-items sheet and a conventions sheet.

### The batch data

Now open the master table: click the artifact, or 主表 in the tool grid.

![Batch modal: master table, cleaning log, pending mappings, quarantined rows](docs/images/04-batch-master-table.png)

The batch modal is where you decide whether the data is fit to review:

- **主表 Master table** — one aligned wide table, joined on the column the dictionary declared
  joinable. The `rollups` column shows how multiple source rows were folded, because folding is a
  declared decision rather than a default.
- **清洗记录 Cleaning log** — every repair, with original value, new value, rule and confidence.
- **待确认映射 Mappings awaiting confirmation** — relations below the confidence threshold, waiting
  for a person. "Awaiting confirmation" is not "wrong".
- **隔离行 Quarantined rows** — rows the system refused to guess at. A batch with quarantined rows
  refuses to report totals; that is the amber 下一步 box in the screenshot.
- Buttons: **发起研判 Start the review** sends the request into the current session;
  改一改再发（复制） copies it so you can edit first; 刷新 Refresh.

## 8 Import your own files

Use the department workbooks in `data/mock_business/monthly/` (three months of the fictional
supplier, with planted filing errors in June and July), or your own files on the templates in
`data/company_templates/source/`.

1. In Sources, click 添加来源 / Add sources.
2. Pick the business month (`2024-07`) and the department files. One file per department, CSV or
   XLSX. If a workbook has several sheets, or its header is not on row 1 (a merged title row above the
   header, as in the business side's v1 procurement template), the import refuses and says which sheets
   exist or which row looks like the header; fill in **Table position (optional)** for that file, or
   declare `sheet_layout` in the dictionary.
3. Click 导入并检查 Import and inspect. The batch id appears in the left pane; copy it if you want to
   refer to it in chat.
4. Open the batch modal and read the four tabs before going any further.

What a broken cell does to a batch is not hypothetical; four worked cases are in
[section 16, example 5](#16-worked-examples).

Limits are enforced on total bytes, decompressed size, department count and row count. The browser can
page through the data; the model never receives raw rows, only counts, formulas and a capped evidence
sample. Being able to see a page of data is a viewing feature, not a performance claim.

If the batch comes back `needs_configuration`, the dictionary declares no joinable column for one of
the departments. Under 「为什么主表是空的」 the panel prints which dictionary was frozen for this
batch; if that is not the file you meant, you have found the whole bug. If the dictionary itself is
what is missing, nobody hand-edits YAML any more: give the captain the business's OA dictionary
spreadsheet to transcribe (`dictionary_import`), or let it draft from the batch's column profiles
(`dictionary_draft`), decide every entry in the approval — a measure also needs its rollup — and
publish (`dictionary_publish`); the version affects later imports only.

## 9 Run the review

Click 发起研判. The request goes into the current session, so you can watch it in Chat and in
轨迹 Trajectory. This step calls the configured model and bills.

![Trajectory: review_context, four subagent calls, review_finalize](docs/images/06-trajectory-four-spawns.png)

*Captured on the real model, 2026-09-23.*

What happens, in order:

1. `review_context` reads the frozen batch packet and issues four one-use dispatch tickets.
2. The captain model calls the official `subagent` tool **four times in one response**, described as
   production, procurement, finance and marketing. The header shows four child sessions; each has its
   own session id, and the timeline shows they really overlap.
3. Each child may only submit `structured_output`. It has no shell, no editor, no code execution, no
   channel to the other three, and cannot read the parent conversation or the raw workbook.
4. `review_finalize` collects what the host actually recorded. The parent model cannot upload four
   judgements of its own and pass them off as children's results.
5. Python re-checks every value, unit, status, action and citation against the frozen dictionary.
   Anything that fails leaves that department unvalidated and the report `partial`.

A department that keeps producing invalid structure is stopped by the step budget (3 steps). The
report then says that department has no valid judgement, keeps the other three, and does not
manufacture a substitute.

Worked version of this whole loop, including doing the arithmetic by hand first:
[section 16, example 1](#16-worked-examples); the failure path is
[section 16, example 6](#16-worked-examples).

## 10 Read the report and trace one number

![Report preview: formula, threshold and responsibility](docs/images/05-report-preview.png)

The report header states its own scope: proposals only, nothing executed, model prose needs a business
reviewer, "cited N times" is not "N distinct cells", and a capped display is not a sample-only
computation. Read that line before you read any number.

Each department card shows the responsibility, the decision owner, the metric with its value, the
suggested action, the formula exactly as the dictionary declares it, and the attention threshold.
Expand 解释与原始来源 for the citations.

To trace a number properly:

1. Take the value, for example 排产负荷 110%.
2. Read its formula: `sum(used hours) / sum(available hours) * 100`, threshold `> 100%`.
3. Expand the citations and note the file, the original row and the original column.
4. Open that source on the left and go to the row. Original row numbers survive blank-row removal,
   de-duplication and quarantine, so the citation still points where it pointed at import time.

![Business state page](docs/images/07-business-state-page.png)

*Captured on the real model, 2026-09-23.* The 业务状态 tab is a status view of the batch, not a workflow engine: nodes
highlight according to what actually happened, clicking filters, and nothing on the page executes a
business action.

Worked examples of tracing a number down to its cells: [section 16, example 2](#16-worked-examples),
and the same code over two different months in [example 3](#16-worked-examples).

Vocabulary, with the traps in it:

| Token | Means | Does not mean |
| --- | --- | --- |
| `needs_configuration` | The dictionary does not declare what is needed | That the import failed. It did not fail |
| `needs_review` | Mappings are awaiting a person | That business computation is forbidden. This sample computes declared columns directly and can produce a validated report while links are pending |
| `validated` | All four departments' judgements passed the dictionary check | Approved, signed off, or executed |
| `partial` | At least one department has no valid judgement | A warning to wave away. It is the honest state |
| `attention` | A declared threshold was crossed | That anyone did anything about it |

## 11 Put a human in the loop: mapping approval

Paste this into the session (swap the batch id if you need to):

> 请仅调用一次 confirm_mapping：source="sku:demo-review"，target="customer:demo"，
> relation="ordered_by"，accepted=true，evidence="合成案例的关系待负责人核对"，period="2025-11"。
> 等待原生审批；若拒绝，说明未写入并转述操作者理由，不重试。

The tool call blocks and the native approval panel opens with the arguments visible, a rejection
reason box (240 characters maximum), the deadline, and two buttons: 拒绝 Reject and 允许一次 Allow
once.

![Approval panel with rejection reason](docs/images/08-approval-rejection-note.png)

*Captured on the real model, 2026-09-24: the card lists the draft values being approved, how each was read, its source and any flagged check.*

- **Allow once** writes one mapping rule bound to exactly these parameters, through a one-use receipt
  the host generated after the decision. Replays are refused.
- **Reject** writes nothing, and your reason goes back to the model, which must relay it. The wording
  in the tool result says the write did not happen and that future imports may ask again.
- **Nobody answers** (timeout) also writes nothing. The default is 300 seconds in production and 5 in
  automated tests, and the panel shows the value actually in force. A timeout is reported as
  `cancelled`, never as "a person refused": inventing a decision-maker is worse than the bug it
  papers over.

A full walk-through of all three endings, including the text the model actually receives:
[section 16, example 4](#16-worked-examples).

One distinction that gets confused on stage: `accepted=false` as a tool argument means "record a
decision that this relation does not hold", and it is still a write that needs approval. The 拒绝
button means "do not perform this write at all". Different things; say them differently.

## 12 Save, leave, come back

![Save before leaving](docs/images/09-save-notebook.png)

Saving is explicit. If you changed the name, purpose or sources and try to leave, you get three
choices: 保存并继续, 不保存并继续 (drops only the notebook edits; the conversation, uploaded files and
saved reports stay), or 取消，继续编辑. A save reports success only after the native title and the
official storage-domain write have both landed. A failed save keeps the page and your input and offers
a retry.

![Notebook list](docs/images/10-notebooks-list.png)

The 笔记本 list restores name, purpose, source batch and the preview position you saved. Notebooks you
named but never sent a message to are in the list; department child sessions are not.

## 13 The quotation workspace

![Quotation workspace, English UI](docs/images/11-quotation-workspace-en.png)

Quotation is a second path next to the monthly review, not a replacement. Open it from Studio
(报价工作区 / Quotation workspace); it also works from an empty session. What you see is the declared
template: which fields a quotation would have, which are still `Awaiting source evidence`, and who
owes each piece of evidence. The badge 等待业务样板 / Awaiting business samples is the honest state of
the feature: the template proves the execution contract, it is not an approved pricing policy.

`data/mock_business/quotation/` holds a fictional but complete quotation sample for a concrete supplier:
customer inquiry, supply contract template, standard quote sheet, cost and capacity basis, pricing and
credit policy, a declaration written from that policy, an extraction record that points every input at
a section or cell of an original, and a hand-computed answer. `backend/tests/test_mock_quotation.py`
opens the originals, checks every extracted value, and confirms the draft matches the hand answer and
that policy violations refuse.

Not built, and not shown as if it were: automatic extraction from a real contract or conversation
transcript, a validated fact store from uploaded documents, and any way to send a quote.

### Filling & handoff, and the three-agent workflow

![Filling & handoff: the handoff board, empty until a record is filled](docs/images/13-workflow-handoff.png)

The business side designed three agents: **Agent 1** reads department materials, proposes candidate
work scenarios, draws information and file flows, scores a four-quadrant proposal and records the MVP
the departments choose; **Agent 2** turns the chosen flow into templates, helps staff fill them and
hands standard records to the next department; **Agent 3** supports rollout with onboarding guidance and
frontline feedback.

What exists: the Agent 1 chain — discovery materials, candidate scenarios, the information/file-flow
diagram, four-quadrant scoring, meeting minutes, and an MVP decision under declared rules with
per-person votes (editors prepare, the native approval records every save; nothing is auto-generated
or auto-approved); assisted filling through the captain (every write needs native approval); native
downstream actions (start / return / complete) with revision confirmation and expiry protection; and
role guidance generated from the declared templates. Not built: the Agent 2 consumer that turns an
approved decision into governed templates, pilot-facing guidance pages, the feedback and
retrospective loop, and real notification channels. The item-by-item comparison with the design and
the planned order are in [`HANDOFF.md`](HANDOFF.md).


## 14 Check that your install is healthy

```bash
cd backend && pytest -q && ruff check src tests ../scripts/start_web.py
cd ../plugins && pnpm run typecheck && pnpm test && pnpm run build
pnpm run smoke:web && pnpm run smoke:business
BRIDGEFLOW_TEST_FAULT=step-limit pnpm run smoke:business
```

Expect the Python and TypeScript unit tests to pass offline, with no model calls and no cost.

**Browser smokes.** The historical `client-modules` preload failure ([#97](https://github.com/EricWang1358/BridgeFlow-AI/issues/97))
is closed: the launcher now selects the pinned npm CLI and checks the official client module before it
opens a browser. If it ever reappears, the diagnostic names the missing module; look at the interface
with `pnpm --dir plugins shots` while you investigate.

[`docs/00-status.md`](docs/00-status.md) is the source of truth for what has been measured, what it
cost, and what is still unverified.

## 15 When something does not work

| Symptom | What is actually happening | What to do |
| --- | --- | --- |
| Import succeeds, master table empty, review refuses | The frozen dictionary declares no joinable column or no review contract | Start with `--demo`, or export the right `FIELD_DICTIONARY_PATH`. The panel prints which dictionary the batch froze |
| Chat says the tool needs approval but no channel is available | Approval is not reachable in that composition | Use the native Web path; do not add a bypass answerer |
| Session creation fails after running the Python-packed SDK | The shared `DSH_HOME` module fallback was rewritten to `/snapshot` | Restart `scripts/start_web.py`; the official launcher self-heals. Use a separate `DSH_HOME` for direct SDK experiments |
| An old session log refuses to open (`bridgeflow/review`, `bridgeflow/approval-note`) | Legacy informational events the native cold reader will not ignore | Stop the launcher, run `python scripts/repair_session_metadata.py --root ../.dsh-bridgeflow/sessions` to inspect, then add `--apply` if you agree. It keeps a byte-for-byte backup |
| A Windows browser cannot reach the service | It is bound to `127.0.0.1` inside WSL, or you used the wrong host | Check `ss -tlnp` first, then [`docs/14` step 10](docs/14-wsl-setup.md) |
| Everything is slow and watch mode never reloads | You are under `/mnt` | Move the repo, the venv and `DSH_HOME` into the Linux filesystem |
| A browser smoke fails with the client-modules line | The shell picked a runtime other than the pinned npm CLI (usually an activated venv first on PATH) | Restart `scripts/start_web.py`; the history is in [#97](https://github.com/EricWang1358/BridgeFlow-AI/issues/97) |
| You expected a number and got a refusal | The data is incomplete and the system refuses to guess | Work the four cases in [section 16, example 5](#16-worked-examples) before touching the dictionary |
| Two panels disagree about one number | a specification conflict is possible; it has happened before | Re-derive it from the citations, then record the measurement in `docs/00` |


## 16 Worked examples

Six problems, each with the data, the exact thing you do, the output that actually came back, and the
mistake people make reading it. Everything here was run on this repository; the refusal messages in
example 5 were captured on 2026-09-07 against the code in `main`.

### Example 1 - Judge a month: "is November 2025 healthy?"

**Given.** The four files in `data/business_demo/risk/`, period `2025-11`, dictionary
`data/business_demo/dictionary.yaml`. These worked examples use the older English CSV regression case
(it has independent answers and drives the browser smokes), not the sample notebook's v2 templates;
start with `FIELD_DICTIONARY_PATH=data/business_demo/dictionary.yaml` instead of `--demo`.

**Do it.** Import the four files (step 8), click 发起研判 (step 9), open the report (step 10).

**Before you look at the answer, do the arithmetic yourself.** This is the point of the product: the
numbers are not model output, they are declared formulas over cells.

| Metric | Formula, as declared | By hand |
| --- | --- | --- |
| `capacity_utilisation` | `sum(used hours) / sum(available hours) * 100` | (48+32+18+12) / (40+30+20+10) = 110/100 = **110%** |
| `capacity_headroom` | `sum(available) - sum(used)` | 100 - 110 = **-10 hours** |
| `material_spend` | `sum(unit price * qty)` | 12x10 + 12x20 + 20x10 + 20x10 = **760 SGD** |
| `purchase_budget` | `sum(budget price * qty)` | 10x10 + 10x20 + 20x10 + 20x10 = **700 SGD** |
| `purchase_price_drift` | `(spend - budget) / budget * 100` | 60/700 = **8.5714%** |
| `gross_margin` | `(sales - positive costs) / sales * 100` | (3000 - 3300)/3000 = **-10%** |
| `ar_weighted_days` | `sum(AR balance * AR days) / sum(AR balance)` | (800x60 + 600x30)/1400 = **47.1429 days** |
| `order_gap` | `sum(ordered) - sum(produced)` | 180 - 150 = **30 units** |
| `requested_terms_days` | `sum(qty * requested days) / sum(qty)` | (120x60 + 60x30)/180 = **50 days** |

**What the report says.** All eight declared checks come back `attention`: load above 100%, headroom
below 0, spend above the same-quantity budget, drift above 5%, margin below 0, receivables above 45
days, order gap above 0, requested terms above 45 days. The independent answer key is
`data/business_demo/expected.json`; if the report and that file disagree, the report is wrong and the
disagreement is a defect, not a matter of taste.

**The trap.** The report's own `limitations` list is part of the answer: no BOM or inventory here, so
"orders exceed output by 30 units" does **not** prove a delivery failure; the drift is a same-quantity
budget comparison, not a month-on-month price change; and 47 days of weighted terms is not bad debt.
A reviewer who reads "margin -10%" and writes "book a provision" has left the evidence behind.

### Example 2 - Trace one number down to a cell

**Question.** Where does 110% come from, and can you prove it?

Open 解释与原始来源 on the production card. The stored record is:

```json
{"check_id": "capacity", "metric": "capacity_utilisation", "value": 110, "unit": "%",
 "formula": "sum(used hours) / sum(available hours) * 100",
 "source_count": 8, "source_count_basis": "formula input cell occurrences", "truncated": true,
 "threshold": 100, "attention_when": "above", "expected_status": "attention",
 "action": "提交排产与加班预算复核", "explanation_status": "model_advice",
 "execution_status": "proposed_only"}
```

Read it in this order:

1. `source_count: 8` is four `used_hrs` cells plus four `available_hrs` cells, which is exactly the
   formula's input. `truncated: true` means the display lists at most 5 of them; it does not mean the
   computation used a sample.
2. The listed citations carry `filename`, `source_row` and `original_column` - production.csv rows
   2 to 5, column `used_hrs`. Open that file in Sources and you are looking at the cells.
3. `action` is not model text: it is the `attention` branch of the declared check, copied verbatim.
4. `explanation_status: "model_advice"` marks the one sentence that *is* model prose. Different
   authority; different colour in the card.
5. `execution_status: "proposed_only"`: nothing was bought, scheduled or credited.

**The trap.** "Cited 8 times" is not "8 distinct cells" either: a cell used twice by a formula counts
twice. The count is of inputs, not of locations.

### Example 3 - Same code, two months: risk vs balanced

Import `balanced/` as a second batch and review it. Nothing about the code changes; the data does.

| Metric | risk | balanced |
| --- | --- | --- |
| capacity load / headroom | 110% / -10 h | 80% / +20 h |
| spend / budget / drift | 760 / 700 / +8.5714% | 700 / 700 / 0% |
| sales / positive cost / margin | 3000 / 3300 / -10% | 3000 / 2000 / +33.3333% |
| weighted AR days | 47.1429 | 30 |
| order gap / requested terms | +30 units / 50 days | -20 units / 30 days |
| status of all eight checks | attention | ok |

**The two traps.** First, "ok" is not "no risk": the balanced case still has a -20 unit order gap
below its threshold and an unapproved 30-day request. Second, reopen the risk batch afterwards: it is
byte-identical. A new import never recomputes an old batch, which is the whole reason batches are
immutable.

### Example 4 - Mapping approval, three endings

**Ask.** Paste into the session (step 11 has the full sentence): request one `confirm_mapping` with
`accepted=true` for `sku:demo-review` to `customer:demo`, then wait.

**Ending A - Allow once.** The write happens, mapping memory gains one rule naming who authorised it,
and the next import applies it without asking.

**Ending B - Reject, with a reason.** Type a reason, e.g. "客户编码未核实，请销售负责人确认后再提交。"
Nothing is written. The tool result the model receives is ours, and it says what happened:

```text
confirm_mapping did NOT run: a person reviewed it and refused. The reviewer said:
"evidence is stale - use the October BOM, not this one". Nothing was written, ...
```

The model then has to relay it. In review we found it claiming "the mapping will not be asked about
next month", which was false, so the wording now says future imports may ask again - and the live test
checks the sentence against the file.

**Ending C - Nobody answers.** Also nothing is written, and the narration says no one was available to
decide. It never says "a person refused". `cancelled`, `unavailable` and `rejected` are three
different facts.

**The trap that costs the most.** `accepted=false` is not "reject". It means "record the decision that
this relation does not hold", and it is still a write that needs approval. The 拒绝 button means "do not
run this call". Say them differently or you will explain your own product wrongly on stage.

### Example 5 - Four ways the system refuses to produce a number

Copy `data/business_demo/risk/` to a scratch folder, break one cell, import the copy, click 发起研判.
Each row below is a message this build actually returned (409 at `/tools/review-context`; the panel
shows the same text).

| Broken input | What you see | Why it refuses instead of reporting |
| --- | --- | --- |
| `price` blank on one procurement row | `Declared numeric cell is missing or unreadable` | Reporting 640 of 760 would turn "at least this much" into "exactly this much". A sum with a missing row is a smaller lie than a refusal |
| one procurement row in USD | `procurement: currency missing or mismatched; conversion is not configured` | There is no declared FX rule, so any total would be an invented rate |
| `cost` entered as -2000 | `finance: cost violates the declared nonnegative convention` | The dictionary declares costs positive; a negative silently mixed in changes what `sales - cost` means |
| date written `03/11/2025` | import: production 3 rows kept, **1 quarantined, 1 correction**; review: `Resolve batch configuration or quarantined rows and import a new batch before review` | Is that 3 November or 11 March? Guessing once put a row in the wrong month and the total inherited it (#79). The row is kept verbatim in quarantine, and the batch refuses to report totals |

**The fix is not "make it accept less".** Fix the source file and import a new batch. The old batch
stays as evidence of what was asked.

**The trap.** A refusal is not a broken demo. If a panel shows a refusal, the honest move is to show
the refusal and name what is missing; the dishonest move is to delete the row.

### Example 6 - A partial review, and what a human note may not do

**Reproduce it offline, free:**

```bash
BRIDGEFLOW_TEST_FAULT=step-limit pnpm --dir plugins smoke:business
```

The finance child produces invalid structure three times in a row, hits the step budget and stops. The
report is `partial`: finance has no valid judgement, the other three departments keep theirs, and the
child count is still 4 (four sessions really started; one failed).

Then submit a human review note from the partial page. It reaches the captain as an ordinary chat
message, the report stays `partial`, and the note does not sign for finance.

**What the host enforces:** a turn that carries a human note is guarded by the plugin — it cannot start,
rerun or finalize a review, dispatch departments or call an approval tool. Every review is registered with
one deadline when it opens; a late success cannot overwrite `deadline_exceeded`, and a restart closes open
runs as `host_restarted`. Do not present a partial report as "handled".

**The trap.** Filling the missing department with a plausible sentence makes the report look complete
and is the single most damaging thing this product could do: the approver signs a number nobody
computed.

## Where the real documentation is

| If you want | Read |
| --- | --- |
| Current progress, next steps, known defects | [`HANDOFF.md`](HANDOFF.md) |
| Every measured number, with its command | [`docs/00-status.md`](docs/00-status.md), the only source |
| Why the architecture is what it is | [`docs/13-golden-standard.md`](docs/13-golden-standard.md) |
| Hard constraints before touching code | [`CLAUDE.md`](CLAUDE.md) |
| Demo script and what runs on stage | [`docs/04-demo-plan.md`](docs/04-demo-plan.md), [`docs/17`](docs/17-business-mvp-acceptance.md) |
| Which document answers which question | [`docs/README.md`](docs/README.md) |

Architecture in one block, for the impatient:

```text
Official DSH Web: native chat, sessions, approvals, trajectory
  └─ BridgeFlow slots: import/data, rejection note, review cards
       └─ Typed domain tools + host policy
            ├─ Python: immutable batches, dictionary, arithmetic, validation
            ├─ Official DSH spawn: production / procurement / finance / marketing
            └─ Native approval → one-use receipt → mapping memory
```

Repo layout:

```text
backend/          Python domain computation, persistence and private FastAPI service
plugins/          DSH tools, guards, native approval integration and Client UI slots
dsh/              Pinned Web policy patch and restricted analyst preset
scripts/          Native Web launcher and runtime checks
data/samples/     Historical development spreadsheets
data/business_demo/ English CSV regression cases and independent answers (browser smokes, worked examples)
data/company_templates/ The business side's v2 templates, dictionary and the integration declaration
data/mock_business/ Fictional monthly exports, the sample notebook case and quotation samples
examples/         Standalone demos (production → marketing handoff MVP)
docs/images/      Screenshots used by this guide
docs/             Requirements, architecture, measured status and review
```

Status: a business-use-case demonstration MVP with live-model and browser evidence. Real customer
data and enterprise deployment still need validation. Work is tracked on the
[project board](https://github.com/users/EricWang1358/projects/1).

There are no Dockerfiles. One CI file (`.github/workflows/deploy.yml`) runs the offline checks on every
pull request and deploys merges to the Lightsail instance ([docs/22](docs/22-lightsail-deploy.md)); browser
smokes and billed model runs are not part of CI.