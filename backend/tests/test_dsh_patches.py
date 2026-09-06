"""Tests for the patch layer that takes the shells away from the runtime.

The runtime is not started here — these cover path resolution, which is where
this can be wrong without any network. What the patch does to a live turn is
recorded in dsh/no-shell.patch.yml.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bridgeflow.config import REPO_ROOT, Settings


def test_the_shipped_patch_resolves():
    paths = Settings().dsh_patch_paths

    assert paths, "the default patch layer must resolve — it is what removes bash"
    assert Path(paths[0]).is_file()


def test_the_shipped_patch_disables_every_shell():
    text = (REPO_ROOT / "dsh" / "no-shell.patch.yml").read_text(encoding="utf-8")

    for plugin in ("persistent-bash", "persistent-pwsh"):
        assert plugin in text, f"{plugin} must be listed, or the model keeps a shell"


def test_relative_paths_are_anchored_to_the_repository():
    """So the same setting works from backend/ and from the repository root."""
    resolved = Settings(dsh_patches="dsh/no-shell.patch.yml").dsh_patch_paths

    assert resolved == [str(REPO_ROOT / "dsh" / "no-shell.patch.yml")]


def test_a_missing_patch_fails_closed():
    with pytest.raises(FileNotFoundError, match="required DSH policy"):
        _ = Settings(dsh_patches="dsh/does-not-exist.yml").dsh_patch_paths


def test_absolute_paths_pass_through(tmp_path):
    patch = tmp_path / "extra.yml"
    patch.write_text("[]\n", encoding="utf-8")

    assert Settings(dsh_patches=str(patch)).dsh_patch_paths == [str(patch)]
