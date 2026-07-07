import secrets

from fastapi import Header, HTTPException

from .config import settings


def require_admin_token(x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> None:
    if not x_admin_token or not secrets.compare_digest(x_admin_token, settings.ADMIN_TOKEN or ""):
        raise HTTPException(status_code=401, detail="Invalid or missing admin token")
