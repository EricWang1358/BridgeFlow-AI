"""The runtime's tool inventory, locked down.

`sdk-minimal` hands the model a shell, and untrusted spreadsheet content reaches
that model. `dsh/no-shell.patch.yml` takes the shells away — but a patch entry that
is not complete enough to read as an override does nothing at all, and the runtime
carries on with the tool still enabled. That failure is silent in the sense that
matters: everything still works, just with a shell in reach.

So the inventory is asserted rather than trusted. If a dsh upgrade renames a plugin,
these fail instead of quietly restoring the shell.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from bridgeflow.config import REPO_ROOT, Settings

PATCH = REPO_ROOT / "dsh" / "no-shell.patch.yml"

#: Every plugin in sdk-minimal that can reach the filesystem or a shell.
DANGEROUS = {
    "persistent-bash": "@deepseek-ai/dsh-tool-bash-persistent",
    "persistent-pwsh": "@deepseek-ai/dsh-tool-pwsh-persistent",
    "str-replace-editor": "@deepseek-ai/dsh-tool-str-replace-editor",
}


@pytest.fixture(scope="module")
def entries() -> dict[str, dict]:
    parsed = yaml.safe_load(PATCH.read_text(encoding="utf-8"))
    return {entry["id"]: entry for entry in parsed if "id" in entry}


@pytest.mark.parametrize(("plugin_id", "package"), sorted(DANGEROUS.items()))
def test_every_shell_and_editor_is_disabled(entries, plugin_id: str, package: str):
    entry = entries.get(plugin_id)

    assert entry is not None, f"{plugin_id} is not disabled — the model can still reach it"
    assert entry.get("disabled") is True


@pytest.mark.parametrize(("plugin_id", "package"), sorted(DANGEROUS.items()))
def test_each_entry_names_the_package_it_disables(entries, plugin_id: str, package: str):
    """A name mismatch makes the runtime skip the entry and keep the tool enabled.

    It says so on boot — `patch: name mismatch for "<id>" ... skipping` — but nothing
    fails, so the warning is easy to scroll past.
    """
    assert entries[plugin_id].get("name") == package


@pytest.mark.parametrize("plugin_id", sorted(DANGEROUS))
def test_each_entry_is_a_complete_override(entries, plugin_id: str):
    """`disabled: true` on its own is read as a fragment and silently ignored.

    This is how str-replace-editor stayed enabled through the first version of the
    patch while the file looked correct.
    """
    assert "config" in entries[plugin_id], (
        f"{plugin_id} needs a config key, or the override is dropped without an error"
    )


def test_the_patch_is_loaded_by_default():
    assert any(PATCH.samefile(p) for p in map(Path, Settings().dsh_patch_paths)), (
        "the patch exists but nothing loads it"
    )


def test_the_patch_explains_itself():
    """A future reader must not 'simplify' this file back into a fragment."""
    text = PATCH.read_text(encoding="utf-8")

    assert re.search(r"name mismatch", text), "the silent-skip trap must stay documented"
