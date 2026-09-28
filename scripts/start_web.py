"""Start the native DSH Web and its private domain service with one host credential.

Three modes (docs/deployment.md):

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
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.request import Request, urlopen

import yaml

ROOT = Path(__file__).resolve().parents[1]

# dsh web prints its per-boot launch token exactly once, on stdout:
#   dsh web: http://127.0.0.1:3080/?token=<random>
# The token rotates every restart and has no config/env override (verified in
# dsh-client-connection: processLaunchToken is plain randomBytes). The login
# portal's /enter endpoint needs the current value to hand a signed-in browser
# over to dsh's native session, so we capture the line into a file.
TOKEN_LOG = re.compile(r"dsh web: \S+\?token=(\S+)")
TOKEN_FILE_NAME = ".web-launch-token"

# Guest mode (docs/deployment.md): an isolated instance for people without a Feishu account.
# Everything it writes lives under GUEST_ROOT and is wiped on every start; the operator's
# data, dictionary and credentials are never reachable from it.
GUEST_ROOT = ROOT / "data" / "guest"
GUEST_BACKEND_PORT = 8001
# Never handed to a guest instance: Feishu, the login portal and the demo model gate's own config.
GUEST_ALWAYS_STRIPPED = ("FEISHU_", "PORTAL_", "LLM_GATE_")
# Also never handed over, AI on or off: every way to reach a paid model directly. With
# BRIDGEFLOW_GUEST_LLM=1 the guest gets the loopback model gate instead (docs/deployment.md), whose
# client token is worthless anywhere else; the operator's key stays in the gate's process.
GUEST_MODEL_STRIPPED = ("DEEPSEEK_", "ANTHROPIC_", "OPENAI_", "HERMES_", "HYPER_CHARM_", "OPENCODE_", "COMMANDCODE_",
                        "OPENCLAW_", "DSH_PROVIDER", "DSH_MODEL")
# Backend providers a guest can still reach through the gate; any other choice is rerouted to it.
GUEST_BACKEND_PROVIDERS = ("mock", "deepseek", "dsh")


def web_token_path() -> Path:
    """Shared with the portal (PORTAL_DSH_TOKEN_FILE defaults to the same path)."""
    return Path(os.environ["DSH_HOME"]) / TOKEN_FILE_NAME


def resolve_web_model(env: dict[str, str]) -> tuple[str, str] | None:
    """Which model dsh Web starts on: the one last chosen in Web, else DSH_PROVIDER/DSH_MODEL.

    dsh Web keeps the person's last choice (Sessions & settings) as `agent-default-model` in
    settings.yaml, and that choice is theirs: it is never overwritten here, and a difference from
    env.sh is not an error. The launched processes then carry the same pair, so the captain and
    its SDK route agree. Only with nothing chosen does env.sh's pair apply; the caller writes it
    into the launch patch, and it is returned for that. Returns None when Web already has a choice
    or neither side names a model.
    """
    path = Path(env["DSH_HOME"]) / "settings.yaml"
    selected: object = {}
    if path.is_file():
        try:
            settings = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            raise SystemExit(f"Cannot read dsh Web model settings at {path}: {exc}") from exc
        selected = settings.get("agent-default-model", {}) if isinstance(settings, dict) else {}
    chosen = (selected.get("provider"), selected.get("model")) if isinstance(selected, dict) else (None, None)
    if all(isinstance(v, str) and v for v in chosen):
        provider, model = str(chosen[0]), str(chosen[1])
        if (env.get("DSH_PROVIDER"), env.get("DSH_MODEL")) != (provider, model) and env.get("DSH_MODEL"):
            print(f"BridgeFlow model: {provider}/{model}, last chosen in dsh Web "
                  f"(env.sh names {env.get('DSH_PROVIDER')}/{env.get('DSH_MODEL')}, used only when nothing is chosen)", flush=True)
        else:
            print(f"BridgeFlow model: {provider}/{model}, last chosen in dsh Web", flush=True)
        env["DSH_PROVIDER"], env["DSH_MODEL"] = provider, model
        return None
    provider, model = env.get("DSH_PROVIDER"), env.get("DSH_MODEL")
    if provider and model:
        print(f"BridgeFlow model: {provider}/{model} from DSH_PROVIDER/DSH_MODEL (nothing chosen in dsh Web yet)", flush=True)
        return provider, model
    return None


def fallback_model_patch(dsh_home: str, provider: str, model: str) -> Path:
    """The Web patch with env.sh's model as the default, for a DSH_HOME where none was chosen."""
    patch = (ROOT / "dsh/enterprise.patch.yml").read_text(encoding="utf-8")
    patch = (patch.replace("'../plugins/src/index.ts'", repr(str(ROOT / "plugins/src/index.ts")))
             .replace("./dsh/presets", str(ROOT / "dsh/presets")))
    patch += ("\n# Nothing chosen in dsh Web yet: start on DSH_PROVIDER/DSH_MODEL. A choice made in Web wins next time.\n"
              "- id: agent-default-model\n  name: '@deepseek-ai/dsh-agent-default-model'\n"
              f"  config:\n    provider: {provider!r}\n    model: {model!r}\n")
    path = Path(dsh_home) / "bridgeflow-web.patch.yml"
    path.write_text(patch, encoding="utf-8")
    return path


