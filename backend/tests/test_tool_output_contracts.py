"""Every field the host returns for a strictly declared tool is declared in the plugin.

A live captain run (#41) found `batch_summary` rejected as invalid output: the host had
gained fields the plugin's `additionalProperties: false` schema did not list. Offline
fixtures never call that tool, so nothing noticed. This keeps the two sides in step.
"""
import re

import pytest

from bridgeflow import column_matches, profiling
from bridgeflow.api.batches import BatchSummary, DepartmentSummary
from bridgeflow.api.tools import ColumnMatchResult, ConfirmationResult
from bridgeflow.config import REPO_ROOT

TOOLS = REPO_ROOT / "plugins" / "src" / "tools"

CONTRACTS = [
    ("batch-summary.ts", [BatchSummary, DepartmentSummary]),
    ("column-candidates.ts", [column_matches.CandidateList, column_matches.ColumnQuestion, column_matches.Candidate]),
    ("profile-batch.ts", [profiling.BatchProfile, profiling.ColumnProfile, profiling.ColumnOverlap]),
    ("confirm-column-match.ts", [ColumnMatchResult]),
    ("confirm-mapping.ts", [ConfirmationResult]),
]


@pytest.mark.parametrize("filename, models", CONTRACTS, ids=[c[0] for c in CONTRACTS])
def test_the_plugin_schema_declares_every_field_the_host_returns(filename, models):
    source = (TOOLS / filename).read_text(encoding="utf-8")
    declared = set(re.findall(r"\b([a-z_][a-z0-9_]*)\s*:\s*\{\s*type\s*:", source))
    for model in models:
        missing = sorted(set(model.model_fields) - declared)
        assert not missing, f"{filename} does not declare {model.__name__} fields {missing}"
