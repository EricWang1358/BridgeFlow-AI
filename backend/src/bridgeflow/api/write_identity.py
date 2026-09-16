"""Only the host can submit the pending native call for employee authorization."""
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from bridgeflow.identity import UserIdentity, require_user
from bridgeflow.write_authorization import issue

router = APIRouter(prefix="/identity", tags=["identity"])


class AuthorizeWrite(BaseModel):
    operation: str = Field(min_length=1, max_length=100)
    body: str = Field(min_length=2, max_length=65536)


@router.post("/authorize-write")
async def authorize_write(request: AuthorizeWrite,
                          user: Annotated[UserIdentity | None, Depends(require_user)]) -> dict:
    if user is None:
        return {"required": False}
    return {"required": True, "permit": issue(user, request.operation, request.body), "subject": user.sub}
