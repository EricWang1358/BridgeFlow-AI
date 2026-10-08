# Quotation contract compliance samples (#302 demo cut)

> **All fictional.** Two quotations for an invented ready-mix concrete supplier, each with its own contract, checked
> against an invented company legal baseline. Read-only: nothing here is stored, edited or sent.

| File | What it stands for |
| --- | --- |
| `quotes.yaml` | Entry point: the two quotations, their extraction records and contracts, and the structured contract terms a person read off each contract |
| `01-customer-enquiry-A.md`, `03-customer-enquiry-B.md` | Customer enquiry records |
| `02-supply-contract-A.md` | Quotation A's contract: the company's standard template (no warranty, liability cap or intellectual property clause) |
| `04-supply-contract-B.md` | Quotation B's contract: the customer's own project contract |
| `05-cost-and-capacity-basis.md` | Material cost, transport and production cost, plant capacity, customer collection record (shared by both) |
| `extraction-A.yaml`, `extraction-B.yaml` | Human-checked extraction: where each declared quotation input was read |
| `legal-requirements.yaml` | Legal requirements v1: payment days, supplier damages cap, unlimited liability (rule checks); intellectual property and warranty clauses (model checks) |
| `clause-judgements.yaml` | Frozen model conclusions for the clause checks, re-checked against the contract on every load |
| `expected-compliance.md` | The hand answer, line by line |

The quotation arithmetic is the one declared in `data/demo_en/demo/dictionary.yaml` (and its Chinese original
`data/mock_business/demo/dictionary.yaml`, which has the same formulas). The samples show in the quotation workspace
whenever the active dictionary declares that arithmetic: `./run.sh --demo` or a guest instance.
The two quotations are evaluated independently and do not net plant capacity against each other.

- Tests: `backend/tests/test_quote_compliance.py` compares both quotations with `expected-compliance.md`.
- Regenerating the clause conclusions with a real model: `scripts/freeze_clause_judgements.py` (refuses the mock provider).
