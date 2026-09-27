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


def test_the_backend_paths_the_scripts_probe_are_routes():
    # app.openapi() flattens every included router; iterating app.routes does
    # not, because this FastAPI wraps includes as _IncludedRouter with no .path
    # — a blindness that hid every /tools/* route until preflight started
    # probing one.
    paths = set(app.openapi()["paths"])
    for script in ("deploy.sh", "preflight.sh"):
        for path in re.findall(r"http://127\.0\.0\.1:8000(/[\w/-]+)", (DEPLOY / script).read_text(encoding="utf-8")):
            assert path in paths, (script, path)


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


def _render(*args: str) -> str:
    import sys
    return subprocess.run([sys.executable, str(DEPLOY / "render_caddy.py"), "example.com", *args],
                          check=True, capture_output=True, text=True).stdout


def _site(caddyfile: str, host: str) -> str:
    start = caddyfile.index(f"\n{host} {{") if not caddyfile.startswith(f"{host} {{") else 0
    return caddyfile[start:caddyfile.index("\n}", start + 1) + 2]


def test_the_apex_becomes_the_public_demo_only_once_the_guest_instance_is_on():
    # docs/36 §3: without the guest instance the apex keeps redirecting to the portal.
    assert "redir https://portal.example.com{uri} 302" in _render()
    demo = _render("--guest-port", "3090")
    apex = _site(demo, "example.com")
    assert "forward_auth" not in apex and "reverse_proxy 127.0.0.1:3090" in apex
    # No session → the portal's token handover on this host; a failing ?token= must not loop.
    assert "rewrite * /guest" in apex and "redir @page /__enter 302" in apex
    assert "{http.request.uri.query.token} == \"\"" in apex and "header Accept *text/html*" in apex
    assert "copy_response" in apex and "portal.example.com" not in apex
    assert "guest.example.com" not in demo
    # Seats and the portal are untouched.
    assert "seat-1.console.example.com {" in demo and "portal.example.com {" in demo


def test_no_rendered_shape_issues_a_permanent_redirect(tmp_path):
    # docs/37: the seat-era apex's 301 stayed in browsers after the apex became the demo, and
    # sent every guest entry back to the portal. The front door changes with a unit toggle, so
    # nothing Caddy answers may be cacheable forever.
    for args in ((), ("--guest-port", "3090"), ("--seats", str(tmp_path / "none.yaml")),
                 ("--guest-port", "3090", "--seats", str(tmp_path / "none.yaml"))):
        redirects = [line for line in _render(*args).splitlines() if line.strip().startswith("redir ")]
        assert not [line for line in redirects if re.search(r"\b(permanent|301|308)\b", line)], args


def test_the_demo_token_exchange_purges_a_stale_redirect_and_cannot_loop():
    apex = _site(_render("--guest-port", "3090"), "example.com")
    exchange = apex[apex.index("handle @token_entry {"):apex.index("\n    handle {")]
    assert "path /" in apex and "query token=*" in apex
    # Cache only: "cookies" would drop the dsh session set by this very response.
    assert 'header_down Clear-Site-Data "\\"cache\\""' in exchange and "cookies" not in exchange
    assert 'header_down Location "^/$" "/?entered=1"' in exchange
    assert "reverse_proxy 127.0.0.1:3090" in exchange
    # The landing URL joins the loop guard: a 401 there is shown, not redirected to /__enter.
    assert '{http.request.uri.query.entered} == ""' in apex
    # The exchange is matched before the catch-all, and only there is the cache cleared.
    assert apex.index("handle @token_entry {") < apex.index("\n    handle {")
    assert apex.count("Clear-Site-Data") == 1


def test_legacy_single_console_moves_off_the_apex_for_the_demo(tmp_path):
    rendered = _render("--guest-port", "3090", "--seats", str(tmp_path / "none.yaml"))
    assert "console.example.com {" in rendered and "forward_auth" in _site(rendered, "console.example.com")
    assert "forward_auth" not in _site(rendered, "example.com")


@pytest.mark.skipif(shutil.which("caddy") is None, reason="caddy not installed")
@pytest.mark.parametrize("args", [(), ("--guest-port", "3090")])
def test_rendered_caddyfiles_validate(tmp_path, args):
    path = tmp_path / "Caddyfile"
    path.write_text(_render(*args), encoding="utf-8")
    subprocess.run(["caddy", "validate", "--adapter", "caddyfile", "--config", str(path)],
                   check=True, capture_output=True)


def test_guest_unit_trusts_the_apex_and_the_gate_stays_on_loopback():
    guest = (DEPLOY / "bridgeflow-guest.service").read_text(encoding="utf-8")
    assert "--trusted-host <domain> --trusted-host <domain>:443" in guest and "guest.<domain>" not in guest
    gate = (DEPLOY / "bridgeflow-llm-gate.service").read_text(encoding="utf-8")
    assert "source env.sh" in gate and "-m bridgeflow.llm_gate" in gate and "--host" not in gate
    deploy = (DEPLOY / "deploy.sh").read_text(encoding="utf-8")
    assert "bridgeflow-llm-gate.service:bridgeflow-llm-gate.service" in deploy
    assert deploy.index("restart bridgeflow-llm-gate") < deploy.index("restart bridgeflow-guest")
