from fastapi import APIRouter

from app.api.routes import admin, analytics, auth, evaluations, health, meta, suites, test_cases

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(suites.router)
api_router.include_router(test_cases.router)
api_router.include_router(evaluations.router)
api_router.include_router(analytics.router)
api_router.include_router(meta.router)
api_router.include_router(admin.router)

__all__ = ["api_router", "health"]