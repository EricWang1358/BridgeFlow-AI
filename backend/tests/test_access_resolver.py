"""Role resolution from Feishu wiki membership (issue #204).

Offline: the Feishu seam (access_resolver.fetch_space_members / client_factory)
is faked; the structure file is a real YAML written per test, re-read per call.
"""
import time

import httpx
import pytest
import yaml
from fastapi import HTTPException

from bridgeflow import access_resolver, identity
from bridgeflow.access import departments_for, operations_for
from bridgeflow.config import settings
from bridgeflow.feishu import FeishuError

SPACES = {
    "departments": {d: {"space_id": f"spc_{d}", "member": f"{d}_member", "admin": f"{d}_admin"}
                    for d in ("production", "procurement", "finance", "marketing")},
    "master_office": {"space_id": "spc_master", "member": "master_office_member", "admin": "master_office_admin"},
}
ROLES = {
    "master_office_member": {"departments": ["production", "procurement", "finance", "marketing"],
                             "operations": ["batch_import"]},
    "master_office_admin": {"departments": ["production", "procurement", "finance", "marketing"],
                            "operations": ["confirm_mapping", "batch_import"]},
    **{f"{d}_member": {"departments": [d], "operations": ["batch_import"]}
       for d in ("production", "procurement", "finance", "marketing")},
    **{f"{d}_admin": {"departments": [d], "operations": ["batch_import", "review_note"]}
       for d in ("production", "procurement", "finance", "marketing")},
}


@pytest.fixture
def configured(monkeypatch, tmp_path):
    """A valid structure file plus a dict-backed fake membership."""
    acl = tmp_path / "access-control.yaml"
    acl.write_text(yaml.safe_dump({"spaces": SPACES, "roles": ROLES}), encoding="utf-8")
    monkeypatch.setattr(settings, "access_control_path", str(acl))
    membership: dict[str, dict[str, str]] = {}
    calls: list[str] = []
    monkeypatch.setattr(access_resolver, "fetch_space_members",
                        lambda space_id: calls.append(space_id) or dict(membership.get(space_id, {})))
    access_resolver.reset_cache()
    yield membership, calls, acl
    access_resolver.reset_cache()


def test_a_member_resolves_the_role_bound_to_their_seat(configured):
    membership, _, _ = configured
    membership["spc_production"] = {"ou_bob": "member"}
    resolved = access_resolver.resolve("ou_bob")
    assert resolved.roles == {"production_member"}
    assert departments_for("ou_bob") == {"production"}
    assert operations_for("ou_bob") == {"batch_import"}


def test_an_admin_resolves_the_admin_role(configured):
    membership, _, _ = configured
    membership["spc_production"] = {"ou_boss": "admin"}
    resolved = access_resolver.resolve("ou_boss")
    assert resolved.roles == {"production_admin"}
    assert operations_for("ou_boss") == {"batch_import", "review_note"}


def test_membership_in_several_spaces_unions_the_grants(configured):
    membership, _, _ = configured
    membership["spc_production"] = {"ou_bob": "member"}
    membership["spc_finance"] = {"ou_bob": "admin"}
    resolved = access_resolver.resolve("ou_bob")
    assert resolved.roles == {"production_member", "finance_admin"}
    assert departments_for("ou_bob") == {"production", "finance"}
    assert operations_for("ou_bob") == {"batch_import", "review_note"}


def test_the_master_office_admin_satisfies_global_mapping_scope(configured):
    membership, _, _ = configured
    membership["spc_master"] = {"ou_chief": "admin"}
    resolved = access_resolver.resolve("ou_chief")
    assert access_resolver.KNOWN_DEPARTMENTS <= set(resolved.departments)
    assert "confirm_mapping" in resolved.operations


def test_a_user_no_space_lists_sees_nothing(configured):
    resolved = access_resolver.resolve("ou_stranger")
    assert resolved.roles == set() and departments_for("ou_stranger") == set()


def test_open_id_membership_is_bridged_through_the_observed_pair(configured, monkeypatch):
    membership, _, _ = configured
    membership["spc_production"] = {"on_bob_open": "member"}  # the wiki API answers open_ids
    monkeypatch.setattr(identity, "_open_ids", {"ou_bob": "on_bob_open"})
    assert identity.open_id_for("ou_bob") == "on_bob_open"
    assert departments_for("ou_bob") == {"production"}
    assert departments_for("ou_never_logged_in") == set()


