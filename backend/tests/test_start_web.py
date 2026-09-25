"""The launcher must not silently serve stale UI or report a dead service as healthy."""
import importlib.util
import os
from pathlib import Path
from unittest.mock import Mock

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]

spec = importlib.util.spec_from_file_location("start_web", REPO_ROOT / "scripts/start_web.py")
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


def test_the_model_last_chosen_in_web_wins_and_env_only_fills_in(tmp_path):
    settings = tmp_path / "settings.yaml"
    env = {"DSH_HOME": str(tmp_path), "DSH_PROVIDER": "deepseek-official", "DSH_MODEL": "env-model"}
    # Nothing chosen in Web yet: env.sh's pair becomes the launch default.
    assert launcher.resolve_web_model(dict(env)) == ("deepseek-official", "env-model")
    patch = launcher.fallback_model_patch(str(tmp_path), "deepseek-official", "env-model").read_text(encoding="utf-8")
    assert "agent-default-model" in patch and "'env-model'" in patch
    assert "'../plugins/src/index.ts'" not in patch and "./dsh/presets" not in patch
    # A choice made in Web is the person's and wins; the launch carries it to every process.
    settings.write_text("agent-default-model:\n  provider: hyper-charm\n  model: chosen-model\n")
    launched = dict(env)
    assert launcher.resolve_web_model(launched) is None
    assert (launched["DSH_PROVIDER"], launched["DSH_MODEL"]) == ("hyper-charm", "chosen-model")
    assert settings.read_text() == "agent-default-model:\n  provider: hyper-charm\n  model: chosen-model\n"
    # Neither side names a model: nothing to add.
    assert launcher.resolve_web_model({"DSH_HOME": str(tmp_path / "fresh")}) is None
    settings.write_text("agent-default-model: [unclosed\n")
    with pytest.raises(SystemExit, match="Cannot read dsh Web model settings"):
        launcher.resolve_web_model(dict(env))


def test_backend_death_and_web_exit_are_not_silent_success():
    with pytest.raises(SystemExit, match="Domain service stopped"):
        launcher.wait_services(Mock(poll=Mock(return_value=1)), Mock(poll=Mock(return_value=None)))
    with pytest.raises(SystemExit) as error:
        launcher.wait_services(Mock(), Mock(poll=Mock(return_value=7), returncode=7))
    assert error.value.code == 7
    launcher.wait_services(Mock(), Mock(poll=Mock(return_value=0), returncode=0))


def test_demo_flag_points_at_the_dictionary_the_walkthrough_needs():
    """`docs/17` step 2 is impossible without it, and step 1 gives no sign.

    Only the sample case's dictionary (`data/mock_business/demo/dictionary.yaml`) declares
    joinable columns for the v2 templates and a `business_review` contract. Under the default dictionary the
    import succeeds, the batch comes back `needs_configuration`, and `review_context`
    refuses — measured once, on stage-shaped data. A prerequisite a person has to
    remember is a prerequisite that fails when it matters.
    """
    source = (REPO_ROOT / "scripts/start_web.py").read_text(encoding="utf-8")

    assert '"--demo" in sys.argv' in source
    assert 'data/mock_business/demo/dictionary.yaml' in source
    assert 'BridgeFlow field dictionary:' in source, "the launcher must say which one is in force"


def test_the_demo_dictionary_declares_what_the_review_requires():
    """If either of these is dropped, the walkthrough dies at step 2 again."""
    demo = yaml.safe_load((REPO_ROOT / "data/mock_business/demo/dictionary.yaml").read_text(encoding="utf-8"))

    assert demo["columns"]["finance"], "finance needs a joinable entity column"
    assert "business_review" in demo, "review_context refuses a batch with no contract"
