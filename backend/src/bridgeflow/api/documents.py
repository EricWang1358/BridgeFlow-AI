"""Read-only declared document catalogue. Extraction and sending are not exposed."""
from __future__ import annotations

import hashlib

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from bridgeflow.documents import DocumentContract
from bridgeflow.metrics import dictionary_path

router = APIRouter(prefix="/quotation", tags=["quotation"])


@router.get("/contract")
async def quotation_contract() -> dict:
    path = dictionary_path()
    if not path.is_file():
        return {"status": "needs_configuration", "contract": None}
    try:
        if path.stat().st_size > 1024 * 1024:
            raise ValueError("Dictionary exceeds supported size")
        raw = path.read_bytes()
        dictionary = yaml.safe_load(raw)
        if dictionary is None:
            dictionary = {}
        if not isinstance(dictionary, dict):
            raise TypeError("Dictionary root must be a mapping")
        if "quotation" not in dictionary:
            return {"status": "needs_configuration", "contract": None}
        contract = DocumentContract.model_validate(dictionary["quotation"])
        contract.verify()
    except (OSError, UnicodeError, yaml.YAMLError, ValidationError, ValueError, TypeError) as exc:
        raise HTTPException(503, "Quotation declaration is invalid; ask the administrator to correct the field dictionary") from exc
    return {"status": "awaiting_samples", "contract": contract.model_dump(mode="json"),
            "source": {"filename": path.name, "document_sha256": hashlib.sha256(raw).hexdigest(), "paragraph": "quotation"}}
