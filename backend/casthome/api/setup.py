"""First-run setup from the browser: the Navidrome connection, then access.

Open to whoever opens CastHome first, as long as it is not set up. Once the
access mode is chosen, finishing a step that is still missing (e.g. the
Navidrome password could not be decrypted) needs a signed-in browser.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel

from casthome.api.deps import client_info, get_ctx, require_session, start_session
from casthome.api.server import AccessBody, NavidromeBody, resolve_navidrome, save_navidrome, validate_new_access
from casthome.appconfig import AccessMode

router = APIRouter(prefix="/api/setup", tags=["setup"])


class SetupBody(BaseModel):
    navidrome: NavidromeBody | None = None
    access: AccessBody | None = None


async def _check_allowed(request: Request, response: Response) -> dict[str, bool]:
    ctx = get_ctx(request)
    needs = await ctx.setup_needs()
    if not any(needs.values()):
        raise HTTPException(status.HTTP_409_CONFLICT, detail={"code": "setup_done"})
    if not needs["access"]:
        await require_session(request, response)
    return needs


@router.get("")
async def setup_info(request: Request, response: Response) -> dict:
    """Values to prefill and the fields locked by environment variables."""
    ctx = get_ctx(request)
    needs = await _check_allowed(request, response)
    return {
        "setup": needs,
        "navidrome": ctx.config.navidrome_fields(),
        "locked": ctx.config.locked,
        **client_info(request),
    }


@router.post("/test")
async def setup_test(body: NavidromeBody, request: Request, response: Response) -> dict:
    await _check_allowed(request, response)
    await resolve_navidrome(get_ctx(request), body)
    return {"ok": True}


@router.post("")
async def finish_setup(body: SetupBody, request: Request, response: Response) -> dict:
    ctx = get_ctx(request)
    needs = await _check_allowed(request, response)
    # Validate everything before saving anything.
    navidrome = None
    if needs["navidrome"]:
        if body.navidrome is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail={"code": "navidrome_required"})
        navidrome = await resolve_navidrome(ctx, body.navidrome)
    if needs["access"]:
        if body.access is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail={"code": "access_required"})
        validate_new_access(ctx, body.access)

    if navidrome is not None:
        await save_navidrome(ctx, *navidrome, reload_queue=True)
    if needs["access"] and body.access is not None:
        await ctx.config.set_access(body.access.mode, body.access.password)
        if body.access.mode is not AccessMode.OPEN:
            await start_session(request, response, body.access.remember)
    return {"ok": True}
