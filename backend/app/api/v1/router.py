from fastapi import APIRouter

from app.api.v1.assets import router as assets_router
from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.imports import router as imports_router
from app.api.v1.products import router as products_router
from app.api.v1.publications import router as publications_router
from app.api.v1.site_products import router as site_products_router
from app.api.v1.sites import router as sites_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(products_router)
api_router.include_router(assets_router)
api_router.include_router(imports_router)
api_router.include_router(sites_router)
api_router.include_router(site_products_router)
api_router.include_router(publications_router)

# Phase 5+ will add: suppliers, collection-jobs, ai/providers, ai/models,
# ai/task-policies, image-processing-jobs, reviews, jobs, team/members,
# audit-logs query endpoints.
