"""Selection must fail closed rather than silently run a different runtime."""
from unittest.mock import Mock

import pytest

from bridgeflow import dsh_runtime


def test_skips_packed_runtime_and_resolves_native_executable(monkeypatch, tmp_path):
    packed = tmp_path / "packed" / "dsh"
    native = tmp_path / "npm" / "dsh"
    for path, content in ((packed, b"\x7fELF\x00\xff"), (native, b"#!/usr/bin/env node\n")):
        path.parent.mkdir()
        path.write_bytes(content)
        path.chmod(0o755)
    monkeypatch.delenv("BRIDGEFLOW_DSH", raising=False)
    monkeypatch.setattr(dsh_runtime.os, "get_exec_path", lambda: [str(packed.parent), str(native.parent)])
    version = Mock(return_value="0.1.2-rc.1\n")
    monkeypatch.setattr(dsh_runtime.subprocess, "check_output", version)
    assert dsh_runtime.native_command() == str(native)
    assert version.call_count == 1, "do not execute the packed binary even for version detection"


@pytest.mark.parametrize("header,version", [
    ("#!/usr/bin/env python3\n", "0.1.2-rc.1"),
    ("#!/usr/bin/env node\n", "0.1.1"),
    ("node is not a shebang\n", "0.1.2-rc.1"),
])
def test_invalid_explicit_override_never_falls_back(monkeypatch, tmp_path, header, version):
    executable = tmp_path / "dsh"
    executable.write_text(header)
    executable.chmod(0o755)
    monkeypatch.setenv("BRIDGEFLOW_DSH", str(executable))
    monkeypatch.setattr(dsh_runtime.subprocess, "check_output", Mock(return_value=version))
    with pytest.raises(RuntimeError, match="same installation"):
        dsh_runtime.native_command()
