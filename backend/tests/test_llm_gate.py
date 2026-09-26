"""The public demo's model gate (docs/36 §6).

What these pin: the real key only ever travels upstream, a guest's token is the only way in, and
every limit a public link needs is enforced before a paid call is made — while the counts it
keeps are numbers only.
"""
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from bridgeflow.llm_gate import guest_model
from bridgeflow.llm_gate.app import GateConfig, Policy, config_from_env, create_app, load_policy

TOKEN = "guest-client-token"
REAL_KEY = "sk-operator-real"


class Upstream:
    def __init__(self, stream: bool = True, usage: bool = True, status: int = 200):
        self.calls: list[httpx.Request] = []
        self.stream, self.usage, self.status = stream, usage, status

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        usage = {"prompt_tokens": 100, "prompt_cache_hit_tokens": 40, "completion_tokens": 20}
        if self.status >= 400:
            return httpx.Response(self.status, json={"error": {"message": "upstream says no"}})
        if not self.stream:
            return httpx.Response(200, json={"choices": [], **({"usage": usage} if self.usage else {})})
        frames = ['data: {"choices":[{"delta":{"content":"hi"}}]}',
                  'data: ' + json.dumps({"choices": [], "usage": usage if self.usage else None}), "data: [DONE]"]
        return httpx.Response(200, headers={"content-type": "text/event-stream"},
                              content="\n\n".join(frames).encode() + b"\n\n")


def gate(tmp_path, upstream: Upstream, clock=None, **policy) -> TestClient:
    config = GateConfig(upstream_url="http://upstream.test/v1", upstream_key=REAL_KEY, client_token=TOKEN,
                        policy=Policy(models=frozenset({"deepseek-v4-flash"}), **policy), state=tmp_path,
                        transport=httpx.MockTransport(upstream))
    if clock:
        config.clock = clock
    return TestClient(create_app(config))


def chat(client: TestClient, token: str = TOKEN, **body):
    payload = {"model": "deepseek-v4-flash", "messages": [{"role": "user", "content": "x"}], "stream": True, **body}
    return client.post("/chat/completions", json=payload, headers={"authorization": f"Bearer {token}"})


def test_forwards_with_the_real_key_and_records_counts_only(tmp_path):
    upstream = Upstream()
    with gate(tmp_path, upstream) as client:
        response = chat(client, max_tokens=999_999)
        assert response.status_code == 200 and "[DONE]" in response.text
        [sent] = upstream.calls
        assert sent.headers["authorization"] == f"Bearer {REAL_KEY}"
        assert str(sent.url) == "http://upstream.test/v1/chat/completions"
        body = json.loads(sent.content)
        assert body["max_tokens"] == 32768 and body["stream_options"] == {"include_usage": True}
        status = client.get("/status").json()
    assert status["requests"] == 1 and status["prompt_tokens"] == 100 and status["cached_tokens"] == 40
    assert status["completion_tokens"] == 20 and status["estimated"] == 0
    assert status["billable_tokens"] == 60 + 4 + 20 and status["daily_tokens"] is None
    ledger = (tmp_path / "usage.sqlite").read_bytes()
    assert b"messages" not in ledger and REAL_KEY.encode() not in ledger


def test_non_streaming_usage_is_read_from_the_body(tmp_path):
    with gate(tmp_path, Upstream(stream=False)) as client:
        assert chat(client, stream=False).status_code == 200
        assert client.get("/status").json()["completion_tokens"] == 20


def test_missing_usage_is_estimated_not_dropped(tmp_path):
    with gate(tmp_path, Upstream(usage=False)) as client:
        assert chat(client).status_code == 200
        status = client.get("/status").json()
    assert status["estimated"] == 1 and status["prompt_tokens"] > 0 and status["completion_tokens"] > 0


@pytest.mark.parametrize(("token", "body", "path", "status", "kind"), [
    ("wrong", {}, "/chat/completions", 401, "unauthorized"),
    ("", {}, "/chat/completions", 401, "unauthorized"),
    (TOKEN, {"model": "deepseek-v4-pro"}, "/chat/completions", 403, "model_not_allowed"),
    (TOKEN, {}, "/files", 403, "path_not_allowed"),
    (TOKEN, {}, "/models", 403, "path_not_allowed"),
])
def test_refusals_never_reach_upstream(tmp_path, token, body, path, status, kind):
    upstream = Upstream()
    with gate(tmp_path, upstream) as client:
        payload = {"model": "deepseek-v4-flash", "messages": [], **body}
        response = client.post(path, json=payload, headers={"authorization": f"Bearer {token}"})
        assert response.status_code == status and response.json()["error"]["type"] == kind
        assert client.get("/status").json()["denied"] == 1
    assert upstream.calls == []


