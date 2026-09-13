"""Workflow foundation: declared stages, assisted intake, handoff and adoption signals.

The three agents in #143, #144 and #145 share one substrate. Each layer is a separate
module with one reason to change, and dependencies point inward only:

    catalogue   declarations people approve: stages, templates, lineage, routes (#143)
    normalise   value strategies selected by declared type                         (#144)
    intake      observations → draft with provenance and blocking issues          (#144)
    lifecycle   state machines over events; the only place transitions are legal  (#144)
    store       append-only event log, idempotent records, transactional outbox
    ports       where records go and how people are told; adapters behind protocols
    service     use cases composing the above — the only module the API calls
    board       read model projected from events                                  (#144)
    adoption    rules over the event log that surface where a flow is stuck       (#145)
    materials   what an uploaded workbook is, before anyone maps it               (#143)

Rules that hold in every module, because the product depends on them:

- **No field name in code.** Every business name comes from the catalogue YAML, the
  same rule as `CLAUDE.md`'s field dictionary. The tests parse these modules to check.
- **Only approved declarations run.** A draft template can be inspected, never used
  to accept data.
- **Nothing is filled in to make a record complete.** Missing, ambiguous and
  conflicting values become issues with a question, never a default.
- **Status follows real results.** "Ready" requires the sink's receipt; "notified"
  requires the channel's; neither implies the downstream work is done.
"""
