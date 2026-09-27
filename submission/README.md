# SMYA final submission documents

| File | Purpose |
| --- | --- |
| `style.typ` | Shared layout, colours and metadata (team code, URLs) for both documents |
| `business-proposal.typ` → `BridgeFlow-Business-Proposal.pdf` | Business proposal (7 pages) |
| `technical-document.typ` → `BridgeFlow-Technical-Document.pdf` | Technical document (8 pages) |

Regenerate (typst ≥ 0.15):

```bash
typst compile business-proposal.typ BridgeFlow-Business-Proposal.pdf
typst compile technical-document.typ BridgeFlow-Technical-Document.pdf
```

Team code (`CA3WTLPW`), event, and demo/portal/repository URLs live once in `style.typ` (`meta`);
change them there and recompile both files.

All figures come from `docs/00-status.md` and `docs/evidence/` — if a number changes before the
deadline, update the source doc first, then these files.
