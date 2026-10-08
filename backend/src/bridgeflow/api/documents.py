"""Read-only declared document catalogue and built-in quotation samples. Extraction and sending are not exposed."""
from __future__ import annotations

import hashlib
from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from bridgeflow.config import REPO_ROOT, settings
from bridgeflow.documents import DocumentContract
from bridgeflow.metrics import dictionary_path
from bridgeflow.quote_compliance import Bundle, CaseError, contract_shape
from bridgeflow.schemas import SourceRef

router = APIRouter(prefix="/quotation", tags=["quotation"])


def _declared() -> tuple[dict, dict] | None:
    """The active dictionary's quotation contract and its frozen source, or None when undeclared."""
    path = dictionary_path()
    if not path.is_file():
        return None
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
            return None
        contract = DocumentContract.model_validate(dictionary["quotation"])
        contract.verify()
    except (OSError, UnicodeError, yaml.YAMLError, ValidationError, ValueError, TypeError) as exc:
        raise HTTPException(503, "Quotation declaration is invalid; ask the administrator to correct the field dictionary") from exc
    return dictionary["quotation"], {"filename": path.name, "document_sha256": hashlib.sha256(raw).hexdigest(), "paragraph": "quotation"}


@router.get("/contract")
async def quotation_contract() -> dict:
    declared = _declared()
    if declared is None:
        return {"status": "needs_configuration", "contract": None}
    config, source = declared
    return {"status": "awaiting_samples", "contract": DocumentContract.model_validate(config).model_dump(mode="json"),
            "source": source}


def _bundle() -> tuple[Bundle, dict, dict] | None:
    """The sample applies only to a quotation contract with the arithmetic its evidence was extracted for."""
    if not settings.quotation_cases_path:
        return None
    declared = _declared()
    if declared is None:
        return None
    path = Path(settings.quotation_cases_path)
    path = path if path.is_absolute() else REPO_ROOT / path
    if not path.is_file():
        return None
    try:
        bundle = Bundle(path)
        if contract_shape(bundle.config) != contract_shape(declared[0]):
            return None
    except (CaseError, ValidationError) as exc:
        raise HTTPException(503, f"Quotation sample is invalid: {exc}") from exc
    return bundle, *declared


@router.get("/cases")
async def quotation_cases() -> dict:
    loaded = _bundle()
    if loaded is None:
        return {"status": "not_applicable", "legal": None, "quotes": []}
    return {"status": "available", **loaded[0].summary()}


@router.get("/cases/{quote_id}")
async def quotation_case(quote_id: str) -> dict:
    loaded = _bundle()
    if loaded is None:
        raise HTTPException(404, "No built-in quotation sample applies to the current declaration")
    bundle, config, source = loaded
    quote = bundle.quote(quote_id)
    if quote is None:
        raise HTTPException(404, f"Unknown quotation {quote_id}")
    declaration = SourceRef(department="marketing", filename=source["filename"], paragraph="quotation",
                            excerpt="quotation:", document_sha256=source["document_sha256"])
    try:
        return bundle.evaluate(quote, config, declaration)
    except CaseError as exc:
        raise HTTPException(503, f"Quotation sample is invalid: {exc}") from exc
