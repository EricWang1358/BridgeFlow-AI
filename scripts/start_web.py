"""Start the native DSH Web and its private domain service with one host credential."""

from __future__ import annotations

import importlib.metadata
import os
import re
import secrets
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]

# dsh web prints its per-boot launch token exactly once, on stdout:
#   dsh web: http://127.0.0.1:3080/?token=<random>
# The token rotates every restart and has no config/env override (verified in
# dsh-client-connection: processLaunchToken is plain randomBytes). The login
# portal's /enter endpoint needs the current value to hand a signed-in browser
# over to dsh's native session, so we capture the line into a file.
TOKEN_LOG = re.compile(r"dsh web: \S+\?token=(\S+)")
TOKEN_FILE_NAME = ".web-launch-token"


def web_token_path() -> Path:
    """Shared with the portal (PORTAL_DSH_TOKEN_FILE defaults to the same path)."""
    return Path(os.environ["DSH_HOME"]) / TOKEN_FILE_NAME


def pump_web_output(web: subprocess.Popen, token_path: Path) -> None:
    """Tee dsh web's stdout to ours; stash the launch token when it appears."""
    assert web.stdout is not None
    for line in web.stdout:
        print(line, end="", flush=True)
        match = TOKEN_LOG.search(line)
        if match:
            token_path.write_text(match.group(1) + "\n", encoding="utf-8")
            token_path.chmod(0o600)


# Keep both SDK and Web on the same physical installation. Packed-runtime
# fallbacks point into /snapshot and cannot be imported by the running Node Web.
sys.path.insert(0, str(ROOT / "backend/src"))
from bridgeflow.dsh_runtime import native_command


def web_command() -> str:
    try:
        return native_command()
    except RuntimeError as error:
        raise SystemExit(str(error)) from error


def check_client_build(root: Path) -> None:
    artifact = root / "plugins/dist/client.js"
    inputs = [* (root / "plugins/src/client").rglob("*.ts*"),
              *[root / "plugins" / name for name in ("build.mjs", "package.json", "pnpm-lock.yaml")]]
    if not artifact.is_file() or any(path.is_file() and path.stat().st_mtime_ns > artifact.stat().st_mtime_ns for path in inputs):
        raise SystemExit("Client build is missing or stale. Run: pnpm --dir plugins build")


def wait_services(backend: subprocess.Popen, web: subprocess.Popen) -> None:
    while web.poll() is None:
        if backend.poll() is not None:
            raise SystemExit("Domain service stopped; stopping Web. Restart BridgeFlow after checking the service log.")
        time.sleep(.1)
    if web.returncode:
        raise SystemExit(web.returncode)


def main() -> None:
    if importlib.metadata.version("deepseek-harness-sdk") != "0.1.2rc1":
        raise SystemExit("This integration requires deepseek-harness-sdk==0.1.2rc1")
    if not os.environ.get("DSH_HOME"):
        raise SystemExit("Export DSH_HOME in the launching shell (see env.sh.example)")
    check_client_build(ROOT)
    dsh = web_command()
    env = dict(os.environ)
    env.setdefault("BRIDGEFLOW_SERVICE_TOKEN", secrets.token_urlsafe(32))
    env["BRIDGEFLOW_ENABLE_LEGACY_CONSOLE"] = "false"
    env["BRIDGEFLOW_ENABLE_LEGACY_PIPELINE"] = "false"
    env["BRIDGEFLOW_ALLOW_SAMPLE_DATA"] = "false"
    env["DSH_TOOLS_MODE"] = "native"
    env["PYTHONPATH"] = str(ROOT / "backend/src")

    # `--demo` points the service at the walkthrough's own dictionary.
    #
    # `data/business_demo/README.md` already said to use it, and nothing made that
    # happen: the default dictionary declares `gl_account` for finance while the demo
    # sheets carry `project`, so the import succeeded, the batch came back
    # `needs_configuration`, and `review_context` refused. Step 1 of the walkthrough
    # passed and step 2 was impossible. A prerequisite a person has to remember is a
    # prerequisite that fails on stage.
    if "--demo" in sys.argv:
        sys.argv.remove("--demo")
        # The sample notebook's case: the business side's v2 templates filled with the
        # fictional concrete supplier (data/mock_business/demo). The older English CSV case
        # in data/business_demo stays as the browser smokes' fixture with its own dictionary.
        env["FIELD_DICTIONARY_PATH"] = str(ROOT / "data/mock_business/demo/dictionary.yaml")
        # The synthetic production → marketing handoff (#147); never a company standard.
        env.setdefault("WORKFLOW_CATALOGUE_PATH", str(ROOT / "data/workflow_demo/catalogue.yaml"))

    # Say which dictionary is in force, every time. Which one is loaded decides
    # whether a batch can be joined at all, and it was the one fact neither the
    # launcher nor the screen ever stated.
    dictionary = env.get("FIELD_DICTIONARY_PATH", "data/mappings/field-dictionary.yaml")
    print(f"BridgeFlow field dictionary: {dictionary}", flush=True)
    processes: list[subprocess.Popen] = []
    def stop(_sig=None, _frame=None):
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
    signal.signal(signal.SIGTERM, stop)
    try:
        backend = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "bridgeflow.api.main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=ROOT, env=env,
        )
        processes.append(backend)
        for _ in range(100):
            if backend.poll() is not None:
                raise SystemExit("Domain service failed to start; check whether port 8000 is occupied")
            try:
                request = Request("http://127.0.0.1:8000/tools/list-metrics", data=b"{}", headers={
                    "content-type": "application/json", "authorization": f"Bearer {env['BRIDGEFLOW_SERVICE_TOKEN']}",
                })
                with urlopen(request, timeout=.5) as response:
                    if response.status == 200:
                        break
            except OSError:
                time.sleep(.1)
        else:
            raise SystemExit("Domain service did not become ready")
        web = subprocess.Popen(
            [dsh, "web", "--patch", "dsh/enterprise.patch.yml", "--no-open", *sys.argv[1:]],
            cwd=ROOT, env=env, stdout=subprocess.PIPE, text=True, bufsize=1,
        )
        processes.append(web)
        # A stale token from a previous boot is worse than none: /enter would
        # hand out a credential dsh no longer accepts. Cleared before boot.
        token_path = web_token_path()
        token_path.unlink(missing_ok=True)
        threading.Thread(target=pump_web_output, args=(web, token_path), daemon=True).start()
        wait_services(backend, web)
    except KeyboardInterrupt:
        pass
    finally:
        stop()
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    main()
