"""Whether a signed-in person may reach the agent console at all (issue #229).

The console — dsh web's chat, sessions, notebooks and approval queue — is one
shared dsh identity: everybody who gets in is the same dsh user, so anyone
inside can read everybody else's work (docs/34 §二 第 1 步). Until per-employee
isolation is evaluated (#230), reaching it must be a declared grant rather than
a side effect of having logged in.

The portal asks this route from its own `/verify`, carrying the user token it
just signed. So this router is mounted WITHOUT `require_host`: the portal holds
no host credential and must not — the host token is the model runtime's, and
handing it to the identity service would invert the trust direction docs/27
established. A valid portal signature for this audience *is* the authentication
here, and the route answers only about the bearer of that token.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from bridgeflow import access
from bridgeflow.config import settings
from bridgeflow.identity import UserIdentity, require_user

router = APIRouter(prefix="/identity", tags=["identity"])


@router.get("/console-access")
async def console_access(user: Annotated[UserIdentity | None, Depends(require_user)]) -> dict:
    """`{"allowed": bool, "roles": [...]}` for the token's own subject.

    `user is None` means this backend has no portal configured, so it did not
    verify anything. A portal that asks the question while the backend cannot
    answer it is a half-configured deployment: say so (503) instead of returning
    a permissive answer nobody checked.
    """
    if user is None:
        raise HTTPException(503, "Portal identity is not configured on this service: set PORTAL_BASE_URL")
    # One resolution, not one per field: each call re-reads the mapping file.
    resolved = access.resolve(user.sub)
    return {"allowed": access.CONSOLE_OPERATION in resolved.operations,
            "roles": sorted(resolved.roles),
            "operation": access.CONSOLE_OPERATION,
            "audience": settings.portal_audience}
