# Retained onboarding case

All records describe a **fictional concrete supplier**. The department templates and integration declaration come from the business template work; the records and policies are demonstration inputs, not verified company accounts or approved policies.

This directory is the durable input for **Open sample notebook** and the guided task. Keep the XLSX files, `dictionary.yaml` and `manifest.json` in version control together. The manifest fixes the input fingerprints, declaration fingerprint and expected outcomes. Verification and measured results live in [status](../../../docs/00-status.md).

The case connects the existing integration and department-review declarations to the same monthly files. Opening it imports and retains actual sources, computes the real table, creates a native session and saves its notebook bookmark. It does not run department agents. A report requires a separate explicit model action.

Reproduce from the repository root:

```bash
../.venv/bin/python scripts/start_web.py --demo
```

In the application, choose **Help & guided tours → First task · combine & verify**. The sample button imports a fresh independent batch; replay offers reuse of the current sample without a second import. Results retain an unresolved customer-name discrepancy. There is no hidden resolution or approval.

For deliberate sample revisions, `scripts/make_mock_business.py` regenerates monthly workbooks and this demo from declared synthetic inputs. It writes files: do not run it merely to view the retained case. Review changes and update the manifest explicitly; XLSX container timestamps can change byte fingerprints even when cell values do not. Do not silently reclassify this demonstration case as evaluation holdout data.

Repository inputs and saved application state are different. Keep the configured `RESULT_STORE_PATH` (retained sources/results), mappings if needed, and the installation's `DSH_HOME` (native sessions and notebook domain records) when moving or backing up the installation. Reuse the same directories after restart. Do not commit private runtime data or service tokens. Session cleanup is a separate explicit operation; a retained file is not a backup. Tour progress is small navigation metadata in tab storage, not where the case or result is stored.
