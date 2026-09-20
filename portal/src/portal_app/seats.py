"""The seat registry: which person owns which console instance (docs/35).

One file, `seats.yaml`, declares every provisioned seat. The portal routes
/enter by it and binds subdomains in /verify by it; deploy scripts render
Caddy blocks and systemd units from the same file, so a seat is provisioned
exactly once in exactly one place. It follows the `access-control.yaml`
discipline: the mapping is declared by people in a PR, never inferred.

An empty PORTAL_SEATS_PATH keeps the single-console behaviour — dev machines
and the pre-seat deployment never see any of this.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

#: Seat names become subdomain labels and systemd instance names, so they stay
#: lowercase and conservative even though nothing here enforces DNS beyond it.
_NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,30}$")


@dataclass(frozen=True)
class Seat:
    name: str
    #: Portal subject (Feishu union_id) owning this seat — routing key.
    sub: str
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
    """Validated registry with the two lookups the portal needs."""

    def __init__(self, seats: list[Seat], base_domain: str, scheme: str):
        self._seats = seats
        self.base_domain = base_domain
        self.scheme = scheme
        self._by_sub = {seat.sub: seat for seat in seats}
        self._by_host = {seat.host_under(base_domain): seat for seat in seats}

    def __len__(self) -> int:
        return len(self._seats)

    def names(self) -> list[str]:
        return [seat.name for seat in self._seats]

    def for_sub(self, sub: str) -> Seat | None:
        return self._by_sub.get(sub)

    def for_host(self, host: str) -> Seat | None:
        """`host` is the request authority without a port."""
        return self._by_host.get(host)

    def url(self, seat: Seat) -> str:
        return f"{self.scheme}://{seat.host_under(self.base_domain)}"


def load_seats(path: str, base_domain: str, scheme: str) -> Seats:
    """Parse and fully validate seats.yaml; a broken registry must not boot.

    Every field is load-bearing in a different component (portal routing,
    /verify binding, Caddy rendering, systemd units), so a missing field is a
    provisioning half-step that would surface as a silent wrong route later.
    """
    try:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise RuntimeError(f"seat registry cannot be read ({path}): {exc}") from exc
    entries = raw.get("seats")
    if entries is None:
        entries = []
    if not isinstance(entries, list):
        raise RuntimeError(f"seat registry is invalid ({path}): 'seats' must be a list")
    if not base_domain:
        raise RuntimeError("PORTAL_SEAT_BASE_DOMAIN is required when PORTAL_SEATS_PATH is set")
    seats: list[Seat] = []
    seen_names: set[str] = set()
    seen_subs: set[str] = set()
    seen_ports: set[int] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise RuntimeError(f"seat registry is invalid ({path}): each seat is a mapping")
        name, sub, port, home = (str(entry.get(k, "")).strip() for k in ("name", "sub", "port", "home"))
        if not _NAME.match(name):
            raise RuntimeError(f"seat name {name!r} must match {_NAME.pattern}")
        if not sub:
            raise RuntimeError(f"seat {name!r} needs a sub (the owner's portal subject)")
        try:
            port_number = int(port)
        except ValueError as exc:
            raise RuntimeError(f"seat {name!r} has a non-numeric port {port!r}") from exc
        if not 1024 <= port_number <= 65535:
            raise RuntimeError(f"seat {name!r} port {port_number} is outside 1024–65535")
        if not Path(home).is_absolute():
            raise RuntimeError(f"seat {name!r} home must be an absolute path (got {home!r})")
        for label, seen, value in (("name", seen_names, name), ("sub", seen_subs, sub),
                                   ("port", seen_ports, port_number)):
            if value in seen:
                raise RuntimeError(f"seat {name!r} repeats the {label} {value!r}")
            seen.add(value)
        seats.append(Seat(name=name, sub=sub, port=port_number, home=home))
    return Seats(seats, base_domain, scheme)
