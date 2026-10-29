import hashlib
import secrets
from datetime import timedelta
from urllib.parse import urlparse

from fastapi import Request, Security
from fastapi.security import APIKeyCookie
from sqlalchemy import delete, func, select

from app.platform.database import session_factory
from app.platform.errors import DomainError
from app.platform.models import AccessSession
from app.platform.settings import get_settings

COOKIE_NAME = "egrant_session"


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def require_access(
    request: Request,
    cookie: str | None = Security(APIKeyCookie(name=COOKIE_NAME, auto_error=False)),
) -> None:
    settings = get_settings()
    if settings.dev_auth_bypass and request.url.hostname in {"localhost", "127.0.0.1", "::1"}:
        return
    if not cookie or len(cookie) > 256:
        raise DomainError("UNAUTHENTICATED", 401, "Authentication required")
    with session_factory()() as session:
        valid = session.scalar(
            select(AccessSession).where(
                AccessSession.token_hash == token_hash(cookie),
                AccessSession.expires_at > func.now(),
            )
        )
    if valid is None:
        raise DomainError("UNAUTHENTICATED", 401, "Authentication required")


def check_origin(request: Request) -> None:
    settings = get_settings()
    origin = request.headers.get("origin")
    if origin != settings.public_origin:
        raise DomainError("ORIGIN_FORBIDDEN", 403, "Trusted origin required")
    if urlparse(origin).scheme not in {"http", "https"}:
        raise DomainError("ORIGIN_FORBIDDEN", 403, "Trusted origin required")


def create_session(access_code: str) -> str:
    configured = get_settings().access_code
    if configured is None or not secrets.compare_digest(
        access_code.encode(), configured.get_secret_value().encode()
    ):
        raise DomainError("UNAUTHENTICATED", 401, "Invalid access code")
    token = secrets.token_urlsafe(32)
    with session_factory().begin() as session:
        session.execute(delete(AccessSession).where(AccessSession.expires_at <= func.now()))
        session.add(
            AccessSession(
                token_hash=token_hash(token),
                expires_at=session.scalar(select(func.now())) + timedelta(hours=8),
            )
        )
    return token
