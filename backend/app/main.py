import logging
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import Depends, FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.integrations.routes import router as integrations_router
from app.platform.access import (
    COOKIE_NAME,
    check_origin,
    create_session,
    require_access,
    token_hash,
)
from app.platform.contracts import Capabilities, ErrorEnvelope, Login, SessionInfo, Success
from app.platform.database import session_factory
from app.platform.errors import DomainError
from app.platform.logging import log, request_id
from app.platform.models import AccessSession
from app.platform.routes import router
from app.platform.settings import get_settings

ERROR_RESPONSES = {
    status: {"model": ErrorEnvelope} for status in [401, 403, 404, 409, 413, 422, 500, 502, 503]
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_settings()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="eGrant document assistant",
        version="1.0.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        responses=ERROR_RESPONSES,
    )

    @app.middleware("http")
    async def correlate(request: Request, call_next):
        correlation = str(uuid4())
        token = request_id.set(correlation)
        start = time.monotonic()
        try:
            if request.method not in {"GET", "HEAD", "OPTIONS"}:
                check_origin(request)
            response = await call_next(request)
        except DomainError as error:
            response = error_response(error)
        except Exception:
            log("request.failed", level=logging.ERROR, errorCode="INTERNAL_ERROR", exc_info=True)
            response = error_response(DomainError("INTERNAL_ERROR", 500, "Internal server error"))
        finally:
            log("request.completed", durationMs=round((time.monotonic() - start) * 1000))
            request_id.reset(token)
        response.headers["X-Request-ID"] = correlation
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.exception_handler(DomainError)
    async def handle_domain(request, error):
        return error_response(error)

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request, error):
        # Validation inputs can contain document contents or access codes.
        return error_response(DomainError("VALIDATION_ERROR", 422, "Invalid input"))

    @app.exception_handler(HTTPException)
    async def handle_http(request, error):
        return error_response(DomainError("HTTP_ERROR", error.status_code, "Request rejected"))

    @app.get("/health", response_model=Success[dict[str, str]])
    def health():
        return {"data": {"status": "ok"}}

    @app.post("/api/v1/auth/login", response_model=Success[SessionInfo])
    def login(body: Login, response: Response):
        token = create_session(body.access_code)
        response.set_cookie(
            COOKIE_NAME,
            token,
            max_age=8 * 3600,
            httponly=True,
            secure=get_settings().cookie_secure,
            samesite="strict",
            path="/api/v1",
        )
        return {"data": {"authenticated": True, "mode": get_settings().app_mode}}

    @app.delete("/api/v1/auth/session", status_code=204, dependencies=[Depends(require_access)])
    def logout(request: Request, response: Response):
        cookie = request.cookies.get(COOKIE_NAME)
        if cookie:
            with session_factory().begin() as session:
                record = session.get(AccessSession, token_hash(cookie))
                if record:
                    session.delete(record)
        response.delete_cookie(COOKIE_NAME, path="/api/v1")

    @app.get(
        "/api/v1/auth/session",
        response_model=Success[SessionInfo],
        dependencies=[Depends(require_access)],
    )
    def session_info():
        return {"data": {"authenticated": True, "mode": get_settings().app_mode}}

    @app.get(
        "/api/v1/capabilities",
        response_model=Success[Capabilities],
        dependencies=[Depends(require_access)],
    )
    def capabilities():
        # Keys alone do not constitute an implemented and verified adapter.
        return {
            "data": {
                "ocrConfigured": False,
                "aiConfigured": False,
                "egrantConfigured": False,
                "mode": get_settings().app_mode,
            }
        }

    app.include_router(router, prefix="/api/v1", dependencies=[Depends(require_access)])
    app.include_router(
        integrations_router, prefix="/api/v1", dependencies=[Depends(require_access)]
    )
    return app


def error_response(error: DomainError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status,
        content={"error": {"code": error.code, "message": error.message, "details": error.details}},
    )


app = create_app()
