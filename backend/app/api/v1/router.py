from fastapi import APIRouter

from app.api.v1.endpoints import ai, auth, dashboard, matching, pre_registrations, profiles, resources, selection, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(profiles.router)
api_router.include_router(dashboard.router)
api_router.include_router(users.router)
api_router.include_router(pre_registrations.router)
api_router.include_router(matching.router)
api_router.include_router(selection.router)
api_router.include_router(selection.admin_router)
api_router.include_router(resources.router)
api_router.include_router(resources.mentor_router)
api_router.include_router(resources.admin_router)
api_router.include_router(ai.router)
api_router.include_router(ai.admin_router)
