# Scope and known limitations

BridgeFlow AI 1.0.0 is a business workflow demonstration built for a hackathon. Its sample workflows and tests should not be treated as enterprise acceptance.

- Business rules, field dictionaries, aggregation and joins must be declared and approved for the actual data. The included templates and examples do not establish a customer's accounting or operational policy.
- Deterministic import and sample exploration work without model calls. AI reviews require a configured provider and incur usage charges. Model latency, cost and judgment quality vary.
- Discovery and handoff records are shared business state. Notebook separation and optional per-seat sessions do not establish a complete multi-tenant authorization boundary.
- Guest mode uses separate sample data and blocks uploads. Public AI access requires an operator-configured model gate, limits and monitoring.
- Feishu integrations require tenant configuration and appropriate permissions. Large-sheet paging and end-to-end acceptance with real enterprise exports remain incomplete.
- Large datasets remain constrained by upload, decompression, row and memory limits. This release does not claim production readiness for 200,000-row batches.
- The quotation workspace supports declared drafts and evidence checks; it does not provide completed external quotation issuance.
- Formal report sign-off, third-party security review and customer acceptance remain outside the demonstrated scope.

The test suite documents reproducible rule and interface behavior. Live-provider evidence, operational logs and internal evaluation notes are maintained separately from public source distributions.
