"""Start the native DSH Web and its private domain service with one host credential.

Three modes (docs/35 §4):

  default          supervise backend (:8000) + dsh web in one process — the dev flow
  --backend-only   the shared backend alone (production bridgeflow.service)
  --web-only       one dsh web alone against the shared backend (seat units)

Split modes require BRIDGEFLOW_SERVICE_TOKEN to be set in the launching
environment: the backend's require_host and the approval-receipt HMAC both key
on it, so every seat must carry the same value a random mint here would not
match.
"""

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


def warn_if_token_missing(web: subprocess.Popen, token_path: Path, seconds: float = 20) -> None:
    """The capture above is one regex over dsh web's stdout; a reworded launch
    line breaks it silently, and the portal then hands browsers the site with no
    token. Say so on the console instead of letting /enter degrade in the dark."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if token_path.exists() or web.poll() is not None:
            return
        time.sleep(.5)
    print(f"WARNING: dsh web printed no launch token in {seconds:.0f}s; {token_path} is missing. "
          "The login portal will send browsers to the site without one, so a browser that has no "
          "dsh session cookie yet will meet dsh's 401. Check dsh web's startup line against TOKEN_LOG.",
          file=sys.stderr, flush=True)


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


def warn_if_backend_absent(env: dict) -> None:
    """One probe, warning only. A seat calls the shared backend lazily, so a
    backend that is still starting is fine; a wrong shared token, however, is
    invisible until the first tool call — one request now turns both into a
    line on the unit's console instead of a silent 401 later."""
    try:
        request = Request("http://127.0.0.1:8000/tools/list-metrics", data=b"{}", headers={
            "content-type": "application/json", "authorization": f"Bearer {env['BRIDGEFLOW_SERVICE_TOKEN']}",
        })
        with urlopen(request, timeout=1) as response:
            if response.status != 200:
                print(f"WARNING: shared backend answered {response.status}", file=sys.stderr, flush=True)
    except OSError:
        print("WARNING: shared backend not reachable on 127.0.0.1:8000 yet; "
              "the seat keeps its own retry on first use", file=sys.stderr, flush=True)


def wait_services(backend: subprocess.Popen | None, web: subprocess.Popen | None) -> None:
    if web is None:
        # --backend-only: this process is the supervisor of exactly one child.
        if backend.wait():
            raise SystemExit(backend.returncode)
        return
    if backend is None:
        # --web-only: same shape, other child.
        if web.wait():
            raise SystemExit(web.returncode)
        return
    while web.poll() is None:
        if backend.poll() is not None:
            raise SystemExit("Domain service stopped; stopping Web. Restart BridgeFlow after checking the service log.")
        time.sleep(.1)
    if web.returncode:
        raise SystemExit(web.returncode)


def main() -> None:
    if importlib.metadata.version("deepseek-harness-sdk") != "0.1.2rc1":
        raise SystemExit("This integration requires deepseek-harness-sdk==0.1.2rc1")
    backend_only = "--backend-only" in sys.argv
    web_only = "--web-only" in sys.argv
    if backend_only and web_only:
        raise SystemExit("--backend-only and --web-only are mutually exclusive")
    for flag in ("--backend-only", "--web-only"):
        while flag in sys.argv:
            sys.argv.remove(flag)
    run_web, run_backend = not backend_only, not web_only
    if run_web:
        if not os.environ.get("DSH_HOME"):
            raise SystemExit("Export DSH_HOME in the launching shell (see env.sh.example)")
        check_client_build(ROOT)
    dsh = web_command() if run_web else ""
    env = dict(os.environ)
    if backend_only or web_only:
        # Split deployments share this credential across processes; minting a
        # fresh random one here would lock every other process out.
        if len(os.environ.get("BRIDGEFLOW_SERVICE_TOKEN", "")) < 32:
            raise SystemExit("Split mode requires BRIDGEFLOW_SERVICE_TOKEN (32+ chars) in the "
                             "launching environment — set it in env.sh, shared by backend and seats")
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
        backend: subprocess.Popen | None = None
        web: subprocess.Popen | None = None
        if run_backend:
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
        if run_web:
            if web_only:
                warn_if_backend_absent(env)
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
            threading.Thread(target=warn_if_token_missing, args=(web, token_path), daemon=True).start()
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