def guest_environment(env: dict[str, str]) -> Path:
    """Point this launch at a fresh, isolated guest instance; returns the dsh patch to use."""
    allow_llm = env.get("BRIDGEFLOW_GUEST_LLM") == "1"
    model = guest_model(env)
    gate_token = read_gate_token(env) if allow_llm else ""
    # Checked again after stripping: no operator secret may survive under any other name.
    secrets_held = {v for k, v in env.items()
                    if len(v) >= 8 and (k.endswith(("_API_KEY", "_SECRET")) or k == "LLM_GATE_UPSTREAM_KEY")}
    # Where staff sign in: the demo sits on the apex, so it links to the portal (docs/deployment.md).
    staff_url = env.get("PORTAL_EXTERNAL_BASE_URL", "")
    shutil.rmtree(GUEST_ROOT, ignore_errors=True)
    outputs, home = GUEST_ROOT / "outputs", GUEST_ROOT / "dsh-home"
    outputs.mkdir(parents=True)
    home.mkdir(parents=True)
    for key in list(env):
        if key.startswith(GUEST_ALWAYS_STRIPPED + GUEST_MODEL_STRIPPED) or key.endswith(("_API_KEY", "_SECRET")):
            del env[key]
    # Its own host credential: the operator's service token would also open the real backend on :8000.
    env["BRIDGEFLOW_SERVICE_TOKEN"] = secrets.token_urlsafe(32)
    if allow_llm:
        # dsh's DeepSeek provider and the backend's both append /chat/completions to this base.
        env.update({"DEEPSEEK_BASE_URL": f"http://127.0.0.1:{env.get('BRIDGEFLOW_GATE_PORT', DEFAULT_GATE_PORT)}",
                    "DEEPSEEK_API_KEY": gate_token, "DEEPSEEK_MODEL": model,
                    "DSH_PROVIDER": "deepseek-official", "DSH_MODEL": model})
        for key in [k for k in env if k == "LLM_PROVIDER" or k.startswith("LLM_PROVIDER_")]:
            if env[key] and env[key] not in GUEST_BACKEND_PROVIDERS:
                env[key] = "deepseek"
    leaked = [k for k, v in env.items() if v in secrets_held]
    if leaked:
        raise SystemExit(f"guest environment would still carry an operator secret in {leaked}; refusing to start")
    if staff_url:
        env["BRIDGEFLOW_STAFF_URL"] = staff_url
    samples = guest_sample_set(env)
    # A copy of the sample dictionary: publishing a dictionary rewrites the active file,
    # and a guest must only ever rewrite its own copy.
    dictionary = GUEST_ROOT / "dictionary.yaml"
    shutil.copy2(samples["dictionary"], dictionary)
    # Set, not defaulted: an operator's own catalogue or policies in env.sh are for staff.
    env.update({name: str(samples[key]) for key, name in GUEST_SAMPLE_ENV.items()})
    env.update({
        "DSH_HOME": str(home), "BRIDGEFLOW_GUEST_MODE": "1", "BRIDGEFLOW_GUEST_LLM": "1" if allow_llm else "0",
        "BRIDGEFLOW_BACKEND_PORT": str(GUEST_BACKEND_PORT), "FIELD_DICTIONARY_PATH": str(dictionary),
        "RESULT_STORE_PATH": str(outputs), "MAPPING_MEMORY_PATH": str(outputs / "mappings.json"),
        "COLUMN_MATCH_PATH": str(outputs / "column-matches.json"),
        "DICTIONARY_DRAFT_PATH": str(outputs / "dictionary-drafts"),
    })
    os.environ["DSH_HOME"] = str(home)  # web_token_path() reads it
    patch = (ROOT / "dsh/enterprise.patch.yml").read_text(encoding="utf-8")
    patch = (patch.replace("'../plugins/src/index.ts'", repr(str(ROOT / "plugins/src/index.ts")))
             .replace("./dsh/presets", str(ROOT / "dsh/presets"))
             .replace("http://127.0.0.1:8000", f"http://127.0.0.1:{GUEST_BACKEND_PORT}"))
    if allow_llm:
        # One model, the one the gate lets through; the operator's own Web routes are not copied.
        patch += ("\n# Guest mode with the model: through the loopback demo gate only (docs/deployment.md).\n"
                  "- id: agent-default-model\n  name: '@deepseek-ai/dsh-agent-default-model'\n"
                  f"  config:\n    provider: deepseek-official\n    model: {model!r}\n")
    else:
        patch += ("\n# Guest mode without the model: every turn is answered by a fixed note, at no cost.\n"
                  "- id: agent-default-model\n  name: '@deepseek-ai/dsh-agent-default-model'\n"
                  "  config:\n    provider: bridgeflow-guest-notice\n    model: guest-notice\n"
                  f"- insert:\n    - id: bridgeflow-guest-notice-model\n"
                  f"      name: {str(ROOT / 'plugins/src/guest-model/index.ts')!r}\n")
    path = GUEST_ROOT / "web.yml"
    path.write_text(patch, encoding="utf-8")
    # A sample set may name absolute paths outside the repository; show those as they are.
    cases = samples["demo_cases"]
    cases = cases.relative_to(ROOT) if cases.is_relative_to(ROOT) else cases
    print(f"BridgeFlow guest mode: data under {GUEST_ROOT} (wiped on start), Feishu off, AI model "
          f"{f'ON via the demo gate ({model})' if allow_llm else 'off'}, samples from "
          f"{cases.parent.parent}", flush=True)
    return path


