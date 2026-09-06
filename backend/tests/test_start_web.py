"""The launcher must not silently serve stale UI or report a dead service as healthy."""
import importlib.util
import os
from pathlib import Path
from unittest.mock import Mock

import pytest

spec = importlib.util.spec_from_file_location("start_web", Path(__file__).resolve().parents[2] / "scripts/start_web.py")
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


def test_client_build_rejects_missing_and_outdated_artifacts(tmp_path):
    with pytest.raises(SystemExit, match="missing or stale"):
        launcher.check_client_build(tmp_path)
    artifact = tmp_path / "plugins/dist/client.js"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("built")
    source = tmp_path / "plugins/src/client/index.tsx"
    source.parent.mkdir(parents=True)
    source.write_text("updated")
    os.utime(artifact, (10, 10))
    os.utime(source, (20, 20))
    with pytest.raises(SystemExit, match="missing or stale"):
        launcher.check_client_build(tmp_path)
    os.utime(artifact, (30, 30))
    launcher.check_client_build(tmp_path)


def test_backend_death_and_web_exit_are_not_silent_success():
    with pytest.raises(SystemExit, match="Domain service stopped"):
        launcher.wait_services(Mock(poll=Mock(return_value=1)), Mock(poll=Mock(return_value=None)))
    with pytest.raises(SystemExit) as error:
        launcher.wait_services(Mock(), Mock(poll=Mock(return_value=7), returncode=7))
    assert error.value.code == 7
    launcher.wait_services(Mock(), Mock(poll=Mock(return_value=0), returncode=0))
