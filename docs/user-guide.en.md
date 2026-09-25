# BridgeFlow user guide

This guide is for your first time with BridgeFlow. You need no technical background and no files to start: follow "Five minutes to your first result" once and you will know what it does. Every button is written exactly as it appears on screen, so you can find it by its words.

> Generated from `plugins/src/client/user-guide.ts` (`pnpm --dir plugins docs:guide`), the same source as Sessions & settings → User guide in the product. Edit the source, not this file.

## What it does

Every month, production, procurement, finance and marketing each hand in their own spreadsheet. The same customer or project is spelled differently, columns are named differently, units differ, so someone reconciles them by hand every month. BridgeFlow combines the four into one table that adds up, lists every place they disagree, and has AI agents review it department by department. Every figure traces back to its original row, and nothing is written without you approving it on an approval card.

## Five minutes to your first result

Walk through the built-in sample: no files to prepare and no cost (no AI is called).

1. In Sources on the left, choose Open sample notebook. Four department files are imported for you.
2. Choose any file on the left; its original content appears on the right.
3. In Studio on the right, choose This month’s tasks: it says what this month still needs and who handles it.
4. Then choose Data → Cross-department master: the four files as one table. Open the open questions to see the one mismatch: production shortened a customer’s name.
5. Choose any figure in the table; below it you see which file, row and column it came from.
6. To see the AI review (it calls the model and costs money): go back to This month’s tasks and choose Start the review; about a minute later the report appears under Artifacts.

> Prefer to be walked through? Choose Help & guided tours at the top right → First task · combine & verify.

## Finding your way around

The page has three panes and a row of buttons along the top.

- Sources (left): this notebook’s department files. Add sources uploads new ones; Open sample notebook and More sample cases open ready-made examples; Notebook purpose decides which steps you see.
- Chat (middle): where you talk to the captain (the AI). Above it, Trajectory shows each tool call step by step, and Business state tells you where the month stands and what to click next.
- Studio (right): Overview for the whole month, This month’s tasks for what is open, Data for tables and cleaning, Conclusions for the review’s findings, Records for who did what and when. Under Other workspaces: Quotation workspace, Discovery materials and opportunities, and Filling & handoff.
- Top bar: Create notebook, Save notebook, Notebooks (reopen an earlier one) and Exit notebook; Sources and Studio fold or unfold the side panes; Sessions & settings holds earlier sessions, the model, the language and this guide; Help & guided tours opens step-by-step tours.

## Your monthly routine

A month has five steps. Whenever you are unsure what comes next, open Business state above the chat: What to do now at the top spells it out.

1. Add files: Add sources on the left, pick the month, choose one file per department (xlsx or csv) and import. Import cleans and checks everything itself, with no AI. No template? On the Data page, choose Download this month’s template on each department’s row.
2. Clean up: open This month’s tasks. Each open item says How to settle; Open to settle takes you to its page. Unsure? Ask the captain for a suggestion. If one department’s file is wrong, fix it and choose Replace one department’s file on its row of the Data page; that makes a new batch and leaves the old one as it was.
3. Review: once the data is ready, Start the review lights up at the top right of This month’s tasks. The captain sends four department agents at once; you can watch them under Trajectory. About a minute later the report appears under Artifacts.
4. Decide: open Conclusions and start with the flagged findings. Each shows its formula, threshold and source cells. Once you decide, tell the captain in the chat; it records your decision through an approval card.
5. Close: back in This month’s tasks, check that every close step is done; read or download the monthly brief under Conclusions, and download the table with Download master xlsx under Data → Cross-department master.

## Working with the captain (the AI)

The captain is the AI assistant in the chat. It looks things up, computes and suggests, but it never decides for you and never reads raw data rows itself.

- Ask it directly: "What is still open this month, and how would you settle each item?", "What is the total production volume?", "Review this batch across the four departments", "Where is the quadrant chart?". When you ask where something is, it lists the clicks and opens the page on the right.
- The captain knows which notebook you are in: "this batch" and "this month" mean the current notebook’s batch.
- Anything it writes comes to you as an approval card. Check the values and where they came from; to refuse, write why in Rejection reason and choose Reject, and the captain hears your reason; to accept, choose Allow once. Nothing is written until you decide.
- Its suggestions are marked as model advice. When unsure, ask for its basis; the basis should be something you can find in the table.

## Other workspaces

- Quotation workspace: which facts a quote needs, who provides each, and how the price band is computed from declared formulas. Without the evidence, no quote is produced.
- Discovery materials and opportunities: department materials, improvement ideas, flow graphs, Rating quadrants, meetings and decisions. Choose Load the sample project to see a complete example.
- Filling & handoff: fill department templates under the approved scope, review them and hand them to the next department. Choose Load the sample workflow to see an example.

> Filling & handoff and discovery are shared across the company, so every notebook sees the same records; sources, tasks, data, conclusions and artifacts belong to the current notebook.

## Notebooks and saving

- A notebook is one piece of work, such as "July 2024 reconciliation". Rename it in the title at the top; next to it you see Saved or Unsaved.
- After Save notebook, you can reopen it from Notebooks with its sources, batch and artifacts restored. Leaving an unsaved notebook asks whether to save first.
- Notebook purpose (Monthly review, Quotation, Combined work) decides which steps and guidance the notebook shows.

## Tours and samples

- Help & guided tours at the top right has four step-by-step tours: First task · combine & verify, Explore · department review, Explore · quotation workspace, and Explore · from an idea to a handoff between departments. A tour never submits anything for you.
- More sample cases on the left holds three samples, each with different problems planted on purpose. After opening one, choose Walk me through this sample at the top of This month’s tasks.
- If a tour says This step is behind an open window, choose Close this window and continue.

## Settings

- Sessions & settings switches between Chinese and English. In English, the business’s Chinese field names show an English name beside them, such as Customer name (客户名称).
- The model you choose here stays until you change it. If a review says a credential is missing, the chosen model has no key configured; pick one that does.

## Common questions

**Start the review is greyed out?**

The data is not ready yet. The reason is shown beside it; settle the open items in This month’s tasks and it lights up.

**The report says Incomplete review?**

A department returned no findings. Open the report to see which; if it can be confirmed offline, write a Human review note and choose Send to captain; if the data is wrong, fix the file and use Replace one department’s file.

**Some uploaded columns are not recognised?**

In Business state choose Open column matches to see the candidates, or Ask the captain to propose matches. An approved match applies after the files are imported again.

**Why are some values still Chinese?**

Company and project names are the data itself and stay as written, so you can match them to the original files.

**No Feishu import?**

Feishu features need a Feishu sign-in and are unavailable in guest mode; everything else works without it.

**Could the AI make numbers up?**

No. Figures are computed by the system from declared formulas, and every finding must cite its source cells; a finding without evidence is rejected.

## Terms

- **Batch**: One import of the four department files. Changing a file creates a new batch and keeps the old one.
- **Cross-department master**: The four files combined into one table by the dictionary; every cell has a source.
- **Open items**: Questions a person must decide, such as departments spelling something differently.
- **Convention**: A common-practice rule used where the dictionary is silent; it counts as declared once the business confirms it.
- **Evidence grade G1–G4**: G1 read straight from a file, G2 computed by a formula, G3 resting on an unconfirmed convention, G4 model advice.
- **Approval card**: The card shown before any write; you choose Reject or Allow once.
- **Captain / department agents**: The captain is the AI in the chat; for a review it sends four department agents, each reading only its own department’s metrics.
