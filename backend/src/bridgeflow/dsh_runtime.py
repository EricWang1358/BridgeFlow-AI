"""Select one supported runtime for Web and Python SDK profile writers."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def native_command() -> str:
    """Never let the SDK's packed default overwrite a live Web's shared proxies."""
    configured = os.environ.get("BRIDGEFLOW_DSH")
    candidates = [configured] if configured else [str(Path(p) / "dsh") for p in os.get_exec_path()]
    for candidate in candidates:
        if not candidate:
            continue
        executable = shutil.which(candidate)
        if not executable:
            continue
        path = Path(executable).resolve()
        try:
            with path.open(encoding="utf-8") as stream:
                header = stream.readline()
            if not header.startswith("#!") or "node" not in header:
                continue
            version = subprocess.check_output([str(path), "--version"], text=True, timeout=10).strip()
            if version == "0.1.2-rc.1":
                return str(path)
        except (OSError, UnicodeError, subprocess.SubprocessError):
            continue
    raise RuntimeError(
        "Install the native CLI: npm install -g @deepseek-ai/dsh@0.1.2-rc.1; "
        "or set BRIDGEFLOW_DSH to its executable. Web and SDK must use this same installation."
    )