# Set only on the re-executed guest launcher: the prepared patch path, and proof the environment
# this process started with is already the stripped one.
GUEST_PREPARED = "BRIDGEFLOW_GUEST_PATCH"


# The guest's samples (docs/deployment.md): the English translation by default, so the public demo reads
# in English; BRIDGEFLOW_GUEST_SAMPLE_SET may name another set, e.g. the Chinese originals.
GUEST_SAMPLE_SET = "data/demo_en/sample-set.yaml"
# sample-set.yaml key → the setting it becomes. `dictionary` is copied, not pointed at.
GUEST_SAMPLE_ENV = {
    "integration_spec": "INTEGRATION_SPEC_PATH", "demo_cases": "DEMO_CASES_PATH",
    "workflow_catalogue": "WORKFLOW_CATALOGUE_PATH", "workflow_samples": "WORKFLOW_SAMPLES_PATH",
    "discovery_sample": "DISCOVERY_SAMPLE_PATH", "discovery_scoring_policy": "DISCOVERY_SCORING_POLICY_PATH",
    "discovery_decision_policy": "DISCOVERY_DECISION_POLICY_PATH",
}


def guest_sample_set(env: dict[str, str]) -> dict[str, Path]:
    """Read the declared sample set; every path must exist, or the guest does not start."""
    declared = Path(env.get("BRIDGEFLOW_GUEST_SAMPLE_SET") or GUEST_SAMPLE_SET)
    path = declared if declared.is_absolute() else ROOT / declared
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise SystemExit(f"guest sample set cannot be read ({path}): {exc}") from exc
    if not isinstance(raw, dict):
        raise SystemExit(f"guest sample set {path} must be a mapping of sample names to paths, not {type(raw).__name__}")
    wanted = ["dictionary", *GUEST_SAMPLE_ENV]
    missing = [key for key in wanted if not raw.get(key)]
    if missing:
        raise SystemExit(f"guest sample set {path} does not declare: {', '.join(missing)}")
    resolved = {key: ROOT / str(raw[key]) for key in wanted}
    absent = [str(p) for p in resolved.values() if not p.is_file()]
    if absent:
        raise SystemExit(f"guest sample set {path} names files that do not exist: {', '.join(absent)}")
    return resolved


