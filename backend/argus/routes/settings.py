"""Settings endpoints — store API keys provided by the user via the UI.

SECURITY notes:
- The actual key values are NEVER returned. Only a 'configured' flag per slot.
- Keys are stored in `<cache>/secrets.json` with mode 0600. The cache dir is
  gitignored. Anyone with read access to the host can read the file — the same
  threat model as `.env`. Argus is a local desktop tool, not a server-side
  multi-tenant service.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..agents import data_test, llm_test
from ..agents.llm import _resolve_primary
from ..storage import secrets


router = APIRouter(prefix="/api/settings", tags=["settings"])


class KeyUpdate(BaseModel):
    updates: dict[str, str]


@router.get("/keys")
def get_keys():
    """Return which slots are configured. Source = 'ui' | 'env' | None."""
    chosen = _resolve_primary()
    return {
        "active_llm": {"provider": chosen[0], "model": chosen[2]} if chosen else None,
        "providers": secrets.merged_view(),
    }


@router.post("/keys")
def update_keys(body: KeyUpdate):
    """Set or clear one or more keys. Empty string = clear that slot."""
    secrets.set_many(body.updates)
    return get_keys()


@router.delete("/keys/{slot}")
def clear_key(slot: str):
    secrets.clear(slot)
    return get_keys()


@router.post("/test/{slot}")
async def test_key(slot: str):
    """Smoke-test a configured provider, classify any upstream error, and
    return a structured result. The actual key value is never echoed back."""
    provider = llm_test.SLOT_TO_PROVIDER.get(slot)
    if provider is not None:
        return await llm_test.smoke_test_llm(provider)
    if slot in data_test.DATA_SLOTS:
        return await data_test.smoke_test_data(slot)
    raise HTTPException(
        status_code=404,
        detail=f"Smoke test not available for slot '{slot}'.",
    )
