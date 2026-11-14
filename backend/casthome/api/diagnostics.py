"""Errors of the web interface, written to the server log.

An error in a browser (a phone, typically) is otherwise invisible: the
interface reports uncaught errors here and they show up in CastHome's log,
with the page and the browser they happened in.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from casthome.api.deps import client_host, require_session
from casthome.auth.sessions import Session

router = APIRouter(prefix="/api", tags=["diagnostics"])
log = logging.getLogger("casthome.client")

# At most this many reports logged per minute, whatever the number of browsers.
MAX_PER_MINUTE = 30
_recent: deque[float] = deque()


class ClientError(BaseModel):
    message: str = Field(max_length=500)
    stack: str = Field(default="", max_length=4000)
    page: str = Field(default="", max_length=200)
    agent: str = Field(default="", max_length=300)


def _allowed() -> bool:
    now = time.monotonic()
    while _recent and now - _recent[0] > 60:
        _recent.popleft()
    if len(_recent) >= MAX_PER_MINUTE:
        return False
    _recent.append(now)
    return True


@router.post("/client-errors", status_code=204)
async def client_error(
    body: ClientError, request: Request, _session: Annotated[Session, Depends(require_session)]
) -> None:
    if not _allowed():
        return
    stack = "\n    ".join(line.strip() for line in body.stack.splitlines()[:12] if line.strip())
    log.warning(
        "Interface error on %s (%s, %s): %s%s",
        body.page or "?",
        client_host(request) or "?",
        body.agent or "?",
        body.message,
        f"\n    {stack}" if stack else "",
    )
