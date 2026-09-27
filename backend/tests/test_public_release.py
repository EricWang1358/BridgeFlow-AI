"""Public artifacts omit private configuration; upgrades preserve the live files."""
import importlib.util
import subprocess
import zipfile

import pytest

from bridgeflow.config import REPO_ROOT

spec = importlib.util.spec_from_file_location("public_release", REPO_ROOT / "scripts/check_public_release.py")
public_release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(public_release)


def test_release_scan_rejects_credentials_without_echoing_them(tmp_path):
    credential = "gh" + "p_" + "A" * 36
    (tmp_path / "settings.txt").write_text(credential)
    issues = public_release.inspect_file(tmp_path, "settings.txt")
    assert issues == ["GitHub token"]
    assert credential not in str(issues)


def test_release_scan_rejects_internal_paths_and_workbook_authors(tmp_path):
    assert public_release.inspect_file(tmp_path, "HANDOFF.md")
    assert public_release.inspect_file(tmp_path, "data/mappings/access-control.yaml")
    with zipfile.ZipFile(tmp_path / "sample.xlsx", "w") as workbook:
        workbook.writestr("docProps/core.xml", '<root><creator>Personal Author</creator></root>')
    assert public_release.inspect_file(tmp_path, "sample.xlsx") == ["personal workbook author metadata"]


def test_release_scan_accepts_localhost_and_documentation_examples(tmp_path):
    (tmp_path / "example.txt").write_text("http://127.0.0.1:8000 https://192.0.2.1 example.com")
    assert public_release.inspect_file(tmp_path, "example.txt") == []


@pytest.mark.parametrize("target_exists", [True, False])
def test_deploy_preserves_private_config_when_checkout_removes_it(tmp_path, target_exists):
    def git(*args):
        return subprocess.check_output(["git", "-C", str(tmp_path), *args], text=True).strip()

    git("init", "-q")
    git("config", "user.name", "Test")
    git("config", "user.email", "test@example.invalid")
    config_dir = tmp_path / "data/mappings"
    config_dir.mkdir(parents=True)
    paths = [config_dir / name for name in ("access-control.yaml", "seats.yaml")]
    for path in paths:
        path.write_text("instance-specific test configuration\n")
    git("add", ".")
    git("commit", "-qm", "old tracked configuration")
    original = git("rev-parse", "HEAD")
    git("rm", "--", *(str(path.relative_to(tmp_path)) for path in paths))
    (tmp_path / ".gitignore").write_text("data/mappings/*.yaml\n")
    git("add", ".gitignore")
    git("commit", "-qm", "source without instance configuration")
    clean = git("rev-parse", "HEAD")
    git("reset", "--hard", original)
    script = (REPO_ROOT / "deploy/deploy.sh").read_text()
    migration = script.split("instance_config_backup=$(mktemp -d)", 1)[1].split("# Dependencies", 1)[0]
    command = "set -euo pipefail\ninstance_config_backup=$(mktemp -d)" + migration
    result = subprocess.run(["bash", "-c", command, "deploy-migration", clean if target_exists else "missing-target"],
                            cwd=tmp_path, capture_output=True, text=True, check=False)
    assert (result.returncode == 0) == target_exists
    for path in paths:
        assert path.read_text() == "instance-specific test configuration\n"
        assert path.stat().st_mode & 0o777 == 0o600
    if target_exists:
        assert git("status", "--porcelain") == ""
