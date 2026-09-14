"""The deployment files agree with each other and with the app, before any instance exists (#138).

AWS is not provisioned yet, so nothing here connects anywhere. What can be checked is that the
pieces a first deploy depends on are consistent: the port Caddy proxies to is the port the unit
starts on, the health path the deploy waits for is a real route, CI deploys stay off until a
person turns them on, and no secret is committed.
"""
import re
import shutil
import subprocess

import pytest
import yaml

from bridgeflow.api.main import app
from bridgeflow.config import REPO_ROOT

DEPLOY = REPO_ROOT / "deploy"


def test_caddy_proxies_to_the_port_the_unit_starts_on():
    unit = (DEPLOY / "bridgeflow.service").read_text(encoding="utf-8")
    bootstrap = (DEPLOY / "bootstrap.sh").read_text(encoding="utf-8")
    [unit_port] = re.findall(r"^ExecStart=.*--port (\d+)", unit, re.MULTILINE)
    [bootstrap_port] = re.findall(r"^WEB_PORT=(\d+)$", bootstrap, re.MULTILINE)
    assert unit_port == bootstrap_port
    template = (DEPLOY / "Caddyfile.template").read_text(encoding="utf-8")
    assert "reverse_proxy 127.0.0.1:__WEB_PORT__" in template
    assert "--host 127.0.0.1" in unit  # Caddy is the only public listener


def test_portal_unit_and_caddy_site_agree_on_the_portal_port():
    unit = (DEPLOY / "portal.service").read_text(encoding="utf-8")
    bootstrap = (DEPLOY / "bootstrap.sh").read_text(encoding="utf-8")
    [unit_port] = re.findall(r"portal_app\.main:app.*--port (\d+)", unit)
    [bootstrap_port] = re.findall(r"^PORTAL_PORT=(\d+)$", bootstrap, re.MULTILINE)
    assert unit_port == bootstrap_port
    template = (DEPLOY / "Caddyfile.template").read_text(encoding="utf-8")
    assert "portal.__DOMAIN__" in template
    assert "reverse_proxy 127.0.0.1:__PORTAL_PORT__" in template
    # No pre-auth anywhere: the Feishu callback must reach the portal directly.
    assert "basic_auth" not in template


def test_the_unit_runs_the_launcher_that_exists():
    unit = (DEPLOY / "bridgeflow.service").read_text(encoding="utf-8")
    [command] = re.findall(r"^ExecStart=(\S+)", unit, re.MULTILINE)
    assert command.endswith("/BridgeFlow-AI/run.sh") and (REPO_ROOT / "run.sh").stat().st_mode & 0o111


def test_the_health_path_deploy_waits_for_is_a_route():
    routes = {getattr(r, "path", "") for r in app.routes}
    for script in ("deploy.sh", "preflight.sh"):
        for path in re.findall(r"http://127\.0\.0\.1:8000(/[\w/-]+)", (DEPLOY / script).read_text(encoding="utf-8")):
            assert path in routes, (script, path)


def test_ci_deploys_stay_off_until_a_person_enables_them():
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/deploy.yml").read_text(encoding="utf-8"))
    condition = workflow["jobs"]["deploy"]["if"]
    assert "vars.DEPLOY_ENABLED == 'true'" in condition and "pull_request" in condition


def test_no_secret_or_bootstrap_variable_is_committed_in_deploy_files():
    for path in DEPLOY.iterdir():
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"\$2[aby]\$\d\d\$[./A-Za-z0-9]{53}", text), path  # a real bcrypt hash
        assert not re.search(r"sk-[A-Za-z0-9]{20,}", text), path
        # Bootstrap/credential variables come from the launching shell only. PORTAL_PORT
        # and the like are non-secret tuning knobs and stay assignable in scripts.
        assert not re.search(
            r"^\s*(export\s+)?(DSH_[A-Z_]+|DEEPSEEK_BASE_URL"
            r"|PORTAL_(FEISHU_APP_ID|FEISHU_APP_SECRET|SESSION_SECRET|KEY_PATH"
            r"|EXTERNAL_BASE_URL|BASE_URL|APPS_PATH))=",
            text, re.MULTILINE), path


@pytest.mark.parametrize("script", ["bootstrap.sh", "preflight.sh", "deploy.sh"])
def test_deploy_scripts_parse(script):
    subprocess.run(["bash", "-n", str(DEPLOY / script)], check=True)
    if shutil.which("shellcheck"):
        subprocess.run(["shellcheck", "-S", "error", str(DEPLOY / script)], check=True)
