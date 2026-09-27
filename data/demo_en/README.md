# English sample set (public demo)

The public guest instance (`https://<domain>/`, [docs/22 §9e](../../docs/22-lightsail-deploy.md))
loads these files, so judges see an English product on English data. They are a **translation**
of the Chinese originals, not a second dataset. The originals are the business's own v2
templates filled with the fictional concrete supplier: see
[`data/mock_business/`](../mock_business/README.md) and
[`data/company_templates/`](../company_templates/).

| What | Here | Translated from |
| --- | --- | --- |
| Paths the guest loads | `sample-set.yaml` | `data/mock_business/sample-set.yaml` (Chinese) |
| Integration declaration and templates | `company_templates/` | `data/company_templates/` |
| Guided-tour case, dictionary, manifest | `demo/` | `data/mock_business/demo/` |
| Other cases and earlier months | `cases/` | `data/mock_business/cases/` |
| Discovery sample project and policies | `discovery_demo/` | `data/discovery_demo/` |
| Filling & handoff catalogue and sample | `workflow_demo/` | `data/workflow_demo/` |
| The words | `glossary.yaml`, on top of `data/company_templates/labels.en.yaml` | — |

## Rules

- **Do not edit the generated files.** Change the original or `glossary.yaml`, then run:

  ```bash
  python scripts/make_english_samples.py
  ```

  `--check` fails when this folder is stale. The same check runs in
  `backend/tests/test_english_samples.py`.
- **Only words change.** Every number, row, column order and planted problem is copied. The test
  imports each case from both sets and requires identical outcomes: status, rows, quarantined
  rows, open-item kinds, column questions, review checks and every metric value.
- **A missing word is an error, never a guess.** Two originals may not become one English word,
  and two headers may not become one sanitized key. Either would silently merge columns.
- The field dictionary names the sanitizer's snake-cased keys (`Customer name` →
  `customer_name`). The integration declaration names headers exactly as written. The generator
  applies both rules; no field name is written in code.
- The dictionary declares `business_review.explanation_language: en`. The generator sets it, and it is
  the only value not translated from the original. The four department agents write their explanations
  in English, and the host refuses any other language ([docs/38](../../docs/38-review-explanation-language.md)).
- Case ids stay the same as in the Chinese set (`mock-company-2024-07`, `demo-history-2024-05`, …).
  The guided tour and the history lookup key on them.

To run a guest instance on the Chinese originals instead, set
`BRIDGEFLOW_GUEST_SAMPLE_SET=data/mock_business/sample-set.yaml` in `env.sh` and restart the
guest unit.
