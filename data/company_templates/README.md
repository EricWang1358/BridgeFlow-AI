# Demonstration templates

This directory contains the declared field schemas and template workbooks used by the example workflows. They are business-supplied template structures with anonymous example labels, not customer transaction exports. Workbook author metadata is normalized for distribution.

- `source/`: versioned dictionaries, department headers and master-table templates.
- `integration.yaml`: field sources, connection keys, formulas, aggregation and cross-department checks.
- `labels.en.yaml`: English display labels for the declared fields.
- `example/`: example department workbooks derived from the anonymous master-table example.
- `tuning/`: generated fixtures and expected results with deliberately planted data problems.

The implementation reads `integration.yaml`; tests verify the declared schema against workbook headers and expected results. Assumptions are declared in the schema and shown in outputs. Review or replace them before using a template with actual business data.

Generate and score local fixtures with `python scripts/integration_cases.py tuning` or `python scripts/integration_cases.py grade data/company_templates/tuning/seed-1`. Generated fixtures do not replace customer acceptance testing.
