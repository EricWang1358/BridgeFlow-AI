# 38 — The language of department explanations

The four department agents write one short explanation per check. That language was hard-coded to
Chinese, so the English guest demo showed Chinese sentences in the monthly brief and the review report.
It also left one host check unable to fire on the English sample set. This plan makes the language a
declaration of the batch's review contract, frozen with the batch like everything else in it, and makes
the host verify it.

> Found 2026-09-27 while rehearsing `plugins/tests/demo-video.mjs` (beat 4) on a local guest instance with
> the English sample set ([docs/37 §6](37-portal-english-and-guest-entry.md)).

## 1. What was wrong

**Seen.** The review finished and was validated, but every *Proposed action* line in **Conclusions** was
followed by a Chinese sentence, for example 该值低于关注阈值，需由财务牵头启动成本与定价联合复核。
The same text is in the saved report and in the Word download.

**Cause.** There are three places, and each one assumes Chinese.

| Where | What it hard-codes |
| --- | --- |
| `plugins/src/tools/review-batch.ts`, `instruction` (the task each department agent receives) | "Explain … in Chinese", "Call thresholds only 关注阈值", "write 不作为该结论的依据 instead of naming the topic" |
| `backend/src/bridgeflow/business.py`, `context()` | Built-in forbidden topics 已批准上限 / 已批准标准 / 现行批准标准, added to every role |
| `backend/src/bridgeflow/business.py`, `validate_role()` | A case-sensitive substring match of those topics, and a 120-character limit sized for Chinese |

**The safety side.** The English sample set translated the finance role's `unsupported_topics`
(计提, 减值, …) into English (Accrue, Impairment, …). The explanations were still Chinese, so an
English topic could never match a Chinese sentence: on the English set, the check that refuses a
department for discussing a topic outside its evidence could not fire. The reverse is also possible on
any set. An explanation written in a language other than the one its topic list is written in slips
past the check. That is a check that can be bypassed by switching language, not only a display problem.

## 2. Goals and non-goals

Goals:

1. Department explanations are written in a declared language: English on the English sample set,
   Chinese everywhere else (unchanged).
2. The host verifies the language, so an explanation in the wrong language is refused rather than shown.
   "Refused, not downgraded" is the same rule as for evidence ([CLAUDE.md](../CLAUDE.md)).
3. The forbidden-topic check cannot be bypassed by writing in the other language.
4. No behaviour change for any existing dictionary, batch or saved report.

Non-goals:

- Translating explanations after the fact. It would be another model call, and a translated sentence
  would no longer be the text the host validated.
- Following the interface language at review time. A saved report is read in both interfaces, and its
  text must be the text that was validated. The language belongs to the batch's frozen contract, as the
  thresholds and actions do.
- The captain's chat replies. They already follow the person.
- Changing any check, threshold, action or metric.

## 3. Design

### 3.1 The declaration

`business_review.explanation_language` in the field dictionary, `zh` or `en`.

