"""Seat capacity and first-come-first-served seat claims (docs/35).

Two files, two different disciplines:

- `seats.yaml` is a **capacity declaration** — the fixed fleet of generic seats
  (name, loopback port, DSH_HOME). No person is named in it. It rides the repo
  through a PR like `access-control.yaml`; provisioning generates it.
- `seats-assigned.json` is **instance state** — which subject claimed which
  seat, first come first served. The portal owns it, rewrites it atomically on
  every claim, and it is untracked so every deploy leaves it alone.

Authorization stays where it was: `console_access` in `access-control.yaml`
decides who may claim at all (the #229 gate); the registry only says how many
seats exist, and the assignment file only says who got there first.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

import yaml

#: Seat names become subdomain labels and systemd instance names.
_NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,30}$")


@dataclass(frozen=True)
class Seat:
    name: str
    #: Loopback port of this seat's dsh web; Caddy maps the subdomain to it.
    port: int
    #: Absolute DSH_HOME. The per-boot launch token lands at home/.web-launch-token.
    home: str

    @property
    def token_file(self) -> Path:
        return Path(self.home) / ".web-launch-token"

    def host_under(self, base_domain: str) -> str:
        return f"{self.name}.console.{base_domain}"


class Seats:
    """The validated capacity list with the lookups the portal needs."""

    def __init__(self, seats: list[Seat], base_domain: str, scheme: str):
        self._seats = seats
        self.base_domain = base_domain
        self.scheme = scheme
        self._by_name = {seat.name: seat for seat in seats}
        self._by_host = {seat.host_under(base_domain): seat for seat in seats}

    def __len__(self) -> int:
        return len(self._seats)

    def names(self) -> list[str]:
        return [seat.name for seat in self._seats]

    def seat(self, name: str) -> Seat | None:
        return self._by_name.get(name)

    def for_host(self, host: str) -> Seat | None:
        """`host` is the request authority without a port."""
        return self._by_host.get(host)

    def url(self, seat: Seat) -> str:
        return f"{self.scheme}://{seat.host_under(self.base_domain)}"


def load_seats(path: str, base_domain: str, scheme: str) -> Seats:
    """Parse and fully validate the capacity file; a broken fleet must not boot.

    Every field feeds a different component (portal routing, /verify binding,
    Caddy rendering, systemd units), so a missing field is a half-provisioned
    fleet that would surface as a silent wrong route later.
    """
    try:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise RuntimeError(f"seat registry cannot be read ({path}): {exc}") from exc
    entries = raw.get("seats")
    if entries is None:
        entries = []
    if not isinstance(entries, list):
        raise TypeError(f"seat registry is invalid ({path}): 'seats' must be a list")
    if not base_domain:
        raise RuntimeError("PORTAL_SEAT_BASE_DOMAIN is required when PORTAL_SEATS_PATH is set")
    seats: list[Seat] = []
    seen_names: set[str] = set()
    seen_ports: set[int] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise TypeError(f"seat registry is invalid ({path}): each seat is a mapping")
        name, port, home = (str(entry.get(k, "")).strip() for k in ("name", "port", "home"))
        if not _NAME.match(name):
            raise RuntimeError(f"seat name {name!r} must match {_NAME.pattern}")
        try:
            port_number = int(port)
        except ValueError as exc:
            raise RuntimeError(f"seat {name!r} has a non-numeric port {port!r}") from exc
        if not 1024 <= port_number <= 65535:
            raise RuntimeError(f"seat {name!r} port {port_number} is outside 1024–65535")
        if not Path(home).is_absolute():
            raise RuntimeError(f"seat {name!r} home must be an absolute path (got {home!r})")
        for label, seen, value in (("name", seen_names, name), ("port", seen_ports, port_number)):
            if value in seen:
                raise RuntimeError(f"seat {name!r} repeats the {label} {value!r}")
            seen.add(value)
        seats.append(Seat(name=name, port=port_number, home=home))
    return Seats(seats, base_domain, scheme)


class Assignments:
    """Who claimed which seat: sub → seat name, first come first served.

    The portal is the only writer; ops release is a script that edits the file
    offline (scripts/provision_seat.sh --release), so the store deliberately has
    no delete API here — a release is an administrative act with an archived
    home, not a request the portal serves.
    """

    def __init__(self, path: str):
        self._path = Path(path)
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8")) if self._path.exists() else {}
        except (OSError, ValueError) as exc:
            raise RuntimeError(f"seat assignments cannot be read ({path}): {exc}") from exc
        if not isinstance(raw, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in raw.items()
        ):
            raise RuntimeError(f"seat assignments are invalid ({path}): expected subject→seat map")
        self._by_sub: dict[str, str] = dict(raw)

    def as_map(self) -> dict[str, str]:
        return dict(self._by_sub)

    def seat_for(self, sub: str) -> str | None:
        return self._by_sub.get(sub)

    def sub_for_seat(self, seat_name: str) -> str | None:
        for sub, name in self._by_sub.items():
            if name == seat_name:
                return sub
        return None

    def claim(self, sub: str, free: list[str]) -> str | None:
        """Idempotent: an existing claim returns the same seat; a new claim
        takes the first free name; ``None`` when the fleet is exhausted."""
        if not free:
            return None
        held = self._by_sub.get(sub)
        if held is not None:
            return held
        taken = set(self._by_sub.values())
        for name in free:
            if name not in taken:
                self._by_sub[sub] = name
                self._save()
                return name
        return None

    def _save(self) -> None:
        """Atomic rewrite: a crash mid-claim must not leave a torn file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        handle, tmp = tempfile.mkstemp(dir=str(self._path.parent), prefix=".seats-assigned-")
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                json.dump(self._by_sub, stream, ensure_ascii=False, indent=2, sort_keys=True)
                stream.write("\n")
            os.replace(tmp, self._path)
        except OSError:
            os.unlink(tmp)
            raise