def reexec_scrubbed_guest(argv: list[str], environ: dict[str, str], execve=os.execve) -> None:
    """Replace this launcher with itself, started on the guest environment. Does not return.

    run.sh sources env.sh and then execs us, so the operator's key is in the environment this
    process was started with. Stripping it from the children's copy is not enough: /proc/<pid>/
    environ shows a process's original environment block — deleting from os.environ does not
    change it — and every guest process runs as the same user as this one. execve swaps that
    block, so nothing in the guest unit ever holds the key (docs/deployment.md; preflight checks it).
    """
    env = dict(environ)
    env[GUEST_PREPARED] = str(guest_environment(env))
    execve(sys.executable, [sys.executable, str(Path(__file__).resolve()), *argv[1:]], env)


def read_gate_token(env: dict[str, str]) -> str:
    """The demo gate's client token, which it mints on first start (docs/deployment.md)."""
    path = Path(llm_gate_state_dir(env)) / GATE_TOKEN_FILE
    token = path.read_text(encoding="utf-8").strip() if path.is_file() else ""
    if not token:
        raise SystemExit(f"BRIDGEFLOW_GUEST_LLM=1 needs the demo model gate: {path} is missing. "
                         "Start it first (sudo systemctl enable --now bridgeflow-llm-gate), or unset BRIDGEFLOW_GUEST_LLM.")
    return token


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
from bridgeflow.llm_gate import CLIENT_TOKEN_FILE as GATE_TOKEN_FILE
from bridgeflow.llm_gate import DEFAULT_PORT as DEFAULT_GATE_PORT
from bridgeflow.llm_gate import guest_model
from bridgeflow.llm_gate import state_dir as llm_gate_state_dir


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
        request = Request(f"http://127.0.0.1:{env.get('BRIDGEFLOW_BACKEND_PORT', '8000')}/tools/list-metrics", data=b"{}", headers={
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
    guest = "--guest" in sys.argv
    if guest:
        if backend_only or web_only:
            raise SystemExit("--guest runs its own backend and console together; drop --backend-only/--web-only")
        if not os.environ.get(GUEST_PREPARED):
            reexec_scrubbed_guest(sys.argv, dict(os.environ))
        sys.argv.remove("--guest")
        os.environ.setdefault("DSH_HOME", str(GUEST_ROOT / "dsh-home"))
    if run_web:
        if not os.environ.get("DSH_HOME"):
            raise SystemExit("Export DSH_HOME in the launching shell (see env.sh.example)")
        check_client_build(ROOT)
    dsh = web_command() if run_web else ""
    env = dict(os.environ)
    if (backend_only or web_only) and len(os.environ.get("BRIDGEFLOW_SERVICE_TOKEN", "")) < 32:
        # Split deployments share this credential across processes; minting a
        # fresh random one here would lock every other process out.
        raise SystemExit("Split mode requires BRIDGEFLOW_SERVICE_TOKEN (32+ chars) in the "
                         "launching environment — set it in env.sh, shared by backend and seats")
    env.setdefault("BRIDGEFLOW_SERVICE_TOKEN", secrets.token_urlsafe(32))
    env["BRIDGEFLOW_ENABLE_LEGACY_CONSOLE"] = "false"
    env["BRIDGEFLOW_ENABLE_LEGACY_PIPELINE"] = "false"
    env["BRIDGEFLOW_ALLOW_SAMPLE_DATA"] = "false"
    env["DSH_TOOLS_MODE"] = "native"
    env["PYTHONPATH"] = str(ROOT / "backend/src")
    patch_path = "dsh/enterprise.patch.yml"
    if guest:
        patch_path = env.pop(GUEST_PREPARED)  # prepared before the re-exec above
    if run_web and not guest:
        fallback = resolve_web_model(env)
        if fallback:
            patch_path = str(fallback_model_patch(env["DSH_HOME"], *fallback))
    backend_port = env.get("BRIDGEFLOW_BACKEND_PORT", "8000")

    # `--demo` selects the built-in XLSX sample notebook's dictionary. The separate
    # CSV case in data/business_demo requires its own FIELD_DICTIONARY_PATH.
    if "--demo" in sys.argv:
        sys.argv.remove("--demo")
        # The sample notebook's case: the business side's v2 templates filled with the
        # fictional concrete supplier (data/mock_business/demo). The older English CSV case
        # in data/business_demo stays as the browser smokes' fixture with its own dictionary.
        if not guest:  # a guest instance already points at its own copy of this dictionary
            env["FIELD_DICTIONARY_PATH"] = str(ROOT / "data/mock_business/demo/dictionary.yaml")

    # The template-filling and handoff workflow is a core flow, and without a catalogue its
    # page is a 503 — deployed, that meant the flow was invisible. No business catalogue
    # exists yet (the templates are still with the business side, #23), so an unset path
    # falls back to the synthetic production → marketing handoff (#147). Its page states
    # the catalogue's case ("合成示例 … 非客户数据"), and an operator's own path always wins.
    env.setdefault("WORKFLOW_CATALOGUE_PATH", str(ROOT / "data/workflow_demo/catalogue.yaml"))
    # Discovery's scoring and decision pages need declared policies; without them they are a
    # 503, which is how the discovery → workflow story went unseen. Same rule as above: the
    # synthetic sample policies (data/discovery_demo/, fictional people) apply only when an
    # operator has declared none.
    env.setdefault("DISCOVERY_SCORING_POLICY_PATH", str(ROOT / "data/discovery_demo/scoring-policy.yaml"))
    env.setdefault("DISCOVERY_DECISION_POLICY_PATH", str(ROOT / "data/discovery_demo/decision-policy.yaml"))

    # Say which dictionary is in force, every time. Which one is loaded decides
    # whether a batch can be joined at all, and it was the one fact neither the
    # launcher nor the screen ever stated.
    dictionary = env.get("FIELD_DICTIONARY_PATH", "data/mappings/field-dictionary.yaml")
    print(f"BridgeFlow field dictionary: {dictionary}", flush=True)
    print(f"BridgeFlow workflow catalogue: {env['WORKFLOW_CATALOGUE_PATH']}", flush=True)
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
                [sys.executable, "-m", "uvicorn", "bridgeflow.api.main:app", "--host", "127.0.0.1", "--port", backend_port],
                cwd=ROOT, env=env,
            )
            processes.append(backend)
            for _ in range(100):
                if backend.poll() is not None:
                    raise SystemExit(f"Domain service failed to start; check whether port {backend_port} is occupied")
                try:
                    request = Request(f"http://127.0.0.1:{backend_port}/tools/list-metrics", data=b"{}", headers={
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
                [dsh, "web", "--patch", patch_path, "--no-open", *sys.argv[1:]],
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