def test_member_lists_are_cached_for_the_ttl(configured):
    _, calls, _ = configured
    access_resolver.resolve("ou_bob")
    access_resolver.resolve("ou_carol")
    assert len(calls) == 5  # four departments + master office, fetched once each
    access_resolver.reset_cache()
    access_resolver.resolve("ou_bob")
    assert len(calls) == 10


def test_a_stale_entry_is_refetched_after_the_ttl(configured, monkeypatch):
    _, calls, _ = configured
    access_resolver.resolve("ou_bob")
    # monotonic() has no epoch: its zero is boot, and a fresh CI runner can be
    # minutes old — "far in the past" only means something relative to now.
    stale = time.monotonic() - access_resolver.MEMBERSHIP_TTL_SECONDS - 1
    cached = {sid: (stale, members) for sid, (_, members) in access_resolver._members_cache.items()}
    monkeypatch.setattr(access_resolver, "_members_cache", cached)
    access_resolver.resolve("ou_bob")
    assert len(calls) == 10


def test_a_failing_space_fails_closed(configured, monkeypatch):
    def down(space_id):
        raise FeishuError("Feishu refused (code 131006): no permission")

    monkeypatch.setattr(access_resolver, "fetch_space_members", down)
    with pytest.raises(HTTPException) as failure:
        access_resolver.resolve("ou_bob")
    assert failure.value.status_code == 503


def test_failed_fetches_are_never_cached(configured, monkeypatch):
    membership, _, _ = configured
    state = {"down": True}

    def flaky(space_id):
        if state["down"]:
            raise FeishuError("Feishu could not be reached")
        return dict(membership.get(space_id, {}))

    monkeypatch.setattr(access_resolver, "fetch_space_members", flaky)
    with pytest.raises(HTTPException):
        access_resolver.resolve("ou_bob")
    state["down"] = False
    membership["spc_master"] = {"ou_bob": "member"}
    assert access_resolver.resolve("ou_bob").roles == {"master_office_member"}


def test_a_missing_structure_file_fails_loudly(configured, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "access_control_path", str(tmp_path / "missing.yaml"))
    with pytest.raises(HTTPException) as failure:
        access_resolver.resolve("ou_bob")
    assert failure.value.status_code == 503 and "not configured" in failure.value.detail


def _invalid(configured, mutate):
    _, _, acl = configured
    config = yaml.safe_load(acl.read_text())
    mutate(config)
    acl.write_text(yaml.safe_dump(config))
    with pytest.raises(HTTPException) as failure:
        access_resolver.structure()
    assert failure.value.status_code == 503


def test_a_missing_department_mapping_is_invalid(configured):
    _invalid(configured, lambda c: c["spaces"]["departments"].pop("marketing"))


def test_a_missing_master_office_is_invalid(configured):
    _invalid(configured, lambda c: c["spaces"].pop("master_office"))


def test_a_dangling_role_reference_is_invalid(configured):
    _invalid(configured, lambda c: c["spaces"]["departments"]["production"].update(admin="ghost"))


def test_duplicate_space_ids_are_invalid(configured):
    _invalid(configured, lambda c: c["spaces"]["departments"]["finance"].update(space_id="spc_production"))


def test_an_unknown_department_in_a_role_is_invalid(configured):
    _invalid(configured, lambda c: c["roles"]["production_member"].update(departments=["logistics"]))


def test_confirm_mapping_requires_all_departments(configured):
    def shrink(config):
        config["roles"]["production_admin"]["operations"] = ["confirm_mapping"]

    _invalid(configured, shrink)


@pytest.mark.parametrize("value", ["production", [123], [" "], None])
def test_malformed_role_fields_are_invalid(configured, value):
    _invalid(configured, lambda c: c["roles"]["production_member"].update(operations=value))


# --- HTTP level: the real fetcher against a fake Feishu transport -------------------------