- **Absent means `zh`.** Every dictionary written so far (the business's, the samples, the eval cases)
  is Chinese, so nothing existing changes, including batches whose dictionary snapshot predates the key.
- **Any other value is refused** by `review_context` ("unknown explanation language"). A typo must not
  silently fall back.
- The value is frozen into each batch's `dictionary_snapshot` at import, so a report's language never
  changes after the fact.
- The Chinese original, `data/mock_business/demo/dictionary.yaml`, is left as it is (absent means `zh`).
  Its hash is pinned in that case's `manifest.json`, and it needs no change. The English set's generator
  (`scripts/make_english_samples.py`) sets `en` rather than translating anything.

This is a declaration, not a field name, so it does not touch the rule that field names come only from
the YAML.

### 3.2 One wording table, in the backend

`business.py` gets `EXPLANATION_LANGUAGES`: per language, the name the agent is told, the character
limit, the threshold term, the out-of-scope phrase and the built-in forbidden topics.

| | `zh` | `en` |
| --- | --- | --- |
| Written in | Simplified Chinese | English |
| Character limit | 120 (unchanged) | 240 (the same amount of content in English) |
| Threshold term | 关注阈值 | attention threshold |
| Say instead of a forbidden topic | 不作为该结论的依据 | not a basis for this conclusion |
| Built-in forbidden topics | 已批准上限, 已批准标准, 现行批准标准 | approved limit, approved standard, currently approved standard |

This is product wording, like the `WORKBOOK_WORDS` for the English downloads, not a business field.

### 3.3 The packet carries it

Each role packet from `review_context` gains
`explanation: {code, language, max_characters, threshold_term, out_of_scope}`. Its `unsupported_topics` are
the built-ins for that language plus the role's declared ones.

The host instruction in `review-batch.ts` no longer names a language or a term. It points at those
packet fields ("written in packet.explanation.language, at most packet.explanation.max_characters
characters, …"). The host refuses to start a review whose context lacks `explanation` on any role, so a
backend and plugin that disagree fail closed.

### 3.4 The host verifies it (`validate_role`)

Checked at finalize, where the review context is recomputed from the frozen batch, so the packet is
the trusted one:

1. **Length:** at most the language's limit. The schema's outer bound is raised from 120 to 240, and
   the per-language limit is enforced here.
2. **Digits:** unchanged.
3. **Language:** `en` refuses any CJK character. `zh` refuses an explanation with no CJK character.
4. **Forbidden topics:** case-insensitive. The built-ins of **both** languages apply whatever the
   declared language, so switching language cannot bypass them. The role's declared topics also apply.

A refused role makes the report `partial` and is named, exactly as a digit in an explanation does
today. There is no retry, for the same reason: the check is the backstop, and the instruction is what
prevents it.

### 3.5 Considered and not done

- **Pre-checking in `structured_output`,** so a child could retry. It would duplicate the host's rules
  in TypeScript. The existing digit rule has the same shape and is not pre-checked either. Revisit if
  the rehearsal measures refusals.
- **Stemming English topics** (Accrue vs accrual). Matching stays literal and case-insensitive: the
  topic list is a declaration, and a looser match would refuse legitimate sentences. The list is shown
  to the model, which is told never to write any of it.

## 4. Changes

| File | Change |
| --- | --- |
| `backend/src/bridgeflow/business.py` | `EXPLANATION_LANGUAGES`; `context()` reads the declaration, refuses unknown values and adds `explanation` plus per-language built-ins to each packet; `Judgement.explanation` outer bound 240; `validate_role()` checks length, language and both languages' topics case-insensitively |
| `plugins/src/tools/review-batch.ts` | Language-neutral `instruction` pointing at `packet.explanation`; `review_context` refuses a context without it |
| `plugins/tests/fixtures/scripted-model/index.ts` | The offline scripted department answers in the packet's language |
| `scripts/make_english_samples.py` | Sets `explanation_language: en` in the English dictionary. It now also keeps a workbook whose content did not change, because openpyxl stamps each save and every run otherwise rewrote all 30 workbooks and their manifest hashes. Regenerate `data/demo_en/` |
| `backend/tests/test_explanation_language.py` (new), `plugins/tests/runtime.test.ts` | See §5 |
| `data/demo_en/README.md`, `docs/requirements/00-foundations.md` §5.4, `HANDOFF.md`, `docs/README.md` | The rule, where it is declared, and this doc |

## 5. Tests

Backend, offline:

- A packet from the Chinese set carries `language` = Simplified Chinese, limit 120 and the Chinese built-ins.
  The English set carries English, 240 and the English built-ins.
- An unknown `explanation_language` is refused by `review_context`.
- A dictionary without the key behaves as `zh`: the existing tests, unchanged, pass.
- English set: an English explanation is accepted. A Chinese one is refused (language). 241 characters is
  refused (length). "within the Approved Limit" is refused (the English built-in, any case). A Chinese
  built-in inside an English sentence is refused (cross-language). "no Impairment" is refused (the
  declared finance topic, translated).
- Chinese set: 121 characters is still refused. An all-English explanation is refused (language). An
  English built-in inside a Chinese sentence is refused.
- The generated English dictionary declares `en`, and `--check` stays clean.

Plugins: typecheck and unit tests. A review whose context has no `explanation` never opens
(`runtime.test.ts`). The round-1 browser journey (scripted model, Chinese set) keeps passing
because the fixture follows the packet.

Live: `demo-video.mjs` beat 4 on a local English guest. Every explanation in **Conclusions** is English,
the report is `validated` with four roles, and the model usage is recorded in the run summary.

## 6. Rollout

- There is no configuration: the declaration travels with the sample dictionary, so a merge to `main`
  deploys it. Guest data is wiped on restart, so the guest re-imports its samples with `en`.
- Existing staff batches keep their snapshot, which has no key, so they stay `zh`. Saved reports are not
  touched.
- **Rollback:** revert the commit. There is no data migration in either direction.

## 7. Risks

| Risk | Mitigation |
| --- | --- |
| The model writes Chinese in `en` mode, so the role is refused and the report partial | The instruction names the language. Measured on the live rehearsal before the take; if it happens, the refusal names it |
| 240 English characters is too tight | The same per-character logic as Chinese at 120. Measured in the rehearsal; raising it is a one-line change in the table |
| A mixed-language sentence dodges a declared topic that exists in one language only | The built-ins cover both languages. A declared topic is in the dictionary's own language, which is the declared explanation language |

## 8. Result (2026-09-27)

Implemented as planned. Measured figures are in [`00`](00-status.md) (2026-09-27 section).

- Backend: all pass, including the new `test_explanation_language.py`. `make_english_samples.py --check` is
  clean, and regenerating changes only the English dictionary and its manifest hash.
- Plugins: typecheck and build are clean. The unit tests pass except the two macOS path tests that
  already failed before this change. `cases-journey.mjs` with the scripted review button passes on the
  Chinese set, so the fixture follows the packet.
- Live, on a local English guest: beat 4 of `demo-video.mjs` produced a `validated` report with four roles
  and English explanations in **Conclusions**.
- One thing to watch rather than a defect: that review took much longer than the previous rehearsal on
  the same model, close to the 180 s review deadline. Re-measure on the live instance before the real take
  (see 00).
