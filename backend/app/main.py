from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from app.services.request_security import rate_allowed, client_peer, begin_audit, finish_audit
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import DbSession
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.services.bootstrap import ensure_bootstrap_data

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_bootstrap_data()
    yield


app = FastAPI(
    title="AcademicNexus API / 智导未来 API",
    version=settings.app_version,
    description="Academic development and mentor-matching platform / AI 学术发展与导师匹配平台",
    lifespan=lifespan,
    docs_url="/docs" if settings.api_docs_enabled else None,
    redoc_url="/redoc" if settings.api_docs_enabled else None,
    openapi_url="/openapi.json" if settings.api_docs_enabled else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,
    # Keep direct API clients working as well as the same-origin Nginx proxy.
    # Profile editing and resource management use PUT and DELETE respectively.
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept-Language"],
    expose_headers=["Content-Disposition", "X-Pre-Registration-Count", "X-Subscription-Key-Count"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/api/v1/health", tags=["System / 系统"])
def health_check(db: DbSession) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Database unavailable") from None
    return {"status": "ok", "message": "AcademicNexus is ready / 智导未来服务已就绪"}


@app.middleware("http")
async def security_controls(request: Request, call_next):
    path = request.url.path
    limited = request.method == "POST" and (path in {"/api/v1/auth/login", "/api/v1/auth/activate", "/api/v1/admin/pre-registrations/reissue"} or path.endswith("/receipt") or (path.startswith("/api/v1/ai/conversations/") and path.endswith("/messages")))
    audited = request.method in {"POST", "PUT", "PATCH", "DELETE"} and (path.startswith("/api/v1/admin/") or path == "/api/v1/auth/me/contact")
    event_id = None
    try:
        peer = await run_in_threadpool(client_peer, request.client.host if request.client else "unknown", request.headers.get("x-real-ip", "")) if limited else ""
        rate_path = "/ai/messages" if path.startswith("/api/v1/ai/conversations/") and path.endswith("/messages") else "/activation-receipt" if path.endswith("/receipt") else path
        if limited and not await run_in_threadpool(rate_allowed, peer, rate_path):
            return JSONResponse({"detail": {"code": "rate_limit_exceeded"}}, status_code=429, headers={"Retry-After": "60"})
        if audited:
            token = request.headers.get("authorization", "").removeprefix("Bearer ")
            event_id = await run_in_threadpool(begin_audit, token, request.method, path)
    except SQLAlchemyError:
        return JSONResponse({"detail": "Security service unavailable"}, status_code=503)
    try:
        response = await call_next(request)
    except Exception:
        if event_id:
            await run_in_threadpool(finish_audit, event_id, 500)
        raise
    if event_id:
        await run_in_threadpool(finish_audit, event_id, response.status_code)
    return response
