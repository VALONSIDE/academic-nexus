from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/api/v1/health", tags=["System / 系统"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "message": "AcademicNexus is ready / 智导未来服务已就绪"}
