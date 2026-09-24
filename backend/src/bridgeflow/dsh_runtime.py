"""Select one supported runtime for Web and Python SDK profile writers."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

#: Where scripts/install_dsh.sh puts the pinned CLI: beside the repository, like .venv.
PRIVATE_DSH = Path(__file__).resolve().parents[3].parent / ".dsh-cli" / "node_modules" / ".bin" / "dsh"


def native_command() -> str:
    """Never let the SDK's packed default overwrite a live Web's shared proxies."""
    configured = os.environ.get("BRIDGEFLOW_DSH")
    # The private install beside the repository (scripts/install_dsh.sh) comes before PATH, so a
    # person's own global dsh — any version — is never replaced or picked up by accident.
    private = str(PRIVATE_DSH)
    candidates = [configured] if configured else [private, *(str(Path(p) / "dsh") for p in os.get_exec_path())]
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
        "Install the pinned dsh privately (leaves any other dsh alone): bash scripts/install_dsh.sh; "
        "or set BRIDGEFLOW_DSH to a dsh 0.1.2-rc.1 executable. Web and SDK must use this same installation."
    )
