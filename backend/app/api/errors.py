"""FastAPI exception handlers."""
from __future__ import annotations

from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.services.errors import NotFoundError


async def not_found_handler(_: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)},
    )