def test_oversized_requests_are_refused(tmp_path):
    upstream = Upstream()
    with gate(tmp_path, upstream, max_request_bytes=200) as client:
        assert chat(client, messages=[{"role": "user", "content": "x" * 500}]).status_code == 413
    assert upstream.calls == []


def test_kill_switch_pauses_everything(tmp_path):
    upstream = Upstream()
    (tmp_path / "OFF").write_text("", encoding="utf-8")
    with gate(tmp_path, upstream) as client:
        response = chat(client)
        assert response.status_code == 503 and "paused" in response.json()["error"]["message"]
    assert upstream.calls == []


def test_rate_limit_is_a_retryable_429(tmp_path):
    now = [1000.0]
    with gate(tmp_path, Upstream(), clock=lambda: now[0], rpm=2) as client:
        assert chat(client).status_code == 200 and chat(client).status_code == 200
        limited = chat(client)
        assert limited.status_code == 429 and limited.json()["error"]["type"] == "rate_limited"
        assert int(limited.headers["retry-after"]) >= 1
        now[0] += 61
        assert chat(client).status_code == 200


def test_a_daily_budget_when_declared_stops_calls_with_a_readable_message(tmp_path):
    upstream = Upstream()
    with gate(tmp_path, upstream, daily_tokens=50) as client:
        assert chat(client).status_code == 200  # 84 billable: over from now on
        exhausted = chat(client)
        assert exhausted.status_code == 429 and exhausted.json()["error"]["type"] == "demo_budget_exhausted"
        assert "00:00" in exhausted.json()["error"]["message"]
        assert client.get("/status").json()["used_ratio"] > 1
    assert len(upstream.calls) == 1


def test_upstream_errors_pass_through_and_are_not_billed(tmp_path):
    with gate(tmp_path, Upstream(status=429)) as client:
        assert chat(client).status_code == 429
        assert client.get("/status").json()["requests"] == 0


def test_policy_file_declares_limits_and_rejects_unknown_keys(tmp_path):
    path = tmp_path / "gate.yaml"
    path.write_text("models: []\nrpm: 5\ndaily_tokens: null\n", encoding="utf-8")
    policy = load_policy(path, {"DSH_PROVIDER": "deepseek-official", "DSH_MODEL": "deepseek/deepseek-v4.1-flash"})
    assert policy.models == {"deepseek/deepseek-v4.1-flash"} and policy.rpm == 5 and policy.daily_tokens is None
    path.write_text("rmp: 5\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="unknown keys"):
        load_policy(path, {})


def test_the_committed_policy_loads_and_has_no_budget_yet():
    from bridgeflow.config import REPO_ROOT
    policy = load_policy(REPO_ROOT / "data/mappings/llm-gate.yaml", {})
    assert policy.paths == {"/chat/completions"} and policy.daily_tokens is None


@pytest.mark.parametrize(("env", "model"), [
    ({"BRIDGEFLOW_GUEST_MODEL": "a", "DSH_PROVIDER": "deepseek-official", "DSH_MODEL": "b"}, "a"),
    ({"DSH_PROVIDER": "deepseek-official", "DSH_MODEL": "b", "DEEPSEEK_MODEL": "c"}, "b"),
    ({"DSH_PROVIDER": "hyper-charm", "DSH_MODEL": "b", "DEEPSEEK_MODEL": "c"}, "c"),
    ({}, "deepseek-v4-flash"),
])
def test_guest_model_resolution(env, model):
    assert guest_model(env) == model


def test_config_needs_a_key_and_mints_one_client_token(tmp_path):
    env = {"LLM_GATE_STATE_DIR": str(tmp_path), "LLM_GATE_POLICY_PATH": str(tmp_path / "none.yaml")}
    with pytest.raises(SystemExit, match="DEEPSEEK_API_KEY"):
        config_from_env(env)
    first = config_from_env({**env, "DEEPSEEK_API_KEY": "k", "DEEPSEEK_BASE_URL": "http://llm/"})
    again = config_from_env({**env, "DEEPSEEK_API_KEY": "k"})
    assert first.client_token == again.client_token and len(first.client_token) >= 32
    assert first.upstream_url == "http://llm" and again.upstream_url == "https://api.deepseek.com"
    assert (tmp_path / "client-token").stat().st_mode & 0o777 == 0o600