@pytest.fixture
def feishu_transport(monkeypatch):
    """A canned Feishu tenant: token endpoint plus one paged members endpoint."""
    seen = {"tokens": 0, "member_calls": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("tenant_access_token/internal"):
            seen["tokens"] += 1
            return httpx.Response(200, json={"code": 0, "tenant_access_token": "t-test", "expire": 7200})
        if "/members" in request.url.path:
            seen["member_calls"] += 1
            if request.url.params.get("page_token") != "p2":
                return httpx.Response(200, json={"code": 0, "data": {
                    "has_more": True, "page_token": "p2",
                    "members": [{"member_id": "on_a", "member_role": "admin", "member_type": "openid"},
                                {"member_id": "chat_x", "member_role": "member", "member_type": "openchat"}]}})
            return httpx.Response(200, json={"code": 0, "data": {
                "has_more": False,
                "members": [{"member_id": "on_b", "member_role": "member", "member_type": "openid"}]}})
        return httpx.Response(404, json={"code": 404, "msg": "unknown path"})

    monkeypatch.setattr(settings, "feishu_app_id", "cli_test")
    monkeypatch.setattr(settings, "feishu_app_secret", "secret")
    monkeypatch.setattr(access_resolver, "client_factory",
                        lambda: httpx.Client(base_url="https://open.feishu.cn",
                                             transport=httpx.MockTransport(handler)))
    access_resolver.reset_cache()
    yield seen
    access_resolver.reset_cache()


def test_fetch_space_members_pages_and_skips_non_people(feishu_transport):
    members = access_resolver.fetch_space_members("spc_x")
    assert members == {"on_a": "admin", "on_b": "member"}
    assert feishu_transport["tokens"] == 1 and feishu_transport["member_calls"] == 2


def test_frequency_control_is_retried_then_fails_closed(monkeypatch, tmp_path):
    acl = tmp_path / "access-control.yaml"
    acl.write_text(yaml.safe_dump({"spaces": SPACES, "roles": ROLES}), encoding="utf-8")
    monkeypatch.setattr(settings, "access_control_path", str(acl))

    def limited(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("tenant_access_token/internal"):
            return httpx.Response(200, json={"code": 0, "tenant_access_token": "t", "expire": 7200})
        return httpx.Response(429, json={"code": 99991400, "msg": "frequency control"})

    monkeypatch.setattr(access_resolver, "client_factory",
                        lambda: httpx.Client(base_url="https://open.feishu.cn",
                                             transport=httpx.MockTransport(limited)))
    monkeypatch.setattr(access_resolver.time, "sleep", lambda seconds: None)
    access_resolver.reset_cache()
    with pytest.raises(HTTPException) as failure:
        access_resolver.resolve("ou_bob")
    assert failure.value.status_code == 503
    assert "99991400" in failure.value.detail


def test_missing_feishu_credentials_fail_closed(monkeypatch, tmp_path):
    acl = tmp_path / "access-control.yaml"
    acl.write_text(yaml.safe_dump({"spaces": SPACES, "roles": ROLES}), encoding="utf-8")
    monkeypatch.setattr(settings, "access_control_path", str(acl))
    monkeypatch.setattr(settings, "feishu_app_id", "")
    monkeypatch.setattr(settings, "feishu_app_secret", "")
    access_resolver.reset_cache()
    with pytest.raises(HTTPException) as failure:
        access_resolver.resolve("ou_bob")
    assert failure.value.status_code == 503 and "not configured" in failure.value.detail.lower()


def test_department_grants_union_across_roles(configured):
    _, _, acl = configured
    config = yaml.safe_load(acl.read_text())
    config["roles"]["production_member"]["departments"] = ["production"]
    config["roles"]["master_office_member"]["departments"] = ["production", "procurement"]
    acl.write_text(yaml.safe_dump(config))
    configured[0]["spc_production"] = {"ou_bob": "member"}
    configured[0]["spc_master"] = {"ou_bob": "member"}
    assert departments_for("ou_bob") == {"production", "procurement"}


def test_the_repository_access_control_file_ships_valid():
    """The tracked file is what deploy.sh puts on the instance (docs/22 §5b).

    No monkeypatch: this reads the default path deliberately, so an invalid
    policy edit fails review instead of turning the deployed data plane into
    503s. Nothing here talks to Feishu — structure() is pure validation.
    """
    assert access_resolver.access_path().is_file()
    declared = access_resolver.structure()
    assert set(declared["spaces"]["departments"]) == access_resolver.KNOWN_DEPARTMENTS
