# Development

Install the environment described in [Setup](setup.md). Use the pinned dependency lockfiles.

## Offline verification

From the repository root with the virtual environment activated:

```bash
python scripts/check_public_release.py
ruff check backend/src backend/tests scripts/start_web.py
python -m pytest backend/tests -q
python -m pip install -e 'portal[dev]'
python -m pytest portal/tests -q
pnpm --dir plugins typecheck
pnpm --dir plugins build
pnpm --dir plugins test
```

Python tests isolate provider settings and data directories. Plugin unit tests exercise tool contracts, approvals and UI state. The deployment workflow runs these checks before deployment when an operator has enabled deployment.

Browser journeys under `plugins/tests/` cover sample notebooks, reviews, handoffs and guided tasks. They require the pinned CLI and Playwright browser installation. Offline journeys use the scripted test model. Real-model scripts require explicit model configuration and can incur provider charges.

## Samples and templates

`data/mock_business/`, `data/demo_en/`, `data/business_demo/` and `data/workflow_demo/` contain demonstration fixtures. Template schemas in `data/company_templates/` declare the demonstration's business rules. Template workbooks contain headers or anonymized examples; generated datasets are not customer exports.

Keep numeric expectations and tests together. Offline tests establish rule and contract behavior, not real-world model accuracy or enterprise acceptance.

## Documentation and public artifacts

Edit `plugins/src/client/user-guide.ts`, then run `pnpm --dir plugins docs:guide` to regenerate the two user guides.

Keep internal handoffs, meeting notes, screenshots, recordings, raw traces and installation-specific configuration outside the repository. Generated browser evidence directories are ignored. The release-content check examines tracked files and workbook metadata; its output reports paths and categories without printing secret values. Run it before tagging a release.
