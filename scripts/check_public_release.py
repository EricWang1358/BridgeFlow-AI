#!/usr/bin/env python3
"""Check public source contents without printing credential or metadata values."""
from __future__ import annotations

import argparse
import ipaddress
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

PRIVATE_ROOTS = (
    ".claude/", ".codegraph/", "docs/evidence/", "docs/images/", "docs/design/",
    "docs/requirements/", "submission/", "demo-walkthrough/", "data/uploads/",
    "data/outputs/", "data/homes/", "data/guest/", "data/gate/",
)
PRIVATE_FILES = {
    "CLAUDE.md", "HANDOFF.md", "env.sh", "data/mappings/access-control.yaml",
    "data/mappings/seats.yaml", "data/mappings/field-dictionary.yaml",
    "data/seats-assigned.json",
}
SECRET_PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GitHub token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{35,})\b"),
    "API key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "AWS access key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "JWT": re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    "tenant wiki ID": re.compile(r"space_id:\s*[\"']?\d{12,}"),
}
IP_ADDRESS = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")


def inspect_file(root: Path, name: str) -> list[str]:
    issues = []
    path = root / name
    if (name in PRIVATE_FILES or name.startswith(PRIVATE_ROOTS)
            or re.match(r"docs/\d\d-", name)
            or path.name.startswith("env.sh.") and path.name != "env.sh.example"
            or path.name.startswith(".env") and path.name != ".env.example"
            or path.suffix in {".pem", ".key", ".log"}):
        issues.append("internal or instance-local file")
    if path.is_symlink():
        issues.append("symlink must be reviewed before publication")
        return issues
    if not path.is_file():
        return issues
    if path.suffix == ".xlsx":
        try:
            with zipfile.ZipFile(path) as book:
                for member in book.namelist():
                    if member.startswith("xl/externalLinks/"):
                        issues.append("external workbook link")
                    if member.startswith("docProps/") and member.endswith(".xml"):
                        for element in ET.fromstring(book.read(member)).iter():
                            field = element.tag.rsplit("}", 1)[-1]
                            if field in {"creator", "lastModifiedBy"} and element.text not in {
                                None, "", "BridgeFlow", "openpyxl",
                            }:
                                issues.append("personal workbook author metadata")
                            if field in {"Company", "Manager", "HyperlinkBase"} and element.text:
                                issues.append("private workbook metadata")
        except (OSError, zipfile.BadZipFile, ET.ParseError):
            issues.append("unreadable workbook metadata")
        return sorted(set(issues))
    try:
        content = path.read_text(encoding="utf-8")
    except (UnicodeError, OSError):
        return issues
    for label, pattern in SECRET_PATTERNS.items():
        if pattern.search(content):
            issues.append(label)
    for match in IP_ADDRESS.finditer(content):
        try:
            address = ipaddress.ip_address(match.group())
        except ValueError:
            continue
        if address.is_global:
            issues.append("public server IP; use a configurable domain or documentation example")
            break
    return sorted(set(issues))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tree", type=Path, help="inspect an extracted source archive instead of Git")
    args = parser.parse_args()
    root = args.tree.resolve() if args.tree else Path(__file__).resolve().parents[1]
    if args.tree:
        names = sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file() or p.is_symlink())
    else:
        names = subprocess.check_output(["git", "-C", str(root), "ls-files", "-z"]).decode().split("\0")[:-1]
    failures = 0
    for name in names:
        issues = inspect_file(root, name)
        if issues:
            failures += 1
            print(f"{name}: {', '.join(issues)}", file=sys.stderr)
    print(f"Public release check: {len(names)} files, {failures} flagged paths.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
